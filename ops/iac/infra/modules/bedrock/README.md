# Bedrock Terraform module

This folder contains the Terraform configuration for the "bedrock" module used by the project. It provisions the main infrastructure components required for the Bedrock environment (IAM resources, OpenSearch, and other core resources).

What you'll find here

- `main.tf` — Core resources and module wiring.
- `variables.tf` — Input variables and their defaults.
- `iam.tf` — IAM roles, policies and permissions.
- `open_search.tf` — OpenSearch (domain) resources and settings.
