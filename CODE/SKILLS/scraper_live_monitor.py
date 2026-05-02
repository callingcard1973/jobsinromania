#!/usr/bin/env python3
"""
Live Scraper Monitor - Watch scrapers in real-time.

Usage:
    python3 scraper_live_monitor.py              # Monitor all active scrapers
    python3 scraper_live_monitor.py paginiaurii  # Monitor specific scraper
    python3 scraper_live_monitor.py --once       # Single status check
"""

import sys
import os
import time
import json
import subprocess
from pathlib import Path
from datetime import datetime

PROGRESS_DIR = Path('/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
LOG_DIR = Path('/opt/ACTIVE/INFRA/LOGS/scrapers')

def get_running_scrapers():
    """Get list of running scraper processes."""
    result = subprocess.run(
        ['ps', 'aux'], capture_output=True, text=True
    )
    scrapers = []
    for line in result.stdout.split('\n'):
        if 'python' in line.lower() and 'scraper' in line.lower():
            if 'grep' not in line and 'monitor' not in line:
                parts = line.split()
                if len(parts) >= 11:
                    pid = parts[1]
                    cpu = parts[2]
                    mem = parts[3]
                    cmd = ' '.join(parts[10:])
                    # Extract scraper name
                    name = 'unknown'
                    for word in cmd.split():
                        if 'scraper' in word.lower() and '.py' in word:
                            name = Path(word).stem
                            break
                    scrapers.append({
                        'pid': pid,
                        'cpu': cpu,
                        'mem': mem,
                        'name': name,
                        'cmd': cmd[:80]
                    })
    return scrapers

def get_progress(scraper_name):
    """Get progress from JSON file."""
    progress_file = PROGRESS_DIR / f'{scraper_name}_progress.json'
    if progress_file.exists():
        try:
            data = json.loads(progress_file.read_text())
            return data
        except:
            pass
    return None

def get_log_tail(scraper_name, lines=5):
    """Get last N lines of log file."""
    # Try multiple log file patterns
    patterns = [
        f'{scraper_name}_full.log',
        f'{scraper_name}.log',
        f'{scraper_name}_*.log',
    ]
    for pattern in patterns:
        matches = list(LOG_DIR.glob(pattern))
        if matches:
            log_file = max(matches, key=lambda p: p.stat().st_mtime)
            try:
                result = subprocess.run(
                    ['tail', '-n', str(lines), str(log_file)],
                    capture_output=True, text=True
                )
                return result.stdout.strip()
            except:
                pass
    return None

def get_output_stats(scraper_name):
    """Get output file stats."""
    # Common output locations
    output_dirs = [
        Path(f'/opt/ACTIVE/OPENDATA/DATA/ROMANIA/PAGINI_AURII'),
        Path(f'/opt/ACTIVE/OPENDATA/DATA/{scraper_name.upper()}'),
        Path(f'/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/{scraper_name.upper()}/OUTPUT'),
        Path(f'/mnt/hdd/SCRAPER_DATA/csv/{scraper_name.upper()}'),
    ]

    for output_dir in output_dirs:
        if output_dir.exists():
            csvs = list(output_dir.glob('*.csv'))
            if csvs:
                latest = max(csvs, key=lambda p: p.stat().st_mtime)
                # Count rows
                try:
                    result = subprocess.run(
                        ['wc', '-l', str(latest)],
                        capture_output=True, text=True
                    )
                    rows = int(result.stdout.split()[0]) - 1  # minus header
                    mtime = datetime.fromtimestamp(latest.stat().st_mtime)
                    return {
                        'file': latest.name,
                        'rows': rows,
                        'updated': mtime.strftime('%H:%M:%S'),
                        'dir': str(output_dir)
                    }
                except:
                    pass
    return None

def display_status(scraper_name=None, clear=True):
    """Display current scraper status."""
    if clear:
        os.system('clear')

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"=== SCRAPER LIVE MONITOR ({now}) ===\n")

    scrapers = get_running_scrapers()

    if scraper_name:
        scrapers = [s for s in scrapers if scraper_name.lower() in s['name'].lower()]

    if not scrapers:
        print("No scrapers running.")
        if scraper_name:
            print(f"\nLooking for: {scraper_name}")
        return

    for scraper in scrapers:
        name = scraper['name']
        print(f"--- {name.upper()} (PID: {scraper['pid']}) ---")
        print(f"CPU: {scraper['cpu']}%  MEM: {scraper['mem']}%")

        # Progress
        progress = get_progress(name)
        if progress:
            status = progress.get('status', 'unknown')
            category = progress.get('current_category', '-')
            stats = progress.get('stats', {})
            print(f"Status: {status}")
            print(f"Category: {category}")
            if stats:
                print(f"Stats: {json.dumps(stats)}")

        # Output
        output = get_output_stats(name)
        if output:
            print(f"Output: {output['file']} ({output['rows']} rows, updated {output['updated']})")

        # Log tail
        log = get_log_tail(name, 3)
        if log:
            print(f"\nRecent log:")
            for line in log.split('\n'):
                print(f"  {line[:100]}")

        print()

def monitor_loop(scraper_name=None, interval=10):
    """Continuous monitoring loop."""
    print("Press Ctrl+C to stop monitoring\n")
    try:
        while True:
            display_status(scraper_name)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description='Live Scraper Monitor')
    p.add_argument('scraper', nargs='?', help='Scraper name to monitor')
    p.add_argument('--once', action='store_true', help='Single check, no loop')
    p.add_argument('--interval', '-i', type=int, default=10, help='Update interval (seconds)')
    args = p.parse_args()

    if args.once:
        display_status(args.scraper, clear=False)
    else:
        monitor_loop(args.scraper, args.interval)
