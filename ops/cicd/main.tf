terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    key = "ops/cicd/terraform.tfstate"
    bucket = "world-brief-qa-state"
    region = "us-east-1"
  }
}

provider "aws" {

  default_tags {
    tags = {
      Environment  = var.environment
      Project      = var.project_name
      ManagedBy    = "Terraform"
      map-migrated = var.map_migrated_tag
    }
  }
}

module "user"{
  source = "./modules/iam"

  environment = var.environment
  project_name = var.project_name
}

module "cicd_terraform_iac" {
  source = "./modules/cicd"

  aws_access_key_id           = var.aws_access_key_id
  aws_account_id              = var.aws_account_id
  aws_region                  = var.aws_region
  bucket_name                 = "${var.project_name}-ops-${var.aws_region}-bucket-${var.environment}"
  build_name                  = "${var.project_name}-ops-${var.environment}"
  buildspec_file_path         = "./ops/iac/infra/buildspec.yml" # OPS PIPLEINE
  codebuild_compute_image     = "aws/codebuild/standard:7.0"
  codebuild_compute_size      = "BUILD_GENERAL1_MEDIUM"
  codebuild_compute_type      = "LINUX_CONTAINER"
  codestar_connection         = "${var.project_name}-ops-gc-${var.environment}"
  environment                 = var.environment
  pipeline_name               = "${var.project_name}-ops-pipeline-${var.environment}"
  project_build_artifact_type = "CODEPIPELINE"
  project_name                = var.project_name
  provider_type               = var.provider_type
  repository_branch           = var.repository_branch
  repository_path             = var.repository_path
  role_name                   = "${var.project_name}_ops_project_role-${var.environment}"
  terraform_state_bucket      = var.terraform_state_bucket
  trigger_file_paths          = "ops/iac/infra/**"
  trigger_file_paths_excludes = "packages/**"
}

module "cicd_terraform_api" {
  source = "./modules/cicd"

  aws_access_key_id           = var.aws_access_key_id
  aws_account_id              = var.aws_account_id
  aws_region                  = var.aws_region
  bucket_name                 = "${var.project_name}-api-${var.aws_region}-bucket-${var.environment}"
  build_name                  = "${var.project_name}-api-${var.environment}"
  buildspec_file_path         = "./ops/iac/api/buildspec.yml"
  codebuild_compute_image     = "aws/codebuild/standard:7.0"
  codebuild_compute_size      = "BUILD_GENERAL1_MEDIUM"
  codebuild_compute_type      = "LINUX_CONTAINER"
  codestar_connection         = "${var.project_name}-api-gc-${var.environment}"
  environment                 = var.environment
  pipeline_name               = "${var.project_name}-api-pipeline-${var.environment}"
  project_build_artifact_type = "CODEPIPELINE"
  project_name                = var.project_name
  provider_type               = var.provider_type
  repository_branch           = var.repository_branch
  repository_path             = var.repository_path
  role_name                   = "${var.project_name}_api_project_role-${var.environment}"
  terraform_state_bucket      = var.terraform_state_bucket
  trigger_file_paths          = "packages/**,ops/iac/api/**"
  trigger_file_paths_excludes = "ops/iac/infra/**"
}