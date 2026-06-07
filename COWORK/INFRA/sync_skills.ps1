# Sync Python skills from laptop to raspibig + raspi
# Usage: .\sync_skills.ps1
# Unifies skills across all machines:
# - Laptop:   D:\MEMORY\CODE\ACTIVE\SKILLS\ (640 files, source)
# - raspibig: /opt/ACTIVE/SKILLS/ (target)
# - raspi:    /opt/ACTIVE/INFRA/SKILLS/ (target)

param(
    [string]$RaspibigIP = "192.168.100.21",
    [string]$RaspiIP = "192.168.100.20",
    [string]$User = "tudor"
)

$PuTTYPath = "C:\Program Files\PuTTY\plink.exe"
$PSCPPath = "C:\Program Files\PuTTY\pscp.exe"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ssZ"

# Secure password input
$securePassword = Read-Host "Enter password for $User" -AsSecureString
$Password = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToCoTaskMemUnicode($securePassword))

Write-Host "[$timestamp] Skills Sync Pipeline (All Machines)" -ForegroundColor Cyan
Write-Host ""

# Get skill files
$skillsPath = "D:\MEMORY\CODE\ACTIVE\SKILLS"
$files = @(Get-ChildItem "$skillsPath\*.py" -ErrorAction SilentlyContinue)
$count = $files.Count

Write-Host "Source: $count skills from laptop"
Write-Host ""

# ===== RASPIBIG =====
Write-Host "[$timestamp] Syncing to raspibig..." -ForegroundColor Green
try {
    $sourceGlob = "$skillsPath\*.py"
    $targetPath = "$User@$RaspibigIP`:/opt/ACTIVE/SKILLS/"
    & $PSCPPath -batch -pw $Password $sourceGlob $targetPath 2>&1 | Out-Null
    Write-Host "  ✅ Uploaded $count files to raspibig:/opt/ACTIVE/SKILLS/"
} catch {
    Write-Host "  ❌ raspibig sync failed: $_" -ForegroundColor Red
}

# ===== RASPI =====
Write-Host "[$timestamp] Syncing to raspi..." -ForegroundColor Green
try {
    $sourceGlob = "$skillsPath\*.py"
    $targetPath = "$User@$RaspiIP`:/opt/ACTIVE/INFRA/SKILLS/"
    & $PSCPPath -batch -pw $Password $sourceGlob $targetPath 2>&1 | Out-Null
    Write-Host "  ✅ Uploaded $count files to raspi:/opt/ACTIVE/INFRA/SKILLS/"
} catch {
    Write-Host "  ❌ raspi sync failed: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "[$timestamp] ✅ SYNC COMPLETE" -ForegroundColor Green
Write-Host "Unified structure:"
Write-Host "  - Laptop:   D:\MEMORY\CODE\ACTIVE\SKILLS\ ($count files)"
Write-Host "  - raspibig: /opt/ACTIVE/SKILLS/ (→ $count files)"
Write-Host "  - raspi:    /opt/ACTIVE/INFRA/SKILLS/ (→ $count files)"
