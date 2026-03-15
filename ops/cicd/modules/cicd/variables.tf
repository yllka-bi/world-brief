variable "aws_access_key_id" {}
variable "aws_account_id" {}
variable "aws_region" {}
variable "bucket_name" {}
variable "build_name" {}
variable "buildspec_file_path" {}
variable "codebuild_compute_image" {}
variable "codebuild_compute_size" {}
variable "codebuild_compute_type" {}
variable "codebuild_source_type" { default = "" }
variable "codebuild_source_version" { default = "" }
variable "codestar_connection" {}
variable "environment" {}
variable "pipeline_name" {}
variable "project_build_artifact_type" {}
variable "project_description" { default = "" }
variable "project_name" {}
variable "provider_type" {}
variable "repository_branch" {}
variable "repository_path" {}
variable "role_name" {}
variable "terraform_state_bucket" {}
variable "trigger_file_paths_excludes" {} // optional "packages/**"
variable "trigger_file_paths" {} // optional "ops/iac/**"
