<#
  verify.ps1 — single entrypoint for INTERJOB verification.
  Usage:
    .\verify.ps1                 # local layers: python lint + harness validator
    .\verify.ps1 -All            # also run db-contract + smoke (need SSH/DB to raspi/raspibig)
    .\verify.ps1 -Path "..\ANOFM"  # scope python/harness to a subfolder
#>
param(
  [string]$Path = "..",
  [switch]$All,
  [switch]$Db,
  [switch]$Smoke
)

$ErrorActionPreference = "Continue"
$here = $PSScriptRoot
$py = "python"
$fail = 0

function Run($label, $argv) {
  Write-Host "`n========== $label ==========" -ForegroundColor Cyan
  & $py @argv
  if ($LASTEXITCODE -ne 0) { $script:fail++; Write-Host "[$label] FAILED" -ForegroundColor Red }
  else { Write-Host "[$label] passed" -ForegroundColor Green }
}

function RunPytest($label, $target) {
  Write-Host "`n========== $label ==========" -ForegroundColor Cyan
  & $py -m pytest $target -q -p no:cacheprovider
  # exit 5 = "no tests collected" → not a failure for this scope
  if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 5) { $script:fail++; Write-Host "[$label] FAILED" -ForegroundColor Red }
  else { Write-Host "[$label] passed" -ForegroundColor Green }
}

Run "PYTHON LINT" @("$here\verify_python.py", $Path)
Run "HARNESS"     @("$here\verify_harness.py", $Path)
RunPytest "PYTEST" $Path

if ($All -or $Db)    { Run "DB CONTRACTS" @("$here\verify_db.py") }
if ($All -or $Smoke) { Run "SMOKE"        @("$here\verify_smoke.py") }

Write-Host "`n================================" -ForegroundColor Cyan
if ($fail -gt 0) { Write-Host "VERIFY: $fail layer(s) FAILED" -ForegroundColor Red; exit 1 }
Write-Host "VERIFY: ALL PASSED" -ForegroundColor Green
exit 0
