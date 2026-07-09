#!/usr/bin/env pwsh
# Sync DNC suppression list from raspibig (canonical) to this laptop mirror.
# Read-only pull; never writes back to raspibig. Run before audience build.
[CmdletBinding()]
param(
    [string]$Host_ = "192.168.100.21",
    [string]$User = "tudor"
)
$ErrorActionPreference = "Stop"
# SSH password: read from env RASPIBIG_PASS — never hardcoded (secret, pre-push blocked).
$Pass = $env:RASPIBIG_PASS
if (-not $Pass) { Write-Error "Set $env:RASPIBIG_PASS before running (raspibig SSH password)."; exit 3 }
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$plink = "C:\Program Files\PuTTY\plink.exe"
$pscp  = "C:\Program Files\PuTTY\pscp.exe"
$remote = "${User}@${Host_}"
$base = "/opt/ACTIVE/EMAIL/CAMPAIGNS"
$files = @("dnc_list.csv", "dnc_bounces.txt")

foreach ($f in $files) {
    $src = "${base}/${f}"
    $dst = Join-Path $here $f
    Write-Host "Pull $src -> $dst"
    & $pscp -batch -pw $Pass "${remote}:$src" $dst
    if ($LASTEXITCODE -ne 0) { Write-Error "pscp failed for $f (exit $LASTEXITCODE)"; exit 2 }
}
# sanity: count rows in dnc_list.csv
$csv = Join-Path $here "dnc_list.csv"
if (Test-Path $csv) {
    $n = (Get-Content $csv | Measure-Object -Line).Lines
    Write-Host "dnc_list.csv lines: $n"
}
Get-Date -Format o | Out-File (Join-Path $here ".last_sync") -Encoding ascii
Write-Host "DNC sync done."
