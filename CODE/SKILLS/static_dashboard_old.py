#!/usr/bin/env python3
"""
Static Dashboard Generator v3 - Full features from unified_dashboard
"""
import subprocess
import json
from datetime import datetime
from pathlib import Path

def run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() or r.stderr.strip()
    except:
        return "timeout"

def get_uptime():
    return run("uptime -p").replace("up ", "")

def get_disk():
    lines = []
    for line in run("df -h / /mnt/* 2>/dev/null | grep -v tmpfs | tail -n +2").split('\n'):
        if line.strip():
            parts = line.split()
            if len(parts) >= 6:
                pct = int(parts[4].replace('%',''))
                cls = 'err' if pct > 90 else 'warn' if pct > 80 else 'ok'
                lines.append(f'<div class="item"><span>{parts[5]}</span><span class="{cls}">{parts[4]} ({parts[3]} free)</span></div>')
    return '\n'.join(lines) or 'No disks'

def get_mem():
    line = run("free -h | grep Mem")
    if line:
        parts = line.split()
        return parts[2], parts[1]
    return "?", "?"

def get_docker():
    lines = []
    for line in run("docker ps -a --filter 'name=freescout' --filter 'name=signal' --filter 'name=portainer' --format '{{.Names}}|{{.Status}}' 2>/dev/null").split('\n'):
        if '|' in line:
            name, status = line.split('|', 1)
            cls = 'ok' if status.startswith('Up') else 'err'
            lines.append(f'<div class="item"><span>{name}</span><span class="{cls}">{status[:25]}</span></div>')
    return '\n'.join(lines) or 'No containers'

def get_services():
    checks = [
        ('postgresql', 'systemctl is-active postgresql'),
        ('node-red', 'pgrep -x node-red >/dev/null && echo running || echo stopped'),
        ('telegram-bot', 'systemctl is-active telegram-bot'),
        ('nginx', 'systemctl is-active nginx'),
        ('fail2ban', 'systemctl is-active fail2ban'),
        ('bounce-webhook', 'systemctl is-active bounce-webhook'),
    ]
    lines = []
    for name, cmd in checks:
        result = run(cmd)
        ok = result in ['active', 'running']
        lines.append(f'<div class="item"><span>{name}</span><span class="{"ok" if ok else "err"}">{result[:15]}</span></div>')
    return '\n'.join(lines)

def get_scrapers():
    count = run("ps aux | grep -E 'python.*scraper' | grep -v grep | wc -l")
    # Get recent scraper runs from logs
    recent = run("ls -lt /opt/ACTIVE/INFRA/LOGS/*scraper*.log /opt/ACTIVE/INFRA/LOGS/eures*.log 2>/dev/null | head -5 | awk '{print $6,$7,$9}' | while read d t f; do echo \"$d $t $(basename $f .log)\"; done")
    # Get rows from recent CSVs
    rows = run("find /mnt/hdd/SCRAPER_DATA/csv -name '*.csv' -mtime -1 2>/dev/null | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}'") or "0"
    return count, recent or 'none', rows

def get_email_stats():
    """Get detailed email stats from raspibig campaigns with sender type."""
    today = datetime.now().strftime('%Y%m%d')
    # Format: (display_name, folder_name, limit, sender_type) - 'BREVO'=Brevo, 'A2'=A2 SMTP
    campaigns = [
        ('Germany Agencies', 'GERMANY_AGENCIES', 290, 'BREVO'),
        ('Romania Translators', 'ROMANIA_TRANSLATORS', 290, 'BREVO'),
        ('EU Contractors', 'EU_CONTRACTORS', 290, 'BREVO'),
        ('Nordic', 'NORDIC', 290, 'BREVO'),
    ]

    lines = []
    total_sent = 0
    active = 0

    for display_name, folder, limit, sender_type in campaigns:
        log_path = f'/opt/ACTIVE/EMAIL/CAMPAIGNS/{folder}/logs/sent_{today}.log'
        sent = run(f"grep -c '| OK |' {log_path} 2>/dev/null || echo 0")
        try:
            sent = int(sent)
        except:
            sent = 0
        total_sent += sent
        if sent > 0:
            active += 1
        status = 'ok' if sent > 0 else 'dim'
        badge_class = 'brevo' if sender_type == 'BREVO' else 'a2hosting'
        lines.append(f'<div class="item"><span>{display_name}</span><span class="sender-badge {badge_class}">{sender_type}</span><span class="{status}">{sent}/{limit}</span></div>')

    return total_sent, active, '\n'.join(lines)

def get_raspi_campaigns():
    """Get campaign status from raspi with sender type."""
    # Format: (display_name, path, limit, sender_type, a2_domain)
    # sender_type: 'BREVO' or 'A2HOSTING'
    campaigns = [
        ('Poland Agencies', '/opt/ACTIVE/EMAIL/CAMPAIGNS/POLAND', 290, 'BREVO', None),
        ('Factory EU', '/opt/ACTIVE/EMAIL/CAMPAIGNS/FACTORY_EU', 290, 'BREVO', None),
        ('EU Funds', '/opt/ACTIVE/EMAIL/CAMPAIGNS/EUFUNDS2026', 290, 'BREVO', None),
        ('CQC UK', '/opt/ACTIVE/EMAIL/CAMPAIGNS/CQC', 100, 'BREVO', None),
        ('Build Jobs', '/opt/ACTIVE/EMAIL/CAMPAIGNS/BUILDJOBS_BREVO', 290, 'BREVO', None),
        ('Care Workers', '/opt/ACTIVE/EMAIL/CAMPAIGNS/CAREWORKERS_BREVO', 290, 'BREVO', None),
        ('Horeca Workers', '/opt/ACTIVE/EMAIL/CAMPAIGNS/HORECAWORKERS_A2', 50, 'A2HOSTING', 'horecaworkers.eu'),
        ('Meat Workers', '/opt/ACTIVE/EMAIL/CAMPAIGNS/MEATWORKERS_A2', 50, 'A2HOSTING', 'meatworkers.eu'),
        ('Electric Jobs', '/opt/ACTIVE/EMAIL/CAMPAIGNS/ELECTRICJOBS_A2', 50, 'A2HOSTING', 'electricjobs.eu'),
        ('Farm Workers', '/opt/ACTIVE/EMAIL/CAMPAIGNS/FARMWORKERS_A2', 50, 'A2HOSTING', 'farmworkers.eu'),
        ('Mechanic Jobs', '/opt/ACTIVE/EMAIL/CAMPAIGNS/MECHANICJOBS_A2', 50, 'A2HOSTING', 'mechanicjobs.eu'),
    ]

    # Get A2 warmup state
    a2_state = {}
    a2_data = run("ssh -o ConnectTimeout=3 raspi 'cat /opt/ACTIVE/EMAIL/CAMPAIGNS/a2_warmup_state.json 2>/dev/null' 2>/dev/null", timeout=8)
    try:
        a2_state = json.loads(a2_data)
    except:
        pass

    lines = []
    total = 0
    today = datetime.now().strftime('%Y-%m-%d')

    for name, path, limit, sender_type, a2_domain in campaigns:
        sent = 0

        if sender_type == 'A2HOSTING' and a2_domain:
            # Get from A2 warmup state (format: daily_sends dict or sent_today)
            domain_state = a2_state.get(a2_domain, {})
            # Try new format first
            if domain_state.get('last_send_date') == today:
                sent = domain_state.get('sent_today', 0)
            # Try old format (daily_sends dict)
            elif 'daily_sends' in domain_state:
                sent = domain_state.get('daily_sends', {}).get(today, 0)
        else:
            # Get from campaign state.json
            cmd = f"ssh -o ConnectTimeout=3 raspi 'cat {path}/state.json 2>/dev/null || cat {path}/.eufunds_sender_state.json 2>/dev/null' 2>/dev/null"
            result = run(cmd, timeout=8)
            try:
                state = json.loads(result)
                sent = state.get('sent_today', state.get('daily_sent', 0))
            except:
                pass

        total += sent
        status = 'ok' if sent > 0 else 'dim'
        badge_class = 'a2hosting' if sender_type == 'A2HOSTING' else 'brevo'
        lines.append(f'<div class="item"><span>{name}</span><span class="sender-badge {badge_class}">{sender_type}</span><span class="{status}">{sent}/{limit}</span></div>')

    return total, '\n'.join(lines)

def get_raspi():
    data = run("ssh -o ConnectTimeout=5 raspi 'echo CPU:$(top -bn1 | grep Cpu | awk \"{print \\$2}\")%; MEM:$(free | grep Mem | awk \"{printf(\\\"%.0f\\\", \\$3/\\$2*100)}\")%; DISK:$(df / | tail -1 | awk \"{print \\$5}\"); UP:$(uptime -p)' 2>/dev/null", timeout=15)
    if 'CPU:' in data:
        return data.replace(';', '<br>')
    return "unreachable"

def get_raspi_services():
    data = run("ssh -o ConnectTimeout=5 raspi 'for s in nodered postgresql nginx fail2ban applicant-dashboard; do echo $s:$(systemctl is-active $s); done' 2>/dev/null", timeout=10)
    if ':' in data:
        lines = []
        for line in data.split('\n'):
            if ':' in line:
                name, status = line.split(':')
                cls = 'ok' if status == 'active' else 'err'
                lines.append(f'<div class="item"><span>{name}</span><span class="{cls}">{status}</span></div>')
        return '\n'.join(lines)
    return '<div class="item">unreachable</div>'

def get_logs():
    count = run("find /opt/ACTIVE/INFRA/LOGS -name '*.log' -mtime -1 2>/dev/null | wc -l")
    errors = run("grep -l -i 'error\\|fail\\|exception' /opt/ACTIVE/INFRA/LOGS/*.log 2>/dev/null | wc -l")
    recent = run("ls -t /opt/ACTIVE/INFRA/LOGS/*.log 2>/dev/null | head -5 | while read f; do echo \"$(basename \"$f\")\"; done")
    return count, errors, recent or 'none'

def get_brevo_warmup():
    # Parse the warmup log file for latest status
    log_file = Path('/opt/ACTIVE/INFRA/LOGS/brevo_warmup_daily.log')
    if log_file.exists():
        try:
            content = log_file.read_text()
            # Find last status table in log
            lines = content.split('\n')
            campaigns = {}
            in_table = False
            for line in reversed(lines):
                if line.startswith('Schedule:'):
                    in_table = True
                    continue
                if in_table and line.startswith('---'):
                    break
                if in_table and line.strip() and not line.startswith('Campaign'):
                    parts = line.split()
                    if len(parts) >= 7:
                        name = parts[0]
                        day = parts[1]
                        limit = parts[2]
                        sent = parts[4]
                        campaigns[name] = {'day': day, 'limit': limit, 'sent': sent}
            if campaigns:
                # Clear display names for Brevo campaigns
                brevo_names = {
                    'FINLAND': 'Finland Jobs',
                    'FINLAND_BREVO': 'Finland Jobs',
                    'SWEDEN': 'Sweden Jobs',
                    'SWEDEN_BREVO': 'Sweden Jobs',
                    'NORWAY': 'Norway Jobs',
                    'NORWAY_BREVO': 'Norway Jobs',
                    'CUMPARLEGUME': 'Cumpar Legume',
                    'CUMPARLEGUME_BREVO': 'Cumpar Legume',
                    'SEICARESCU': 'Sei Carescu',
                    'SEICARESCU_BREVO': 'Sei Carescu',
                    'WAREHOUSE': 'Warehouse Workers',
                    'WAREHOUSE_BREVO': 'Warehouse Workers',
                }
                result = []
                for name, info in list(campaigns.items())[:6]:
                    display_name = brevo_names.get(name, name.replace('_BREVO', ''))
                    result.append(f'<div class="item"><span>{display_name}</span><span>Day {info["day"]}: {info["sent"]}/{info["limit"]}</span></div>')
                return '\n'.join(result)
        except:
            pass
    return 'No warmup data'

def get_a2_warmup():
    """Get A2 SMTP warmup status from raspi."""
    # Try to read state file directly
    state_data = run("ssh -o ConnectTimeout=5 raspi 'cat /opt/ACTIVE/EMAIL/CAMPAIGNS/a2_warmup_state.json 2>/dev/null' 2>/dev/null", timeout=10)
    creds_data = run("ssh -o ConnectTimeout=5 raspi 'cat /opt/ACTIVE/EMAIL/CAMPAIGNS/a2_smtp_credentials.json 2>/dev/null' 2>/dev/null", timeout=10)

    try:
        state = json.loads(state_data) if state_data else {}
        creds = json.loads(creds_data) if creds_data else {}

        # Calculate warmup day (started Jan 15, 2026)
        from datetime import datetime
        start = datetime(2026, 1, 15)
        day = max(1, (datetime.now() - start).days + 1)

        # Get limit for current day
        schedule = [(1,3,20), (4,7,50), (8,14,100), (15,21,200), (22,28,350), (29,999,500)]
        limit = 500
        for s, e, l in schedule:
            if s <= day <= e:
                limit = l
                break

        lines = []
        total_sent = 0
        total_remaining = 0
        today = datetime.now().strftime('%Y-%m-%d')

        # Clear display names for A2 domains
        domain_names = {
            'horecaworkers.eu': 'Horeca Workers',
            'meatworkers.eu': 'Meat Workers',
            'electricjobs.eu': 'Electric Jobs',
            'mechanicjobs.eu': 'Mechanic Jobs',
            'farmworkers.eu': 'Farm Workers',
            'factoryjobs.eu': 'Factory Jobs',
            'warehouseworkers.eu': 'Warehouse Workers',
        }

        for domain in list(creds.keys())[:7]:
            domain_state = state.get(domain, {})
            sent = 0
            if domain_state.get('last_send_date') == today:
                sent = domain_state.get('sent_today', 0)
            total_sent += sent
            remaining = max(0, limit - sent)
            total_remaining += remaining

            display_name = domain_names.get(domain, domain)
            status = 'ok' if sent > 0 else 'dim'
            lines.append(f'<div class="item"><span>{display_name}</span><span class="{status}">Day {day}: {sent}/{limit}</span></div>')

        return '\n'.join(lines) or 'No A2 domains', total_sent, total_remaining
    except Exception as e:
        return f'A2 error: {str(e)[:30]}', 0, 0

def get_cron_jobs():
    jobs = run("crontab -l 2>/dev/null | grep -v '^#' | grep -v '^$' | head -8")
    lines = []
    for line in jobs.split('\n'):
        if line.strip():
            parts = line.split()
            if len(parts) >= 6:
                schedule = ' '.join(parts[:5])
                cmd = parts[5].split('/')[-1][:20]
                lines.append(f'<div class="item"><span>{cmd}</span><span class="dim">{schedule}</span></div>')
    return '\n'.join(lines) or 'No cron jobs'

def get_failover_status():
    """Check failover monitor status."""
    result = run("ssh -o ConnectTimeout=3 raspi 'systemctl is-active failover-monitor' 2>/dev/null", timeout=5)
    if result == 'active':
        return 'ok', 'Failover monitor active'
    return 'warn', f'Failover: {result}'

def get_email_today():
    result = run("ssh raspi \"PGPASSWORD=scraper123 psql -h localhost -U tudor -d email_sender -t -c \\\"SELECT COUNT(*) FROM send_log WHERE sent_at::date = CURRENT_DATE\\\"\" 2>/dev/null", timeout=10)
    return result.strip() if result.strip().isdigit() else '0'

def get_alerts(disk_html, log_errors, docker_html, failover):
    alerts = []
    if 'class="err"' in disk_html:
        alerts.append(('err', 'Disk critical (>90%)'))
    elif 'class="warn"' in disk_html:
        alerts.append(('warn', 'Disk warning (>80%)'))
    if int(log_errors or 0) > 20:
        alerts.append(('err', f'{log_errors} logs with errors'))
    elif int(log_errors or 0) > 5:
        alerts.append(('warn', f'{log_errors} logs with errors'))
    if 'class="err"' in docker_html:
        alerts.append(('warn', 'Container(s) down'))
    if failover[0] != 'ok':
        alerts.append(('warn', failover[1]))
    return alerts

# Gather data
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
uptime = get_uptime()
mem_used, mem_total = get_mem()
disk_html = get_disk()
docker_html = get_docker()
scraper_count, scraper_recent, scraper_rows = get_scrapers()
log_count, log_errors, log_list = get_logs()
emails_today = get_email_today()
a2_html, a2_sent, a2_remaining = get_a2_warmup()
failover = get_failover_status()
alerts = get_alerts(disk_html, log_errors, docker_html, failover)

# Email stats
email_sent, email_active, email_list = get_email_stats()
raspi_sent, raspi_camp_list = get_raspi_campaigns()
total_sent = int(emails_today) + email_sent + raspi_sent

# Overall status
if any(a[0] == 'err' for a in alerts):
    overall = ('err', 'ERROR')
elif any(a[0] == 'warn' for a in alerts):
    overall = ('warn', 'WARNING')
else:
    overall = ('ok', 'OK')

alerts_html = ''.join(f'<span class="alert {a[0]}">{a[1]}</span>' for a in alerts) or '<span class="alert ok">All systems OK</span>'

html = f'''<!DOCTYPE html>
<html>
<head>
<title>Dashboard</title>
<meta charset="utf-8">
<meta http-equiv="refresh" content="60">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: #0a0a1a; color: #eee; font-family: -apple-system, sans-serif; padding: 12px; font-size: 16px; }}
.header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #333; }}
h1 {{ color: #00d9ff; font-size: 1.2em; }}
.status {{ display: flex; gap: 10px; align-items: center; }}
.status-badge {{ padding: 4px 12px; border-radius: 12px; font-weight: bold; font-size: 0.85em; }}
.status-badge.ok {{ background: #4ade80; color: #000; }}
.status-badge.warn {{ background: #ffc107; color: #000; }}
.status-badge.err {{ background: #ff6b6b; color: #fff; }}
.meta {{ color: #666; font-size: 0.7em; }}
.alerts {{ margin-bottom: 12px; }}
.alert {{ display: inline-block; padding: 3px 8px; border-radius: 4px; margin-right: 6px; font-size: 0.75em; }}
.alert.ok {{ background: #1a3a1a; color: #4ade80; }}
.alert.warn {{ background: #3a3a1a; color: #ffc107; }}
.alert.err {{ background: #3a1a1a; color: #ff6b6b; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 10px; }}
.card {{ background: #12122a; padding: 10px; border-radius: 6px; border: 1px solid #2a2a4a; }}
.card.raspi {{ border-color: #4ade80; }}
.card h2 {{ color: #888; font-size: 1em; text-transform: uppercase; margin-bottom: 10px; display: flex; justify-content: space-between; }}
.card h2 .badge {{ background: #00d9ff; color: #000; padding: 1px 6px; border-radius: 8px; font-size: 0.8em; }}
.card h2 .badge.warn {{ background: #ffc107; }}
.card h2 .badge.err {{ background: #ff6b6b; color: #fff; }}
.card h2 .badge.raspi {{ background: #4ade80; }}
.item {{ display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #1a1a3a; font-size: 1em; }}
.item:last-child {{ border: none; }}
.ok {{ color: #4ade80; }}
.warn {{ color: #ffc107; }}
.err {{ color: #ff6b6b; }}
.dim {{ color: #666; }}
.stats {{ display: flex; gap: 6px; margin-bottom: 6px; }}
.stat {{ flex: 1; background: #1a1a3a; padding: 5px; border-radius: 4px; text-align: center; }}
.stat .val {{ font-size: 1.2em; font-weight: bold; }}
.stat .lbl {{ font-size: 0.6em; color: #666; }}
pre {{ background: #1a1a2e; padding: 5px; border-radius: 4px; font-size: 0.7em; overflow-x: auto; white-space: pre-wrap; margin-top: 5px; }}
.sender-badge {{ padding: 3px 10px; border-radius: 4px; font-size: 0.9em; font-weight: bold; margin: 0 10px; }}
.sender-badge.brevo {{ background: #ffc107; color: #000; }}
.sender-badge.a2hosting {{ background: #4ade80; color: #000; }}
</style>
</head>
<body>
<div class="header">
    <div>
        <h1>Unified Dashboard</h1>
        <span class="meta">Up: {uptime} | {now}</span>
    </div>
    <div class="status">
        <span class="status-badge {overall[0]}">{overall[1]}</span>
    </div>
</div>

<div class="alerts">{alerts_html}</div>

<div class="grid">
    <div class="card">
        <h2>Email (raspibig) <span class="badge">{email_active} active</span></h2>
        <div class="stats">
            <div class="stat"><div class="val">{email_sent}</div><div class="lbl">Sent Today</div></div>
            <div class="stat"><div class="val">1160</div><div class="lbl">Capacity</div></div>
        </div>
        {email_list}
    </div>

    <div class="card raspi">
        <h2>Email (raspi) <span class="badge raspi">{raspi_sent} sent</span></h2>
        {raspi_camp_list}
    </div>
    
    <div class="card">
        <h2>Scrapers <span class="badge">{scraper_count} running</span></h2>
        <div class="stats">
            <div class="stat"><div class="val">{scraper_rows}</div><div class="lbl">Rows Today</div></div>
        </div>
        <pre>{scraper_recent}</pre>
    </div>
    
    <div class="card">
        <h2>Disk Usage</h2>
        {disk_html}
    </div>
    
    <div class="card">
        <h2>Memory</h2>
        <div class="stats">
            <div class="stat"><div class="val">{mem_used}</div><div class="lbl">Used</div></div>
            <div class="stat"><div class="val">{mem_total}</div><div class="lbl">Total</div></div>
        </div>
    </div>
    
    <div class="card">
        <h2>Docker <span class="badge">{run("docker ps -q 2>/dev/null | wc -l")} up</span></h2>
        {docker_html}
    </div>
    
    <div class="card">
        <h2>Services (raspibig)</h2>
        {get_services()}
    </div>
    
    <div class="card">
        <h2>Logs <span class="badge{' warn' if int(log_errors or 0) > 5 else ''}">{log_errors} errors</span></h2>
        <pre>{log_list}</pre>
    </div>
    
    <div class="card">
        <h2>Cron Jobs</h2>
        {get_cron_jobs()}
    </div>
    
    <div class="card raspi">
        <h2>Raspi System <span class="badge raspi">remote</span></h2>
        <p style="font-size:0.75em">{get_raspi()}</p>
    </div>

    <div class="card raspi">
        <h2>Raspi Services <span class="badge {failover[0]}">{failover[1][:15]}</span></h2>
        {get_raspi_services()}
    </div>
    
    <div class="card">
        <h2>Brevo Warmup</h2>
        {get_brevo_warmup()}
    </div>
    
    <div class="card raspi">
        <h2>A2 SMTP Warmup <span class="badge raspi">{a2_sent} sent</span></h2>
        <div class="stats">
            <div class="stat"><div class="val">{a2_sent}</div><div class="lbl">Sent</div></div>
            <div class="stat"><div class="val">{a2_remaining}</div><div class="lbl">Remaining</div></div>
        </div>
        {a2_html}
    </div>
</div>

<p style="margin-top:12px;color:#444;font-size:0.65em;text-align:center">
    Total emails today: {total_sent} | Auto-refresh: 60s | <a href="dashboard.html" style="color:#00d9ff">Refresh</a>
</p>
</body>
</html>'''

with open("/tmp/dashboard.html", "w") as f:
    f.write(html)
print(f"Dashboard generated: {now}")
