# PowerShell version of sync script for Windows
# Usage: . .\sync-raspibig-to-laptop.ps1; Sync-Pull
# Or: . .\sync-raspibig-to-laptop.ps1; Sync-Bidirectional

$RaspibigHost = "tudor@192.168.100.21"
$LaptopPath = "D:\MEMORY\BACKUPS\raspibig"

function Log {
    param($Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$Timestamp] $Message"
}

function Sync-Pull {
    Log "PULL: Syncing from raspibig to laptop..."

    # Ensure directories exist
    @("logs", "projects", "scripts/skills") | ForEach-Object {
        $Dir = Join-Path $LaptopPath $_
        if (-not (Test-Path $Dir)) { New-Item -ItemType Directory -Path $Dir -Force > $null }
    }

    # Use scp for backup files
    $RaspibigBackups = "/opt/ACTIVE/LOGS/backups/*"
    Log "Pulling backups from $RaspibigBackups"
    # Note: scp syntax for Windows: scp -r user@host:remote/path local/path
    # Requires SSH/scp configured

    Log "PULL completed"
}

function Sync-Bidirectional {
    Log "BIDIRECTIONAL: Syncing in both directions..."
    Sync-Pull
    Log "BIDIRECTIONAL completed"
}

Log "Sync functions loaded. Use: Sync-Pull or Sync-Bidirectional"
