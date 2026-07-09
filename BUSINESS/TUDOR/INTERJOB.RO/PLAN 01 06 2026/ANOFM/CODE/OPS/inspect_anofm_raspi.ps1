# inspect_anofm_raspi.ps1
# Health-check pentru pipeline-ul ANOFM de pe raspi (192.168.100.20).
# Rezultatul se scrie in ANOFM\DATA\RASPI\raspi_health_<timestamp>.txt
#
# Rulare (din folderul ANOFM):
#   powershell -ExecutionPolicy Bypass -File .\inspect_anofm_raspi.ps1 -Pw 'PAROLA_SSH'
# Daca folosesti cheie SSH (fara parola), lasa -Pw gol:
#   powershell -ExecutionPolicy Bypass -File .\inspect_anofm_raspi.ps1

param(
    [string]$RaspiHost = "192.168.100.20",
    [string]$User      = "tudor",
    [string]$Pw        = ""
)

$ErrorActionPreference = "Continue"
$ts      = Get-Date -Format "yyyyMMdd_HHmmss"
$outDir  = Join-Path $PSScriptRoot "DATA\RASPI"
if (!(Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }
$outFile = Join-Path $outDir "raspi_health_$ts.txt"

# Comenzile de diagnostic rulate pe raspi (un singur bloc, output etichetat)
$remote = @'
echo "=== HOST ==="; hostname; uptime
echo; echo "=== TIMERS anofm ==="; systemctl list-timers "anofm-*" --all --no-pager 2>/dev/null
echo; echo "=== TIMER STATUS ==="; for t in anofm-scraper anofm-ingest anofm-audience-rebuild; do en=$(systemctl is-enabled $t.timer 2>/dev/null); ac=$(systemctl is-active $t.timer 2>/dev/null); printf "%-28s enabled=%s active=%s\n" "$t.timer" "$en" "$ac"; done
echo; echo "=== DB anofm_db ==="; sudo -u postgres psql anofm_db -tAc "SELECT count(*) FROM ij_jobs;" 2>&1; sudo -u postgres psql anofm_db -tAc "SELECT count(*) FROM ij_jobs WHERE source='anofm' AND status='active';" 2>&1
echo; echo "=== LATEST CSV ==="; ls -lt /opt/ACTIVE/ANOFM_DATA/csv/ 2>/dev/null | head -5; echo "rows in newest:"; f=$(ls -t /opt/ACTIVE/ANOFM_DATA/csv/*.csv 2>/dev/null | head -1); if [ -n "$f" ]; then echo "$f"; wc -l "$f"; else echo "no csv found"; fi
echo; echo "=== TMP leftovers ==="; ls -l /opt/ACTIVE/ANOFM_DATA/csv/*.tmp 2>/dev/null || echo none
echo; echo "=== SENT csv ==="; s=/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/sent.csv; if [ -f "$s" ]; then wc -l "$s"; echo "--- last 5 ---"; tail -5 "$s"; echo "--- sent today ---"; grep "$(date +%F)" "$s" | wc -l; else echo "sent.csv not found"; fi
echo; echo "=== DISK ==="; df -h /opt 2>/dev/null; echo "csv dir size:"; du -sh /opt/ACTIVE/ANOFM_DATA/csv/ 2>/dev/null
echo; echo "=== SCRAPER LOG last 15 ==="; (journalctl -u anofm-scraper.service -n 15 --no-pager 2>/dev/null || sudo journalctl -u anofm-scraper.service -n 15 --no-pager 2>/dev/null || tail -15 /opt/ACTIVE/INFRA/LOGS/ingest_anofm.log 2>/dev/null || echo "no log")
echo; echo "=== DONE ==="
'@

# Normalizeaza la LF si encodeaza base64 -> evita probleme de shell (zsh vs bash, paranteze, quoting)
$remoteLf  = $remote -replace "`r`n", "`n"
$remoteB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($remoteLf))
$remoteCmd = "echo $remoteB64 | base64 --decode | bash"

# Construieste comanda plink
$plinkArgs = @("-batch")
if ($Pw -ne "") { $plinkArgs += @("-pw", $Pw) }
$plinkArgs += @("$User@$RaspiHost", $remoteCmd)

Write-Host "Inspectez raspi ($RaspiHost) ... output -> $outFile"

$header = @"
ANOFM raspi health check
Host: $RaspiHost   User: $User
Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
=====================================================
"@

$result = $null
try {
    $result = & plink @plinkArgs 2>&1
} catch {
    $result = "EROARE la plink: $_`nVerifica daca plink este in PATH si daca parola/cheia SSH e corecta."
}

$header + "`n" + ($result -join "`n") | Out-File -FilePath $outFile -Encoding UTF8
Write-Host "Gata. Raport salvat in: $outFile"
Write-Host "------ PREVIEW ------"
Get-Content $outFile -Tail 40
