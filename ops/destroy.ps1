# Destroy AWS infrastructure to stop costs
# Run from project root. Requires: AWS CLI configured, Terraform installed.
# Order: API -> Infra -> CICD (reverse of deployment)

param(
    [switch]$SkipApi,
    [switch]$SkipInfra,
    [switch]$SkipCicd,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$ConfigPath = Join-Path $ProjectRoot "ops\configs\qa.tfvars"

function Invoke-TerraformDestroy {
    param([string]$Dir, [string]$Description)
    Push-Location $Dir
    try {
        Write-Host "`n=== $Description ===" -ForegroundColor Cyan
        if ($DryRun) {
            Write-Host "[DRY RUN] Would run: terraform init, terraform destroy" -ForegroundColor Yellow
            return
        }
        terraform init -reconfigure
        terraform destroy -var-file="$ConfigPath" -auto-approve
    } finally {
        Pop-Location
    }
}

# Ensure we're in project root
Set-Location $ProjectRoot

Write-Host "Destroying World Brief QA infrastructure..." -ForegroundColor Yellow
Write-Host "Config: $ConfigPath" -ForegroundColor Gray

# 1. API (Lambda, DynamoDB, EventBridge, etc.)
if (-not $SkipApi) {
    # API Lambda needs build_daily_news - create minimal if missing
    $BuildDir = Join-Path $ProjectRoot "ops\iac\api\lambda\build_daily_news"
    if (-not (Test-Path $BuildDir)) {
        Write-Host "Creating minimal build_daily_news for destroy..." -ForegroundColor Gray
        New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
        "# Placeholder for destroy" | Out-File -FilePath (Join-Path $BuildDir "__init__.py") -Encoding utf8
    }
    Invoke-TerraformDestroy -Dir "ops\iac\api" -Description "Destroying API (Lambda, DynamoDB, EventBridge)"
} else {
    Write-Host "Skipping API (use -SkipApi to skip)" -ForegroundColor Gray
}

# 2. Infra (VPC, S3, Bedrock, OpenSearch)
if (-not $SkipInfra) {
    Invoke-TerraformDestroy -Dir "ops\iac\infra" -Description "Destroying Infra (VPC, S3, Bedrock, OpenSearch)"
} else {
    Write-Host "Skipping Infra" -ForegroundColor Gray
}

# 3. CICD (CodePipeline, CodeBuild, CodeStar)
if (-not $SkipCicd) {
    Invoke-TerraformDestroy -Dir "ops\cicd" -Description "Destroying CICD (Pipelines, CodeBuild)"
} else {
    Write-Host "Skipping CICD" -ForegroundColor Gray
}

Write-Host "`nDone. Infrastructure destroyed." -ForegroundColor Green
