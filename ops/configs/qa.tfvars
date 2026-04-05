aws_account_id = "796973508449"
aws_region     = "us-east-1"
environment    = "qa"
log_retention  = 14
project_name   = "world-brief"

# Infra (for destroy)
enable_nat_gateway       = false
kb_oss_collection_name  = "world-brief-qa-kb"
map_migrated_tag        = "d-server-12345678"
terraform_state_bucket  = "world-brief-qa-state"
provider_type           = "GitHub"
repository_branch       = "main"
repository_path         = "yllka-bi/world-brief"

# Use existing CodeConnections connection (skip creating new one)
connection_arn          = "arn:aws:codeconnections:us-east-1:082455449324:connection/d7e9ff35-6192-407a-8f5e-fbb9d2de776b"

# Daily News Summary Configuration
# IMPORTANT: Sender email must be verified in AWS SES before deployment
rss_feed_urls    = "https://feeds.bbci.co.uk/news/rss.xml,https://feeds.bbci.co.uk/news/world/rss.xml,https://www.theguardian.com/world/rss,https://www.npr.org/rss/rss.php?id=1001,https://feeds.bbci.co.uk/news/business/rss.xml,https://www.theguardian.com/business/rss,https://feeds.reuters.com/reuters/businessNews,https://techcrunch.com/feed/,https://www.theverge.com/rss/index.xml,https://feeds.bbci.co.uk/news/technology/rss.xml,https://feeds.bbci.co.uk/news/science_and_environment/rss.xml,https://www.npr.org/rss/rss.php?id=1007,https://www.theguardian.com/science/rss"
email_recipients = "yllka.bicaj@student.uni-pr.edu"
sender_email     = "yllka.bj@gmail.com"
bedrock_model_id = "amazon.nova-lite-v1:0"
