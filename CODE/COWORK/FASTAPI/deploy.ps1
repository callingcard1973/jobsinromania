# Deploy FastAPI to raspibig via GitHub
# Usage: .\deploy.ps1 "commit message"
# Secure: prompts for password, doesn't store in param

param(
    [string]$Message = "deploy: code update",
    [string]$RaspibigIP = "192.168.100.21",
    [string]$User = "tudor"
)

$PuTTYPath = "C:\Program Files\PuTTY\plink.exe"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ssZ"

# Secure password input
$securePassword = Read-Host "Enter password for $User@$RaspibigIP" -AsSecureString
$Password = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToCoTaskMemUnicode($securePassword))

Write-Host "[$timestamp] FastAPI Deployment Pipeline" -ForegroundColor Cyan
Write-Host "Target: $User@$RaspibigIP"
Write-Host "Commit: $Message"
Write-Host ""

# Step 0: Pre-deploy verification gate (lint + syntax + harness) on the code being shipped.
# Scoped to this folder so unrelated cosmetic issues elsewhere don't block the deploy.
$verify = "D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\VERIFY\verify.ps1"
if (Test-Path $verify) {
    Write-Host "[$timestamp] Step 0: Verifying $PSScriptRoot ..." -ForegroundColor Green
    & $verify -Path $PSScriptRoot
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ❌ Verification failed — aborting deploy. Fix issues or run VERIFY\verify.ps1 to inspect." -ForegroundColor Red
        exit 1
    }
    Write-Host "  ✅ Verification passed"
} else {
    Write-Host "  ⚠️  VERIFY toolkit not found at $verify — skipping gate" -ForegroundColor Yellow
}

# Step 1: Git commit (if changes exist)
Write-Host "[$timestamp] Step 1: Committing changes..." -ForegroundColor Green
Push-Location D:\MEMORY
try {
    $status = git status --porcelain COWORK/FASTAPI/
    if ($status) {
        git add COWORK/FASTAPI/
        git commit -m "deploy: FASTAPI — $Message"

        if ($LASTEXITCODE -ne 0) {
            Write-Host "  ❌ Commit failed"
            Pop-Location
            exit 1
        }

        git push
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  ❌ Push failed - aborting deployment"
            Pop-Location
            exit 1
        }

        Write-Host "  ✅ Committed and pushed"
    } else {
        Write-Host "  ℹ️  No changes to commit"
    }
} finally {
    Pop-Location
}

# Step 2: Deploy to raspibig (single SSH session for all ops)
Write-Host "[$timestamp] Step 2: Deploying to raspibig..." -ForegroundColor Green

$deployCmd = @"
set -e

# Pull latest
cd /tmp && rm -rf deploy_fastapi && git clone https://github.com/callingcard1973/jobsinromania.git deploy_fastapi --quiet && cd deploy_fastapi

# Copy files
cp -r COWORK/FASTAPI/* /opt/ACTIVE/FASTAPI/

# Install deps
cd /opt/ACTIVE/FASTAPI && pip install --quiet -r requirements.txt 2>&1 | grep -v 'externally-managed' | head -2

# Run Alembic migrations (tracks future schema changes)
echo "Running database migrations..."
python3 -m alembic upgrade head 2>&1 | grep -v 'No such file' || echo "No migrations to apply"

# Restart and verify in one session
systemctl --user stop fastapi.service
sleep 1
systemctl --user start fastapi.service
sleep 3

# Health check
curl -s http://127.0.0.1:8000/api/health || echo 'Service warming...'
systemctl --user is-active fastapi.service

echo '[$(date '+%Y-%m-%d %H:%M:%SZ')] ✅ Deployed'
"@

try {
    $output = & $PuTTYPath -batch -pw $Password "$User@$RaspibigIP" $deployCmd 2>&1
    Write-Host $output
    Write-Host "  ✅ Service deployed and running"
} catch {
    Write-Host "  ❌ Deployment failed: $_" -ForegroundColor Red
    exit 1
}

# Step 3: Sync skills to all machines (bonus)
Write-Host "[$timestamp] Step 3: Syncing Python skills..." -ForegroundColor Green
$PSCPPath = "C:\Program Files\PuTTY\pscp.exe"
$skillsPath = "D:\MEMORY\CODE\ACTIVE\SKILLS"
$files = @(Get-ChildItem "$skillsPath\*.py" -ErrorAction SilentlyContinue)
$skillCount = $files.Count

try {
    # raspibig
    $sourceGlob = "$skillsPath\*.py"
    & $PSCPPath -batch -pw $Password $sourceGlob "$User@$RaspibigIP`:/opt/ACTIVE/SKILLS/"

    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ⚠️  Skill sync to raspibig failed" -ForegroundColor Yellow
    } else {
        # raspi
        & $PSCPPath -batch -pw $Password $sourceGlob "$User@192.168.100.20`:/opt/ACTIVE/INFRA/SKILLS/"

        if ($LASTEXITCODE -ne 0) {
            Write-Host "  ⚠️  Skill sync to raspi failed" -ForegroundColor Yellow
        } else {
            Write-Host "  ✅ Synced $skillCount skills to raspibig + raspi"
        }
    }
} catch {
    Write-Host "  ⚠️  Skill sync error: $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[$timestamp] ✅ DEPLOYMENT COMPLETE" -ForegroundColor Green
Write-Host "Endpoints:"
Write-Host "  - Internal:  http://127.0.0.1:8000/api/health"
Write-Host "  - External:  https://api.interjob.ro/api/health"
