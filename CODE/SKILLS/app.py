#!/usr/bin/env python3
"""
Unified Dashboard v3.1 - Refactored
URL: http://raspibig:8085
"""
import os
import sys
import re
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

from flask import Flask, render_template, jsonify

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

app = Flask(__name__)

LOG_DIR = Path('/opt/ACTIVE/INFRA/LOGS')
DATA_DIR = Path('/opt/ACTIVE/OPENDATA/DATA')
EMAIL_DIR = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS')


def get_uptime():
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        return f"{days}d {hours}h"
    except:
        return "?"


def get_disk_usage():
    disks = []
    try:
        result = subprocess.run(['df', '-h'], capture_output=True, text=True)
        for line in result.stdout.strip().split('\n')[1:]:
            parts = line.split()
            if len(parts) >= 6:
                mount = parts[5]
                if mount in ['/', '/home'] or mount.startswith('/mnt/'):
                    disks.append({
                        'mount': mount,
                        'size': parts[1],
                        'used': parts[2],
                        'free': parts[3],
                        'percent': int(parts[4].replace('%', ''))
                    })
    except:
        pass
    return sorted(disks, key=lambda x: x['mount'])


def get_docker_status():
    containers = []
    ARCHIVED = {'odoo', 'odoo-db'}
    try:
        result = subprocess.run(
            ['docker', 'ps', '-a', '--format', '{{.Names}}\t{{.Status}}'],
            capture_output=True, text=True
        )
        for line in result.stdout.strip().split('\n'):
            if '\t' in line:
                name, status = line.split('\t', 1)
                if name.lower() in ARCHIVED:
                    continue
                containers.append({
                    'name': name,
                    'status': 'Up' if status.startswith('Up') else 'Down'
                })
    except:
        pass
    running = sum(1 for c in containers if c['status'] == 'Up')
    return {'containers': containers, 'running': running, 'total': len(containers)}


def get_services():
    ports = []
    try:
        result = subprocess.run(['ss', '-tlnp'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            match = re.search(r':(\d+)\s', line)
            if match:
                ports.append(int(match.group(1)))
    except:
        pass
    return list(set(ports))


def get_raspi_stats():
    stats = {'online': False, 'cpu': 0, 'mem': 0, 'disk': 0, 'services': []}
    try:
        cmd = '''
cpu=$(top -bn1 | grep "Cpu(s)" | awk '{print int($2)}' 2>/dev/null || echo 0)
mem=$(free | awk '/Mem:/ {printf "%.0f", $3/$2 * 100}' 2>/dev/null || echo 0)
disk=$(df / | awk 'NR==2 {print $5}' | tr -d '%' 2>/dev/null || echo 0)
echo "$cpu $mem $disk"
systemctl is-active telegram-bot bounce-webhook 2>/dev/null || true
'''
        result = subprocess.run(
            ['ssh', '-o', 'ConnectTimeout=3', '-o', 'StrictHostKeyChecking=no', 'raspi', cmd],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if lines:
                parts = lines[0].split()
                if len(parts) >= 3:
                    stats['online'] = True
                    stats['cpu'] = int(parts[0]) if parts[0].isdigit() else 0
                    stats['mem'] = int(parts[1]) if parts[1].isdigit() else 0
                    stats['disk'] = int(parts[2]) if parts[2].isdigit() else 0
                services = [('telegram-bot', 'TG Bot'), ('bounce-webhook', 'Bounce WH')]
                service_lines = lines[1:] if len(lines) > 1 else []
                for i, (svc_name, display) in enumerate(services):
                    status = service_lines[i] if i < len(service_lines) else 'unknown'
                    stats['services'].append({
                        'name': display,
                        'status': 'ok' if status == 'active' else 'err',
                        'info': status
                    })
    except:
        pass
    return stats


def get_raspi_campaigns():
    raspi_campaigns = []
    today = datetime.now().strftime('%Y-%m-%d')
    campaigns = [
        {'name': 'Poland (raspi)', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/POLAND', 'limit': 290},
        {'name': 'Factory (raspi)', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/FACTORY_EU', 'limit': 290},
        {'name': 'EUFunds-buildjobs', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/EUFUNDS2026', 'limit': 290, 'sender': 'brevo_buildjobs'},
        {'name': 'EUFunds-factoryjobs', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/EUFUNDS2026', 'limit': 290, 'sender': 'brevo_factoryjobs'},
        {'name': 'EUFunds-warehouse', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/EUFUNDS2026', 'limit': 290, 'sender': 'brevo_warehouseworkers'},
        {'name': 'CQC-UK (raspi)', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/CQC', 'limit': 100, 'state_file': '.cqc_sender_state.json'},
        {'name': 'EUFunds-mivromania', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/EUFUNDS2026', 'limit': 290, 'sender': 'brevo_mivromania'},
        {'name': 'EUFunds-mivonline', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/EUFUNDS2026', 'limit': 290, 'sender': 'brevo_mivromania_online'},
        {'name': 'EUFunds-cifn', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/EUFUNDS2026', 'limit': 290, 'sender': 'brevo_cifn'},
        {'name': 'EUFunds-expats', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/EUFUNDS2026', 'limit': 290, 'sender': 'brevo_expatsinromania'},
    ]
    for camp in campaigns:
        sent = 0
        status = 'ok'
        stale = False
        try:
            state_file = camp.get('state_file', 'state.json')
            state_cmd = f'cat {camp["path"]}/{state_file} 2>/dev/null || cat {camp["path"]}/.eufunds_sender_state.json 2>/dev/null || cat {camp["path"]}/state.json 2>/dev/null'
            result = subprocess.run(['ssh', '-o', 'ConnectTimeout=3', 'raspi', state_cmd], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                state = json.loads(result.stdout)
                state_date = state.get('date', state.get('last_reset', ''))[:10]
                sent = state.get('sent_today', state.get('daily_sent', 0))
                if state_date and state_date != today:
                    stale = True
                    sent = 0
                if sent == 0 and 'sent_emails' in state:
                    sender_filter = camp.get('sender')
                    if sender_filter:
                        sent = sum(1 for v in state['sent_emails'].values() if v.get('date', '')[:10] == today and v.get('sender') == sender_filter)
                    else:
                        sent = sum(1 for v in state['sent_emails'].values() if v.get('date', '')[:10] == today)
                if sent > 0:
                    status = 'ok'
        except:
            status = 'warn'
        raspi_campaigns.append({'name': camp['name'], 'sent': sent, 'limit': camp['limit'], 'status': status, 'stale': stale})
    return raspi_campaigns


def get_brevo_warmup_status():
    try:
        result = subprocess.run(["ssh", "raspi", "/opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/INFRA/SKILLS/brevo_warmup.py status"], capture_output=True, text=True, timeout=30)
        lines = result.stdout.strip().split("\n")
        campaigns = []
        active = 0
        paused = 0
        sent_today = 0
        for line in lines:
            if "_BREVO" in line:
                parts = line.split()
                if len(parts) >= 7:
                    name = parts[0]
                    day = parts[1] if parts[1] != "--" else "0"
                    limit = parts[2] if parts[2] != "--" else "0"
                    today_val = parts[4] if parts[4] != "--" else "0"
                    status = "WARMING" if "WARMING" in line else "PAUSED" if "NOT STARTED" in line else "DONE"
                    campaigns.append({"name": name.replace("_BREVO", ""), "day": day, "limit": limit, "today": today_val, "status": status})
                    if status == "WARMING":
                        active += 1
                        sent_today += int(today_val) if today_val.isdigit() else 0
                    elif status == "PAUSED":
                        paused += 1
        return {"active": active, "paused": paused, "sent_today": sent_today, "campaigns": campaigns}
    except:
        return {"active": 0, "paused": 0, "sent_today": 0, "campaigns": []}


def get_a2_warmup_status():
    try:
        result = subprocess.run(["ssh", "-o", "ConnectTimeout=3", "raspi", "/opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/INFRA/SKILLS/a2_status.py --json"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
    except:
        pass
    return {"error": "Cannot fetch A2 status", "domains": [], "summary": {"total_sent_today": 0, "total_remaining": 0, "total_limit": 0}}


def get_email_stats():
    stats = {'sent_today': 0, 'capacity': 2610, 'bounces': 0, 'active': 0, 'campaigns': []}
    campaigns = [
        ('TRANSPORT (raspibig)', 'TRANSPORT_EU', 290),
        ('TOURISM (raspibig)', 'TOURISM_RO', 290),
        ('HORECA (raspibig)', 'HORECA2026', 290),
        ('NEPAL (raspibig)', 'CIFN_NEPAL', 290),
        ('NORWAY (raspibig)', 'NORWAY', 290),
        ('CAREWORKERS (raspibig)', 'CAREWORKERS', 290),
        ('WAREHOUSE (raspibig)', 'WAREHOUSE_EU', 290)
    ]
    today = datetime.now().strftime('%Y%m%d')
    for display_name, folder_name, limit in campaigns:
        sent = 0
        status = 'ok'
        stale = False
        try:
            log_path = EMAIL_DIR / folder_name / 'logs' / f'sent_{today}.log'
            if log_path.exists():
                content = log_path.read_text(errors='ignore')
                sent = content.count('| OK |')
                if sent > 0:
                    stats['active'] += 1
        except:
            pass
        stats['campaigns'].append({'name': display_name, 'sent': sent, 'limit': limit, 'status': status, 'stale': stale})
        stats['sent_today'] += sent
    try:
        raspi_camps = get_raspi_campaigns()
        for camp in raspi_camps:
            stats['campaigns'].append(camp)
            if not camp.get('stale', False):
                stats['sent_today'] += camp['sent']
            if camp['sent'] > 0 and not camp.get('stale', False):
                stats['active'] += 1
    except:
        pass
    return stats


def get_scraper_stats():
    stats = {'running': 0, 'completed_today': 0, 'rows_today': 0, 'recent': []}
    try:
        result = subprocess.run(['pgrep', '-af', 'python3.*scraper'], capture_output=True, text=True)
        seen_scripts = set()
        for line in result.stdout.split('\n'):
            if not line.strip():
                continue
            if '/bin/bash' in line or 'ssh ' in line or 'EOF' in line:
                continue
            match = re.search(r'python3?\s+.*?(\w+_scraper\.py|\w+scraper\.py)', line)
            if match:
                script = match.group(1)
                if script not in seen_scripts:
                    seen_scripts.add(script)
                    stats['running'] += 1
    except:
        pass
    scraper_log_dir = LOG_DIR / 'scrapers'
    if scraper_log_dir.exists():
        today = datetime.now().date()
        for log in sorted(scraper_log_dir.glob('*.log'), key=lambda x: x.stat().st_mtime, reverse=True)[:10]:
            try:
                mtime = datetime.fromtimestamp(log.stat().st_mtime)
                name = log.stem.replace('_', ' ')[:20]
                if mtime.date() == today:
                    stats['completed_today'] += 1
                    content = log.read_text(errors='ignore')[-5000:]
                    match = re.search(r'(\d+)\s*(rows|records|items)', content, re.I)
                    if match:
                        stats['rows_today'] += int(match.group(1))
                status = 'ok' if 'complet' in log.read_text(errors='ignore')[-1000:].lower() else 'warn'
                stats['recent'].append({'name': name, 'info': mtime.strftime('%H:%M'), 'status': status})
            except:
                pass
    return stats


def get_log_stats():
    stats = {'total_files': 0, 'total_size': '0 MB', 'errors_24h': 0, 'recent_errors': []}
    total_bytes = 0
    cutoff = datetime.now() - timedelta(hours=24)
    error_pattern = re.compile(r'.*(error|exception|failed|failure|traceback).*', re.I)
    for log in LOG_DIR.rglob('*.log'):
        try:
            stat = log.stat()
            stats['total_files'] += 1
            total_bytes += stat.st_size
            if datetime.fromtimestamp(stat.st_mtime) > cutoff:
                content = log.read_text(errors='ignore')[-20000:]
                errors = [e for e in error_pattern.findall(content) if 'warning' not in e.lower()]
                stats['errors_24h'] += len(errors)
                for line in content.split('\n')[-50:]:
                    if error_pattern.match(line) and 'warning' not in line.lower():
                        stats['recent_errors'].append(line[:100])
        except:
            pass
    stats['total_size'] = f"{total_bytes / (1024*1024):.1f} MB"
    stats['recent_errors'] = stats['recent_errors'][-5:]
    return stats


def get_failover_status():
    state_file = Path('/opt/ACTIVE/INFRA/SYNC_STATE/failover_state.json')
    heartbeat_file = Path('/opt/ACTIVE/INFRA/SYNC_STATE/heartbeat.json')
    status = {'mode': 'normal', 'active': 'raspibig', 'raspi_ok': False, 'heartbeat_age': None, 'last_sync': None}
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
            status['mode'] = state.get('mode', 'normal')
            status['active'] = state.get('active', 'raspibig')
        except:
            pass
    if heartbeat_file.exists():
        try:
            hb = json.loads(heartbeat_file.read_text())
            age = time.time() - hb.get('epoch', 0)
            status['heartbeat_age'] = int(age)
        except:
            pass
    result = subprocess.run(['ping', '-c', '1', '-W', '2', '192.168.100.20'], capture_output=True, text=True)
    status['raspi_ok'] = result.returncode == 0
    sync_file = Path('/opt/ACTIVE/INFRA/SYNC_STATE/last_sync.json')
    if sync_file.exists():
        try:
            sync = json.loads(sync_file.read_text())
            status['last_sync'] = sync.get('last_sync', '')[:16]
        except:
            pass
    return status


def get_alerts(disk, docker, logs, email, raspi):
    alerts = []
    for d in disk:
        if d['percent'] > 90:
            alerts.append({'level': 'err', 'message': f"Disk {d['mount']} critical: {d['percent']}%"})
        elif d['percent'] > 80:
            alerts.append({'level': 'warn', 'message': f"Disk {d['mount']} high: {d['percent']}%"})
    down = [c for c in docker['containers'] if c['status'] != 'Up']
    if down:
        alerts.append({'level': 'err', 'message': f"Docker down: {', '.join(c['name'] for c in down)}"})
    if logs['errors_24h'] > 100:
        alerts.append({'level': 'err', 'message': f"{logs['errors_24h']} errors in logs (24h)"})
    elif logs['errors_24h'] > 20:
        alerts.append({'level': 'warn', 'message': f"{logs['errors_24h']} errors in logs (24h)"})
    if not raspi.get('online', False):
        alerts.append({'level': 'err', 'message': "Raspi offline - cannot get stats"})
    else:
        if raspi.get('mem', 0) > 85:
            alerts.append({'level': 'err', 'message': f"Raspi memory critical: {raspi['mem']}%"})
        elif raspi.get('mem', 0) > 70:
            alerts.append({'level': 'warn', 'message': f"Raspi memory high: {raspi['mem']}%"})
        if raspi.get('disk', 0) > 90:
            alerts.append({'level': 'err', 'message': f"Raspi disk critical: {raspi['disk']}%"})
    stale_campaigns = [c['name'] for c in email.get('campaigns', []) if c.get('stale', False)]
    if stale_campaigns:
        alerts.append({'level': 'info', 'message': f"Stale stats: {', '.join(stale_campaigns[:3])}..."})
    return alerts


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/stats')
def api_stats():
    disk = get_disk_usage()
    docker = get_docker_status()
    logs = get_log_stats()
    email = get_email_stats()
    raspi = get_raspi_stats()
    return jsonify({
        'uptime': get_uptime(),
        'alerts': get_alerts(disk, docker, logs, email, raspi),
        'email': email,
        'scrapers': get_scraper_stats(),
        'logs': logs,
        'disk': disk,
        'docker': docker,
        'services': get_services(),
        'raspi': raspi,
        'failover': get_failover_status(),
        'brevo_warmup': get_brevo_warmup_status(),
        'a2_warmup': get_a2_warmup_status()
    })


@app.route('/api/logs')
def api_logs():
    logs = []
    for log in LOG_DIR.rglob('*.log'):
        try:
            stat = log.stat()
            logs.append({
                'path': str(log),
                'name': log.name,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        except:
            pass
    return jsonify(sorted(logs, key=lambda x: x['modified'], reverse=True))


@app.route('/api/raspi')
def api_raspi():
    return jsonify(get_raspi_stats())


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Unified Dashboard v3.1')
    parser.add_argument('--port', type=int, default=8085)
    parser.add_argument('--host', default='0.0.0.0')
    args = parser.parse_args()
    print(f"Starting Unified Dashboard v3.1 on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False, threaded=True)
