#!/usr/bin/env python3
"""
Scraper Health Monitor - Alerts if scrapers haven't run
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from alerting import send_telegram

LOGS_DIR = Path('/opt/ACTIVE/INFRA/LOGS/scrapers')
MAX_AGE_HOURS = 48

SCRAPERS = [
    ('Denmark', 'denmark'),
    ('Sweden', 'sweden'),
    ('Norway', 'norway'),
    ('Finland', 'finland'),
    ('Iceland', 'iceland'),
    ('EURES', 'eures'),
    ('Bulgaria', 'bulgaria'),
    ('ANOFM', 'anofm'),
]

def check_scraper_logs():
    """Check when each scraper last ran."""
    alerts = []
    cutoff = datetime.now() - timedelta(hours=MAX_AGE_HOURS)
    
    for name, pattern in SCRAPERS:
        # Find most recent log
        logs = list(LOGS_DIR.glob(f'{pattern}*.log'))
        if not logs:
            alerts.append(f"⚠️ {name}: NO LOGS FOUND")
            continue
        
        newest = max(logs, key=lambda x: x.stat().st_mtime)
        mtime = datetime.fromtimestamp(newest.stat().st_mtime)
        
        if mtime < cutoff:
            age_hours = (datetime.now() - mtime).total_seconds() / 3600
            alerts.append(f"⚠️ {name}: Last run {age_hours:.0f}h ago")
        else:
            print(f"✓ {name}: {mtime:%Y-%m-%d %H:%M}")
    
    return alerts

def main():
    print(f"Checking scrapers (max age: {MAX_AGE_HOURS}h)\n")
    
    alerts = check_scraper_logs()
    
    if alerts:
        msg = "🚨 SCRAPER HEALTH ALERT\n\n" + "\n".join(alerts)
        print("\n" + msg)
        if '--alert' in sys.argv:
            send_telegram(msg)
    else:
        print("\n✓ All scrapers healthy")

if __name__ == '__main__':
    main()
