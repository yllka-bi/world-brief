variable "aws_account_id" {}
variable "aws_region" {}
variable "environment" {}
variable "log_retention" {}
variable "project_name" {}

# Daily News Summary variables
variable "rss_feed_urls" {
  description = "Comma-separated list of RSS feed URLs"
  type        = string
  default     = "https://feeds.bbci.co.uk/news/rss.xml,https://feeds.bbci.co.uk/news/world/rss.xml,https://www.theguardian.com/world/rss,https://www.npr.org/rss/rss.php?id=1001,https://feeds.bbci.co.uk/news/business/rss.xml,https://www.theguardian.com/business/rss,https://feeds.reuters.com/reuters/businessNews,https://techcrunch.com/feed/,https://www.theverge.com/rss/index.xml,https://feeds.bbci.co.uk/news/technology/rss.xml,https://feeds.bbci.co.uk/news/science_and_environment/rss.xml,https://www.npr.org/rss/rss.php?id=1007,https://www.theguardian.com/science/rss"
}

variable "email_recipients" {
  description = "Comma-separated list of email recipients"
  type        = string
  default     = ""
}

variable "sender_email" {
  description = "Verified SES sender email address"
  type        = string
  default     = ""
}
