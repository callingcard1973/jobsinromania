param([string]$H="192.168.100.21",[string]$User="tudor",[string]$Pw="RASPI_PW_REDACTED")
$ts=Get-Date -Format "yyyyMMdd_HHmmss"
$o=Join-Path $PSScriptRoot "DATA\RASPI"; if(!(Test-Path $o)){New-Item -ItemType Directory -Path $o|Out-Null}
$f=Join-Path $o "raspi_bigemail_$ts.txt"
$remote=@'
set +e
echo "=== A) CRED DISCOVERY ==="
grep -rl "GMAIL_MANPOWER_DRISTOR_APP_PASSWORD" /opt/ACTIVE 2>/dev/null | head
echo "--- matching lines ---"
grep -rhE "GMAIL_MANPOWER_DRISTOR_(USER|APP_PASSWORD)|elena.manpower.dristor" /opt/ACTIVE 2>/dev/null | sort -u | head

echo "=== B) WRITE HEALTH SCRIPT ==="
PYB64='__PYB64__'
echo "$PYB64" | base64 --decode | sudo tee /opt/ACTIVE/INTERJOB/anofm_health_check.py >/dev/null
sudo chmod +x /opt/ACTIVE/INTERJOB/anofm_health_check.py
echo "wrote bytes:"; sudo wc -c /opt/ACTIVE/INTERJOB/anofm_health_check.py

echo "=== C) TEST RUN ==="
python3 /opt/ACTIVE/INTERJOB/anofm_health_check.py 2>&1

echo "=== D) INSTALL CRON ==="
mkdir -p /opt/ACTIVE/INFRA/LOGS 2>/dev/null
CRONLINE='5 8 * * * /usr/bin/python3 /opt/ACTIVE/INTERJOB/anofm_health_check.py >> /opt/ACTIVE/INFRA/LOGS/anofm_health.log 2>&1'
( crontab -l 2>/dev/null | grep -F "anofm_health_check.py" ) >/dev/null
if crontab -l 2>/dev/null | grep -qF "anofm_health_check.py"; then
  echo "cron already present"
else
  ( crontab -l 2>/dev/null; echo "$CRONLINE" ) | crontab -
  echo "cron installed"
fi
echo "--- crontab tail ---"
crontab -l | tail -5
echo "=== DONE ==="
'@
$py=@'
#!/usr/bin/env python3
import subprocess, datetime, smtplib, glob, os, traceback
from email.mime.text import MIMEText

GMAIL_USER = "__GMAIL_USER__"
GMAIL_PASS = "__GMAIL_PASS__"
TO = "fruitnature4@gmail.com"

def sh(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception as e:
        return "ERR: %s" % e

def psql(q):
    return sh('sudo -u postgres psql interjob_master -tAc "%s"' % q)

today = datetime.date.today().isoformat()
L = []
L.append("ANOFM raspibig health  %s" % today)
L.append("=" * 50)

L.append("\n[TIMERS] active / enabled")
for t in ["anofm-scraper", "anofm-ingest", "anofm-audience-rebuild"]:
    a = sh("systemctl is-active %s.timer" % t)
    e = sh("systemctl is-enabled %s.timer" % t)
    L.append("  %-26s %s / %s" % (t, a, e))

L.append("\n[DATABASE] interjob_master.ij_jobs")
L.append("  total ij_jobs   : %s" % psql("SELECT count(*) FROM ij_jobs;"))
L.append("  active anofm    : %s" % psql("SELECT count(*) FROM ij_jobs WHERE source='anofm' AND status='active';"))
L.append("  created today   : %s" % psql("SELECT count(*) FROM ij_jobs WHERE created_at::date = CURRENT_DATE;"))

L.append("\n[CSV] /mnt/hdd/SCRAPER_DATA/csv/ANOFM/")
csvdir = "/mnt/hdd/SCRAPER_DATA/csv/ANOFM/"
try:
    files = glob.glob(os.path.join(csvdir, "*.csv"))
    if files:
        newest = max(files, key=os.path.getmtime)
        mt = datetime.datetime.fromtimestamp(os.path.getmtime(newest)).strftime("%Y-%m-%d %H:%M:%S")
        lc = sh("wc -l < '%s'" % newest)
        L.append("  newest : %s" % os.path.basename(newest))
        L.append("  mtime  : %s" % mt)
        L.append("  lines  : %s" % lc)
    else:
        L.append("  (no csv files found)")
except Exception as e:
    L.append("  ERR: %s" % e)

L.append("\n[CAMPAIGNS] sent today")
sent_csv = "/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/sent.csv"
if os.path.exists(sent_csv):
    n = sh("grep -c '%s' '%s'" % (today, sent_csv))
    L.append("  ANOFM_ANGAJATORI : %s" % n)
else:
    L.append("  ANOFM_ANGAJATORI : (sent.csv not found)")
sent_json = "/opt/ACTIVE/EMAIL/CAMPAIGNS/CANDIDATE_BROADCAST/DATA/sent.json"
if os.path.exists(sent_json):
    n = sh("grep -o '%s' '%s' | wc -l" % (today, sent_json))
    L.append("  CANDIDATE_BCAST  : %s" % n)
else:
    L.append("  CANDIDATE_BCAST  : (sent.json not found)")

L.append("\n[SYSTEM]")
L.append("  disk / : " + sh("df -h / | tail -1"))
L.append("  uptime : " + sh("uptime"))

L.append("\n[INGEST LOG] journalctl -u anofm-ingest -n 8")
L.append(sh("journalctl -u anofm-ingest.service -n 8 --no-pager"))

body = "\n".join(L)
print(body)

try:
    msg = MIMEText(body)
    msg["Subject"] = "ANOFM raspibig health %s" % today
    msg["From"] = GMAIL_USER
    msg["To"] = TO
    s = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30)
    s.login(GMAIL_USER, GMAIL_PASS)
    s.sendmail(GMAIL_USER, [TO], msg.as_string())
    s.quit()
    print("HEALTH_EMAIL_OK")
except Exception:
    print("HEALTH_EMAIL_FAIL")
    traceback.print_exc()
'@
$py = $py -replace "__GMAIL_USER__","elena.manpower.dristor@gmail.com" -replace "__GMAIL_PASS__","xibcxpuzqxfmcaei"
$pylf = $py -replace "`r`n","`n"
$pyb = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($pylf))
$remote = $remote -replace "__PYB64__",$pyb
$lf=$remote -replace "`r`n","`n"; $b=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($lf))
$a=@("-batch","-pw",$Pw,"$User@$H","echo $b | base64 --decode | bash")
$r= try { & plink @a 2>&1 } catch { "ERR $_" }
("host=$H`n"+($r -join "`n"))|Out-File $f -Encoding UTF8; Write-Host $f
