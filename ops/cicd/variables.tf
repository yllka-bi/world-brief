variable "aws_access_key_id" { default = "" }
variable "aws_account_id" {}
variable "connection_arn" {
  description = "Optional. Use existing CodeConnections ARN instead of creating a new connection."
  type        = string
  default     = ""
}
variable "aws_region" {}
variable "environment" {}
variable "map_migrated_tag" {}
variable "project_name" {}
variable "provider_type" {}
variable "repository_branch" {}
variable "repository_path" {}
variable "terraform_state_bucket" {}
