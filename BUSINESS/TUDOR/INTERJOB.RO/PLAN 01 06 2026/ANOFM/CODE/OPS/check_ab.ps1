param([string]$H,[string]$User="tudor",[string]$Pw="RASPI_PW_REDACTED")
$ts=Get-Date -Format "yyyyMMdd_HHmmss"
$o=Join-Path $PSScriptRoot "DATA\RASPI"; if(!(Test-Path $o)){New-Item -ItemType Directory -Path $o|Out-Null}
$f=Join-Path $o "raspi_AB_${H}_$ts.txt"
$remote=@'
HN=$(hostname); echo "=== HOSTNAME: $HN ==="
if [ "$HN" = "raspibig" ] || ip a | grep -q 192.168.100.21; then
  CSVDIR=/mnt/hdd/SCRAPER_DATA/csv/ANOFM; DB=interjob_master
else
  CSVDIR=/opt/ACTIVE/ANOFM_DATA/csv; DB=anofm_db
fi
echo "CSVDIR=$CSVDIR DB=$DB"
echo "=== PART A: scraper service show ==="
systemctl show anofm-scraper.service -p ActiveEnterTimestamp,ExecMainStatus,Result 2>&1
echo "=== PART A: newest CSV ==="
NEW=$(ls -t $CSVDIR/anofm*.csv 2>/dev/null | head -1)
if [ -n "$NEW" ]; then echo "FILE=$NEW"; stat -c 'mtime=%y' "$NEW"; echo "lines=$(wc -l < "$NEW")"; else echo "NO CSV FOUND in $CSVDIR"; ls -t $CSVDIR 2>&1 | head -5; fi
echo "=== PART A: scraper journal last 10 ==="
journalctl -u anofm-scraper.service -n 10 --no-pager 2>&1
echo "=== PART A: scraper FAILURE today? ==="
journalctl -u anofm-scraper.service --since today --no-pager 2>&1 | grep -iE "fail|error|traceback" | head -10
echo "=== PART B: timers ==="
for T in anofm-scraper anofm-ingest anofm-audience-rebuild; do echo "$T active=$(systemctl is-active $T.timer 2>&1) enabled=$(systemctl is-enabled $T.timer 2>&1)"; done
echo "=== PART B: DB counts ==="
if [ "$DB" = "interjob_master" ]; then
  echo "total_ij_jobs=$(sudo -u postgres psql $DB -tAc "SELECT count(*) FROM ij_jobs" 2>&1)"
  echo "active_anofm=$(sudo -u postgres psql $DB -tAc "SELECT count(*) FROM ij_jobs WHERE source='anofm' AND status='active'" 2>&1)"
  echo "created_today=$(sudo -u postgres psql $DB -tAc "SELECT count(*) FROM ij_jobs WHERE created_at::date=CURRENT_DATE" 2>&1)"
else
  echo "tables:"; sudo -u postgres psql $DB -tAc "SELECT tablename FROM pg_tables WHERE schemaname='public'" 2>&1 | head -20
  echo "anofm_jobs_total=$(sudo -u postgres psql $DB -tAc "SELECT count(*) FROM anofm_jobs" 2>&1)"
  echo "anofm_jobs_today=$(sudo -u postgres psql $DB -tAc "SELECT count(*) FROM anofm_jobs WHERE created_at::date=CURRENT_DATE" 2>&1)"
fi
echo "=== PART B: sent-today per campaign ==="
TODAY=$(date +%Y-%m-%d)
for C in ANOFM_ANGAJATORI PRIMARII FACTORY_RO CANDIDATE_BROADCAST; do
  D=/opt/ACTIVE/EMAIL/CAMPAIGNS/$C
  if [ -d "$D" ]; then
    SC=$(find "$D" -name 'sent.csv' 2>/dev/null | head -1)
    SJ=$(find "$D" -name 'sent.json' 2>/dev/null | head -1)
    if [ -n "$SC" ]; then echo "$C sent.csv today=$(grep -c "$TODAY" "$SC" 2>/dev/null)"; fi
    if [ -n "$SJ" ]; then echo "$C sent.json today=$(grep -o "$TODAY" "$SJ" 2>/dev/null | wc -l)"; fi
    if [ -z "$SC" ] && [ -z "$SJ" ]; then echo "$C no sent file"; fi
  else echo "$C dir absent"; fi
done
echo "=== PART B: disk / ==="; df -h / 2>&1 | tail -1
echo "=== PART B: uptime/load ==="; uptime 2>&1
echo "=== PART B: ingest failures today ==="
journalctl -u anofm-ingest.service --since today --no-pager 2>&1 | grep -iE "fail|error|traceback" | head -10
echo "=== PART D: ingest invalid env count ==="
echo "ignoring_invalid_env=$(journalctl -u anofm-ingest.service --since today --no-pager 2>&1 | grep -c 'Ignoring invalid environment')"
echo "=== PART D: crontab ==="; crontab -l 2>&1
echo "=== PART C: locate .env with GMAIL_APP_PASSWORD ==="
grep -rl "GMAIL_APP_PASSWORD" /opt/ACTIVE 2>/dev/null | head -10
echo "=== DONE ==="
'@
$lf=$remote -replace "`r`n","`n"; $b=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($lf))
$a=@("-batch","-pw",$Pw,"$User@$H","echo $b | base64 --decode | bash")
$r= try { & plink @a 2>&1 } catch { "ERR $_" }
("host=$H`n"+($r -join "`n"))|Out-File $f -Encoding UTF8; Write-Host $f
