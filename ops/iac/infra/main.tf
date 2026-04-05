terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    key = "ops/iac/infra/terraform.tfstate"
    bucket = "world-brief-qa-state"
    region = "us-east-1"
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

module "vpc" {
  source = "./modules/vpc"

  aws_region         = var.aws_region
  enable_nat_gateway = var.enable_nat_gateway
  environment        = var.environment
  project_name       = var.project_name
  aws_account_id     = var.aws_account_id
  availability_zones = data.aws_availability_zones.available.names
}

module "bedrock" {
  source = "./modules/bedrock/"

  environment            = var.environment
  kb_oss_collection_name = var.kb_oss_collection_name
  project_name           = var.project_name
}