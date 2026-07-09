# inspect_env_usage.ps1 — cum e consumat /opt/ACTIVE/ANOFM/.env (raspi .20) - READ ONLY
param(
    [string]$RaspiHost = "192.168.100.20",
    [string]$User      = "tudor",
    [string]$Pw        = "RASPI_PW_REDACTED"
)
$ErrorActionPreference = "Continue"
$ts      = Get-Date -Format "yyyyMMdd_HHmmss"
$outDir  = Join-Path $PSScriptRoot "DATA\RASPI"
if (!(Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }
$outFile = Join-Path $outDir "raspi_envusage_$ts.txt"

$remote = @'
echo "=== files referencing ANOFM/.env ==="; grep -rln "ANOFM/.env" /opt/ACTIVE 2>/dev/null
echo; echo "=== run_anofm_campaign.py : env-related lines ==="; grep -nE "dotenv|load_dotenv|environ|getenv|[.]env|subprocess|os.system|Popen|source" /opt/ACTIVE/EMAIL/CAMPAIGNS/run_anofm_campaign.py 2>/dev/null
echo; echo "=== run_anofm_campaign.py : first 50 lines ==="; sed -n "1,50p" /opt/ACTIVE/EMAIL/CAMPAIGNS/run_anofm_campaign.py 2>/dev/null
echo; echo "=== campaign_anofm_angajatori.py : env-related lines ==="; grep -nE "dotenv|load_dotenv|environ|getenv|[.]env" /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/campaign_anofm_angajatori.py 2>/dev/null | head -20
echo; echo "=== any .sh that sources the .env ==="; grep -rnE "source .*[.]env|^[.] .*[.]env|ANOFM/[.]env" /opt/ACTIVE --include=*.sh 2>/dev/null | head -20
echo; echo "=== ingest_anofm.py : db/env lines ==="; grep -nE "dbname|host=|password|connect|psycopg|PG_|getenv|dotenv" /opt/ACTIVE/INTERJOB/ingest/ingest_anofm.py 2>/dev/null | head -20
echo; echo "=== units EnvironmentFile/ExecStart ==="; for u in anofm-ingest anofm-scraper anofm-audience-rebuild; do echo "[$u.service]"; systemctl cat $u.service 2>/dev/null | grep -iE "EnvironmentFile|ExecStart|^User="; done
echo; echo "=== python-dotenv installed? ==="; python3 -c "import dotenv; print('dotenv', dotenv.__version__)" 2>&1
echo; echo "=== DONE ==="
'@

$remoteLf  = $remote -replace "`r`n", "`n"
$remoteB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($remoteLf))
$remoteCmd = "echo $remoteB64 | base64 --decode | bash"

$plinkArgs = @("-batch")
if ($Pw -ne "") { $plinkArgs += @("-pw", $Pw) }
$plinkArgs += @("$User@$RaspiHost", $remoteCmd)

$header = "ANOFM .env usage inspection`nHost: $RaspiHost   $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n=====================================================`n"
$result = try { & plink @plinkArgs 2>&1 } catch { "EROARE plink: $_" }
($header + ($result -join "`n")) | Out-File -FilePath $outFile -Encoding UTF8
Write-Host "Raport: $outFile"
