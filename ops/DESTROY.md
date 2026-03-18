# Destroy AWS Infrastructure

Use this to tear down all World Brief AWS resources and stop costs.

## Prerequisites

- **AWS CLI** configured with credentials that can manage the resources
- **Terraform** installed
- Same `ops/configs/qa.tfvars` values used during deployment (or update them)

## Quick Destroy (PowerShell)

From the **project root**:

```powershell
.\ops\destroy.ps1
```

This destroys in order: **API → Infra → CICD**.

## Manual Destroy

If the script fails, run these in order from the project root:

### 1. API (Lambda, DynamoDB, EventBridge, IAM)

```powershell
cd ops\iac\api
terraform init -reconfigure
terraform destroy -var-file="../../configs/qa.tfvars" -auto-approve
cd ..\..
```

**Note:** If `build_daily_news` is missing, create it first:
```powershell
mkdir -Force ops\iac\api\lambda\build_daily_news
echo "# placeholder" > ops\iac\api\lambda\build_daily_news\__init__.py
```

### 2. Infra (VPC, S3, Bedrock, OpenSearch)

```powershell
cd ops\iac\infra
terraform init -reconfigure
terraform destroy -var-file="../../configs/qa.tfvars" -auto-approve
cd ..\..
```

### 3. CICD (CodePipeline, CodeBuild, CodeStar)

```powershell
cd ops\cicd
terraform init -reconfigure
terraform destroy -var-file="../configs/qa.tfvars" -auto-approve
cd ..\..
```

## Config Updates

`ops/configs/qa.tfvars` must include variables for all stacks. If destroy fails with "variable not set", add:

- `enable_nat_gateway` (infra)
- `kb_oss_collection_name` (infra) — must match deployed value
- `map_migrated_tag`, `provider_type`, `repository_branch`, `repository_path`, `terraform_state_bucket` (CICD/infra)

## State Bucket

Terraform state is stored in `world-brief-qa-state`. After destroying all stacks, you can optionally delete the bucket and its contents to remove any remaining data.

## Troubleshooting

- **"Secret not found"** — The API references Secrets Manager. Delete the Lambda first, or ensure the secret exists.
- **"Resource in use"** — Destroy in the order above. Infra depends on nothing; API depends on Infra; CICD is independent.
- **"Variable not defined"** — Add the missing variable to `qa.tfvars` or pass it with `-var "name=value"`.
