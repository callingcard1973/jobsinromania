# fix_and_ingest.ps1 — forteaza ingest + investigheaza esec 15:52 + diag .env pe raspi (192.168.100.20)
param(
    [string]$RaspiHost = "192.168.100.20",
    [string]$User      = "tudor",
    [string]$Pw        = "RASPI_PW_REDACTED"
)
$ErrorActionPreference = "Continue"
$ts      = Get-Date -Format "yyyyMMdd_HHmmss"
$outDir  = Join-Path $PSScriptRoot "DATA\RASPI"
if (!(Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }
$outFile = Join-Path $outDir "raspi_fix_ingest_$ts.txt"

$remote = @'
echo "=== BEFORE counts ==="; sudo -u postgres psql anofm_db -tAc "SELECT 'total='||count(*) FROM ij_jobs;"; sudo -u postgres psql anofm_db -tAc "SELECT 'maxcreated='||max(created_at) FROM ij_jobs;"; sudo -u postgres psql anofm_db -tAc "SELECT 'today='||count(*) FROM ij_jobs WHERE created_at::date=CURRENT_DATE;"
echo; echo "=== FORCE INGEST now ==="; sudo systemctl start anofm-ingest.service; sleep 8; echo "is-active: $(systemctl is-active anofm-ingest.service)"; echo "result: $(systemctl show anofm-ingest.service -p Result --value)"
echo; echo "=== this ingest run log ==="; journalctl -u anofm-ingest.service --since "-3 min" --no-pager 2>/dev/null | grep -viE "Ignoring invalid environment" | tail -25
echo; echo "=== AFTER counts ==="; sudo -u postgres psql anofm_db -tAc "SELECT 'total='||count(*) FROM ij_jobs;"; sudo -u postgres psql anofm_db -tAc "SELECT 'maxcreated='||max(created_at) FROM ij_jobs;"; sudo -u postgres psql anofm_db -tAc "SELECT 'today='||count(*) FROM ij_jobs WHERE created_at::date=CURRENT_DATE;"
echo; echo "=== FAILURE investigation (today, no secret lines) ==="; journalctl -u anofm-ingest.service --since today --no-pager 2>/dev/null | grep -viE "Ignoring invalid environment" | grep -iE "process|insert|skip|error|trace|exception|status=|fail|exited|Traceback|Error|csv" | tail -40
echo; echo "=== unit config ==="; systemctl cat anofm-ingest.service 2>/dev/null | grep -iE "EnvironmentFile|ExecStart|WorkingDirectory|^User=|Environment="
echo; echo "=== how ingest script loads env ==="; grep -nE "dotenv|load_dotenv|environ|getenv|\.env" /opt/ACTIVE/INTERJOB/ingest/ingest_anofm.py 2>/dev/null | head -15
echo; echo "=== who else references the .env (run scripts) ==="; grep -rln "ANOFM/.env" /opt/ACTIVE 2>/dev/null | head
echo; echo "=== .env structure (values masked) ==="; sudo sed -E 's/(=).*/\1<masked>/' /opt/ACTIVE/ANOFM/.env 2>/dev/null
echo; echo "=== DONE ==="
'@

$remoteLf  = $remote -replace "`r`n", "`n"
$remoteB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($remoteLf))
$remoteCmd = "echo $remoteB64 | base64 --decode | bash"

$plinkArgs = @("-batch")
if ($Pw -ne "") { $plinkArgs += @("-pw", $Pw) }
$plinkArgs += @("$User@$RaspiHost", $remoteCmd)

$header = "ANOFM raspi FIX+INGEST`nHost: $RaspiHost   $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n=====================================================`n"
$result = try { & plink @plinkArgs 2>&1 } catch { "EROARE plink: $_" }
($header + ($result -join "`n")) | Out-File -FilePath $outFile -Encoding UTF8
Write-Host "Raport: $outFile"
