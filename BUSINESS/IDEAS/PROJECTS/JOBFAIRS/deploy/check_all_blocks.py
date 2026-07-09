"""Check ALL blockers across the entire system."""
import requests, json, subprocess, os, psycopg2
from datetime import datetime

def run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except:
        return "TIMEOUT"

env = {}
with open('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env') as f:
    for l in f:
        if '=' in l and not l.startswith('#'):
            k, v = l.strip().split('=', 1)
            env[k] = v

print("=" * 70)
print("FULL BLOCKER REPORT — " + datetime.now().strftime("%Y-%m-%d %H:%M"))
print("=" * 70)

# 1. BREVO ACCOUNTS
print("\n1. BREVO BOUNCE RATES (threshold: 10%)")
accounts = [
    'BREVO_BUILDJOBS_API_KEY', 'BREVO_SEICARESCU_API_KEY',
    'BREVO_MIVROMANIA_API_KEY', 'BREVO_CAREWORKERS_API_KEY',
    'BREVO_FACTORYJOBS_API_KEY', 'BREVO_EXPATSINROMANIA_API_KEY',
    'BREVO_HORECAWORKERS2026_EU_API_KEY', 'BREVO_MEATWORKERS_API_KEY',
    'BREVO_WAREHOUSEWORKERS_API_KEY', 'BREVO_AGROEVOLUTION_API_KEY',
    'BREVO_CUMPARLEGUME_API_KEY', 'BREVO_CIFN_API_KEY', 'BREVO_BPPLTD_API_KEY',
]
for name in accounts:
    key = env.get(name, '')
    if not key:
        continue
    short = name.replace('BREVO_', '').replace('_API_KEY', '')
    try:
        r = requests.get('https://api.brevo.com/v3/smtp/statistics/aggregatedReport',
            headers={'api-key': key}, params={'days': 7}, timeout=10)
        if r.status_code == 200:
            d = r.json()
            t, h, s, b = d.get('requests', 0), d.get('hardBounces', 0), d.get('softBounces', 0), d.get('blocked', 0)
            rate = (h + s) / t * 100 if t else 0
            icon = "RED" if rate > 10 else "YEL" if rate > 5 else "GRN"
            print(f"  [{icon}] {short}: {t} sent, {h}H+{s}S ({rate:.1f}%) blocked={b}")
        elif r.status_code == 401:
            print(f"  [BAD] {short}: INVALID KEY")
    except Exception as e:
        print(f"  [ERR] {short}: {e}")

# 2. GMAIL ACCOUNTS
print("\n2. GMAIL APP PASSWORDS")
gmails = [k for k in env if k.startswith('GMAIL_') and 'PASSWORD' in k.upper()]
for g in sorted(set([k.replace('_APP_PASSWORD', '').replace('_PASSWORD', '') for k in env if 'GMAIL_' in k and ('USER' in k or 'EMAIL' in k)])):
    print(f"  {g}: configured")

# 3. ORCHESTRATOR
print("\n3. ORCHESTRATOR STATUS")
r = run("pgrep -f 'orchestrator.py.*configs'")
print(f"  PID: {r or 'NOT RUNNING'}")
r = run("tail -1 /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/logs/orchestrator.log")
print(f"  Last: {r[:100]}")

# 4. CAMPAIGNS BLOCKED BY BOUNCE
print("\n4. CAMPAIGNS THAT WOULD BE BLOCKED (bounce >10%)")
from pathlib import Path
for f in sorted(Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs').glob('*.json')):
    try:
        cfg = json.loads(f.read_text())
        if not cfg.get('enabled'):
            continue
        for sname, scfg in cfg.get('sectors', {}).items():
            if not scfg.get('enabled'):
                continue
            sender_key = scfg.get('sender_key', '')
            key = env.get(sender_key, '')
            if not key:
                continue
            try:
                r = requests.get('https://api.brevo.com/v3/smtp/statistics/aggregatedReport',
                    headers={'api-key': key}, params={'days': 7}, timeout=5)
                if r.status_code == 200:
                    d = r.json()
                    t = d.get('requests', 0)
                    h, s = d.get('hardBounces', 0), d.get('softBounces', 0)
                    rate = (h + s) / t * 100 if t else 0
                    if rate > 10:
                        print(f"  BLOCKED: {cfg['campaign_name']}/{sname} -> {sender_key} ({rate:.1f}%)")
            except:
                pass
    except:
        pass

# 5. DISK
print("\n5. DISK SPACE")
print("  " + run("df -h / | tail -1"))
print("  " + run("df -h /mnt/hdd | tail -1") if run("df -h /mnt/hdd 2>/dev/null") else "  HDD: not mounted")

# 6. SERVICES DOWN
print("\n6. SERVICES")
svcs = ["interjob-nanoclaw", "interjob-governor", "interjob-watchdog",
    "telegram-unified-controller", "telegram-moderation", "telegram-order-approval",
    "campaign-dashboard", "postgresql", "redis-server", "ollama", "caddy"]
for s in svcs:
    r = run(f"systemctl is-active {s}")
    if r != "active":
        print(f"  DOWN: {s} ({r})")

# 7. DB CONNECTIONS
print("\n7. DATABASE")
try:
    conn = psycopg2.connect(host="/var/run/postgresql", dbname="interjob_master",
        user="tudor", password="scraper123")
    cur = conn.cursor()
    cur.execute("SELECT pg_size_pretty(pg_database_size('interjob_master'))")
    print(f"  Size: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM pg_stat_activity WHERE state='active'")
    print(f"  Active connections: {cur.fetchone()[0]}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"  DB ERROR: {e}")

# 8. ZOHO SMTP
print("\n8. ZOHO SMTP")
zoho_user = env.get('ZOHO_EMAIL', '')
zoho_pass = env.get('ZOHO_PASSWORD', '')
if zoho_user and zoho_pass:
    print(f"  Account 1: {zoho_user} (configured)")
zoho_user2 = env.get('ZOHO_EMAIL_2', '')
zoho_pass2 = env.get('ZOHO_PASSWORD_2', '')
if zoho_user2 and zoho_pass2:
    print(f"  Account 2: {zoho_user2} (configured)")

# 9. A2 SMTP
print("\n9. A2 SMTP")
for k in env:
    if 'A2_' in k and 'PASSWORD' in k:
        short = k.replace('_PASSWORD', '')
        print(f"  {short}: configured")

# 10. RESPONSE TRACKER
print("\n10. RESPONSE TRACKER")
r = run("crontab -l | grep response_tracker")
print(f"  Cron: {'ACTIVE' if r else 'NOT INSTALLED'}")
try:
    conn = psycopg2.connect(host="/var/run/postgresql", dbname="interjob_master",
        user="tudor", password="scraper123")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM campaign_responses")
    print(f"  Responses tracked: {cur.fetchone()[0]}")
    cur.close()
    conn.close()
except:
    print("  Table not created yet")

print("\n" + "=" * 70)
print("ACTIONS NEEDED:")
blocked_accounts = []
for name in accounts:
    key = env.get(name, '')
    if not key:
        continue
    try:
        r = requests.get('https://api.brevo.com/v3/smtp/statistics/aggregatedReport',
            headers={'api-key': key}, params={'days': 7}, timeout=10)
        if r.status_code == 200:
            d = r.json()
            t = d.get('requests', 0)
            h, s = d.get('hardBounces', 0), d.get('softBounces', 0)
            rate = (h + s) / t * 100 if t else 0
            if rate > 10:
                blocked_accounts.append(name.replace('BREVO_', '').replace('_API_KEY', ''))
    except:
        pass
if blocked_accounts:
    print(f"  - Brevo accounts with >10% bounce: {', '.join(blocked_accounts)}")
    print(f"    Options: wait 7 days (dilutes), clean lists, or raise threshold")
r = run("df -h / | awk '{print $5}' | tail -1").replace('%', '')
try:
    if int(r) > 70:
        print(f"  - Disk at {r}%: run VACUUM or move old data")
except:
    pass
print("=" * 70)
