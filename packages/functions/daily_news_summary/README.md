# Daily News Summary Lambda Function

Automatically generates and emails a daily global news summary every morning at 8 AM using Amazon EventBridge Scheduler.

## Features

- **RSS Feed Aggregation**: Fetches articles from multiple RSS feeds
- **Article Extraction**: Uses BeautifulSoup (and optionally ScraperAPI) to extract full article text
- **NLP Analysis**: Uses Amazon Comprehend (free tier compatible) for:
  - Sentiment analysis (positive, negative, neutral)
  - Key phrase extraction
  - Content analysis
- **Smart Categorization**: Automatically categorizes articles into sections (World, Business, Technology, Health, Science, General)
- **Email Delivery**: Sends formatted HTML and plain text emails via Amazon SES
- **Environment Variable Support**: Fully configurable via environment variables

## Environment Variables

- `RSS_FEED_URLS`: Comma-separated list of RSS feed URLs (default: 12 diverse sources including BBC, Guardian, CNN, NPR, Reuters, TechCrunch, The Verge, and more)
- `EMAIL_RECIPIENTS`: Comma-separated list of recipient email addresses
- `SENDER_EMAIL`: Verified SES sender email address (must be verified in SES)
- `SCRAPERAPI_KEY`: (Optional) ScraperAPI key for better article extraction success rate
- `AWS_REGION`: AWS region (default: us-east-1)

## Example Email Output

```
Daily Global News Summary
December 15, 2024
Here's what happened in the world today

============================================================

World
-----

• Global Summit Reaches Climate Agreement [POSITIVE]
  Source: BBC News
  World leaders reached a historic climate agreement at the UN summit in Dubai. The deal commits nations to...
  Key Topics: climate agreement, emissions, renewable energy, global summit
  Read more: https://www.bbc.com/news/climate

Business
--------

• Stock Markets Hit Record Highs [POSITIVE]
  Source: Reuters
  Global stock markets surged to record levels following positive economic indicators. Technology stocks led...
  Key Topics: stock market, economic growth, technology stocks, financial markets
  Read more: https://www.reuters.com/business

Technology
----------

• AI Breakthrough in Medical Diagnosis [POSITIVE]
  Source: TechCrunch
  Researchers announced a major breakthrough in AI-powered medical diagnosis. The new system can detect...
  Key Topics: artificial intelligence, medical diagnosis, machine learning, healthcare technology
  Read more: https://techcrunch.com/ai-medical
```

## AWS Services Used (Free Tier Compatible)

- **Amazon EventBridge Scheduler**: Free tier includes 14 million invocations per month
- **AWS Lambda**: Free tier includes 1M requests and 400,000 GB-seconds per month
- **Amazon Comprehend**: Free tier includes 50,000 characters per month (analyzes ~10 articles per day)
- **Amazon SES**: Free tier includes 62,000 emails per month (from verified email addresses)
- **CloudWatch Logs**: Free tier includes 5 GB of log data ingestion per month

## Local Testing

### Quick Start (No AWS Required)

**Option 1: Without Virtual Environment (Quick & Simple)**

```powershell
cd packages/functions/daily_news_summary
python -m pip install -r requirements.txt
python test_quick.py
```

**Option 2: With Virtual Environment (Recommended - Keeps packages isolated)**

```powershell
cd packages/functions/daily_news_summary

# Create virtual environment
python -m venv venv

# Activate it
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Windows CMD:
# venv\Scripts\activate.bat
# Linux/Mac:
# source venv/bin/activate

# Install dependencies
python -m pip install -r requirements.txt

# Run tests
python test_quick.py

# When done, deactivate (optional)
deactivate
```

### Full Testing Guide

See [README_LOCAL_TESTING.md](README_LOCAL_TESTING.md) for detailed testing instructions.

### Quick Test Scripts

1. **Quick test (no AWS):**
   ```bash
   python test_quick.py
   ```

2. **Interactive test suite:**
   ```bash
   python test_local.py
   ```

### Manual Testing

```python
from lambda_function import DailyNewsSummary

# Set environment variables
import os
os.environ['RSS_FEED_URLS'] = 'https://feeds.bbci.co.uk/news/rss.xml,https://techcrunch.com/feed/'
os.environ['EMAIL_RECIPIENTS'] = 'your-email@example.com'
os.environ['SENDER_EMAIL'] = 'sender@example.com'
os.environ['AWS_REGION'] = 'us-east-1'

# Run
news_summary = DailyNewsSummary()
result = news_summary.generate_summary()
print(result)
```

## Deployment

The function is deployed via Terraform with:
- EventBridge Scheduler trigger at 8:00 AM daily (UTC)
- IAM role with permissions for:
  - Comprehend (sentiment and key phrases)
  - SES (send email)
  - CloudWatch Logs
  - VPC access (if deployed in VPC)

## Error Handling

- **RSS Feed Failures**: Continues processing other feeds
- **Article Extraction Failures**: Uses RSS description as fallback
- **Comprehend Limits**: Falls back to simple text extraction if limit exceeded
- **Email Failures**: Logs error but returns success for Lambda

## Monitoring

- CloudWatch Logs: All operations logged with INFO/ERROR levels
- CloudWatch Metrics: Lambda metrics available automatically
- SES Sending Statistics: Available in SES console

## Free Tier Considerations

1. **Comprehend Limits**: 
   - Free tier: 50,000 characters/month
   - Each article analyzed: ~5,000 characters
   - Max ~10 articles/day within free tier
   - Function limits articles per feed to stay within budget

2. **SES**:
   - Must verify sender email in SES console
   - Must verify recipient emails (or use production access)
   - Free tier: 62,000 emails/month (more than enough for daily newsletter)

3. **Lambda**:
   - Free tier is generous for daily execution
   - Function timeout: 5 minutes (configurable)
   - Memory: 512 MB (configurable)

## Troubleshooting

### Email Not Sending
1. Verify sender email in SES console
2. Verify recipient emails (or request production access)
3. Check SES sandbox limitations
4. Review CloudWatch logs for SES errors

### No Articles Found
1. Check RSS feed URLs are accessible
2. Verify network connectivity (if in VPC)
3. Review CloudWatch logs for fetch errors

### Comprehend Errors
1. Check AWS region matches Comprehend availability
2. Verify IAM permissions
3. Check character count limits
4. Review error codes in CloudWatch logs

## Customization

### Default News Sources

The function comes with **14 diverse news sources** by default:
- **World News**: BBC World News, BBC World, The Guardian World, NPR World News, BBC UK
- **Business**: BBC Business, The Guardian Business, Reuters Business News
- **Technology**: TechCrunch, The Verge, BBC Technology
- **Science**: BBC Science & Environment, NPR Science, The Guardian Science

### Adding More RSS Feeds

To customize sources, set `RSS_FEED_URLS` environment variable:
```
RSS_FEED_URLS=https://feeds.bbci.co.uk/news/rss.xml,https://techcrunch.com/feed/,https://your-feed.com/rss
```

The function automatically balances article selection across feeds to ensure diverse coverage.

### Custom Categories
Modify `category_keywords` dictionary in `__init__` method to add/change categories.

### Email Template
Modify `generate_email_content` method to customize HTML and text email templates.

