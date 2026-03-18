terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.2"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
  backend "s3" {
    key    = "ops/iac/api/terraform.tfstate"
    bucket = "world-brief-qa-state"
    region = "us-east-1"
  }
}

module "lambda" {
  source = "./lambda"

  aws_region     = var.aws_region
  environment    = var.environment
  project_name   = var.project_name
  aws_account_id = var.aws_account_id
  log_retention  = var.log_retention

  rss_feed_urls    = var.rss_feed_urls
  email_recipients = var.email_recipients
  sender_email     = var.sender_email
  bedrock_model_id = var.bedrock_model_id
}
