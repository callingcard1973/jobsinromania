# Sync Python skills from laptop to raspibig
# Usage: .\sync_skills.ps1
# Uploads D:\MEMORY\CODE\ACTIVE\SKILLS\*.py to raspibig:/opt/ACTIVE/SKILLS/

param(
    [string]$RaspibigIP = "192.168.100.21",
    [string]$User = "tudor"
)

$PuTTYPath = "C:\Program Files\PuTTY\plink.exe"
$PSCPPath = "C:\Program Files\PuTTY\pscp.exe"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ssZ"

# Secure password input
$securePassword = Read-Host "Enter password for $User@$RaspibigIP" -AsSecureString
$Password = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToCoTaskMemUnicode($securePassword))

Write-Host "[$timestamp] Skills Sync Pipeline" -ForegroundColor Cyan
Write-Host ""

# Get skill files
$skillsPath = "D:\MEMORY\CODE\ACTIVE\SKILLS"
$files = @(Get-ChildItem "$skillsPath\*.py" -ErrorAction SilentlyContinue)
$count = $files.Count

Write-Host "[$timestamp] Syncing $count skills..." -ForegroundColor Green

# Prepare remote directory
$prepCmd = "mkdir -p /opt/ACTIVE/SKILLS"
& $PuTTYPath -batch -pw $Password "$User@$RaspibigIP" $prepCmd | Out-Null

# Upload all files at once via pscp (faster than one-by-one)
try {
    $sourceGlob = "$skillsPath\*.py"
    $targetPath = "$User@$RaspibigIP`:/opt/ACTIVE/SKILLS/"

    # Use -r flag to recurse, but since we're targeting *.py directly, just copy
    & $PSCPPath -batch -pw $Password $sourceGlob $targetPath

    Write-Host "  ✅ Uploaded $count files"
} catch {
    Write-Host "  ❌ Upload failed: $_" -ForegroundColor Red
    exit 1
}

# Verify on remote
$verifyCmd = "ls /opt/ACTIVE/SKILLS/*.py 2>/dev/null | wc -l"
$remoteCount = & $PuTTYPath -batch -pw $Password "$User@$RaspibigIP" $verifyCmd

Write-Host "[$timestamp] Remote count: $remoteCount" -ForegroundColor Cyan
if ([int]$remoteCount -eq $count) {
    Write-Host "✅ Verified: $remoteCount skills on raspibig"
} else {
    Write-Host "⚠️  Count mismatch: laptop=$count, raspibig=$remoteCount" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[$timestamp] ✅ SYNC COMPLETE" -ForegroundColor Green
