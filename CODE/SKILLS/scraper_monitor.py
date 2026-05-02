#!/usr/bin/env python3
"""
Scraper Monitor - Dashboard for all scrapers health and status
Usage: python3 scraper_monitor.py [--full] [--json]
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, sanitize, FIELD_LIMITS

import os
import glob
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Optional

# ============================================================
# CONFIGURATION
# ============================================================

SCRAPER_BASE = '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE'
OUTPUT_DIRS = [
    '/mnt/hdd/SCRAPER_DATA/csv',
    '/mnt/hdd/SCRAPER_DATA',
    '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE',
]

SCRAPERS = {
    'BULGARIA': {'script': 'bulgarian_job_scraper.py', 'patterns': ['bulgaria*.csv', 'bg_*.csv']},
    'DENMARK': {'script': 'jobindex_scraper.py', 'patterns': ['denmark*.csv', 'dk_*.csv', 'jobindex*.csv']},
    'EURES': {'script': 'eures_scraper.py', 'patterns': ['eures*.csv']},
    'FINLAND': {'script': 'finland_scraper.py', 'patterns': ['finland*.csv', 'fi_*.csv']},
    'FRANCE': {'script': 'france_scraper.py', 'patterns': ['france*.csv', 'fr_*.csv']},
    'ICELAND': {'script': 'iceland_scraper.py', 'patterns': ['iceland*.csv', 'is_*.csv']},
    'IRELAND': {'script': 'ireland_scraper.py', 'patterns': ['ireland*.csv', 'ie_*.csv']},
    'MALTA': {'script': 'malta_scraper.py', 'patterns': ['malta*.csv', 'mt_*.csv']},
    'MOLDOVA': {'script': 'moldova_scraper.py', 'patterns': ['moldova*.csv', 'md_*.csv']},
    'NETHERLANDS': {'script': 'netherlands_scraper.py', 'patterns': ['netherlands*.csv', 'nl_*.csv']},
    'NORWAY': {'script': 'nav_scraper.py', 'patterns': ['norway*.csv', 'nav*.csv', 'no_*.csv']},
    'NORTH_MACEDONIA': {'script': 'north_macedonia_scraper.py', 'patterns': ['macedonia*.csv', 'mk_*.csv']},
    'POLAND': {'script': 'kraz_scraper.py', 'patterns': ['poland*.csv', 'kraz*.csv', 'pl_*.csv']},
    'ROMANIA': {'script': 'anofm_scraper.py', 'patterns': ['romania*.csv', 'anofm*.csv', 'ro_*.csv']},
    'SWEDEN': {'script': 'sweden_scraper.py', 'patterns': ['sweden*.csv', 'se_*.csv']},
    'UK': {'script': 'uk_scraper.py', 'patterns': ['uk_*.csv', 'britain*.csv']},
    'CAREWORKERS_EU': {'script': 'careworkers_scraper.py', 'patterns': ['careworker*.csv', 'care_*.csv']},
    'FACTORYJOBS_EU': {'script': 'factoryjobs_scraper.py', 'patterns': ['factory*.csv', 'factory_*.csv']},
}

# ============================================================
# STATUS CHECKING
# ============================================================

def get_scraper_status(name: str, config: Dict) -> Dict:
    """Get status for a single scraper"""
    scraper_dir = os.path.join(SCRAPER_BASE, name)

    status = {
        'name': name,
        'exists': os.path.isdir(scraper_dir),
        'script': config.get('script'),
        'script_exists': False,
        'last_modified': None,
        'last_output': None,
        'last_output_file': None,
        'last_output_size': 0,
        'last_output_rows': 0,
        'outputs_24h': 0,
        'outputs_7d': 0,
        'total_outputs': 0,
        'health': 'unknown',
        'issues': [],
    }

    if not status['exists']:
        status['health'] = 'missing'
        status['issues'].append('Scraper directory not found')
        return status

    # Check script exists
    script_path = os.path.join(scraper_dir, config.get('script', ''))
    if os.path.exists(script_path):
        status['script_exists'] = True
        status['last_modified'] = datetime.fromtimestamp(os.path.getmtime(script_path))
    else:
        # Try to find any Python script
        scripts = glob.glob(os.path.join(scraper_dir, '*.py'))
        if scripts:
            status['script_exists'] = True
            status['script'] = os.path.basename(scripts[0])
            status['last_modified'] = datetime.fromtimestamp(os.path.getmtime(scripts[0]))
        else:
            status['issues'].append('No Python script found')

    # Find output files
    outputs = []
    for output_dir in OUTPUT_DIRS:
        for pattern in config.get('patterns', []):
            # Check in base dir
            outputs.extend(glob.glob(os.path.join(output_dir, pattern)))
            # Check in country subdir
            outputs.extend(glob.glob(os.path.join(output_dir, name, pattern)))
            # Check in subdirs
            outputs.extend(glob.glob(os.path.join(output_dir, '**', pattern), recursive=True))

    # Also check scraper dir itself
    for pattern in config.get('patterns', []):
        outputs.extend(glob.glob(os.path.join(scraper_dir, pattern)))
        outputs.extend(glob.glob(os.path.join(scraper_dir, '**', pattern), recursive=True))

    # Dedupe and sort by mtime
    outputs = list(set(outputs))
    if outputs:
        outputs_with_time = [(f, os.path.getmtime(f)) for f in outputs if os.path.exists(f)]
        outputs_with_time.sort(key=lambda x: -x[1])

        status['total_outputs'] = len(outputs_with_time)

        now = datetime.now().timestamp()
        status['outputs_24h'] = sum(1 for _, t in outputs_with_time if now - t < 86400)
        status['outputs_7d'] = sum(1 for _, t in outputs_with_time if now - t < 604800)

        if outputs_with_time:
            latest = outputs_with_time[0]
            status['last_output'] = datetime.fromtimestamp(latest[1])
            status['last_output_file'] = latest[0]
            status['last_output_size'] = os.path.getsize(latest[0])

            # Count rows
            try:
                with open(latest[0], 'r', encoding='utf-8', errors='ignore') as f:
                    status['last_output_rows'] = sum(1 for _ in f) - 1  # Minus header
            except Exception:
                pass

    # Determine health
    if status['last_output']:
        age = datetime.now() - status['last_output']
        if age < timedelta(days=1):
            status['health'] = 'healthy'
        elif age < timedelta(days=7):
            status['health'] = 'stale'
            status['issues'].append(f'No output in {age.days} days')
        else:
            status['health'] = 'dead'
            status['issues'].append(f'No output in {age.days} days')
    else:
        status['health'] = 'no_output'
        status['issues'].append('No output files found')

    return status

def get_all_status() -> List[Dict]:
    """Get status for all scrapers"""
    results = []
    for name, config in SCRAPERS.items():
        status = get_scraper_status(name, config)
        results.append(status)
    return results

def check_cron_jobs() -> Dict:
    """Check cron jobs related to scrapers"""
    cron_info = {'jobs': [], 'scraper_jobs': 0}

    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    cron_info['jobs'].append(line)
                    if 'scraper' in line.lower() or 'SCRAPERS' in line:
                        cron_info['scraper_jobs'] += 1
    except Exception:
        pass

    return cron_info

def check_disk_space() -> Dict:
    """Check disk space for output directories"""
    disk_info = {}

    for path in ['/mnt/usb', '/opt']:
        try:
            stat = os.statvfs(path)
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bavail * stat.f_frsize
            used = total - free
            disk_info[path] = {
                'total_gb': round(total / 1024**3, 1),
                'used_gb': round(used / 1024**3, 1),
                'free_gb': round(free / 1024**3, 1),
                'percent_used': round(used * 100 / total, 1) if total > 0 else 0,
            }
        except Exception:
            pass

    return disk_info

# ============================================================
# OUTPUT
# ============================================================

def print_dashboard(statuses: List[Dict], full: bool = False):
    """Print scraper dashboard"""
    print(f"\n{'='*70}")
    print(f"SCRAPER MONITOR - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*70}\n")

    # Summary
    healthy = sum(1 for s in statuses if s['health'] == 'healthy')
    stale = sum(1 for s in statuses if s['health'] == 'stale')
    dead = sum(1 for s in statuses if s['health'] == 'dead')
    missing = sum(1 for s in statuses if s['health'] in ['missing', 'no_output'])

    print(f"SUMMARY:")
    print(f"  Total scrapers: {len(statuses)}")
    print(f"  Healthy (24h):  {healthy} {'#' * healthy}")
    print(f"  Stale (7d):     {stale} {'#' * stale}")
    print(f"  Dead (>7d):     {dead} {'#' * dead}")
    print(f"  Missing/None:   {missing} {'#' * missing}")

    # Disk space
    disk = check_disk_space()
    if disk:
        print(f"\nDISK SPACE:")
        for path, info in disk.items():
            bar = '#' * int(info['percent_used'] / 5)
            print(f"  {path}: {info['used_gb']}/{info['total_gb']} GB ({info['percent_used']}%) [{bar}]")

    # Status table
    print(f"\n{'='*70}")
    print(f"{'SCRAPER':<20} {'HEALTH':<10} {'LAST OUTPUT':<12} {'ROWS':>8} {'24H':>4} {'7D':>4}")
    print(f"{'-'*70}")

    # Sort by health (healthy first, then stale, then dead, then missing)
    health_order = {'healthy': 0, 'stale': 1, 'dead': 2, 'no_output': 3, 'missing': 4, 'unknown': 5}
    statuses_sorted = sorted(statuses, key=lambda s: (health_order.get(s['health'], 5), s['name']))

    for s in statuses_sorted:
        health_icon = {
            'healthy': '[OK]',
            'stale': '[!]',
            'dead': '[X]',
            'missing': '[-]',
            'no_output': '[?]',
        }.get(s['health'], '[?]')

        last_output = ''
        if s['last_output']:
            age = datetime.now() - s['last_output']
            if age < timedelta(hours=24):
                last_output = f"{int(age.total_seconds() / 3600)}h ago"
            else:
                last_output = f"{age.days}d ago"

        print(f"{s['name']:<20} {health_icon:<10} {last_output:<12} {s['last_output_rows']:>8} {s['outputs_24h']:>4} {s['outputs_7d']:>4}")

    # Issues
    issues = [(s['name'], s['issues']) for s in statuses if s['issues']]
    if issues:
        print(f"\n{'='*70}")
        print(f"ISSUES:")
        for name, issue_list in issues:
            for issue in issue_list:
                print(f"  [{name}] {issue}")

    # Full details
    if full:
        print(f"\n{'='*70}")
        print(f"DETAILED STATUS:")
        for s in statuses_sorted:
            print(f"\n  {s['name']}:")
            print(f"    Script: {s['script']} ({'exists' if s['script_exists'] else 'NOT FOUND'})")
            if s['last_modified']:
                print(f"    Script modified: {s['last_modified'].strftime('%Y-%m-%d')}")
            if s['last_output']:
                print(f"    Last output: {s['last_output'].strftime('%Y-%m-%d %H:%M')}")
                print(f"    Output file: {s['last_output_file']}")
                print(f"    Size: {s['last_output_size'] / 1024:.1f} KB, Rows: {s['last_output_rows']}")
            print(f"    Total outputs: {s['total_outputs']}")

    print(f"\n{'='*70}\n")

# ============================================================
# MAIN
# ============================================================

def main():
    args = sys.argv[1:]

    full = '--full' in args
    as_json = '--json' in args

    if '-h' in args or '--help' in args:
        print(f"""
{'='*60}
SCRAPER MONITOR
{'='*60}

Usage: scraper_monitor.py [options]

Options:
  --full    Show detailed status for each scraper
  --json    Output as JSON

Monitors {len(SCRAPERS)} scrapers in {SCRAPER_BASE}
""")
        return

    statuses = get_all_status()

    if as_json:
        # Convert datetime to string for JSON
        for s in statuses:
            if s['last_modified']:
                s['last_modified'] = s['last_modified'].isoformat()
            if s['last_output']:
                s['last_output'] = s['last_output'].isoformat()
        print(json.dumps(statuses, indent=2))
    else:
        print_dashboard(statuses, full)

if __name__ == '__main__':
    main()
