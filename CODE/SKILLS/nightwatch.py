#!/usr/bin/env python3
"""
Nightwatch - Comprehensive monitoring that alerts you IMMEDIATELY when things break.
Run every 10 minutes via cron.
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from alerting import send_telegram

STATE_FILE = Path('/opt/ACTIVE/INFRA/LOGS/nightwatch_state.json')

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {'last_alerts': {}}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def should_alert(state, key, cooldown_minutes=60):
    """Only alert once per cooldown period."""
    last = state['last_alerts'].get(key)
    if not last:
        return True
    last_time = datetime.fromisoformat(last)
    return datetime.now() - last_time > timedelta(minutes=cooldown_minutes)

def mark_alerted(state, key):
    state['last_alerts'][key] = datetime.now().isoformat()

def check_docker():
    """Check if critical containers are running."""
    issues = []
    critical = ['odoo', 'odoo-db', 'freescout', 'freescout-db']
    
    result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'], 
                          capture_output=True, text=True)
    running = result.stdout.strip().split('\n')
    
    for container in critical:
        if container not in running:
            issues.append(f"Docker DOWN: {container}")
    
    return issues

def check_disk():
    """Check disk usage."""
    issues = []
    result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
    for line in result.stdout.split('\n')[1:]:
        if line:
            parts = line.split()
            usage = int(parts[4].replace('%', ''))
            if usage > 90:
                issues.append(f"DISK CRITICAL: {usage}% full")
            elif usage > 80:
                issues.append(f"DISK WARNING: {usage}% full")
    return issues

def check_campaigns():
    """Check if campaigns are blocked."""
    issues = []
    lock_file = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/GLOBAL_SEND_LOCK')
    
    if lock_file.exists():
        content = lock_file.read_text().strip()
        if content:
            issues.append(f"CAMPAIGNS BLOCKED: {content[:50]}")
    
    return issues

def check_nodered():
    """Check if Node-RED is running."""
    issues = []
    result = subprocess.run(['systemctl', 'is-active', 'nodered'], 
                          capture_output=True, text=True)
    if result.stdout.strip() != 'active':
        issues.append("Node-RED DOWN")
    return issues

def check_postgres():
    """Check if PostgreSQL is running."""
    issues = []
    result = subprocess.run(['systemctl', 'is-active', 'postgresql'], 
                          capture_output=True, text=True)
    if result.stdout.strip() != 'active':
        issues.append("PostgreSQL DOWN")
    return issues

def check_scrapers_output():
    """Check if scrapers produced output today."""
    issues = []
    today = datetime.now().strftime('%Y%m%d')
    logs_dir = Path('/opt/ACTIVE/INFRA/LOGS/scrapers')
    
    # Only check after 8am
    if datetime.now().hour < 8:
        return issues
    
    today_logs = list(logs_dir.glob(f'*{today}*.log'))
    if not today_logs:
        issues.append("NO SCRAPER LOGS TODAY")
    
    return issues

def main():
    state = load_state()
    all_issues = []
    
    checks = [
        ('docker', check_docker),
        ('disk', check_disk),
        ('campaigns', check_campaigns),
        ('nodered', check_nodered),
        ('postgres', check_postgres),
        ('scrapers', check_scrapers_output),
    ]
    
    for name, check_fn in checks:
        try:
            issues = check_fn()
            for issue in issues:
                key = f"{name}:{issue[:30]}"
                if should_alert(state, key):
                    all_issues.append(issue)
                    mark_alerted(state, key)
        except Exception as e:
            print(f"Check {name} failed: {e}")
    
    save_state(state)
    
    if all_issues:
        msg = f"🚨 NIGHTWATCH ALERT ({datetime.now():%H:%M})\n\n"
        msg += "\n".join(f"• {i}" for i in all_issues)
        print(msg)
        send_telegram(msg)
        return 1
    else:
        print(f"[{datetime.now():%H:%M}] All systems OK")
        return 0

if __name__ == '__main__':
    sys.exit(main())
