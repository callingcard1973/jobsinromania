#!/usr/bin/env python3
"""
Static Dashboard Generator v4 - Zero SSH calls
Reads from local metrics JSON files (collected by metrics_collector.py)
"""
import json
import logging
import subprocess
import time
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    filename='/opt/ACTIVE/INFRA/LOGS/dashboard.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)

# Import config
import sys
sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS')
from dashboard_config import (
    RASPIBIG_CAMPAIGNS, RASPI_CAMPAIGNS, A2_DOMAINS,
    A2_WARMUP_SCHEDULE, A2_WARMUP_START_DATE,
    BREVO_CAMPAIGNS, PATHS, CSS_COLORS,
    DISK_WARNING_PERCENT, DISK_CRITICAL_PERCENT,
    LOG_ERROR_WARNING_THRESHOLD, LOG_ERROR_CRITICAL_THRESHOLD,
    METRICS_STALE_THRESHOLD_SECONDS
)

SYNC_STATE_DIR = Path(PATHS.get('sync_state_dir', '/opt/ACTIVE/INFRA/SYNC_STATE'))


def run(cmd, timeout=10):
    """Execute local shell command."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() or r.stderr.strip()
    except subprocess.TimeoutExpired:
        logger.warning(f"Command timeout: {cmd[:50]}")
        return "timeout"
    except Exception as e:
        logger.error(f"Command error: {cmd[:50]} - {e}")
        return ""


def load_metrics(hostname):
    """Load metrics from local JSON file."""
    path = SYNC_STATE_DIR / f"{hostname}_metrics.json"
    if not path.exists():
        logger.warning(f"Metrics file not found: {path}")
        return None

    try:
        data = json.loads(path.read_text())
        age = time.time() - data.get('epoch', 0)
        data['stale'] = age > METRICS_STALE_THRESHOLD_SECONDS
        data['age_minutes'] = int(age / 60)
        return data
    except Exception as e:
        logger.error(f"Error loading {path}: {e}")
        return None


def get_uptime():
    """Get local system uptime."""
    return run("uptime -p").replace("up ", "")


def get_disk_html(metrics):
    """Generate disk usage HTML from metrics."""
    lines = []
    disk_data = metrics.get('disk_usage', {}) if metrics else {}

    for mount, info in disk_data.items():
        pct = info.get('percent', 0)
        free = info.get('free', '?')
        cls = 'err' if pct > DISK_CRITICAL_PERCENT else 'warn' if pct > DISK_WARNING_PERCENT else 'ok'
        lines.append(f'<div class="item"><span>{mount}</span><span class="{cls}">{pct}% ({free} free)</span></div>')

    return '\n'.join(lines) or '<div class="item">No disk data</div>'


def get_mem_html(metrics):
    """Generate memory stats from metrics."""
    if not metrics:
        return '?', '?'
    mem = metrics.get('memory', {})
    return f"{mem.get('used_gb', '?')}Gi", f"{mem.get('total_gb', '?')}Gi"


def get_docker_html(metrics):
    """Generate Docker container HTML from metrics."""
    lines = []
    docker = metrics.get('docker', {}) if metrics else {}

    for name, info in docker.items():
        running = info.get('running', False)
        status = info.get('status', 'unknown')[:25]
        cls = 'ok' if running else 'err'
        lines.append(f'<div class="item"><span>{name}</span><span class="{cls}">{status}</span></div>')

    return '\n'.join(lines) or '<div class="item">No containers</div>'


def get_services_html(metrics):
    """Generate services HTML from metrics."""
    lines = []
    services = metrics.get('services', {}) if metrics else {}

    for name, active in services.items():
        cls = 'ok' if active else 'err'
        status = 'active' if active else 'inactive'
        lines.append(f'<div class="item"><span>{name}</span><span class="{cls}">{status}</span></div>')

    return '\n'.join(lines) or '<div class="item">No services</div>'


def get_scrapers_html(metrics):
    """Generate scrapers HTML from metrics."""
    if not metrics:
        return '0', 'No data', '0'

    scrapers = metrics.get('scrapers', {})
    running = scrapers.get('running', 0)
    logs = scrapers.get('recent_logs', [])
    rows = scrapers.get('rows_today', 0)

    recent = '\n'.join(logs[:5]) if logs else 'No recent logs'
    return str(running), recent, str(rows)


def get_email_stats_html(metrics):
    """Generate raspibig email stats from metrics."""
    lines = []
    total_sent = 0
    active = 0

    campaigns = metrics.get('campaigns', {}) if metrics else {}

    for name, info in campaigns.items():
        display = info.get('display', name)
        sent = info.get('sent_today', 0)
        limit = info.get('limit', 290)
        sender = info.get('sender', 'BREVO')

        total_sent += sent
        if sent > 0:
            active += 1

        status = 'ok' if sent > 0 else 'dim'
        badge_class = 'brevo' if sender == 'BREVO' else 'a2hosting'
        lines.append(f'<div class="item"><span>{display}</span><span class="sender-badge {badge_class}">{sender}</span><span class="{status}">{sent}/{limit}</span></div>')

    return total_sent, active, '\n'.join(lines) or '<div class="item">No campaigns</div>'


def get_raspi_campaigns_html(metrics):
    """Generate raspi campaigns HTML from metrics."""
    lines = []
    total_sent = 0

    campaigns = metrics.get('campaigns', {}) if metrics else {}

    for name, info in campaigns.items():
        display = info.get('display', name)
        sent = info.get('sent_today', 0)
        limit = info.get('limit', 290)
        sender = info.get('sender', 'BREVO')

        total_sent += sent
        status = 'ok' if sent > 0 else 'dim'
        badge_class = 'brevo' if sender == 'BREVO' else 'a2hosting'
        lines.append(f'<div class="item"><span>{display}</span><span class="sender-badge {badge_class}">{sender}</span><span class="{status}">{sent}/{limit}</span></div>')

    return total_sent, '\n'.join(lines) or '<div class="item">No campaigns</div>'


def get_a2_warmup_html(metrics):
    """Generate A2 warmup HTML from metrics."""
    lines = []
    total_sent = 0
    total_remaining = 0

    warmup = metrics.get('a2_warmup', {}) if metrics else {}

    for domain, info in warmup.items():
        display = info.get('display', domain)
        sent = info.get('sent_today', 0)
        limit = info.get('limit', 50)
        day = info.get('day', 1)

        total_sent += sent
        total_remaining += max(0, limit - sent)

        status = 'ok' if sent > 0 else 'dim'
        lines.append(f'<div class="item"><span>{display}</span><span class="{status}">Day {day}: {sent}/{limit}</span></div>')

    return '\n'.join(lines) or '<div class="item">No A2 warmup data</div>', total_sent, total_remaining


def get_brevo_warmup_html():
    """Parse Brevo warmup log file."""
    log_file = Path(PATHS.get('brevo_warmup_log', '/opt/ACTIVE/INFRA/LOGS/brevo_warmup_daily.log'))
    if not log_file.exists():
        return '<div class="item">No warmup data</div>'

    try:
        content = log_file.read_text()
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
            result = []
            for name, info in list(campaigns.items())[:6]:
                display_name = BREVO_CAMPAIGNS.get(name, name.replace('_BREVO', ''))
                result.append(f'<div class="item"><span>{display_name}</span><span>Day {info["day"]}: {info["sent"]}/{info["limit"]}</span></div>')
            return '\n'.join(result)
    except Exception as e:
        logger.error(f"Brevo warmup parse error: {e}")

    return '<div class="item">No warmup data</div>'


def get_logs_html():
    """Get recent logs with error count."""
    log_count = run("find /opt/ACTIVE/INFRA/LOGS -name '*.log' -mtime -1 2>/dev/null | wc -l")
    log_errors = run("grep -l -i 'error\\|fail\\|exception' /opt/ACTIVE/INFRA/LOGS/*.log 2>/dev/null | wc -l")
    recent = run("ls -t /opt/ACTIVE/INFRA/LOGS/*.log 2>/dev/null | head -5 | while read f; do basename \"$f\"; done")
    return log_count, log_errors, recent or 'none'


def get_cron_jobs_html():
    """Get cron jobs."""
    jobs = run("crontab -l 2>/dev/null | grep -v '^#' | grep -v '^$' | head -8")
    lines = []
    for line in jobs.split('\n'):
        if line.strip():
            parts = line.split()
            if len(parts) >= 6:
                schedule = ' '.join(parts[:5])
                cmd = parts[5].split('/')[-1][:20]
                lines.append(f'<div class="item"><span>{cmd}</span><span class="dim">{schedule}</span></div>')
    return '\n'.join(lines) or '<div class="item">No cron jobs</div>'


def get_alerts(raspibig_metrics, raspi_metrics, log_errors):
    """Generate alert badges."""
    alerts = []

    # Disk alerts
    for metrics in [raspibig_metrics, raspi_metrics]:
        if metrics:
            for mount, info in metrics.get('disk_usage', {}).items():
                pct = info.get('percent', 0)
                if pct > DISK_CRITICAL_PERCENT:
                    alerts.append(('err', f'Disk critical {mount}'))
                elif pct > DISK_WARNING_PERCENT:
                    alerts.append(('warn', f'Disk warning {mount}'))

    # Log errors
    try:
        errors = int(log_errors)
        if errors > LOG_ERROR_CRITICAL_THRESHOLD:
            alerts.append(('err', f'{errors} logs with errors'))
        elif errors > LOG_ERROR_WARNING_THRESHOLD:
            alerts.append(('warn', f'{errors} logs with errors'))
    except:
        pass

    # Stale metrics
    if raspibig_metrics and raspibig_metrics.get('stale'):
        alerts.append(('warn', f'raspibig metrics stale ({raspibig_metrics.get("age_minutes", "?")}min)'))
    if raspi_metrics and raspi_metrics.get('stale'):
        alerts.append(('warn', f'raspi metrics stale ({raspi_metrics.get("age_minutes", "?")}min)'))
    if not raspi_metrics:
        alerts.append(('err', 'raspi metrics missing'))

    return alerts


def generate_html():
    """Generate the dashboard HTML."""
    logger.info("Generating dashboard")

    # Load metrics from local files (NO SSH!)
    raspibig_metrics = load_metrics('raspibig')
    raspi_metrics = load_metrics('raspi')

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    uptime = get_uptime()

    # Get data from metrics
    mem_used, mem_total = get_mem_html(raspibig_metrics)
    disk_html = get_disk_html(raspibig_metrics)
    docker_html = get_docker_html(raspibig_metrics)
    services_html = get_services_html(raspibig_metrics)
    scraper_count, scraper_recent, scraper_rows = get_scrapers_html(raspibig_metrics)

    # Email stats
    email_sent, email_active, email_list = get_email_stats_html(raspibig_metrics)
    raspi_sent, raspi_camp_list = get_raspi_campaigns_html(raspi_metrics)
    a2_html, a2_sent, a2_remaining = get_a2_warmup_html(raspi_metrics)
    brevo_html = get_brevo_warmup_html()

    # Raspi system info from metrics
    raspi_info = "unreachable"
    raspi_services_html = '<div class="item">unreachable</div>'
    if raspi_metrics:
        cpu = raspi_metrics.get('cpu_percent', '?')
        mem = raspi_metrics.get('memory', {})
        raspi_info = f"CPU:{cpu}%"
        raspi_services_html = get_services_html(raspi_metrics)

    # Logs
    log_count, log_errors, log_list = get_logs_html()
    cron_html = get_cron_jobs_html()

    # Total emails
    total_sent = email_sent + raspi_sent

    # Alerts
    alerts = get_alerts(raspibig_metrics, raspi_metrics, log_errors)
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
pre {{ background: #1a1a2e; padding: 5px; border-radius: 4px; font-size: 0.8em; overflow-x: auto; white-space: pre-wrap; margin-top: 5px; }}
.sender-badge {{ padding: 3px 10px; border-radius: 4px; font-size: 0.9em; font-weight: bold; margin: 0 10px; }}
.sender-badge.brevo {{ background: #ffc107; color: #000; }}
.sender-badge.a2hosting {{ background: #4ade80; color: #000; }}
</style>
</head>
<body>
<div class="header">
    <div>
        <h1>Unified Dashboard v4</h1>
        <span class="meta">Up: {uptime} | {now} | Zero SSH</span>
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
        <h2>Docker <span class="badge">{len(raspibig_metrics.get('docker', {}))} up</span></h2>
        {docker_html}
    </div>

    <div class="card">
        <h2>Services (raspibig)</h2>
        {services_html}
    </div>

    <div class="card">
        <h2>Logs <span class="badge{' warn' if int(log_errors or 0) > 5 else ''}">{log_errors} errors</span></h2>
        <pre>{log_list}</pre>
    </div>

    <div class="card">
        <h2>Cron Jobs</h2>
        {cron_html}
    </div>

    <div class="card raspi">
        <h2>Raspi System <span class="badge raspi">remote</span></h2>
        <p style="font-size:0.85em">{raspi_info}</p>
    </div>

    <div class="card raspi">
        <h2>Raspi Services <span class="badge ok">OK</span></h2>
        {raspi_services_html}
    </div>

    <div class="card">
        <h2>Brevo Warmup</h2>
        {brevo_html}
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

    # Write to file
    output_path = Path('/tmp/dashboard.html')
    output_path.write_text(html)
    logger.info(f"Dashboard generated: {now}")
    print(f"Dashboard generated: {now}")

    return html


if __name__ == '__main__':
    generate_html()
