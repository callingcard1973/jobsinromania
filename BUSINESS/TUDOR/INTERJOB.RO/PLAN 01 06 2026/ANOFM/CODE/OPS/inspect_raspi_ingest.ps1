# inspect_raspi_ingest.ps1 — verifica ingest + prospetime DB pe raspi (192.168.100.20)
param(
    [string]$RaspiHost = "192.168.100.20",
    [string]$User      = "tudor",
    [string]$Pw        = "RASPI_PW_REDACTED"
)
$ErrorActionPreference = "Continue"
$ts      = Get-Date -Format "yyyyMMdd_HHmmss"
$outDir  = Join-Path $PSScriptRoot "DATA\RASPI"
if (!(Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }
$outFile = Join-Path $outDir "raspi_ingest_$ts.txt"

$remote = @'
echo "=== ij_jobs columns ==="; sudo -u postgres psql anofm_db -tAc "SELECT string_agg(column_name,', ') FROM information_schema.columns WHERE table_name='ij_jobs';"
echo; echo "=== counts ==="; sudo -u postgres psql anofm_db -tAc "SELECT 'total='||count(*) FROM ij_jobs;"; sudo -u postgres psql anofm_db -tAc "SELECT 'anofm_active='||count(*) FROM ij_jobs WHERE source='anofm' AND status='active';"
echo; echo "=== rows with today date (per timestamp col) ==="; for c in created_at updated_at ingested_at inserted_at last_seen scraped_at first_seen; do v=$(sudo -u postgres psql anofm_db -tAc "SELECT count(*) FROM ij_jobs WHERE ${c}::date = CURRENT_DATE;" 2>/dev/null); if [ -n "$v" ]; then echo "${c} today: ${v}"; fi; done
echo; echo "=== max timestamps ==="; for c in created_at updated_at ingested_at last_seen scraped_at; do v=$(sudo -u postgres psql anofm_db -tAc "SELECT max(${c}) FROM ij_jobs;" 2>/dev/null); if [ -n "$v" ]; then echo "max ${c}: ${v}"; fi; done
echo; echo "=== latest CSV files ==="; ls -lt /opt/ACTIVE/ANOFM_DATA/csv/*.csv 2>/dev/null | head -3
echo; echo "=== ingest service log last 25 ==="; (journalctl -u anofm-ingest.service -n 25 --no-pager 2>/dev/null || sudo journalctl -u anofm-ingest.service -n 25 --no-pager 2>/dev/null || tail -25 /opt/ACTIVE/INFRA/LOGS/ingest_anofm.log 2>/dev/null || echo "no log")
echo; echo "=== ingest timer ==="; systemctl list-timers anofm-ingest.timer --all --no-pager 2>/dev/null
echo; echo "=== DONE ==="
'@

$remoteLf  = $remote -replace "`r`n", "`n"
$remoteB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($remoteLf))
$remoteCmd = "echo $remoteB64 | base64 --decode | bash"

$plinkArgs = @("-batch")
if ($Pw -ne "") { $plinkArgs += @("-pw", $Pw) }
$plinkArgs += @("$User@$RaspiHost", $remoteCmd)

$header = "ANOFM raspi INGEST check`nHost: $RaspiHost   $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n=====================================================`n"
$result = try { & plink @plinkArgs 2>&1 } catch { "EROARE plink: $_" }
($header + ($result -join "`n")) | Out-File -FilePath $outFile -Encoding UTF8
Write-Host "Raport: $outFile"
