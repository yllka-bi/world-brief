"""
Quick test to verify source diversity
"""

import os
import sys
from lambda_function import DailyNewsSummary

# Use default multi-source feeds
print("Testing source diversity with default feeds...\n")

news_summary = DailyNewsSummary()
articles = news_summary.fetch_rss_feeds()

# Analyze sources
sources = {}
for article in articles:
    source = article.get('source', 'Unknown')
    sources[source] = sources.get(source, 0) + 1

print(f"\n{'='*60}")
print(f"RESULTS: {len(articles)} total articles from {len(sources)} different sources")
print(f"{'='*60}\n")

print("Articles by source:")
for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
    print(f"  {source}: {count} articles")

print(f"\n{'='*60}")
if len(sources) >= 5:
    print("✅ GOOD: Multiple diverse sources detected!")
else:
    print("⚠️  WARNING: Limited source diversity. Check feed configuration.")

