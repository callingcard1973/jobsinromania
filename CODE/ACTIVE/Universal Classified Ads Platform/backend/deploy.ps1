#!/usr/bin/env pwsh
param(
    [string]$Message = "Deploy Universal Classified Ads Platform"
)

$ErrorActionPreference = "Stop"

# Configuration
$RaspibigIP = "192.168.100.21"
$RaspibigUser = "tudor"
$RaspibigPass = "bucare"
$DeployPath = "/opt/ACTIVE/CLASSIFIED_ADS"
$LocalPath = Get-Location

Write-Host "=== Deploy Universal Classified Ads Platform ===" -ForegroundColor Cyan

# 1. Run tests
Write-Host "`n[1/5] Running tests..." -ForegroundColor Yellow
python -m pytest tests/test_auth.py -v --tb=short
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Tests failed" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Tests passed" -ForegroundColor Green

# 2. Git commit
Write-Host "`n[2/5] Git commit..." -ForegroundColor Yellow
git add -A
git commit -m "$Message" || Write-Host "  No changes to commit"
Write-Host "✓ Committed" -ForegroundColor Green

# 3. Git push
Write-Host "`n[3/5] Git push..." -ForegroundColor Yellow
git push origin main 2>&1 | Select-Object -First 10
Write-Host "✓ Pushed" -ForegroundColor Green

# 4. Deploy to raspibig
Write-Host "`n[4/5] Deploying to raspibig ($RaspibigIP)..." -ForegroundColor Yellow

$PuttyPath = "C:\Program Files\PuTTY\plink.exe"

$DeployCmd = @"
set -e
if [ ! -d $DeployPath ]; then
  mkdir -p $DeployPath
fi
cd $DeployPath
git init || true
git remote remove origin 2>/dev/null || true
git remote add origin https://github.com/user/classified-ads.git
git fetch origin main:main --force 2>&1 || git clone https://github.com/user/classified-ads.git . 2>&1
git checkout main
cd backend
pip install -r requirements.txt --quiet
python -m pytest tests/test_auth.py -v --tb=short
echo '✓ Deploy complete'
"@

& $PuttyPath -batch -pw $RaspibigPass `
    "$RaspibigUser@$RaspibigIP" $DeployCmd

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Raspibig deploy failed" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Deployed to raspibig" -ForegroundColor Green

# 5. Health check
Write-Host "`n[5/5] Health check..." -ForegroundColor Yellow
$HealthCmd = "cd $DeployPath/backend && python -c 'from app.core.config import get_settings; s = get_settings(); print(f\"Config loaded: {s.environment}\")'  "
& $PuttyPath -batch -pw $RaspibigPass `
    "$RaspibigUser@$RaspibigIP" $HealthCmd

Write-Host "`n✅ Deployment successful" -ForegroundColor Green
Write-Host "Deploy path: $DeployPath" -ForegroundColor Cyan
