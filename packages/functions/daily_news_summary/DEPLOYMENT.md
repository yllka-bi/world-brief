# Deployment Guide - Daily News Summary Lambda

## Overview

This Lambda function automatically generates and emails a daily news summary every morning at 8 AM UTC using Amazon EventBridge Scheduler. It's fully compatible with AWS Free Tier.

## Pre-Deployment Checklist

### 1. Amazon SES Setup

**IMPORTANT:** Before deployment, you must:

1. **Verify Sender Email:**
   - Go to AWS SES Console
   - Navigate to "Verified identities"
   - Click "Create identity"
   - Enter your email address and verify it

2. **Verify Recipient Emails (if in SES Sandbox):**
   - AWS Free Tier starts in "Sandbox" mode
   - In Sandbox, you can only send to verified email addresses
   - Verify all recipient email addresses OR
   - Request production access (takes 24-48 hours)

3. **Request Production Access (Optional but Recommended):**
   - In SES Console, go to "Account dashboard"
   - Click "Request production access"
   - Fill out the form (typically approved in 24-48 hours)

### 2. Environment Variables

Set these variables in your Terraform `tfvars` files or pass them during deployment:

```hcl
rss_feed_urls   = "https://feeds.bbci.co.uk/news/rss.xml,https://www.reutersagency.com/feed/?best-topics=business-finance,https://techcrunch.com/feed/"
email_recipients = "your-email@example.com,another-email@example.com"
sender_email     = "sender@example.com"  # Must be verified in SES
```

### 3. Optional: ScraperAPI Key

If you want better article extraction success rates, add your ScraperAPI key to AWS Secrets Manager:

1. Go to AWS Secrets Manager
2. Create a secret at: `/{project_name}/{environment}/serpapi/`
3. Add key `SCRAPERAPI_KEY` with your API key value

## Deployment Steps

### 1. Update Terraform Variables

Add to your `ops/configs/{environment}.tfvars`:

```hcl
rss_feed_urls   = "https://feeds.bbci.co.uk/news/rss.xml,https://techcrunch.com/feed/"
email_recipients = "your-email@example.com"
sender_email     = "sender@example.com"
```

### 2. Deploy Infrastructure

```bash
cd ops/iac/api
terraform init
terraform plan -var-file="../../configs/qa.tfvars"  # or prod.tfvars
terraform apply -var-file="../../configs/qa.tfvars"
```

### 3. Verify EventBridge Scheduler

After deployment:
1. Go to Amazon EventBridge Console
2. Click "Schedules" in left menu
3. Find schedule: `{project_name}-daily-news-schedule-{environment}`
4. Verify it's set to run at 8:00 AM UTC daily

### 4. Test Lambda Manually (Optional)

Before waiting for the scheduled run, you can test manually:

1. Go to AWS Lambda Console
2. Find function: `{project_name}-daily-news-{environment}`
3. Click "Test" and use empty event: `{}`
4. Check CloudWatch Logs for execution

## Free Tier Compatibility

All services used are compatible with AWS Free Tier:

- **Lambda**: 1M requests/month, 400,000 GB-seconds/month
  - Daily execution: ~30 requests/month (well within limit)
  - Memory: 512 MB
  - Execution time: ~2-3 minutes (estimated)

- **EventBridge Scheduler**: 14 million invocations/month
  - Daily execution: ~30 invocations/month (well within limit)

- **Amazon Comprehend**: 50,000 characters/month (free tier)
  - Each article analyzed: ~5,000 characters
  - Articles per day: ~10 (stays within free tier)
  - **Note:** Function limits articles to stay within budget

- **Amazon SES**: 62,000 emails/month (from verified addresses)
  - Daily email: 1 email per day = ~30/month (well within limit)

- **CloudWatch Logs**: 5 GB ingestion/month
  - Estimated logs: ~50 MB/month (well within limit)

## Monitoring

### CloudWatch Logs

View execution logs:
- Log Group: `/aws/lambda/{project_name}-daily-news-{environment}`
- Check for any errors in RSS fetching, article processing, or email sending

### SES Sending Statistics

Monitor email delivery:
- Go to SES Console → Sending statistics
- Check bounce/complaint rates
- Review delivery metrics

### Lambda Metrics

Monitor function performance:
- Go to Lambda Console → Monitoring tab
- Check:
  - Invocations
  - Duration
  - Errors
  - Throttles

## Troubleshooting

### Email Not Sending

1. **Check SES Verification:**
   - Ensure sender email is verified
   - Ensure recipient emails are verified (if in Sandbox)

2. **Check IAM Permissions:**
   - Verify Lambda role has `ses:SendEmail` and `ses:SendRawEmail` permissions

3. **Check CloudWatch Logs:**
   - Look for SES error codes
   - Common errors:
     - `MessageRejected`: Sender not verified
     - `MailFromDomainNotVerified`: Domain not verified (if using custom domain)

### No Articles Found

1. **Check RSS Feed URLs:**
   - Verify URLs are accessible
   - Test in browser
   - Check feed format (should be valid RSS/Atom)

2. **Check Network Connectivity:**
   - If Lambda is in VPC, ensure NAT Gateway or VPC endpoint configured
   - Consider removing VPC config for faster/cheaper execution

### Comprehend Errors

1. **Check Region:**
   - Ensure AWS_REGION has Comprehend available
   - Some regions don't support Comprehend

2. **Check Character Limits:**
   - Free tier: 50,000 characters/month
   - Function limits articles to stay within budget
   - If exceeded, function will use simple text extraction

3. **Check IAM Permissions:**
   - Verify Lambda role has Comprehend permissions

## Cost Estimation (Free Tier)

Monthly costs (assuming daily execution):

- **Lambda**: $0 (within free tier)
- **EventBridge Scheduler**: $0 (within free tier)
- **Amazon Comprehend**: $0 (within free tier)
- **Amazon SES**: $0 (within free tier)
- **CloudWatch Logs**: $0 (within free tier)

**Total: $0/month** (when staying within free tier limits)

## Post-Deployment

1. **Verify First Execution:**
   - Wait for next 8 AM UTC execution OR trigger manually
   - Check email inbox for daily summary
   - Review CloudWatch logs for any issues

2. **Monitor for First Week:**
   - Check daily execution logs
   - Verify email delivery
   - Monitor Comprehend usage (stay within free tier)

3. **Adjust as Needed:**
   - Modify RSS feeds via environment variable
   - Adjust article limits per category in code
   - Customize email template if desired

## Next Steps

- Customize email template in `lambda_function.py`
- Add more RSS feeds via `RSS_FEED_URLS` environment variable
- Adjust schedule time in Terraform (currently 8 AM UTC)
- Add custom categories by modifying `category_keywords` in code

