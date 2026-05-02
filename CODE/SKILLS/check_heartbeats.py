#!/usr/bin/env python3
"""
Check scraper heartbeats - alert if stuck
"""
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from alerting import send_telegram

HEARTBEAT_DIR = Path('/tmp/scraper_heartbeats')
MAX_STALE_MINUTES = 10

def check_heartbeats():
    if not HEARTBEAT_DIR.exists():
        return []
    
    stuck = []
    now = time.time()
    
    for hb_file in HEARTBEAT_DIR.glob('*.heartbeat'):
        try:
            content = hb_file.read_text().strip().split('\n')
            timestamp = float(content[0])
            age_minutes = (now - timestamp) / 60
            
            if age_minutes > MAX_STALE_MINUTES:
                stuck.append(f"{hb_file.stem}: stale {age_minutes:.0f}min")
        except:
            pass
    
    return stuck

def main():
    stuck = check_heartbeats()
    
    if stuck:
        msg = f"🚨 STUCK SCRAPERS\n\n" + "\n".join(stuck)
        print(msg)
        if '--alert' in sys.argv:
            send_telegram(msg)
        return 1
    else:
        print("All heartbeats OK")
        return 0

if __name__ == '__main__':
    sys.exit(main())
