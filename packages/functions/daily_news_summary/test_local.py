"""
Local testing script for Daily News Summary Lambda function

Usage:
    python test_local.py
"""

import os
import sys
from lambda_function import DailyNewsSummary, lambda_handler

# Set up environment variables for local testing
def setup_local_env():
    """Configure environment variables for local testing"""
    
    # RSS Feed URLs (comma-separated)
    os.environ['RSS_FEED_URLS'] = os.getenv(
        'RSS_FEED_URLS',
        'https://feeds.bbci.co.uk/news/rss.xml,https://techcrunch.com/feed/'
    )
    
    # Email configuration (REQUIRED for email sending)
    os.environ['EMAIL_RECIPIENTS'] = os.getenv(
        'EMAIL_RECIPIENTS',
        'your-email@example.com'  # Change this to your email
    )
    
    os.environ['SENDER_EMAIL'] = os.getenv(
        'SENDER_EMAIL',
        'sender@example.com'  # Change this to your verified SES email
    )
    
    # AWS Region
    os.environ['AWS_REGION'] = os.getenv('AWS_REGION', 'us-east-1')
    
    # Optional: ScraperAPI key for better article extraction
    # os.environ['SCRAPERAPI_KEY'] = 'your-scraperapi-key'
    
    print("Environment variables set:")
    print(f"  RSS_FEED_URLS: {os.environ.get('RSS_FEED_URLS')}")
    print(f"  EMAIL_RECIPIENTS: {os.environ.get('EMAIL_RECIPIENTS')}")
    print(f"  SENDER_EMAIL: {os.environ.get('SENDER_EMAIL')}")
    print(f"  AWS_REGION: {os.environ.get('AWS_REGION')}")
    print()


def test_rss_feeds_only():
    """Test 1: Just fetch and parse RSS feeds (no article extraction)"""
    print("=" * 60)
    print("TEST 1: RSS Feed Fetching")
    print("=" * 60)
    
    try:
        news_summary = DailyNewsSummary()
        articles = news_summary.fetch_rss_feeds()
        
        print(f"\n✓ Successfully fetched {len(articles)} articles\n")
        
        # Display first few articles
        for i, article in enumerate(articles[:5], 1):
            print(f"{i}. {article['title'][:60]}...")
            print(f"   Source: {article['source']}")
            print(f"   URL: {article['url']}")
            print()
        
        return True
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_article_extraction():
    """Test 2: Fetch and extract full article text from one article"""
    print("=" * 60)
    print("TEST 2: Article Text Extraction")
    print("=" * 60)
    
    try:
        news_summary = DailyNewsSummary()
        articles = news_summary.fetch_rss_feeds()
        
        if not articles:
            print("No articles found. Skipping extraction test.")
            return False
        
        # Test with first article
        test_article = articles[0]
        print(f"\nTesting with: {test_article['title']}")
        print(f"URL: {test_article['url']}\n")
        
        full_text = news_summary.fetch_full_article_text(test_article['url'])
        
        if full_text:
            print(f"✓ Successfully extracted {len(full_text)} characters")
            print(f"\nPreview (first 300 chars):\n{full_text[:300]}...\n")
            return True
        else:
            print("✗ No text extracted")
            return False
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_comprehend_analysis():
    """Test 3: Test Comprehend analysis (requires AWS credentials)"""
    print("=" * 60)
    print("TEST 3: Comprehend Analysis")
    print("=" * 60)
    
    # Check for AWS credentials
    if not os.getenv('AWS_ACCESS_KEY_ID') and not os.getenv('AWS_PROFILE'):
        print("\n⚠ Warning: No AWS credentials found.")
        print("Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY, or use AWS_PROFILE")
        print("Skipping Comprehend test...\n")
        return False
    
    try:
        news_summary = DailyNewsSummary()
        
        # Create sample text for analysis
        sample_text = """
        Scientists announced a breakthrough in renewable energy technology today.
        The new solar panels are 50% more efficient than previous models.
        This development could significantly reduce carbon emissions worldwide.
        Environmental groups praised the innovation as a major step forward.
        """
        
        print(f"\nAnalyzing sample text ({len(sample_text)} chars)...\n")
        
        analysis = news_summary.analyze_article_with_comprehend(sample_text)
        
        print(f"✓ Analysis complete:")
        print(f"  Sentiment: {analysis['sentiment']}")
        print(f"  Key Phrases: {', '.join(analysis['key_phrases'][:5])}")
        print(f"  Summary: {analysis['summary'][:200]}...\n")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_full_pipeline(without_email=True):
    """Test 4: Full pipeline without sending email"""
    print("=" * 60)
    print("TEST 4: Full Pipeline (No Email)")
    print("=" * 60)
    
    try:
        news_summary = DailyNewsSummary()
        
        # Fetch RSS feeds
        print("\n1. Fetching RSS feeds...")
        articles = news_summary.fetch_rss_feeds()
        print(f"   ✓ Fetched {len(articles)} articles")
        
        if not articles:
            print("   ✗ No articles found. Stopping.")
            return False
        
        # Process first 3 articles only (to save time/API calls)
        print("\n2. Processing articles (limiting to 3 for testing)...")
        limited_articles = articles[:3]
        articles_by_category = news_summary.process_articles(limited_articles)
        
        total_processed = sum(len(arts) for arts in articles_by_category.values())
        print(f"   ✓ Processed {total_processed} articles into {len(articles_by_category)} categories")
        
        # Generate email content
        print("\n3. Generating email content...")
        html_content, text_content = news_summary.generate_email_content(articles_by_category)
        print(f"   ✓ Generated HTML ({len(html_content)} chars)")
        print(f"   ✓ Generated text ({len(text_content)} chars)")
        
        # Save to files for review
        print("\n4. Saving output files...")
        with open('test_email_output.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        print("   ✓ Saved: test_email_output.html")
        
        with open('test_email_output.txt', 'w', encoding='utf-8') as f:
            f.write(text_content)
        print("   ✓ Saved: test_email_output.txt")
        
        print("\n✓ Full pipeline test completed successfully!")
        print("\n📧 Review the generated email files:")
        print("   - test_email_output.html")
        print("   - test_email_output.txt")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_with_email():
    """Test 5: Full pipeline WITH email sending (requires AWS SES setup)"""
    print("=" * 60)
    print("TEST 5: Full Pipeline WITH Email")
    print("=" * 60)
    
    # Check for AWS credentials
    if not os.getenv('AWS_ACCESS_KEY_ID') and not os.getenv('AWS_PROFILE'):
        print("\n⚠ Warning: No AWS credentials found.")
        print("Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY, or use AWS_PROFILE")
        return False
    
    # Check email config
    if not os.getenv('EMAIL_RECIPIENTS') or not os.getenv('SENDER_EMAIL'):
        print("\n⚠ Warning: EMAIL_RECIPIENTS and SENDER_EMAIL must be set")
        return False
    
    print("\n⚠ WARNING: This will send a real email!")
    response = input("Continue? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("Skipped.")
        return False
    
    try:
        # Use lambda_handler to test full flow
        event = {}
        context = None
        
        result = lambda_handler(event, context)
        
        print(f"\n✓ Lambda execution completed")
        print(f"  Status Code: {result.get('statusCode')}")
        
        if result.get('statusCode') == 200:
            body = result.get('body', '{}')
            import json
            data = json.loads(body)
            print(f"  Articles processed: {data.get('articles_processed', 0)}")
            print(f"  Email sent: {data.get('email_sent', False)}")
        
        return result.get('statusCode') == 200
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test runner"""
    print("\n" + "=" * 60)
    print("Daily News Summary - Local Testing")
    print("=" * 60 + "\n")
    
    # Setup environment
    setup_local_env()
    
    # Run tests
    tests = [
        ("RSS Feed Fetching", test_rss_feeds_only),
        ("Article Extraction", test_article_extraction),
        ("Comprehend Analysis", test_comprehend_analysis),
        ("Full Pipeline (No Email)", test_full_pipeline),
        ("Full Pipeline (With Email)", test_with_email),
    ]
    
    print("\n" + "=" * 60)
    print("Available Tests:")
    print("=" * 60)
    for i, (name, _) in enumerate(tests, 1):
        print(f"  {i}. {name}")
    print()
    
    # Ask which test to run
    choice = input("Enter test number (or 'all' for all tests, 'q' to quit): ").strip().lower()
    
    if choice == 'q':
        print("Exiting.")
        return
    
    if choice == 'all':
        results = []
        for name, test_func in tests:
            results.append((name, test_func()))
            print("\n" + "-" * 60 + "\n")
        
        print("\n" + "=" * 60)
        print("Test Results Summary:")
        print("=" * 60)
        for name, result in results:
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"  {status}: {name}")
    else:
        try:
            test_num = int(choice)
            if 1 <= test_num <= len(tests):
                name, test_func = tests[test_num - 1]
                print(f"\nRunning: {name}\n")
                test_func()
            else:
                print(f"Invalid test number. Choose 1-{len(tests)}")
        except ValueError:
            print("Invalid input. Enter a number, 'all', or 'q'")


if __name__ == "__main__":
    main()

