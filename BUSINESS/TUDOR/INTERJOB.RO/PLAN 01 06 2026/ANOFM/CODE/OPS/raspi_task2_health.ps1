param([string]$RaspiHost="192.168.100.20",[string]$User="tudor",[string]$Pw="RASPI_PW_REDACTED")
$ts=Get-Date -Format "yyyyMMdd_HHmmss"
$outDir=Join-Path $PSScriptRoot "DATA\RASPI"; if(!(Test-Path $outDir)){New-Item -ItemType Directory -Path $outDir|Out-Null}
$outFile=Join-Path $outDir "raspi_task2_health_$ts.txt"

# ---- Python health-check script (kept here as a single-quoted literal to avoid PS interpolation) ----
$py=@'
#!/usr/bin/env python3
import subprocess, smtplib, datetime, os, sys
from email.mime.text import MIMEText

ENV_PATH = "/opt/ACTIVE/ANOFM/.env"
TO_ADDR = "fruitnature4@gmail.com"
CSV_DIR = "/opt/ACTIVE/ANOFM_DATA/csv"
SENT_CSV = "/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/sent.csv"

def load_env(path):
    env = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line.startswith("export "):
                    continue
                line = line[len("export "):]
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip()
                if len(v) >= 2 and v[0] in "\"'" and v[-1] == v[0]:
                    v = v[1:-1]
                env[k] = v
    except Exception as e:
        print("env load error:", e)
    return env

def run(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        return out if out else ("[stderr] " + err if err else "(no output)")
    except Exception as e:
        return "ERR: " + str(e)

def newest_csv(d):
    try:
        files = [os.path.join(d, f) for f in os.listdir(d)
                 if f.endswith(".csv") and os.path.isfile(os.path.join(d, f))]
        if not files:
            return "(no csv files)"
        newest = max(files, key=os.path.getmtime)
        mt = datetime.datetime.fromtimestamp(os.path.getmtime(newest)).strftime("%Y-%m-%d %H:%M:%S")
        return "%s  (mtime %s)" % (os.path.basename(newest), mt)
    except Exception as e:
        return "ERR: " + str(e)

def sent_stats(path):
    try:
        if not os.path.exists(path):
            return "(sent.csv not found)"
        total = 0
        today = datetime.date.today().isoformat()
        today_n = 0
        with open(path, errors="replace") as f:
            for line in f:
                total += 1
                if today in line:
                    today_n += 1
        return "lines=%d  sent_today(approx by date match)=%d" % (total, today_n)
    except Exception as e:
        return "ERR: " + str(e)

def main():
    env = load_env(ENV_PATH)
    user = env.get("GMAIL_USER")
    pw = env.get("GMAIL_APP_PASSWORD")
    today = datetime.date.today().isoformat()

    lines = []
    lines.append("ANOFM raspi health check  %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("=" * 50)
    lines.append("")
    lines.append("[TIMERS]")
    for t in ("anofm-scraper.timer", "anofm-ingest.timer", "anofm-audience-rebuild.timer"):
        act = run("systemctl is-active %s" % t)
        en = run("systemctl is-enabled %s" % t)
        lines.append("  %-32s active=%s  enabled=%s" % (t, act, en))
    lines.append("")
    lines.append("[DATABASE ij_jobs]")
    total = run('sudo -u postgres psql anofm_db -tAc "SELECT count(*) FROM ij_jobs;"')
    active = run("sudo -u postgres psql anofm_db -tAc \"SELECT count(*) FROM ij_jobs WHERE source='anofm' AND status='active';\"")
    todayc = run("sudo -u postgres psql anofm_db -tAc \"SELECT count(*) FROM ij_jobs WHERE created_at::date = CURRENT_DATE;\"")
    lines.append("  total rows       : %s" % total)
    lines.append("  active anofm     : %s" % active)
    lines.append("  created today    : %s" % todayc)
    lines.append("")
    lines.append("[NEWEST CSV] (%s)" % CSV_DIR)
    lines.append("  " + newest_csv(CSV_DIR))
    lines.append("")
    lines.append("[SENT.CSV]")
    lines.append("  " + sent_stats(SENT_CSV))
    lines.append("")
    lines.append("[DISK /]")
    lines.append("  " + run("df -h / | tail -1"))
    lines.append("")
    lines.append("[INGEST LOG last 8]")
    log = run("journalctl -u anofm-ingest.service -n 8 --no-pager")
    for l in log.splitlines():
        lines.append("  " + l)
    lines.append("")
    body = "\n".join(lines)

    if not user or not pw:
        print("MISSING CREDS: GMAIL_USER or GMAIL_APP_PASSWORD not found in env")
        print(body)
        sys.exit(1)

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = "ANOFM raspi health %s" % today
    msg["From"] = user
    msg["To"] = TO_ADDR
    try:
        s = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60)
        s.login(user, pw)
        s.sendmail(user, [TO_ADDR], msg.as_string())
        s.quit()
        print("HEALTH_EMAIL_OK")
    except Exception as e:
        print("SEND_FAILED:", repr(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
'@

# Build base64 of the python file (UTF8, LF line endings)
$pyLf = $py -replace "`r`n","`n"
$pyB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($pyLf))

# Remote bash: write python via base64, test-run it, install cron idempotently
$remote=@"
echo "=== WRITE health script ==="
echo $pyB64 | base64 --decode | sudo tee /opt/ACTIVE/INTERJOB/anofm_health_check.py >/dev/null && echo "wrote /opt/ACTIVE/INTERJOB/anofm_health_check.py"
sudo chmod +x /opt/ACTIVE/INTERJOB/anofm_health_check.py
ls -la /opt/ACTIVE/INTERJOB/anofm_health_check.py
echo "=== ENSURE LOG DIR ==="
mkdir -p /opt/ACTIVE/INFRA/LOGS && echo "log dir ok"
echo "=== TEST RUN ==="
python3 /opt/ACTIVE/INTERJOB/anofm_health_check.py 2>&1
echo "=== INSTALL CRON (idempotent) ==="
CRON_LINE='0 8 * * * /usr/bin/python3 /opt/ACTIVE/INTERJOB/anofm_health_check.py >> /opt/ACTIVE/INFRA/LOGS/anofm_health.log 2>&1'
CUR="`$(crontab -l 2>/dev/null)"
if echo "`$CUR" | grep -Fq "anofm_health_check.py"; then
  echo "cron already present, not adding"
else
  printf '%s\n%s\n' "`$CUR" "`$CRON_LINE" | grep -v '^`$' | crontab -
  echo "cron added"
fi
echo "=== CRONTAB -L ==="
crontab -l
echo "=== DONE TASK2 ==="
"@

$remoteLf=$remote -replace "`r`n","`n"
$b64=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($remoteLf))
$plinkArgs=@("-batch","-pw",$Pw,"$User@$RaspiHost","echo $b64 | base64 --decode | bash")
$res= try { & plink @plinkArgs 2>&1 } catch { "EROARE plink: $_" }
("TASK2 HEALTH REPORT $ts`n"+($res -join "`n"))|Out-File -FilePath $outFile -Encoding UTF8
Write-Host "Raport: $outFile"
