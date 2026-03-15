# Local Testing Guide

This guide explains how to test the Daily News Summary Lambda function locally before deploying to AWS.

## Quick Start (No AWS Required)

Test just the RSS feed fetching without AWS services:

```bash
cd packages/functions/daily_news_summary
python test_quick.py
```

This will:
- Fetch articles from RSS feeds
- Display sample articles
- Test article categorization

## Prerequisites

1. **Python 3.12+** installed

### Installing Python on Windows

If Python is not installed:

1. Download Python from [python.org](https://www.python.org/downloads/)
2. **Important:** During installation, check "Add Python to PATH"
3. Verify installation:
   ```powershell
   python --version
   # or
   py --version
   ```

If `python` or `py` commands don't work:
- Python might not be in your PATH
- Try reinstalling Python with "Add to PATH" option checked
- Or manually add Python to PATH in Windows settings

### Installing Dependencies

**Option 1: Without Virtual Environment (Simple)**

Install packages globally (works fine for testing):

```powershell
cd packages/functions/daily_news_summary

# Windows PowerShell:
python -m pip install -r requirements.txt
# OR try: py -m pip install -r requirements.txt

# Linux/Mac:
python3 -m pip install -r requirements.txt
```

**Option 2: With Virtual Environment (Recommended)**

Keeps packages isolated from your system Python:

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

# Your prompt will show (venv) when activated
# When done, deactivate:
# deactivate
```

**Note:** You don't need to activate a venv every time - you can install globally if you prefer. A venv is optional but helps avoid package conflicts.

## Testing Options

### Option 0: Real Data Test (Recommended!)

Test with **real article scraping** + **mocked AWS services** (no AWS credentials needed):

```powershell
python test_with_real_data.py
```

**Features:**
- ✅ Uses real ScraperAPI to scrape full article text
- ✅ Mocks AWS Comprehend (sentiment/key phrases) - no AWS needed
- ✅ Mocks SES email (won't send real emails)
- ✅ Processes real articles and generates email files
- ✅ Shows full pipeline results

**Requires:** ScraperAPI key (configured in script)

### Option 1: Quick Test (No AWS)

Just test RSS feed fetching and basic functionality:

```bash
python test_quick.py
```

**What it tests:**
- RSS feed fetching
- Article parsing
- Article categorization

**No AWS credentials needed**

### Option 2: Interactive Test Suite

Run the full interactive test suite:

```bash
python test_local.py
```

**Available tests:**
1. **RSS Feed Fetching** - Test fetching and parsing RSS feeds
2. **Article Extraction** - Test extracting full article text from URLs
3. **Comprehend Analysis** - Test Amazon Comprehend sentiment/key phrase analysis
4. **Full Pipeline (No Email)** - Test entire pipeline without sending email
5. **Full Pipeline (With Email)** - Test entire pipeline WITH email sending

## Setting Up AWS Credentials (For Tests 3-5)

For tests that require AWS services (Comprehend, SES), you need AWS credentials:

### Option A: AWS Credentials File

```bash
# Linux/Mac
mkdir -p ~/.aws
cat > ~/.aws/credentials << EOF
[default]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
region = us-east-1
EOF
```

### Option B: Environment Variables

```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1
```

### Option C: AWS Profile

```bash
export AWS_PROFILE=your-profile-name
```

## Environment Variables for Testing

Set these before running tests (or edit `test_local.py`):

```bash
export RSS_FEED_URLS="https://feeds.bbci.co.uk/news/rss.xml,https://techcrunch.com/feed/"
export EMAIL_RECIPIENTS="your-email@example.com"
export SENDER_EMAIL="sender@example.com"  # Must be verified in SES
export AWS_REGION="us-east-1"
```

## Detailed Test Descriptions

### Test 1: RSS Feed Fetching
**Requirements:** Internet connection
**Tests:**
- Fetching from multiple RSS feeds
- Parsing RSS/Atom feeds
- Extracting article metadata (title, URL, description)

**Example output:**
```
✓ Successfully fetched 25 articles

1. Global Climate Summit Reaches Historic Agreement...
   Source: BBC News
   URL: https://www.bbc.com/news/climate
```

### Test 2: Article Extraction
**Requirements:** Internet connection, optional ScraperAPI key
**Tests:**
- Fetching full article HTML
- Extracting article text using BeautifulSoup
- Handling different website structures

**Example output:**
```
✓ Successfully extracted 2,450 characters

Preview (first 300 chars):
Scientists announced a breakthrough in renewable energy technology today...
```

### Test 3: Comprehend Analysis
**Requirements:** AWS credentials, Internet connection
**Tests:**
- Amazon Comprehend sentiment detection
- Key phrase extraction
- Text analysis

**Example output:**
```
✓ Analysis complete:
  Sentiment: POSITIVE
  Key Phrases: renewable energy, breakthrough, solar panels, carbon emissions
  Summary: Scientists announced a breakthrough in renewable energy technology...
```

### Test 4: Full Pipeline (No Email)
**Requirements:** AWS credentials (for Comprehend), Internet connection
**Tests:**
- Complete workflow without sending email
- Generates HTML and text email files for review
- Processes multiple articles

**Output files:**
- `test_email_output.html` - HTML email preview
- `test_email_output.txt` - Plain text email preview

**Example:**
```bash
python test_local.py
# Select option 4
# Review generated files: test_email_output.html and test_email_output.txt
```

### Test 5: Full Pipeline (With Email)
**Requirements:** 
- AWS credentials
- Verified SES sender email
- Verified recipient emails (if in SES sandbox)
- Internet connection

**Tests:**
- Complete workflow including email sending
- Actual email delivery

**⚠️ Warning:** This sends a real email!

## Testing Without AWS Comprehend

If you want to test without AWS Comprehend (to save free tier usage), you can modify the function temporarily:

1. Comment out Comprehend calls
2. Use mock sentiment/key phrases
3. Test the rest of the pipeline

Example modification:
```python
def analyze_article_with_comprehend(self, text: str) -> Dict[str, Any]:
    # Mock for local testing
    return {
        'summary': text[:200] + '...' if len(text) > 200 else text,
        'sentiment': 'NEUTRAL',
        'key_phrases': ['sample', 'keywords']
    }
```

## Common Issues

### "No module named 'lambda_function'"
**Solution:** Run from the correct directory:
```bash
cd packages/functions/daily_news_summary
python test_local.py
```

### "AWS credentials not found"
**Solution:** Set up AWS credentials (see above) or skip tests that require AWS (tests 3-5)

### "Email sending failed"
**Solution:** 
- Ensure sender email is verified in SES
- Ensure recipient email is verified (if in SES sandbox)
- Check AWS credentials have SES permissions

### "RSS feed fetch failed"
**Solution:**
- Check internet connection
- Verify RSS feed URLs are accessible
- Some feeds may block automated requests (use ScraperAPI if needed)

### "Comprehend error"
**Solution:**
- Check AWS region supports Comprehend
- Verify AWS credentials
- Check you haven't exceeded free tier limits

## Expected Test Duration

- **Test 1 (RSS):** ~5-10 seconds
- **Test 2 (Extraction):** ~10-30 seconds (depends on article)
- **Test 3 (Comprehend):** ~2-5 seconds
- **Test 4 (Full, no email):** ~2-5 minutes (processes 3 articles)
- **Test 5 (Full, with email):** ~2-5 minutes + email delivery time

## Next Steps

After successful local testing:
1. Review generated email output files
2. Adjust RSS feeds or email template if needed
3. Deploy to AWS using Terraform
4. Verify EventBridge Scheduler is configured
5. Test first scheduled execution

## Tips

1. **Start with Test 1** to verify RSS feeds work
2. **Use Test 4** to preview email without sending
3. **Save API calls** by limiting articles in tests (already done)
4. **Review output files** to customize email template
5. **Test with different RSS feeds** by setting `RSS_FEED_URLS`

