"""
Quick test script - minimal setup required
Just tests RSS fetching and shows sample output
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lambda_function import DailyNewsSummary

def quick_test():
    """Quick test without AWS dependencies"""
    print("Quick Test - RSS Feed Fetching Only\n")
    
    # Minimal setup
    news_summary = DailyNewsSummary()
    
    # Just test RSS fetching
    print("Fetching RSS feeds...")
    articles = news_summary.fetch_rss_feeds()
    
    print(f"\n✓ Fetched {len(articles)} articles\n")
    
    if articles:
        print("Sample articles:")
        for i, article in enumerate(articles[:5], 1):
            print(f"\n{i}. {article['title']}")
            print(f"   Source: {article['source']}")
            print(f"   URL: {article['url'][:80]}...")
        
        # Show keyword-based categorization (fallback, no AWS needed)
        print("\n" + "=" * 60)
        print("Testing keyword categorization (fallback):")
        print("=" * 60)

        for article in articles[:3]:
            text     = article.get('title', '') + ' ' + article.get('description', '')
            category = news_summary._keyword_category(text)
            print(f"\nArticle: {article['title'][:50]}...")
            print(f"Category: {category}")
    else:
        print("No articles found. Check your internet connection and RSS feed URLs.")

if __name__ == "__main__":
    quick_test()


