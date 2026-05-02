#!/usr/bin/env python3
"""
Campaign Health Monitor - Alerts if campaigns are stuck
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from alerting import send_telegram

CAMPAIGNS_DIR = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS')
LOCK_FILE = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/GLOBAL_SEND_LOCK')

def check_global_lock():
    """Check if global send lock is set."""
    if LOCK_FILE.exists():
        content = LOCK_FILE.read_text().strip()
        if content:
            return f"GLOBAL LOCK SET: {content}"
    return None

def check_campaigns_sent_today():
    """Check if any emails were sent today."""
    today = datetime.now().strftime('%Y%m%d')
    total_sent = 0
    
    for campaign_dir in CAMPAIGNS_DIR.iterdir():
        if not campaign_dir.is_dir():
            continue
        log_file = campaign_dir / 'logs' / f'sent_{today}.log'
        if log_file.exists():
            content = log_file.read_text()
            sent = content.count('| OK |')
            total_sent += sent
    
    return total_sent

def main():
    alerts = []
    
    # Check global lock
    lock_status = check_global_lock()
    if lock_status:
        alerts.append(f"⚠️ {lock_status}")
    
    # Check if any emails sent today
    sent_today = check_campaigns_sent_today()
    if sent_today == 0:
        now = datetime.now()
        if now.hour >= 10:  # Only alert after 10am
            alerts.append(f"⚠️ NO EMAILS SENT TODAY (checked at {now:%H:%M})")
    else:
        print(f"✓ Emails sent today: {sent_today}")
    
    if alerts:
        msg = "🚨 CAMPAIGN HEALTH ALERT\n\n" + "\n".join(alerts)
        print(msg)
        if '--alert' in sys.argv:
            send_telegram(msg)
    else:
        print("✓ All campaigns healthy")

if __name__ == '__main__':
    main()
