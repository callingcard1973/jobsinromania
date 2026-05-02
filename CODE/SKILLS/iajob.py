#!/usr/bin/env python3
"""IAJOB scraper skill.

Usage:
    python3 iajob.py scrape [--limit N]    # Scrape jobs (incremental by default)
    python3 iajob.py scrape --full         # Full scrape (ignore seen jobs)  
    python3 iajob.py status                # Show scraper status
    python3 iajob.py clean                 # Clean seen jobs (next run = full)
"""
import os
import sys
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

SCRAPER = '/opt/ACTIVE/SCRAPERS/EUROPE/ROMANIA/IAJOB/src/iajob_scraper.py'
OUTPUT = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/IAJOB/jobs.csv'
SEEN_FILE = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/IAJOB/seen_jobs.txt'
STATE_FILE = '/opt/ACTIVE/SCRAPERS/EUROPE/ROMANIA/IAJOB/src/scraper_state.json'

def run_scrape(limit=0, full=False):
    if full and Path(SEEN_FILE).exists():
        print(f'Removing {SEEN_FILE} for full scrape')
        Path(SEEN_FILE).unlink()
    
    cmd = ['/opt/ACTIVE/INFRA/venv/bin/python3', SCRAPER]
    if limit:
        cmd.extend(['--limit', str(limit)])
    
    print(f'Running: {" ".join(cmd)}')
    subprocess.run(cmd)

def show_status():
    print('=== IAJOB Status ===')
    
    if Path(OUTPUT).exists():
        stat = Path(OUTPUT).stat()
        rows = sum(1 for _ in open(OUTPUT)) - 1
        mtime = datetime.fromtimestamp(stat.st_mtime)
        print(f'Output: {OUTPUT}')
        print(f'Jobs: {rows}')
        print(f'Updated: {mtime}')
    else:
        print('No output file')
    
    if Path(SEEN_FILE).exists():
        seen = sum(1 for _ in open(SEEN_FILE))
        print(f'Seen jobs: {seen}')
    else:
        print('Seen jobs: 0 (full scrape on next run)')

def clean_seen():
    if Path(SEEN_FILE).exists():
        Path(SEEN_FILE).unlink()
        print(f'Removed {SEEN_FILE}')
        print('Next run will be a full scrape')
    else:
        print('Already clean')

def main():
    parser = argparse.ArgumentParser(description='IAJOB scraper skill')
    parser.add_argument('action', choices=['scrape', 'status', 'clean'])
    parser.add_argument('--limit', type=int, default=0, help='Limit jobs')
    parser.add_argument('--full', action='store_true', help='Full scrape')
    
    args = parser.parse_args()
    
    if args.action == 'scrape':
        run_scrape(args.limit, args.full)
    elif args.action == 'status':
        show_status()
    elif args.action == 'clean':
        clean_seen()

if __name__ == '__main__':
    main()
