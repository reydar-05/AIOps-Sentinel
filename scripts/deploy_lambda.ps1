# AIOps Sentinel — Lambda Deployment Script
# Packages all Lambda code and deploys to AWS

param(
    [string]$Region      = "ap-south-1",
    [string]$FunctionName = "aiops-incident-processor-dev",
    [string]$ZipFile     = "lambda_package.zip"
)

Write-Host "`nAIOps Sentinel — Lambda Deployment" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

# ── Step 1: Clean old package ──────────────────────────────────────
Write-Host "`n[1/5] Cleaning old package..." -ForegroundColor Yellow
if (Test-Path $ZipFile) { Remove-Item $ZipFile -Force }
if (Test-Path "package_tmp") { Remove-Item "package_tmp" -Recurse -Force }

# ── Step 2: Install dependencies into temp folder ──────────────────
Write-Host "[2/5] Installing dependencies..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "package_tmp" | Out-Null
pip install boto3 -t package_tmp/ --quiet

# ── Step 3: Copy Lambda source files ──────────────────────────────
Write-Host "[3/5] Copying Lambda source files..." -ForegroundColor Yellow

$sources = @(
    "lambda\incident_processor",
    "lambda\log_processor",
    "lambda\ai_analyzer",
    "lambda\notification_handler",
    "ai\prompts"
)

foreach ($src in $sources) {
    if (Test-Path $src) {
        Copy-Item "$src\*.py" "package_tmp\" -Force
        Write-Host "  Copied: $src" -ForegroundColor Gray
    }
}

# ── Step 4: Create ZIP ─────────────────────────────────────────────
Write-Host "[4/5] Creating deployment ZIP..." -ForegroundColor Yellow
Compress-Archive -Path "package_tmp\*" -DestinationPath $ZipFile -Force
$sizeMB = [math]::Round((Get-Item $ZipFile).Length / 1MB, 2)
Write-Host "  Package size: $sizeMB MB" -ForegroundColor Gray

# ── Step 5: Deploy to AWS Lambda ──────────────────────────────────
Write-Host "[5/5] Deploying to AWS Lambda..." -ForegroundColor Yellow
aws lambda update-function-code `
    --function-name $FunctionName `
    --zip-file fileb://$ZipFile `
    --region $Region `
    --output table

# ── Cleanup ────────────────────────────────────────────────────────
Remove-Item "package_tmp" -Recurse -Force

Write-Host "`nDeployment complete!" -ForegroundColor Green
Write-Host "Function: $FunctionName" -ForegroundColor Green
Write-Host "Region:   $Region`n" -ForegroundColor Green
