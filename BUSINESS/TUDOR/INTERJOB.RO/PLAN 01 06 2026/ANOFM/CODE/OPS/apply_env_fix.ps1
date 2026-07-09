# apply_env_fix.ps1 — drop-in care scoate EnvironmentFile din unit-urile ingest+audience (raspi .20)
# NU modifica .env (sender-ul are nevoie de prefixul 'export'). Reversibil: sterge drop-in + daemon-reload.
param(
    [string]$RaspiHost = "192.168.100.20",
    [string]$User      = "tudor",
    [string]$Pw        = "RASPI_PW_REDACTED"
)
$ErrorActionPreference = "Continue"
$ts      = Get-Date -Format "yyyyMMdd_HHmmss"
$outDir  = Join-Path $PSScriptRoot "DATA\RASPI"
if (!(Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }
$outFile = Join-Path $outDir "raspi_envfix_$ts.txt"

$remote = @'
echo "=== BEFORE: EnvironmentFile in units ==="; for u in anofm-ingest anofm-audience-rebuild; do echo "[$u]"; systemctl cat $u.service 2>/dev/null | grep -i EnvironmentFile || echo "  (none)"; done
echo; echo "=== applying drop-in overrides (clear EnvironmentFile) ==="
for u in anofm-ingest anofm-audience-rebuild; do
  sudo mkdir -p /etc/systemd/system/$u.service.d
  printf "[Service]\nEnvironmentFile=\n" | sudo tee /etc/systemd/system/$u.service.d/zz-no-envfile.conf >/dev/null && echo "override written: $u"
done
echo; echo "=== daemon-reload ==="; sudo systemctl daemon-reload && echo "reloaded OK"
echo; echo "=== AFTER: drop-in visible ==="; for u in anofm-ingest anofm-audience-rebuild; do echo "[$u]"; systemctl cat $u.service 2>/dev/null | grep -iE "no-envfile|EnvironmentFile" || echo "  EnvironmentFile cleared"; done
echo; echo "=== test ingest run (expect NO 'Ignoring invalid environment') ==="; sudo systemctl start anofm-ingest.service; sleep 6; echo "result: $(systemctl show anofm-ingest.service -p Result --value)"; journalctl -u anofm-ingest.service --since "-1 min" --no-pager 2>/dev/null | tail -12
echo; echo "=== warnings still present today? (should be only old ones) ==="; echo "count since this run:"; journalctl -u anofm-ingest.service --since "-1 min" --no-pager 2>/dev/null | grep -c "Ignoring invalid environment"
echo; echo "=== DB ok ==="; sudo -u postgres psql anofm_db -tAc "SELECT 'total='||count(*) FROM ij_jobs;"
echo; echo "=== DONE ==="
'@

$remoteLf  = $remote -replace "`r`n", "`n"
$remoteB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($remoteLf))
$remoteCmd = "echo $remoteB64 | base64 --decode | bash"

$plinkArgs = @("-batch")
if ($Pw -ne "") { $plinkArgs += @("-pw", $Pw) }
$plinkArgs += @("$User@$RaspiHost", $remoteCmd)

$header = "ANOFM .env systemd fix (drop-in)`nHost: $RaspiHost   $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n=====================================================`n"
$result = try { & plink @plinkArgs 2>&1 } catch { "EROARE plink: $_" }
($header + ($result -join "`n")) | Out-File -FilePath $outFile -Encoding UTF8
Write-Host "Raport: $outFile"
