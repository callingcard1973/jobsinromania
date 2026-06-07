# Deploy FastAPI to raspibig via GitHub
# Usage: .\deploy.ps1 "commit message"
# Example: .\deploy.ps1 "add auth endpoints"

param(
    [string]$Message = "deploy: code update",
    [string]$Host = "192.168.100.21",
    [string]$User = "tudor",
    [string]$Password = "bucare"
)

$PuTTYPath = "C:\Program Files\PuTTY\plink.exe"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ssZ"

Write-Host "[$timestamp] FastAPI Deployment Pipeline" -ForegroundColor Cyan
Write-Host "Commit message: $Message"
Write-Host ""

# Step 1: Git commit and push (from D:\MEMORY parent)
Write-Host "[$timestamp] Step 1: Committing to git..." -ForegroundColor Green
Push-Location D:\MEMORY
try {
    git add COWORK/FASTAPI/ -q
    $status = git status --porcelain COWORK/FASTAPI/

    if ($status) {
        git commit -m "deploy: FASTAPI — $Message" -q
        Write-Host "[$timestamp]   ✅ Changes committed"
    } else {
        Write-Host "[$timestamp]   ℹ️  No changes to commit"
    }

    git push -q
    Write-Host "[$timestamp]   ✅ Pushed to GitHub"
} finally {
    Pop-Location
}

# Step 2: Deploy on raspibig
Write-Host ""
Write-Host "[$timestamp] Step 2: Deploying to raspibig..." -ForegroundColor Green

$deployCmd = @"
# Pull latest code
cd /tmp && rm -rf deploy_fastapi && git clone https://github.com/callingcard1973/jobsinromania.git deploy_fastapi --quiet && cd deploy_fastapi

# Copy to active directory
cp -r COWORK/FASTAPI/* /opt/ACTIVE/FASTAPI/ 2>/dev/null

# Install dependencies
cd /opt/ACTIVE/FASTAPI && pip install --quiet -r requirements.txt

# Restart service
systemctl --user restart fastapi.service

echo '[$(date '+%Y-%m-%d %H:%M:%SZ')] Deployment complete'
"@

try {
    $output = & $PuTTYPath -batch -pw $Password "$User@$Host" $deployCmd 2>&1
    Write-Host $output
    Write-Host "[$timestamp]   ✅ Deployed to raspibig"
} catch {
    Write-Host "[$timestamp]   ❌ Deployment failed: $_" -ForegroundColor Red
    exit 1
}

# Step 3: Verify
Write-Host ""
Write-Host "[$timestamp] Step 3: Verifying service..." -ForegroundColor Green

Start-Sleep -Seconds 2

$verifyCmd = "curl -s http://127.0.0.1:8000/api/health 2>/dev/null || echo 'Service warming up...'"
$result = & $PuTTYPath -batch -pw $Password "$User@$Host" $verifyCmd
Write-Host "[$timestamp]   Response: $result"

$statusCmd = "systemctl --user is-active fastapi.service"
$active = & $PuTTYPath -batch -pw $Password "$User@$Host" $statusCmd
if ($active.Trim() -eq "active") {
    Write-Host "[$timestamp]   ✅ Service is active (running)"
} else {
    Write-Host "[$timestamp]   ⚠️  Service state: $active"
}

Write-Host ""
Write-Host "[$timestamp] ✅ Deployment complete" -ForegroundColor Green
Write-Host "Endpoints:"
Write-Host "  - http://127.0.0.1:8000/api/health (internal)"
Write-Host "  - https://api.interjob.ro/api/health (external, after Caddy config)"
