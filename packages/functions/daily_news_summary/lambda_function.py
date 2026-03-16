import calendar
import json
import os
import re
import random
import time
import boto3
import feedparser
import requests
import logging
from bs4 import BeautifulSoup
from botocore.exceptions import ClientError
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# AWS clients (initialised once at cold-start)
# ---------------------------------------------------------------------------

_REGION           = os.getenv('AWS_REGION', 'us-east-1')
ses_client        = boto3.client('ses',             region_name=_REGION)
comprehend_client = boto3.client('comprehend',      region_name=_REGION)
bedrock_client    = boto3.client('bedrock-runtime', region_name=_REGION)
dynamodb          = boto3.resource('dynamodb',      region_name=_REGION)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_COMPREHEND_BYTES         = 4900
BEDROCK_MODEL_ID             = os.getenv('BEDROCK_MODEL_ID', 'amazon.nova-lite-v1:0')
DYNAMODB_TABLE               = os.getenv('DYNAMODB_TABLE', '')
CLUSTER_SIMILARITY_THRESHOLD = 0.40
ARTICLE_AGE_DAYS             = 3   # skip RSS entries older than this
MAX_ARTICLES_PER_ORG         = 4
MAX_ARTICLES_TOTAL           = 35

VALID_CATEGORIES = {'World', 'Business', 'Technology', 'Health', 'Science', 'General'}
CATEGORY_ORDER   = ['World', 'Business', 'Technology', 'Health', 'Science', 'General']

# News sources and photo agencies that are references, not news subjects
ENTITY_ORG_BLOCKLIST: set = {
    'NPR', 'BBC', 'BBC News', 'BBC World Service', 'Reuters', 'AP',
    'Associated Press', 'The Associated Press', 'Getty Images', 'Getty',
    'TechCrunch', 'The Verge', 'Vox Media', 'Engadget', 'Digg',
    'The Guardian', 'Bloomberg', 'Forbes', 'CNBC', 'CNN', 'Fox News',
    'MSNBC', 'ABC News', 'CBS News', 'NBC News', 'Washington Post',
    'New York Times', 'Wall Street Journal', 'TIME', 'Axios',
    'YouTube', 'Twitter', 'Facebook', 'Instagram', 'TikTok',
    'Spotify', 'Apple Podcasts', 'Amazon Music',
    'EPA', 'Shutterstock', 'Corbis', 'ClassicStock',
}

# Known byline writers and bare job-title tokens to exclude from "Who's in the News"
PERSON_BLOCKLIST: set = {
    # Verge staff whose names appear on every article body
    "Terrence O'Brien", 'Cath Virginia', 'Ashley Carman', 'David Pierce',
    'Andrew Webster', 'Chris Cornell',
    # BBC staff
    'Yasmin Morgan-Griffiths', 'Jacqui Wakefield', 'Adrienne Murray',
    # Bare job titles extracted without an accompanying name
    'Chancellor', 'President', 'Prime Minister', 'Secretary', 'Director',
    'Minister', 'Governor', 'Senator', 'Speaker', 'Chief',
}

# Job-title tokens filtered at NER extraction time (lower-cased)
JOB_TITLE_TOKENS: set = {
    'chancellor', 'president', 'prime minister', 'secretary', 'director',
    'minister', 'governor', 'senator', 'speaker', 'chairman', 'chief',
    'commissioner', 'ambassador',
}

# Location abbreviation → canonical form
LOCATION_ALIASES: Dict[str, str] = {
    'U.S.': 'United States',
    'US':   'United States',
    'U.K.': 'United Kingdom',
    'UK':   'United Kingdom',
}

# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _truncate_to_bytes(text: str, max_bytes: int) -> str:
    """Truncate a string so its UTF-8 encoding fits within max_bytes."""
    encoded = text.encode('utf-8')
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode('utf-8', errors='ignore')


def _deduplicate_entities(entities: List[str]) -> List[str]:
    """Keep the longest form of overlapping entity names."""
    unique: List[str] = []
    for entity in sorted(entities, key=len, reverse=True):
        if not any(
            entity.lower() in u.lower() or u.lower() in entity.lower()
            for u in unique
            if len(min(entity, u, key=len)) >= 5
        ):
            unique.append(entity)
    return unique


def _invoke_bedrock(prompt: str, max_tokens: int = 200) -> str:
    """Invoke Amazon Bedrock Nova Lite and return the plain-text response."""
    body = json.dumps({
        "messages": [{"role": "user", "content": [{"text": prompt}]}],
        "inferenceConfig": {"maxTokens": max_tokens, "temperature": 0.2},
    })
    response = bedrock_client.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response['body'].read())
    return result['output']['message']['content'][0]['text'].strip()


def _is_real_person(name: str) -> bool:
    """Accept PERSON entities that are full names (2+ words or 6+ chars), reject bylines/titles."""
    if name in PERSON_BLOCKLIST:
        return False
    return len(name.split()) >= 2 or len(name) >= 6


def _is_real_org(name: str) -> bool:
    return name not in ENTITY_ORG_BLOCKLIST and len(name) >= 3


def _normalise_location(name: str) -> str:
    return LOCATION_ALIASES.get(name, name)


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class DailyNewsSummary:

    def __init__(self) -> None:
        rss_env = os.getenv('RSS_FEED_URLS', '')
        self.rss_feeds: List[str] = (
            [u.strip() for u in rss_env.split(',') if u.strip()]
            if rss_env else [
                'https://feeds.bbci.co.uk/news/rss.xml',
                'https://feeds.bbci.co.uk/news/world/rss.xml',
                'https://www.theguardian.com/world/rss',
                'https://www.npr.org/rss/rss.php?id=1001',
                'https://feeds.bbci.co.uk/news/business/rss.xml',
                'https://www.theguardian.com/business/rss',
                'https://feeds.reuters.com/reuters/businessNews',
                'https://techcrunch.com/feed/',
                'https://www.theverge.com/rss/index.xml',
                'https://feeds.bbci.co.uk/news/technology/rss.xml',
                'https://feeds.bbci.co.uk/news/science_and_environment/rss.xml',
                'https://www.npr.org/rss/rss.php?id=1007',
                'https://www.theguardian.com/science/rss',
            ]
        )

        recipients_env = os.getenv('EMAIL_RECIPIENTS', '')
        self.email_recipients: List[str] = (
            [e.strip() for e in recipients_env.split(',') if e.strip()]
            if recipients_env else []
        )
        self.sender_email   = os.getenv('SENDER_EMAIL', '')
        self.scraperapi_key = os.getenv('SCRAPERAPI_KEY', '')

        # Keyword fallback used only when Bedrock is unavailable
        self._fallback_keywords: Dict[str, List[str]] = {
            'World':      ['president', 'minister', 'parliament', 'election', 'war',
                           'troops', 'coup', 'diplomat', 'sanction', 'protest'],
            'Business':   ['business', 'economy', 'financial', 'market', 'stock',
                           'trade', 'commerce', 'finance'],
            'Technology': ['tech', 'technology', 'software', 'ai', 'digital',
                           'innovation', 'startup', 'silicon', 'robot'],
            'Health':     ['health', 'medical', 'covid', 'disease', 'hospital',
                           'medicine', 'treatment'],
            'Science':    ['science', 'research', 'study', 'discovery',
                           'scientific', 'lab', 'climate'],
        }

    # -----------------------------------------------------------------------
    # 1. RSS ingestion with source-diversity balancing
    # -----------------------------------------------------------------------

    @staticmethod
    def _org_name(source: str, url: str) -> str:
        s = source.lower()
        if 'bbc'        in s:                        return 'BBC'
        if 'guardian'   in s:                        return 'The Guardian'
        if 'npr'        in s or 'npr.org'    in url: return 'NPR'
        if 'reuters'    in s or 'reuters'    in url: return 'Reuters'
        if 'techcrunch' in s or 'techcrunch' in url: return 'TechCrunch'
        if 'verge'      in s or 'theverge'   in url: return 'The Verge'
        try:
            return urlparse(url).netloc.replace('www.', '').split('.')[0].capitalize()
        except Exception:
            return source

    def fetch_rss_feeds(self) -> List[Dict[str, Any]]:
        cutoff = datetime.utcnow() - timedelta(days=ARTICLE_AGE_DAYS)
        org_feeds: Dict[str, List] = {}

        for feed_url in self.rss_feeds:
            try:
                logger.info(f"Fetching RSS feed: {feed_url}")
                feed = feedparser.parse(feed_url)
                if feed.bozo and feed.bozo_exception:
                    logger.warning(f"Error parsing feed {feed_url}: {feed.bozo_exception}")
                    continue

                source = feed.feed.get('title', urlparse(feed_url).netloc)
                org    = self._org_name(source, feed_url)
                fresh  = []
                for entry in feed.entries:
                    parsed = entry.get('published_parsed') or entry.get('updated_parsed')
                    if parsed:
                        try:
                            if datetime.utcfromtimestamp(calendar.timegm(parsed)) < cutoff:
                                continue
                        except Exception:
                            pass
                    fresh.append({
                        'title':       entry.get('title', 'No Title'),
                        'url':         entry.get('link', ''),
                        'description': entry.get('description', ''),
                        'published':   entry.get('published', ''),
                        'source':      source,
                    })
                org_feeds.setdefault(org, []).extend(fresh)
                logger.info(f"  ✓ {len(fresh)} articles from {source}")
            except Exception as e:
                logger.error(f"Error fetching {feed_url}: {e}")

        # Balance: at least 1 from each org, up to MAX_ARTICLES_PER_ORG
        selected: List[Dict] = []
        logger.info(f"Balancing across {len(org_feeds)} organisations:")
        for org, arts in org_feeds.items():
            random.shuffle(arts)
            logger.info(f"  {org}: {len(arts)} available")

        for arts in org_feeds.values():
            selected.extend(arts[:1])

        for arts in org_feeds.values():
            if len(selected) >= MAX_ARTICLES_TOTAL:
                break
            selected.extend(arts[1:MAX_ARTICLES_PER_ORG])

        # Top up if still short
        if len(selected) < MAX_ARTICLES_TOTAL:
            for arts in org_feeds.values():
                if len(selected) >= MAX_ARTICLES_TOTAL:
                    break
                selected.extend(arts[MAX_ARTICLES_PER_ORG:])

        random.shuffle(selected)
        return selected[:MAX_ARTICLES_TOTAL]

    # -----------------------------------------------------------------------
    # 2. Full-article HTML fetcher
    # -----------------------------------------------------------------------

    _BOILERPLATE_PATTERNS = [
        (re.compile(r'^\d+\s+(hours?|minutes?|days?)\s+ago\s+Share\s+Save\s+', re.I), ''),
        (re.compile(r'\s+Share\s+Save\s+',                                      re.I), ' '),
        (re.compile(r'\b(Close|Follow|Subscribe)\s+(Posts?|Follow|See All\S*)', re.I), ''),
        (re.compile(r'your\s+(daily\s+email\s+digest|homepage\s+feed)',         re.I), ''),
        (re.compile(r'Follow\s+Follow\s+See\s+All',                             re.I), ''),
        (re.compile(r'Comments?\s+Sign\s+in\s+to\s+comment',                   re.I), ''),
    ]

    def fetch_full_article_text(self, url: str) -> str:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            if self.scraperapi_key:
                try:
                    r = requests.get(
                        'http://api.scraperapi.com',
                        params={'api_key': self.scraperapi_key, 'url': url},
                        timeout=30, headers=headers,
                    )
                    r.raise_for_status()
                    html = r.text
                except Exception:
                    r = requests.get(url, timeout=30, headers=headers)
                    r.raise_for_status()
                    html = r.text
            else:
                r = requests.get(url, timeout=30, headers=headers)
                r.raise_for_status()
                html = r.text

            soup = BeautifulSoup(html, 'html.parser')

            # Remove non-content elements
            for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form']):
                tag.decompose()
            for cls_pat in ['navigation', 'nav', 'menu', 'sidebar', 'widget',
                            'ad', 'advertisement', 'cookie', 'newsletter', 'popup',
                            'c-shorthand-credit', 'duet--layout--side-bar']:
                for tag in soup.find_all(class_=re.compile(cls_pat, re.I)):
                    tag.decompose()

            content = None
            for sel in ['article', '[role="main"]', '.article-content',
                        '.post-content', '.entry-content', 'main', '.content']:
                content = soup.select_one(sel)
                if content:
                    break
            if not content:
                content = soup.find('body')

            if content:
                text = content.get_text(separator=' ', strip=True)
                text = ' '.join(text.split())
                for pattern, replacement in self._BOILERPLATE_PATTERNS:
                    text = pattern.sub(replacement, text)
                return ' '.join(text.split())[:10000]
            return ''
        except Exception as e:
            logger.warning(f"Could not fetch {url}: {e}")
            return ''

    # -----------------------------------------------------------------------
    # 3. NLP — Extractive summariser (Bedrock fallback)
    # -----------------------------------------------------------------------

    def _extractive_summary(self, text: str, n: int = 3) -> str:
        if not text or len(text.strip()) < 50:
            return (text[:200] + '...') if len(text) > 200 else text
        clean = re.sub(r'\s+', ' ', text.strip())
        sentences = [
            s.strip() for s in re.split(r'(?<=[.!?])\s+', clean)
            if len(s.strip()) > 20
            and not any(p in s for p in ['Share Save', 'Getty Images', 'EPA/Shutterstock'])
        ]
        if len(sentences) <= n:
            return '. '.join(sentences) + '.'
        words     = re.findall(r'\b[a-zA-Z]{3,}\b', ' '.join(sentences).lower())
        freq      = Counter(words)
        max_freq  = max(freq.values()) if freq else 1
        scored    = []
        for i, s in enumerate(sentences):
            sw    = re.findall(r'\b[a-zA-Z]{3,}\b', s.lower())
            score = sum(freq.get(w, 0) / max_freq for w in sw)
            score *= (1.0 + 1.0 / (1.0 + i * 0.1))
            if 20 <= len(sw) <= 150:
                score *= 1.2
            scored.append((score, i, s))
        top = sorted(scored, reverse=True)[:n]
        top.sort(key=lambda x: x[1])
        result = '. '.join(s[2] for s in top)
        return result if result.endswith(('.', '!', '?')) else result + '.'

    # -----------------------------------------------------------------------
    # 4. NLP — Bedrock: abstractive summary + semantic categorisation
    # -----------------------------------------------------------------------

    def _analyze_with_bedrock(self, text: str) -> Dict[str, str]:
        """
        Single Bedrock call returning a 3-sentence summary and a category.

        Category rules (passed verbatim to the model):
          World      — politics, war, diplomacy, elections, government, crime, social issues
          Business   — economy, markets, trade, companies, finance
          Technology — software, hardware, AI, startups, gadgets, internet
          Health     — medical research, public health policy, disease outbreaks,
                       healthcare systems (NOT a political figure who happens to be ill)
          Science    — scientific research, environment, space, nature
          General    — everything else
        """
        if not text or len(text.strip()) < 50:
            return {
                'summary':  (text[:200] + '...') if len(text) > 200 else text,
                'category': 'General',
            }

        prompt = (
            "Analyze the following news article and respond with a JSON object only — no prose.\n\n"
            "Fields:\n"
            "- \"summary\": exactly 3 informative sentences in third person.\n"
            "- \"category\": one of [World, Business, Technology, Health, Science, General].\n"
            "  * Health = medical research, public health policy, disease outbreaks, or healthcare systems.\n"
            "    A political figure being hospitalised is World, not Health.\n"
            "  * World = politics, war, diplomacy, elections, government, crime, social issues.\n\n"
            f"Article:\n{text[:3000]}\n\n"
            "Respond with valid JSON only. Example: {\"summary\": \"...\", \"category\": \"World\"}"
        )
        try:
            raw = _invoke_bedrock(prompt, max_tokens=300)
            raw = re.sub(r'^```(?:json)?\s*', '', raw.strip(), flags=re.I)
            raw = re.sub(r'\s*```$',          '', raw.strip())
            parsed   = json.loads(raw)
            summary  = parsed.get('summary',  '').strip()
            category = parsed.get('category', 'General').strip()
            if category not in VALID_CATEGORIES:
                category = 'General'
            return {
                'summary':  summary or self._extractive_summary(text),
                'category': category,
            }
        except Exception as e:
            logger.warning(f"Bedrock analysis failed, using fallback: {e}")
            return {
                'summary':  self._extractive_summary(text),
                'category': self._keyword_category(text),
            }

    def _keyword_category(self, text: str) -> str:
        """Keyword fallback used only when Bedrock is unavailable."""
        t = text.lower()
        for cat, keywords in self._fallback_keywords.items():
            if any(k in t for k in keywords):
                return cat
        return 'General'

    # -----------------------------------------------------------------------
    # 5. NLP — Amazon Comprehend: sentiment, key phrases, NER
    # -----------------------------------------------------------------------

    def _detect_sentiment(self, text: str) -> Tuple[str, Dict]:
        """
        Journalism-aware sentiment: treat Comprehend's dominant label as a
        probability distribution and apply explicit thresholds to avoid
        over-labelling neutrally-written negative-event coverage as NEUTRAL.
        """
        try:
            resp   = comprehend_client.detect_sentiment(
                Text=_truncate_to_bytes(text, MAX_COMPREHEND_BYTES), LanguageCode='en'
            )
            scores = resp['SentimentScore']
            if   scores['Negative'] >= 0.20: sentiment = 'NEGATIVE'
            elif scores['Positive'] >= 0.20: sentiment = 'POSITIVE'
            elif scores['Mixed']    >= 0.30: sentiment = 'MIXED'
            else:                            sentiment = 'NEUTRAL'
            return sentiment, scores
        except Exception as e:
            logger.warning(f"Comprehend sentiment error: {e}")
            return 'NEUTRAL', {}

    # Key-phrase noise signals — any phrase containing one of these is dropped
    _KP_NOISE = [
        'close', 'posts', 'this topic', 'daily email', 'homepage feed',
        'follow follow', 'see all', 'sign in', 'load more', 'cookie',
        'newsletter', 'subscribe', 'advertisement', 'getty images',
        'listen & follow', 'apple podcasts', 'spotify', 'amazon music',
        'podcasts tech', 'column gaming', 'column tech', 'tech reviews',
        'ai openai', 'gadgets streaming', 'gadgets close', 'policy close',
        'business close', 'news close', 'science close', 'entertainment column',
        'column music', 'column close', 'policy business', 'policy posts',
        'podcasts close', 'reviews close',
        'bbc/', 'epa/', '/getty', 'alamy', 'reuters/',
        'listen & follow npr', 'science listen',
    ]

    # Strip leading source/section labels from key phrases
    _KP_PREFIX = re.compile(
        r'^(BBC|NPR|Reuters|AP|Guardian|TechCrunch|The\s+Verge|Engadget|'
        r'Business|Technology|Science|Health|World|News|Tech|Policy|Column|'
        r'Podcasts|Reviews|Gaming|Entertainment)\s+',
        re.IGNORECASE,
    )

    def _detect_key_phrases(self, text: str) -> List[str]:
        try:
            resp    = comprehend_client.detect_key_phrases(
                Text=_truncate_to_bytes(text, MAX_COMPREHEND_BYTES), LanguageCode='en'
            )
            phrases = []
            for p in resp.get('KeyPhrases', []):
                phrase = p['Text']
                if any(n in phrase.lower() for n in self._KP_NOISE):
                    continue
                if len(phrase) > 80:
                    continue
                phrase = self._KP_PREFIX.sub('', phrase).strip()
                if len(phrase) >= 3:
                    phrases.append(phrase)
                if len(phrases) == 10:
                    break
            return phrases
        except Exception as e:
            logger.warning(f"Comprehend key phrases error: {e}")
            return []

    def _detect_named_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract PERSON, ORGANIZATION, LOCATION, and EVENT entities via Comprehend.
        Confidence threshold: 85 %. Drops bare job-title tokens and media-org names.
        """
        result: Dict[str, List[str]] = {
            'PERSON': [], 'ORGANIZATION': [], 'LOCATION': [], 'EVENT': []
        }
        if not text or len(text.strip()) < 20:
            return result
        try:
            resp = comprehend_client.detect_entities(
                Text=_truncate_to_bytes(text, MAX_COMPREHEND_BYTES), LanguageCode='en'
            )
            raw: Dict[str, List[str]] = defaultdict(list)
            for ent in resp.get('Entities', []):
                etype = ent.get('Type', '')
                score = ent.get('Score', 0)
                value = ent.get('Text', '').strip()
                if etype not in result or score < 0.85 or len(value) < 3:
                    continue
                if etype == 'PERSON' and value.lower() in JOB_TITLE_TOKENS:
                    continue
                if etype == 'ORGANIZATION' and value in ENTITY_ORG_BLOCKLIST:
                    continue
                raw[etype].append(value)
            for etype in result:
                result[etype] = _deduplicate_entities(raw[etype])
        except ClientError as e:
            logger.warning(f"Comprehend NER error: {e}")
        except Exception as e:
            logger.warning(f"NER unexpected error: {e}")
        return result

    # -----------------------------------------------------------------------
    # 6. NLP — Full per-article analysis
    # -----------------------------------------------------------------------

    def _analyze_article(self, text: str) -> Dict[str, Any]:
        if not text or len(text.strip()) < 10:
            return {
                'summary':          'Content too short to analyze.',
                'category':         'General',
                'sentiment':        'NEUTRAL',
                'sentiment_scores': {},
                'key_phrases':      [],
                'key_phrases_raw':  [],
                'entities':         {'PERSON': [], 'ORGANIZATION': [], 'LOCATION': [], 'EVENT': []},
            }
        sentiment, scores = self._detect_sentiment(text)
        key_phrases       = self._detect_key_phrases(text)
        entities          = self._detect_named_entities(text)
        bedrock           = self._analyze_with_bedrock(text)
        return {
            'summary':          bedrock['summary'],
            'category':         bedrock['category'],
            'sentiment':        sentiment,
            'sentiment_scores': scores,
            'key_phrases':      key_phrases[:5],
            'key_phrases_raw':  key_phrases,
            'entities':         entities,
        }

    # -----------------------------------------------------------------------
    # 7. NLP — Multi-source story clustering (Jaccard similarity)
    # -----------------------------------------------------------------------

    def _cluster_articles(self, articles: List[Dict]) -> List[Dict]:
        """
        Union-Find style clustering: two articles from different sources are
        joined if their Jaccard similarity (key-phrase words) or title-word
        overlap exceeds CLUSTER_SIMILARITY_THRESHOLD.
        """
        n       = len(articles)
        cluster = list(range(n))

        def word_set(t: str) -> set:
            return {w.lower() for w in re.findall(r'\b[a-zA-Z]{4,}\b', t)}

        def jaccard(a: set, b: set) -> float:
            return len(a & b) / len(a | b) if a and b else 0.0

        def title_overlap(t1: str, t2: str) -> float:
            w1, w2 = word_set(t1), word_set(t2)
            return len(w1 & w2) / min(len(w1), len(w2)) if w1 and w2 else 0.0

        for i in range(n):
            for j in range(i + 1, n):
                if articles[i].get('source') == articles[j].get('source'):
                    continue
                kp_i = word_set(' '.join(articles[i].get('key_phrases_raw', [])))
                kp_j = word_set(' '.join(articles[j].get('key_phrases_raw', [])))
                sim  = max(jaccard(kp_i, kp_j),
                           title_overlap(articles[i]['title'], articles[j]['title']) * 0.8)
                if sim >= CLUSTER_SIMILARITY_THRESHOLD:
                    old_c = cluster[j]
                    new_c = cluster[i]
                    cluster = [new_c if c == old_c else c for c in cluster]

        members: Dict[int, List[int]] = defaultdict(list)
        for idx, cid in enumerate(cluster):
            members[cid].append(idx)

        for idx, art in enumerate(articles):
            cid = cluster[idx]
            if len(members[cid]) > 1:
                art['cluster_id']      = cid
                art['also_covered_by'] = [
                    articles[j]['source'] for j in members[cid] if j != idx
                ]
            else:
                art['cluster_id']      = None
                art['also_covered_by'] = []
        return articles

    # -----------------------------------------------------------------------
    # 8. NLP — Cross-source framing comparison (Bedrock)
    # -----------------------------------------------------------------------

    def _framing_comparison(self, cluster: List[Dict]) -> str:
        """Ask Bedrock to describe how different outlets frame the same story."""
        if len(cluster) < 2:
            return ''
        parts  = [f"**{a['source']}**: {a['summary'][:300]}" for a in cluster[:3]]
        prompt = (
            "The following are summaries of the SAME news story from different outlets.\n"
            "In ONE concise sentence, explain how their framing or emphasis differs. Be specific.\n\n"
            + "\n\n".join(parts)
            + "\n\nFraming comparison:"
        )
        try:
            return _invoke_bedrock(prompt, max_tokens=120)
        except Exception as e:
            logger.warning(f"Bedrock framing comparison failed: {e}")
            return ''

    # -----------------------------------------------------------------------
    # 9. Trend tracking — DynamoDB
    # -----------------------------------------------------------------------

    def _track_entity_trends(self, entities: Dict[str, Dict]) -> None:
        """
        Upsert today's entity mention counts into DynamoDB.
        Schema: PK=entity (S), SK=date (S), count (N), entity_type (S), expires_at (TTL).
        """
        if not DYNAMODB_TABLE:
            return
        today      = datetime.utcnow().strftime('%Y-%m-%d')
        expires_at = int((datetime.utcnow() + timedelta(days=30)).timestamp())
        table      = dynamodb.Table(DYNAMODB_TABLE)
        for name, data in entities.items():
            try:
                table.update_item(
                    Key={'entity': name, 'date': today},
                    UpdateExpression=(
                        'SET entity_type = :t, '
                        '#cnt = if_not_exists(#cnt, :zero) + :inc, '
                        'expires_at = :exp'
                    ),
                    ExpressionAttributeNames={'#cnt': 'count'},
                    ExpressionAttributeValues={
                        ':t':    data['type'],
                        ':inc':  data['count'],
                        ':zero': 0,
                        ':exp':  expires_at,
                    },
                )
            except Exception as e:
                logger.warning(f"DynamoDB write failed for '{name}': {e}")

    def _get_trending_entities(self, days: int = 7) -> List[Dict]:
        """Return the top 10 entities by mention count over the last N days."""
        if not DYNAMODB_TABLE:
            return []
        cutoff = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
        try:
            table    = dynamodb.Table(DYNAMODB_TABLE)
            response = table.scan(
                FilterExpression='#d >= :cutoff',
                ExpressionAttributeNames={'#d': 'date'},
                ExpressionAttributeValues={':cutoff': cutoff},
            )
            aggregated: Dict[str, Dict] = defaultdict(lambda: {'count': 0, 'type': ''})
            for item in response.get('Items', []):
                name = item['entity']
                aggregated[name]['count'] += int(item.get('count', 0))
                aggregated[name]['type']   = item.get('entity_type', 'OTHER')
            trending = [
                {'entity': k, 'count': v['count'], 'type': v['type']}
                for k, v in aggregated.items()
            ]
            trending.sort(key=lambda x: x['count'], reverse=True)
            return trending[:10]
        except Exception as e:
            logger.warning(f"DynamoDB trending query failed: {e}")
            return []

    # -----------------------------------------------------------------------
    # 10. Article processing pipeline
    # -----------------------------------------------------------------------

    def _process_articles(
        self, articles: List[Dict[str, Any]]
    ) -> Tuple[Dict, Dict, List]:
        """
        Run the full NLP pipeline on every article.
        Returns:
          articles_by_category  Dict[str, List[processed_article]]
          all_entities_today    Dict[entity_name, {count, type}]
          all_processed         flat list (used for clustering)
        """
        by_category: Dict[str, List]   = {}
        all_entities: Dict[str, Dict]  = defaultdict(lambda: {'count': 0, 'type': ''})
        all_processed: List[Dict]      = []

        for article in articles:
            try:
                logger.info(f"Processing: {article['title'][:60]}...")
                raw_text = self.fetch_full_article_text(article['url'])
                text     = raw_text or article.get('description', '')
                analysis = self._analyze_article(text)
                category = analysis['category'] or self._keyword_category(
                    article.get('title', '') + ' ' + article.get('description', '')
                )

                processed = {
                    'title':            article['title'],
                    'url':              article['url'],
                    'source':           article['source'],
                    'published':        article.get('published', ''),
                    'summary':          analysis['summary'],
                    'sentiment':        analysis['sentiment'],
                    'sentiment_scores': analysis['sentiment_scores'],
                    'key_phrases':      ', '.join(analysis['key_phrases']) or 'N/A',
                    'key_phrases_raw':  analysis['key_phrases_raw'],
                    'entities':         analysis['entities'],
                    'also_covered_by':  [],
                    'cluster_id':       None,
                }

                for etype, ents in analysis['entities'].items():
                    for ent in ents:
                        all_entities[ent]['count'] += 1
                        all_entities[ent]['type']   = etype

                by_category.setdefault(category, []).append(processed)
                all_processed.append(processed)
                time.sleep(0.3)

            except Exception as e:
                logger.error(f"Error processing '{article.get('title', 'Unknown')}': {e}")

        return by_category, dict(all_entities), all_processed

    # -----------------------------------------------------------------------
    # 11. Email generation
    # -----------------------------------------------------------------------

    def _build_entity_sections(
        self, all_entities: Dict[str, Dict]
    ) -> Tuple[str, str, List, List, Dict[str, int]]:
        """Compute filtered/normalised entity lists for the email header sections."""
        # Normalise location aliases and merge counts
        norm_locs: Dict[str, int] = defaultdict(int)
        for e, d in all_entities.items():
            if d['type'] == 'LOCATION':
                norm_locs[_normalise_location(e)] += d['count']
        # Drop entries that are substrings of longer canonical forms
        final_locs = {
            k: v for k, v in norm_locs.items()
            if not any(k != k2 and k in k2 for k2 in norm_locs)
        }

        people = sorted(
            [e for e, d in all_entities.items() if d['type'] == 'PERSON' and _is_real_person(e)],
            key=lambda e: all_entities[e]['count'], reverse=True,
        )[:7]
        orgs = sorted(
            [e for e, d in all_entities.items() if d['type'] == 'ORGANIZATION' and _is_real_org(e)],
            key=lambda e: all_entities[e]['count'], reverse=True,
        )[:5]
        locs = sorted(final_locs, key=final_locs.get, reverse=True)[:5]

        html = ''
        text = ''
        if people or orgs or locs:
            html += '<div class="section"><h2>👤 Who\'s in the News Today</h2>\n'
            if people:
                html += '<div style="margin-bottom:8px">'
                for p in people:
                    html += f'<span class="chip person">🧑 {p} ({all_entities[p]["count"]})</span>'
                html += '</div>\n'
            if orgs:
                html += '<div style="margin-bottom:8px">'
                for o in orgs:
                    html += f'<span class="chip org">🏢 {o} ({all_entities[o]["count"]})</span>'
                html += '</div>\n'
            if locs:
                html += '<div>'
                for l in locs:
                    cnt = final_locs.get(l, all_entities.get(l, {}).get('count', 0))
                    html += f'<span class="chip loc">📍 {l} ({cnt})</span>'
                html += '</div>\n'
            html += '</div>\n'

            text += "WHO'S IN THE NEWS TODAY\n"
            if people: text += "  People:        " + ', '.join(people) + '\n'
            if orgs:   text += "  Organizations: " + ', '.join(orgs)   + '\n'
            if locs:   text += "  Locations:     " + ', '.join(locs)   + '\n'
            text += '\n'

        return html, text, people, orgs, final_locs

    def _build_trending_section(self, trending: List[Dict]) -> Tuple[str, str]:
        """Build the 'Trending This Week' HTML and text blocks."""
        clean = [
            t for t in trending
            if not (t['type'] == 'ORGANIZATION' and t['entity'] in ENTITY_ORG_BLOCKLIST)
            and not (t['type'] == 'PERSON'       and not _is_real_person(t['entity']))
        ]
        if not clean:
            return '', ''
        max_count = clean[0]['count'] or 1
        icons     = {'PERSON': '🧑', 'ORGANIZATION': '🏢', 'LOCATION': '📍'}
        html      = '<div class="section"><h2>📈 Trending This Week</h2>\n'
        txt       = "TRENDING THIS WEEK\n"
        for item in clean[:8]:
            bar   = max(4, int(160 * item['count'] / max_count))
            icon  = icons.get(item['type'], '•')
            html += (
                f'<div class="trend-item">'
                f'<span style="min-width:180px">{icon} {item["entity"]}</span>'
                f'<div class="trend-bar" style="width:{bar}px"></div>'
                f'<span class="trend-label">{item["count"]} mentions</span>'
                f'</div>\n'
            )
            txt += f"  {item['entity']} — {item['count']} mentions\n"
        html += '</div>\n'
        txt  += '\n'
        return html, txt

    def _build_article_card(self, art: Dict) -> Tuple[str, str]:
        """Render a single article as an HTML card and plain-text block."""
        sentiment = art['sentiment']
        multi_badge = multi_text = ''
        if art.get('also_covered_by'):
            srcs        = ', '.join(art['also_covered_by'][:2])
            multi_badge = f'<span class="multi">+ {srcs}</span>'
            multi_text  = f" [Also: {srcs}]"

        ent_html = ''
        css_map  = {'PERSON': 'person', 'ORGANIZATION': 'org', 'LOCATION': 'loc'}
        for etype, ents in art.get('entities', {}).items():
            for e in ents[:3]:
                css = css_map.get(etype, 'person')
                ent_html += f'<span class="chip {css}" style="font-size:11px">{e}</span>'

        html = (
            f'<div class="article">\n'
            f'  <div class="art-title">'
            f'<a href="{art["url"]}">{art["title"]}</a>'
            f'<span class="sentiment {sentiment}">{sentiment}</span>'
            f'{multi_badge}</div>\n'
            f'  <div class="art-meta">Source: {art["source"]} | Published: {art["published"] or "N/A"}</div>\n'
            f'  <div class="art-summary">{art["summary"]}</div>\n'
            f'  <div class="art-entities">{ent_html}</div>\n'
            f'  <div class="art-kp">Key phrases: {art["key_phrases"]}</div>\n'
            f'</div>\n'
        )
        all_ents = ', '.join(e for ents in art.get('entities', {}).values() for e in ents[:2])
        txt = (
            f"• {art['title']} [{sentiment}]{multi_text}\n"
            f"  Source: {art['source']}\n"
            f"  {art['summary']}\n"
            f"  Entities: {all_ents}\n"
            f"  Read more: {art['url']}\n\n"
        )
        return html, txt

    def _generate_email_content(
        self,
        articles_by_category: Dict[str, List],
        all_entities:          Dict[str, Dict],
        trending:              List[Dict],
        framing_note:          str,
    ) -> Tuple[str, str]:
        date_str = datetime.utcnow().strftime('%B %d, %Y')
        total    = sum(len(v) for v in articles_by_category.values())

        # ---- HTML shell ----
        html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8">
<style>
  body        {{ font-family: Georgia, serif; line-height: 1.7; color: #222; max-width: 820px; margin: 0 auto; padding: 20px; background: #fafafa; }}
  a           {{ color: #1a0dab; }}
  .header     {{ background: linear-gradient(135deg,#1a1a2e 0%,#16213e 60%,#0f3460 100%); color: white; padding: 36px 30px; border-radius: 12px; margin-bottom: 28px; }}
  .header h1  {{ margin: 0 0 6px 0; font-size: 26px; letter-spacing: .5px; }}
  .header p   {{ margin: 4px 0 0 0; opacity: .8; font-size: 14px; }}
  .section    {{ background: white; border-radius: 10px; padding: 20px 24px; margin-bottom: 22px; box-shadow: 0 1px 4px rgba(0,0,0,.07); }}
  .section h2 {{ margin: 0 0 14px 0; font-size: 17px; color: #0f3460; border-bottom: 2px solid #e8e8e8; padding-bottom: 8px; }}
  .chip       {{ display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 12px; margin: 3px; font-family: Arial,sans-serif; }}
  .chip.person{{ background: #e8f4fd; color: #1a5276; border: 1px solid #aed6f1; }}
  .chip.org   {{ background: #eafaf1; color: #1e8449; border: 1px solid #a9dfbf; }}
  .chip.loc   {{ background: #fef9e7; color: #9a7d0a; border: 1px solid #f9e79f; }}
  .trend-item {{ display: flex; align-items: center; margin: 5px 0; font-size: 13px; font-family: Arial,sans-serif; }}
  .trend-bar  {{ height: 10px; border-radius: 5px; margin: 0 10px; background: #0f3460; min-width: 4px; }}
  .trend-label{{ color: #555; font-size: 12px; }}
  .comparison {{ background: #f0f4ff; border-left: 4px solid #0f3460; padding: 10px 14px; border-radius: 0 6px 6px 0; font-size: 13px; color: #333; margin-bottom: 16px; font-style: italic; }}
  .category   {{ margin: 28px 0 0 0; }}
  .cat-title  {{ font-size: 19px; font-weight: bold; color: #0f3460; border-bottom: 2px solid #0f3460; padding-bottom: 6px; margin-bottom: 16px; }}
  .article    {{ padding: 16px; margin: 12px 0; border-radius: 8px; border-left: 4px solid #ddd; background: #fdfdfd; }}
  .art-title  {{ font-size: 16px; font-weight: bold; margin-bottom: 6px; }}
  .art-meta   {{ color: #777; font-size: 12px; font-family: Arial,sans-serif; margin-bottom: 8px; }}
  .art-summary{{ font-size: 14px; color: #333; margin: 8px 0; }}
  .art-entities{{ margin-top: 8px; }}
  .art-kp     {{ font-size: 12px; color: #888; margin-top: 6px; font-family: Arial,sans-serif; }}
  .multi      {{ font-size: 11px; font-family: Arial,sans-serif; color: white; background: #0f3460; padding: 2px 8px; border-radius: 10px; margin-left: 6px; }}
  .sentiment  {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: bold; font-family: Arial,sans-serif; margin-left: 6px; }}
  .POSITIVE   {{ background: #27ae60; color: white; }}
  .NEGATIVE   {{ background: #e74c3c; color: white; }}
  .NEUTRAL    {{ background: #95a5a6; color: white; }}
  .MIXED      {{ background: #e67e22; color: white; }}
  .footer     {{ text-align: center; color: #aaa; font-size: 12px; margin-top: 30px; padding-top: 16px; border-top: 1px solid #eee; font-family: Arial,sans-serif; }}
</style>
</head>
<body>
<div class="header">
  <h1>📰 World Brief — Daily News Summary</h1>
  <p>{date_str} &nbsp;|&nbsp; {total} articles &nbsp;|&nbsp; NLP: Comprehend NER + Bedrock Summaries + Story Clustering</p>
</div>
"""
        txt = f"WORLD BRIEF — Daily News Summary\n{date_str}\n{'='*60}\n\n"

        # Entity sections
        ent_html, ent_txt, _, _, _ = self._build_entity_sections(all_entities)
        html += ent_html
        txt  += ent_txt

        # Trending section
        tr_html, tr_txt = self._build_trending_section(trending)
        html += tr_html
        txt  += tr_txt

        # Framing comparison
        if framing_note:
            html += f'<div class="comparison">🔍 <strong>Multi-source story:</strong> {framing_note}</div>\n'
            txt  += f"MULTI-SOURCE FRAMING\n  {framing_note}\n\n"

        # Articles by category
        sorted_cats = sorted(
            articles_by_category.items(),
            key=lambda x: (CATEGORY_ORDER.index(x[0]) if x[0] in CATEGORY_ORDER else 999, x[0]),
        )
        for cat, arts in sorted_cats:
            html += f'<div class="category"><div class="cat-title">{cat}</div>\n'
            txt  += f"{cat}\n{'-'*len(cat)}\n\n"
            for art in arts[:5]:
                card_html, card_txt = self._build_article_card(art)
                html += card_html
                txt  += card_txt
            html += '</div>\n'

        html += (
            '<div class="footer"><p>World Brief — automated daily digest powered by '
            'Amazon Comprehend NER, Amazon Bedrock (Nova Lite), and multi-source story clustering.'
            '</p></div>\n</body>\n</html>'
        )
        txt += '='*60 + '\nWorld Brief — automated daily digest\n'
        return html, txt

    # -----------------------------------------------------------------------
    # 12. Email delivery via SES
    # -----------------------------------------------------------------------

    def _send_email(self, html: str, text: str) -> bool:
        if not self.email_recipients:
            logger.warning("No email recipients configured")
            return False
        if not self.sender_email:
            logger.warning("No sender email configured")
            return False
        try:
            msg            = MIMEMultipart('alternative')
            msg['Subject'] = f"World Brief — {datetime.utcnow().strftime('%B %d, %Y')}"
            msg['From']    = self.sender_email
            msg['To']      = ', '.join(self.email_recipients)
            msg.attach(MIMEText(text, 'plain'))
            msg.attach(MIMEText(html,  'html'))
            resp = ses_client.send_raw_email(
                Source=self.sender_email,
                Destinations=self.email_recipients,
                RawMessage={'Data': msg.as_string()},
            )
            logger.info(f"Email sent. Message ID: {resp['MessageId']}")
            return True
        except ClientError as e:
            logger.error(f"SES error: {e.response['Error']['Code']} — {e}")
            return False
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return False

    # -----------------------------------------------------------------------
    # 13. Main orchestrator
    # -----------------------------------------------------------------------

    def generate_summary(self) -> Dict[str, Any]:
        logger.info(f"Starting daily news summary ({len(self.rss_feeds)} feeds)")

        # Step 1 — fetch and balance RSS
        articles = self.fetch_rss_feeds()
        if not articles:
            return {'statusCode': 200, 'body': json.dumps({'message': 'No articles found'})}
        sources = Counter(a['source'] for a in articles)
        logger.info(f"✓ {len(articles)} articles from {len(sources)} sources")
        for src, cnt in sources.most_common():
            logger.info(f"  {src}: {cnt}")

        # Step 2 — NLP pipeline (Comprehend + Bedrock per article)
        by_category, all_entities, all_processed = self._process_articles(articles)
        logger.info(f"Processed {len(all_processed)} articles → {len(by_category)} categories")
        logger.info(f"Extracted {len(all_entities)} unique entities")

        # Step 3 — multi-source clustering
        all_processed = self._cluster_articles(all_processed)
        cluster_sizes = Counter(
            a['cluster_id'] for a in all_processed if a['cluster_id'] is not None
        )
        if cluster_sizes:
            logger.info(f"Found {len(cluster_sizes)} multi-source clusters")

        # Step 4 — cross-source framing comparison for the largest cluster
        framing_note = ''
        if cluster_sizes:
            top_cid   = cluster_sizes.most_common(1)[0][0]
            top_group = [a for a in all_processed if a['cluster_id'] == top_cid]
            if len(top_group) >= 2:
                logger.info(f"Generating framing comparison ({len(top_group)} sources)")
                framing_note = self._framing_comparison(top_group)

        # Step 5 — entity trend tracking (DynamoDB)
        self._track_entity_trends(all_entities)
        trending = self._get_trending_entities(days=7)
        logger.info(f"Loaded {len(trending)} trending entities (last 7 days)")

        # Step 6 — generate and send email
        html, text = self._generate_email_content(
            by_category, all_entities, trending, framing_note
        )
        sent = self._send_email(html, text)

        total = sum(len(v) for v in by_category.values())
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message':            'Daily news summary generated successfully',
                'articles_processed':  total,
                'categories':          list(by_category.keys()),
                'entities_extracted':  len(all_entities),
                'clusters_found':      len(cluster_sizes),
                'email_sent':          sent,
                'timestamp':           datetime.utcnow().isoformat(),
            }),
        }


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        return DailyNewsSummary().generate_summary()
    except Exception as e:
        logger.error(f"Lambda execution error: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error', 'message': str(e)}),
        }
