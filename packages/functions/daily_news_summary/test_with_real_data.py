"""
Test with real data - ScraperAPI + Mocked AWS services

This script:
- Uses real ScraperAPI to scrape articles
- Mocks AWS Comprehend for analysis (no AWS needed)
- Optionally mocks SES email sending
- Processes real articles and shows results
"""

import os
import sys
import json
from unittest.mock import Mock, patch
from lambda_function import DailyNewsSummary

# Set ScraperAPI key
SCRAPERAPI_KEY = "4885066dcb0246dac9ad43fd1d6f9d92"

# Mock Comprehend responses
def mock_comprehend_detect_sentiment(Text, LanguageCode='en'):
    """Mock sentiment detection"""
    # Simple mock: check for positive/negative keywords
    text_lower = Text.lower()
    positive_words = ['breakthrough', 'success', 'improved', 'growth', 'praise', 'historic', 'record', 'innovation', 'aid', 'evacuated', 'help']
    negative_words = ['breach', 'concern', 'crisis', 'failure', 'warn', 'danger', 'attack', 'damage', 'destroyed']
    
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    
    if positive_count > negative_count:
        sentiment = 'POSITIVE'
    elif negative_count > positive_count:
        sentiment = 'NEGATIVE'
    else:
        sentiment = 'NEUTRAL'
    
    # Mock scores
    if sentiment == 'POSITIVE':
        scores = {'POSITIVE': 0.8, 'NEGATIVE': 0.1, 'NEUTRAL': 0.1, 'MIXED': 0.0}
    elif sentiment == 'NEGATIVE':
        scores = {'POSITIVE': 0.1, 'NEGATIVE': 0.8, 'NEUTRAL': 0.1, 'MIXED': 0.0}
    else:
        scores = {'POSITIVE': 0.2, 'NEGATIVE': 0.2, 'NEUTRAL': 0.5, 'MIXED': 0.1}
    
    return {
        'Sentiment': sentiment,
        'SentimentScore': scores
    }

def mock_comprehend_detect_key_phrases(Text, LanguageCode='en'):
    """Mock key phrase extraction"""
    # Extract simple key phrases (first few important words)
    words = Text.lower().split()
    # Filter out common words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'was', 'are', 'were'}
    
    # Get important capitalized words or phrases
    phrases = []
    text_upper_words = Text.split()
    for i, word in enumerate(text_upper_words):
        if word and word[0].isupper() and len(word) > 3:
            # Try to get 2-word phrases
            if i + 1 < len(text_upper_words) and text_upper_words[i+1][0].isupper():
                phrase = f"{word} {text_upper_words[i+1]}"
                phrases.append({'Text': phrase})
            else:
                phrases.append({'Text': word})
    
    # Fallback: extract meaningful words
    if len(phrases) < 5:
        important_words = [w for w in words if len(w) > 5 and w not in stop_words][:10]
        phrases.extend([{'Text': w.capitalize()} for w in important_words[:5-len(phrases)]])
    
    return {'KeyPhrases': phrases[:10]}

# Mock Comprehend client
def create_mock_comprehend_client():
    """Create a mock Comprehend client"""
    mock_client = Mock()
    mock_client.detect_sentiment = Mock(side_effect=mock_comprehend_detect_sentiment)
    mock_client.detect_key_phrases = Mock(side_effect=mock_comprehend_detect_key_phrases)
    return mock_client

def setup_test_environment():
    """Setup environment variables for testing"""
    # RSS feeds - Multiple diverse sources (using reliable feeds)
    os.environ['RSS_FEED_URLS'] = (
        'https://feeds.bbci.co.uk/news/rss.xml,'
        'https://feeds.bbci.co.uk/news/world/rss.xml,'
        'https://www.theguardian.com/world/rss,'
        'https://www.npr.org/rss/rss.php?id=1001,'
        'https://feeds.bbci.co.uk/news/business/rss.xml,'
        'https://www.theguardian.com/business/rss,'
        'https://techcrunch.com/feed/,'
        'https://www.theverge.com/rss/index.xml,'
        'https://feeds.bbci.co.uk/news/science_and_environment/rss.xml,'
        'https://www.npr.org/rss/rss.php?id=1007'
    )
    
    # ScraperAPI
    os.environ['SCRAPERAPI_KEY'] = SCRAPERAPI_KEY
    
    # Email (won't actually send with mock)
    os.environ['EMAIL_RECIPIENTS'] = 'test@example.com'
    os.environ['SENDER_EMAIL'] = 'sender@example.com'
    
    # AWS Region
    os.environ['AWS_REGION'] = 'us-east-1'
    
    print("Environment configured:")
    print(f"  RSS_FEED_URLS: {os.environ.get('RSS_FEED_URLS')}")
    print(f"  SCRAPERAPI_KEY: {SCRAPERAPI_KEY[:10]}...")
    print()

def test_full_pipeline_with_real_data():
    """Test full pipeline with real scraping and mocked AWS"""
    print("=" * 70)
    print("TEST: Full Pipeline with Real Data")
    print("=" * 70)
    print("\nUsing:")
    print("  ✓ Real ScraperAPI for article scraping")
    print("  ✓ Mocked AWS Comprehend (no AWS credentials needed)")
    print("  ✓ Mocked SES email (won't send real email)")
    print()
    
    # Setup environment
    setup_test_environment()
    
    # Create news summary instance
    news_summary = DailyNewsSummary()
    
    # Mock the Comprehend client
    mock_comprehend = create_mock_comprehend_client()
    
    # Patch boto3.client to return our mock
    with patch('boto3.client') as mock_boto3_client:
        # Configure boto3 to return mock for comprehend
        def client_side_effect(service_name, **kwargs):
            if service_name == 'comprehend':
                return mock_comprehend
            elif service_name == 'ses':
                # Mock SES client (won't actually send emails)
                mock_ses = Mock()
                mock_ses.send_raw_email = Mock(return_value={'MessageId': 'mock-message-id-123'})
                return mock_ses
            return None
        
        mock_boto3_client.side_effect = client_side_effect
        
        # Also patch the comprehend_client in the module
        with patch('lambda_function.comprehend_client', mock_comprehend):
            with patch('lambda_function.ses_client') as mock_ses:
                mock_ses.send_raw_email = Mock(return_value={'MessageId': 'mock-message-id-123'})
                
                try:
                    # Step 1: Fetch RSS feeds
                    print("Step 1: Fetching RSS feeds...")
                    articles = news_summary.fetch_rss_feeds()
                    print(f"   ✓ Fetched {len(articles)} articles from RSS feeds\n")
                    
                    if not articles:
                        print("   ✗ No articles found")
                        return False
                    
                    # Limit to 3 articles for testing (to save time/API calls)
                    test_articles = articles[:3]
                    print(f"   Testing with {len(test_articles)} articles (limited for testing)\n")
                    
                    # Step 2: Process articles (with real scraping, mocked Comprehend)
                    print("Step 2: Processing articles...")
                    print("   - Fetching full article text (using ScraperAPI)...")
                    print("   - Analyzing with mocked Comprehend...\n")
                    
                    articles_by_category = news_summary.process_articles(test_articles)
                    
                    total_processed = sum(len(arts) for arts in articles_by_category.values())
                    print(f"   ✓ Processed {total_processed} articles into {len(articles_by_category)} categories\n")
                    
                    # Display processed articles
                    print("Processed Articles:")
                    print("-" * 70)
                    for category, category_articles in articles_by_category.items():
                        print(f"\n📰 {category}")
                        for article in category_articles:
                            print(f"\n   Title: {article['title']}")
                            print(f"   URL: {article['url'][:70]}...")
                            print(f"   Source: {article['source']}")
                            print(f"   Sentiment: {article['sentiment']}")
                            print(f"   Key Phrases: {article['key_phrases']}")
                            print(f"   Summary: {article['summary'][:150]}...")
                    
                    # Step 3: Generate email content
                    print("\n" + "=" * 70)
                    print("Step 3: Generating email content...")
                    html_content, text_content = news_summary.generate_email_content(articles_by_category)
                    print(f"   ✓ Generated HTML email ({len(html_content)} chars)")
                    print(f"   ✓ Generated plain text email ({len(text_content)} chars)\n")
                    
                    # Save email files
                    print("Step 4: Saving output files...")
                    with open('test_email_output_real.html', 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    print("   ✓ Saved: test_email_output_real.html")
                    
                    with open('test_email_output_real.txt', 'w', encoding='utf-8') as f:
                        f.write(text_content)
                    print("   ✓ Saved: test_email_output_real.txt\n")
                    
                    # Step 5: Test email sending (mocked)
                    print("Step 5: Testing email sending (mocked - won't send real email)...")
                    email_sent = news_summary.send_email(html_content, text_content)
                    if email_sent:
                        print("   ✓ Email would be sent (mocked successfully)")
                    else:
                        print("   ✗ Email sending failed")
                    
                    print("\n" + "=" * 70)
                    print("✓ TEST COMPLETED SUCCESSFULLY!")
                    print("=" * 70)
                    print("\n📧 Review the generated email files:")
                    print("   - test_email_output_real.html (open in browser)")
                    print("   - test_email_output_real.txt\n")
                    
                    return True
                    
                except Exception as e:
                    print(f"\n✗ Error during testing: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    return False

def test_with_custom_article_limit():
    """Test with user-specified article limit"""
    print("\n" + "=" * 70)
    print("Article Limit Test")
    print("=" * 70)
    
    try:
        limit = input("\nHow many articles to process? (default: 3, max recommended: 5): ").strip()
        limit = int(limit) if limit else 3
        limit = min(limit, 10)  # Cap at 10
        
        setup_test_environment()
        news_summary = DailyNewsSummary()
        mock_comprehend = create_mock_comprehend_client()
        
        with patch('boto3.client') as mock_boto3_client:
            def client_side_effect(service_name, **kwargs):
                if service_name == 'comprehend':
                    return mock_comprehend
                elif service_name == 'ses':
                    mock_ses = Mock()
                    mock_ses.send_raw_email = Mock(return_value={'MessageId': 'mock-id'})
                    return mock_ses
                return None
            
            mock_boto3_client.side_effect = client_side_effect
            
            with patch('lambda_function.comprehend_client', mock_comprehend):
                with patch('lambda_function.ses_client') as mock_ses:
                    mock_ses.send_raw_email = Mock(return_value={'MessageId': 'mock-id'})
                    
                    articles = news_summary.fetch_rss_feeds()
                    test_articles = articles[:limit]
                    
                    print(f"\nProcessing {len(test_articles)} articles...\n")
                    articles_by_category = news_summary.process_articles(test_articles)
                    
                    total = sum(len(arts) for arts in articles_by_category.values())
                    print(f"✓ Processed {total} articles\n")
                    
                    # Generate and save
                    html, text = news_summary.generate_email_content(articles_by_category)
                    
                    with open('test_email_output_real.html', 'w', encoding='utf-8') as f:
                        f.write(html)
                    with open('test_email_output_real.txt', 'w', encoding='utf-8') as f:
                        f.write(text)
                    
                    print("✓ Email files generated:")
                    print("   - test_email_output_real.html")
                    print("   - test_email_output_real.txt\n")
                    
    except ValueError:
        print("Invalid number, using default (3)")
    except Exception as e:
        print(f"Error: {str(e)}")

def main():
    """Main test runner"""
    print("\n" + "=" * 70)
    print("Daily News Summary - Real Data Test (ScraperAPI + Mocked AWS)")
    print("=" * 70)
    print("\nThis test uses:")
    print("  • Real ScraperAPI for article scraping")
    print("  • Mocked AWS Comprehend (sentiment/key phrases)")
    print("  • Mocked SES email (won't send real emails)")
    print("\nNo AWS credentials needed!\n")
    
    choice = input("Options:\n  1. Quick test (3 articles)\n  2. Custom article limit\n  q. Quit\n\nChoice: ").strip().lower()
    
    if choice == 'q':
        print("Exiting.")
        return
    elif choice == '1':
        test_full_pipeline_with_real_data()
    elif choice == '2':
        test_with_custom_article_limit()
    else:
        print("Invalid choice. Running quick test...\n")
        test_full_pipeline_with_real_data()

if __name__ == "__main__":
    main()

