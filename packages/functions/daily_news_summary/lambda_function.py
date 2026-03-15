import json
import os
import boto3
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from urllib.parse import urljoin, urlparse
import feedparser
import requests
from bs4 import BeautifulSoup
from botocore.exceptions import ClientError
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
from collections import Counter
import random

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
ses_client = boto3.client('ses', region_name=os.getenv('AWS_REGION', 'us-east-1'))
comprehend_client = boto3.client('comprehend', region_name=os.getenv('AWS_REGION', 'us-east-1'))

# Maximum article text length for Comprehend (free tier supports up to 5000 chars per document)
MAX_COMPREHEND_TEXT_LENGTH = 5000


class DailyNewsSummary:
    """Daily Global News Summary Generator"""
    
    def __init__(self):
        # Get RSS feed URLs from environment variable (comma-separated)
        rss_feeds_env = os.getenv('RSS_FEED_URLS', '')
        if rss_feeds_env:
            self.rss_feeds = [url.strip() for url in rss_feeds_env.split(',') if url.strip()]
        else:
            # Default multi-source feeds - diverse global news sources
            self.rss_feeds = [
                # International News
                'https://feeds.bbci.co.uk/news/rss.xml',  # BBC World News
                'https://feeds.bbci.co.uk/news/world/rss.xml',  # BBC World
                'https://www.theguardian.com/world/rss',  # The Guardian World
                'https://www.npr.org/rss/rss.php?id=1001',  # NPR World News
                'https://feeds.bbci.co.uk/news/uk/rss.xml',  # BBC UK (additional perspective)
                
                # Business & Finance
                'https://feeds.bbci.co.uk/news/business/rss.xml',  # BBC Business
                'https://www.theguardian.com/business/rss',  # The Guardian Business
                'https://feeds.reuters.com/reuters/businessNews',  # Reuters Business (alternative)
                
                # Technology
                'https://techcrunch.com/feed/',  # TechCrunch
                'https://www.theverge.com/rss/index.xml',  # The Verge
                'https://feeds.bbci.co.uk/news/technology/rss.xml',  # BBC Technology
                
                # Science & Health
                'https://feeds.bbci.co.uk/news/science_and_environment/rss.xml',  # BBC Science
                'https://www.npr.org/rss/rss.php?id=1007',  # NPR Science
                'https://www.theguardian.com/science/rss',  # The Guardian Science
            ]
        
        # Get email recipients (comma-separated)
        recipients_env = os.getenv('EMAIL_RECIPIENTS', '')
        self.email_recipients = [email.strip() for email in recipients_env.split(',') if email.strip()] if recipients_env else []
        
        # Get sender email
        self.sender_email = os.getenv('SENDER_EMAIL', '')
        
        # Optional: ScraperAPI key for better article extraction
        self.scraperapi_key = os.getenv('SCRAPERAPI_KEY', '')
        
        # Category mapping for organizing articles
        self.category_keywords = {
            'World': ['world', 'international', 'global', 'politics', 'diplomatic', 'un', 'nation'],
            'Business': ['business', 'economy', 'financial', 'market', 'stock', 'trade', 'commerce', 'finance'],
            'Technology': ['tech', 'technology', 'software', 'ai', 'digital', 'innovation', 'startup', 'silicon'],
            'Health': ['health', 'medical', 'covid', 'disease', 'hospital', 'medicine', 'treatment'],
            'Science': ['science', 'research', 'study', 'discovery', 'scientific', 'lab']
        }
    
    def fetch_rss_feeds(self) -> List[Dict[str, Any]]:
        """Fetch and parse RSS feeds"""
        all_articles = []
        feeds_data = []  # Track articles by feed URL (not source name) for balanced selection
        
        # First pass: fetch articles from all feeds
        for feed_url in self.rss_feeds:
            try:
                logger.info(f"Fetching RSS feed: {feed_url}")
                feed = feedparser.parse(feed_url)
                
                if feed.bozo and feed.bozo_exception:
                    logger.warning(f"Error parsing feed {feed_url}: {feed.bozo_exception}")
                    continue
                
                # Get articles from this feed
                articles_from_feed = []
                source_name = feed.feed.get('title', urlparse(feed_url).netloc)
                
                for entry in feed.entries:
                    article = {
                        'title': entry.get('title', 'No Title'),
                        'url': entry.get('link', ''),
                        'description': entry.get('description', ''),
                        'published': entry.get('published', ''),
                        'source': source_name,
                        'feed_url': feed_url
                    }
                    articles_from_feed.append(article)
                
                # Store by feed URL to ensure diversity across feeds (not just source names)
                feeds_data.append({
                    'url': feed_url,
                    'source': source_name,
                    'articles': articles_from_feed
                })
                
                logger.info(f"✓ Fetched {len(articles_from_feed)} articles from {source_name}")
                
            except Exception as e:
                logger.error(f"Error fetching feed {feed_url}: {str(e)}")
                continue
        
        # Second pass: Balance selection to ensure diversity
        # Strategy: Group by organization (extract domain/org name) and balance across orgs
        
        # Extract organization names from sources
        def get_org_name(source_name, feed_url):
            """Extract organization name from source or URL"""
            source_lower = source_name.lower()
            if 'bbc' in source_lower:
                return 'BBC'
            elif 'guardian' in source_lower:
                return 'The Guardian'
            elif 'npr' in source_lower or 'npr.org' in feed_url:
                return 'NPR'
            elif 'reuters' in source_lower or 'reuters' in feed_url:
                return 'Reuters'
            elif 'techcrunch' in source_lower or 'techcrunch' in feed_url:
                return 'TechCrunch'
            elif 'verge' in source_lower or 'theverge' in feed_url:
                return 'The Verge'
            else:
                # Extract domain as org name
                try:
                    domain = urlparse(feed_url).netloc
                    # Remove www. and extract main domain
                    domain = domain.replace('www.', '').split('.')[0]
                    return domain.capitalize()
                except:
                    return source_name
        
        # Group feeds by organization
        org_feeds = {}
        for feed_info in feeds_data:
            org = get_org_name(feed_info['source'], feed_info['url'])
            if org not in org_feeds:
                org_feeds[org] = []
            org_feeds[org].extend(feed_info['articles'])
        
        # Balance: ensure diversity by limiting articles per organization
        # Strategy: Ensure each org gets equal representation (up to limit)
        max_per_org = 4  # Reduced to ensure more diversity
        max_total_articles = 35
        min_per_org = 1  # Ensure at least one article from each org
        
        logger.info(f"Balancing articles across {len(org_feeds)} organizations:")
        for org, articles in org_feeds.items():
            logger.info(f"  {org}: {len(articles)} articles available")
        
        # Shuffle articles within each org for variety
        for org in org_feeds:
            random.shuffle(org_feeds[org])
        
        # First pass: ensure minimum representation from each org
        for org, articles in org_feeds.items():
            if articles:
                selected = articles[:min_per_org]
                all_articles.extend(selected)
                logger.info(f"  → Selected {len(selected)} article(s) from {org} (minimum)")
        
        # Second pass: fill up to max_per_org from each org
        for org, articles in org_feeds.items():
            if len(all_articles) >= max_total_articles:
                break
            if len(articles) > min_per_org:
                # Take additional articles (up to max_per_org total)
                additional_needed = max_per_org - min_per_org
                additional = articles[min_per_org:min_per_org + additional_needed]
                all_articles.extend(additional)
                logger.info(f"  → Added {len(additional)} more from {org} (total: {min_per_org + len(additional)})")
        
        # Third pass: if we still have room, add more from diverse orgs
        if len(all_articles) < max_total_articles:
            remaining = max_total_articles - len(all_articles)
            # Shuffle orgs to ensure fairness
            orgs_list = list(org_feeds.items())
            random.shuffle(orgs_list)
            
            for org, articles in orgs_list:
                if len(all_articles) >= max_total_articles:
                    break
                if len(articles) > max_per_org:
                    # Take additional articles from this org
                    additional = min(remaining, len(articles) - max_per_org)
                    all_articles.extend(articles[max_per_org:max_per_org + additional])
                    remaining -= additional
        
        # Final shuffle to mix sources throughout
        random.shuffle(all_articles)
        
        return all_articles[:max_total_articles]
    
    def fetch_full_article_text(self, article_url: str) -> str:
        """Fetch full article text from URL"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Use ScraperAPI if available for better success rate
            if self.scraperapi_key:
                try:
                    scraper_url = 'http://api.scraperapi.com'
                    params = {
                        'api_key': self.scraperapi_key,
                        'url': article_url
                    }
                    response = requests.get(scraper_url, params=params, timeout=30, headers=headers)
                    response.raise_for_status()
                    html_content = response.text
                except Exception as e:
                    logger.warning(f"ScraperAPI failed, using direct request: {str(e)}")
                    response = requests.get(article_url, timeout=30, headers=headers)
                    response.raise_for_status()
                    html_content = response.text
            else:
                response = requests.get(article_url, timeout=30, headers=headers)
                response.raise_for_status()
                html_content = response.text
            
            # Parse HTML and extract text
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()
            
            # Try to find main article content
            article_content = None
            content_selectors = [
                'article',
                '[role="main"]',
                '.article-content',
                '.post-content',
                '.entry-content',
                'main',
                '.content'
            ]
            
            for selector in content_selectors:
                article_content = soup.select_one(selector)
                if article_content:
                    break
            
            if not article_content:
                # Fallback to body
                article_content = soup.find('body')
            
            if article_content:
                # Extract text
                text = article_content.get_text(separator=' ', strip=True)
                # Clean up excessive whitespace
                text = ' '.join(text.split())
                
                # Remove common metadata patterns (social sharing text, timestamps at start)
                # Remove patterns like "X hours ago Share Save" at the beginning
                text = re.sub(r'^\d+\s+(hours?|minutes?|days?)\s+ago\s+Share\s+Save\s+', '', text, flags=re.IGNORECASE)
                text = re.sub(r'Share\s+Save\s+[A-Z][a-z]+\s+Share\s+Save\s+', '', text, flags=re.IGNORECASE)
                text = re.sub(r'Reporting\s+from\s+[^.]+\s+Share\s+Save\s+', '', text, flags=re.IGNORECASE)
                # Remove standalone "Share Save" patterns
                text = re.sub(r'\s+Share\s+Save\s+', ' ', text, flags=re.IGNORECASE)
                
                return text[:10000]  # Limit to 10k chars
            
            return ""
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error fetching article {article_url}: {str(e)}")
            return ""
        except Exception as e:
            logger.warning(f"Error parsing article {article_url}: {str(e)}")
            return ""
    
    def generate_ai_summary(self, text: str, num_sentences: int = 4) -> str:
        """
        Generate AI-powered extractive summary (4-5 sentences)
        Uses sentence scoring based on TF-IDF-like weighting
        """
        if not text or len(text.strip()) < 50:
            return text[:200] + '...' if len(text) > 200 else text
        
        # Clean text first - remove metadata patterns
        text = re.sub(r'^\d+\s+(hours?|minutes?|days?)\s+ago\s+Share\s+Save\s+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s+Share\s+Save\s+', ' ', text, flags=re.IGNORECASE)
        
        # Clean and split into sentences
        # Remove extra whitespace and split by sentence endings
        text_clean = re.sub(r'\s+', ' ', text.strip())
        sentences = re.split(r'(?<=[.!?])\s+', text_clean)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]  # Filter very short sentences
        
        # Filter out sentences that look like metadata (too short or contain common patterns)
        metadata_patterns = ['Share Save', 'Reporting from', 'Getty Images', 'EPA/Shutterstock']
        sentences = [s for s in sentences if not any(pattern in s for pattern in metadata_patterns)]
        
        if len(sentences) <= num_sentences:
            return '. '.join(sentences) + '.' if sentences else text[:200] + '...'
        
        # Calculate word frequencies
        words = []
        for sentence in sentences:
            # Extract words (simple tokenization)
            sentence_words = re.findall(r'\b[a-zA-Z]{3,}\b', sentence.lower())
            words.extend(sentence_words)
        
        word_freq = Counter(words)
        max_freq = max(word_freq.values()) if word_freq else 1
        
        # Score sentences based on:
        # 1. Important word frequency (TF-IDF-like)
        # 2. Position (earlier sentences are often more important)
        # 3. Length (moderate length sentences are better)
        sentence_scores = []
        for i, sentence in enumerate(sentences):
            score = 0.0
            sentence_words = re.findall(r'\b[a-zA-Z]{3,}\b', sentence.lower())
            
            # TF-IDF-like scoring: words that appear frequently are important
            for word in sentence_words:
                if word in word_freq:
                    score += word_freq[word] / max_freq
            
            # Position bonus: first sentences are more important
            position_score = 1.0 / (1.0 + i * 0.1)
            score *= (1.0 + position_score)
            
            # Length bonus: prefer sentences of moderate length (20-150 words)
            word_count = len(sentence_words)
            if 20 <= word_count <= 150:
                score *= 1.2
            
            sentence_scores.append((score, i, sentence))
        
        # Sort by score and get top sentences
        sentence_scores.sort(key=lambda x: x[0], reverse=True)
        top_sentences = sentence_scores[:num_sentences]
        
        # Sort back by original position to maintain flow
        top_sentences.sort(key=lambda x: x[1])
        
        # Join selected sentences
        summary_sentences = [s[2] for s in top_sentences]
        summary = '. '.join(summary_sentences)
        
        # Ensure proper ending
        if not summary.endswith(('.', '!', '?')):
            summary += '.'
        
        return summary
    
    def analyze_article_with_comprehend(self, text: str) -> Dict[str, Any]:
        """Analyze article using Amazon Comprehend"""
        if not text or len(text.strip()) < 10:
            return {
                'summary': 'Content too short to analyze',
                'sentiment': 'NEUTRAL',
                'key_phrases': []
            }
        
        # Truncate to Comprehend limits
        text_to_analyze = text[:MAX_COMPREHEND_TEXT_LENGTH]
        
        try:
            # Detect sentiment
            sentiment_response = comprehend_client.detect_sentiment(
                Text=text_to_analyze,
                LanguageCode='en'
            )
            sentiment = sentiment_response['Sentiment']
            sentiment_scores = sentiment_response['SentimentScore']
            
            # Extract key phrases
            key_phrases_response = comprehend_client.detect_key_phrases(
                Text=text_to_analyze,
                LanguageCode='en'
            )
            key_phrases = [phrase['Text'] for phrase in key_phrases_response['KeyPhrases'][:10]]
            
            # Generate AI-powered summary (4-5 sentences)
            summary = self.generate_ai_summary(text_to_analyze, num_sentences=4)
            
            return {
                'summary': summary,
                'sentiment': sentiment,
                'sentiment_scores': sentiment_scores,
                'key_phrases': key_phrases
            }
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            logger.error(f"Comprehend error: {error_code} - {str(e)}")
            # Fallback to AI summary
            summary = self.generate_ai_summary(text, num_sentences=4)
            return {
                'summary': summary,
                'sentiment': 'NEUTRAL',
                'key_phrases': []
            }
        except Exception as e:
            logger.error(f"Error analyzing article: {str(e)}")
            # Fallback to AI summary
            summary = self.generate_ai_summary(text, num_sentences=4)
            return {
                'summary': summary,
                'sentiment': 'NEUTRAL',
                'key_phrases': []
            }
    
    def categorize_article(self, article: Dict[str, Any]) -> str:
        """Categorize article based on title and description"""
        text_to_check = (article.get('title', '') + ' ' + article.get('description', '')).lower()
        
        scores = {}
        for category, keywords in self.category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_to_check)
            if score > 0:
                scores[category] = score
        
        if scores:
            return max(scores, key=scores.get)
        return 'General'
    
    def process_articles(self, articles: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Process all articles: fetch content, analyze, and categorize"""
        processed_by_category = {}
        
        for article in articles:
            try:
                logger.info(f"Processing: {article['title'][:50]}...")
                
                # Fetch full article text
                full_text = self.fetch_full_article_text(article['url'])
                
                # Use description if full text not available
                article_text = full_text if full_text else article.get('description', '')
                
                # Analyze with Comprehend
                analysis = self.analyze_article_with_comprehend(article_text)
                
                # Categorize
                category = self.categorize_article(article)
                
                # Combine article data with analysis
                processed_article = {
                    'title': article['title'],
                    'url': article['url'],
                    'source': article['source'],
                    'published': article.get('published', ''),
                    'summary': analysis['summary'],
                    'sentiment': analysis['sentiment'],
                    'key_phrases': ', '.join(analysis['key_phrases'][:5]) if analysis['key_phrases'] else 'N/A'
                }
                
                # Group by category
                if category not in processed_by_category:
                    processed_by_category[category] = []
                processed_by_category[category].append(processed_article)
                
                # Small delay to avoid rate limiting
                import time
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error processing article {article.get('title', 'Unknown')}: {str(e)}")
                continue
        
        return processed_by_category
    
    def generate_email_content(self, articles_by_category: Dict[str, List[Dict[str, Any]]]) -> Tuple[str, str]:
        """Generate HTML and plain text email content"""
        date_str = datetime.now().strftime('%B %d, %Y')
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }}
        .header h1 {{ margin: 0; font-size: 28px; }}
        .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
        .category {{ margin: 30px 0; }}
        .category h2 {{ color: #667eea; border-bottom: 2px solid #667eea; padding-bottom: 10px; }}
        .article {{ background: #f9f9f9; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #667eea; }}
        .article-title {{ font-size: 18px; font-weight: bold; margin-bottom: 10px; }}
        .article-title a {{ color: #667eea; text-decoration: none; }}
        .article-title a:hover {{ text-decoration: underline; }}
        .article-meta {{ color: #666; font-size: 12px; margin-bottom: 10px; }}
        .article-summary {{ margin: 10px 0; color: #555; }}
        .article-tags {{ margin-top: 10px; font-size: 12px; }}
        .sentiment {{ display: inline-block; padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; margin-left: 10px; }}
        .sentiment.POSITIVE {{ background: #4caf50; color: white; }}
        .sentiment.NEGATIVE {{ background: #f44336; color: white; }}
        .sentiment.NEUTRAL {{ background: #9e9e9e; color: white; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #999; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📰 Daily Global News Summary</h1>
        <p>{date_str}</p>
        <p>Here's what happened in the world today</p>
    </div>
"""
        
        text_content = f"""
Daily Global News Summary
{date_str}
Here's what happened in the world today

{'=' * 60}
"""
        
        # Sort categories: World, Business, Technology, then others
        category_order = ['World', 'Business', 'Technology', 'Health', 'Science', 'General']
        sorted_categories = sorted(
            articles_by_category.items(),
            key=lambda x: (category_order.index(x[0]) if x[0] in category_order else 999, x[0])
        )
        
        for category, articles in sorted_categories:
            html_content += f'<div class="category"><h2>{category}</h2>\n'
            text_content += f"\n{category}\n{'-' * len(category)}\n\n"
            
            for article in articles[:5]:  # Limit to 5 articles per category
                sentiment_class = article['sentiment']
                html_content += f"""
    <div class="article">
        <div class="article-title">
            <a href="{article['url']}" target="_blank">{article['title']}</a>
            <span class="sentiment {sentiment_class}">{sentiment_class}</span>
        </div>
        <div class="article-meta">
            Source: {article['source']} | Published: {article['published'] or 'N/A'}
        </div>
        <div class="article-summary">{article['summary']}</div>
        <div class="article-tags">Key Topics: {article['key_phrases']}</div>
    </div>
"""
                text_content += f"• {article['title']} [{sentiment_class}]\n"
                text_content += f"  Source: {article['source']}\n"
                text_content += f"  {article['summary']}\n"
                text_content += f"  Key Topics: {article['key_phrases']}\n"
                text_content += f"  Read more: {article['url']}\n\n"
        
        html_content += """
    <div class="footer">
        <p>This is an automated daily news summary. Stay informed!</p>
    </div>
</body>
</html>
"""
        
        text_content += "\n" + "=" * 60 + "\n"
        text_content += "This is an automated daily news summary. Stay informed!\n"
        
        return html_content, text_content
    
    def send_email(self, html_content: str, text_content: str) -> bool:
        """Send email via Amazon SES"""
        if not self.email_recipients:
            logger.warning("No email recipients configured")
            return False
        
        if not self.sender_email:
            logger.warning("No sender email configured")
            return False
        
        try:
            # Create multipart message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Daily Global News Summary - {datetime.now().strftime('%B %d, %Y')}"
            msg['From'] = self.sender_email
            msg['To'] = ', '.join(self.email_recipients)
            
            # Add both text and HTML versions
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send via SES
            response = ses_client.send_raw_email(
                Source=self.sender_email,
                Destinations=self.email_recipients,
                RawMessage={'Data': msg.as_string()}
            )
            
            logger.info(f"Email sent successfully. Message ID: {response['MessageId']}")
            return True
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            logger.error(f"SES error: {error_code} - {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
    
    def generate_summary(self) -> Dict[str, Any]:
        """Main method to generate the daily news summary"""
        logger.info("Starting daily news summary generation")
        logger.info(f"Fetching from {len(self.rss_feeds)} news sources")
        
        # Step 1: Fetch RSS feeds
        articles = self.fetch_rss_feeds()
        
        # Show source diversity
        sources = {}
        for article in articles:
            source = article.get('source', 'Unknown')
            sources[source] = sources.get(source, 0) + 1
        
        logger.info(f"✓ Fetched {len(articles)} total articles from {len(sources)} different sources:")
        for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  - {source}: {count} articles")
        
        if not articles:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'No articles found',
                    'articles_processed': 0
                })
            }
        
        # Step 2: Process articles
        articles_by_category = self.process_articles(articles)
        logger.info(f"Processed articles into {len(articles_by_category)} categories")
        
        # Step 3: Generate email content
        html_content, text_content = self.generate_email_content(articles_by_category)
        
        # Step 4: Send email
        email_sent = self.send_email(html_content, text_content)
        
        # Prepare response
        total_articles = sum(len(articles) for articles in articles_by_category.values())
        result = {
            'message': 'Daily news summary generated successfully',
            'articles_processed': total_articles,
            'categories': list(articles_by_category.keys()),
            'email_sent': email_sent,
            'timestamp': datetime.now().isoformat()
        }
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for Daily News Summary
    
    Environment Variables:
    - RSS_FEED_URLS: Comma-separated list of RSS feed URLs
    - EMAIL_RECIPIENTS: Comma-separated list of email addresses
    - SENDER_EMAIL: Verified SES sender email address
    - SCRAPERAPI_KEY: (Optional) ScraperAPI key for better article extraction
    - AWS_REGION: AWS region (default: us-east-1)
    """
    try:
        news_summary = DailyNewsSummary()
        return news_summary.generate_summary()
        
    except Exception as e:
        logger.error(f"Lambda execution error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }

