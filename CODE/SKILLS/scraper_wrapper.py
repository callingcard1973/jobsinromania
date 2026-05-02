#!/usr/bin/env python3
"""
Scraper Wrapper - Runs scrapers with retries, heartbeat, and error handling.
Usage: python3 scraper_wrapper.py SCRAPER_PATH [args...]
"""
import os
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from alerting import send_telegram

MAX_RETRIES = 3
RETRY_DELAY = 300  # 5 minutes
HEARTBEAT_DIR = Path('/tmp/scraper_heartbeats')

def get_scraper_name(path):
    return Path(path).stem

def update_heartbeat(name):
    HEARTBEAT_DIR.mkdir(exist_ok=True)
    hb_file = HEARTBEAT_DIR / f"{name}.heartbeat"
    hb_file.write_text(f"{time.time()}\n{datetime.now().isoformat()}")

def run_scraper(scraper_path, args):
    name = get_scraper_name(scraper_path)
    log_file = Path(f'/opt/ACTIVE/INFRA/LOGS/scrapers/{name}_{datetime.now():%Y%m%d}.log')
    
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"[{datetime.now():%H:%M}] Starting {name} (attempt {attempt}/{MAX_RETRIES})")
        update_heartbeat(name)
        
        try:
            cmd = ['/opt/ACTIVE/INFRA/venv/bin/python3', scraper_path] + args
            
            with open(log_file, 'a') as log:
                log.write(f"\n{'='*50}\n")
                log.write(f"Started: {datetime.now()}\n")
                log.write(f"Attempt: {attempt}/{MAX_RETRIES}\n")
                log.write(f"{'='*50}\n\n")
                
                process = subprocess.Popen(
                    cmd,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    cwd=str(Path(scraper_path).parent)
                )
                
                # Monitor with heartbeat
                while process.poll() is None:
                    update_heartbeat(name)
                    time.sleep(60)
                
                exit_code = process.returncode
                
                log.write(f"\n{'='*50}\n")
                log.write(f"Finished: {datetime.now()}\n")
                log.write(f"Exit code: {exit_code}\n")
                log.write(f"{'='*50}\n")
            
            if exit_code == 0:
                print(f"[{datetime.now():%H:%M}] {name} completed successfully")
                return 0
            else:
                print(f"[{datetime.now():%H:%M}] {name} failed with code {exit_code}")
                
        except Exception as e:
            print(f"[{datetime.now():%H:%M}] {name} exception: {e}")
            with open(log_file, 'a') as log:
                log.write(f"\nEXCEPTION: {e}\n")
        
        if attempt < MAX_RETRIES:
            print(f"[{datetime.now():%H:%M}] Retrying in {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)
    
    # All retries failed
    msg = f"🚨 SCRAPER FAILED: {name}\n\nFailed after {MAX_RETRIES} attempts.\nCheck: {log_file}"
    print(msg)
    send_telegram(msg)
    return 1

def main():
    if len(sys.argv) < 2:
        print("Usage: scraper_wrapper.py SCRAPER_PATH [args...]")
        sys.exit(1)
    
    scraper_path = sys.argv[1]
    args = sys.argv[2:]
    
    if not Path(scraper_path).exists():
        print(f"Scraper not found: {scraper_path}")
        sys.exit(1)
    
    sys.exit(run_scraper(scraper_path, args))

if __name__ == '__main__':
    main()
