#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
Nordic Jobs Skill - Unified dashboard for Scandinavian job scrapers.

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/nordic_jobs.py --status     # Check all scrapers
    python3 /opt/ACTIVE/INFRA/SKILLS/nordic_jobs.py --run DK     # Run Denmark scraper
    python3 /opt/ACTIVE/INFRA/SKILLS/nordic_jobs.py --run all    # Run all scrapers
    python3 /opt/ACTIVE/INFRA/SKILLS/nordic_jobs.py --gaps       # Show coverage gaps
    python3 /opt/ACTIVE/INFRA/SKILLS/nordic_jobs.py --schedule   # Show/set schedules

See /opt/CLAUDE.md for shared code rules.
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import csv
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import argparse
import json

from skills_common import to_ascii, sanitize

# Country configs
NORDIC_COUNTRIES = {
    'DK': {
        'name': 'Denmark',
        'scraper': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/DENMARK/danish_scraper.py',
        'output': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/DENMARK/OUTPUT/Denmark_ULTIMATE_MASTER.csv',
        'portals': ['jobnet.dk', 'jobindex.dk'],
        'gaps': ['workindenmark.dk'],
        'extra_scrapers': ['/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/DENMARK/jobindex_scraper.py'],
    },
    'SE': {
        'name': 'Sweden',
        'scraper': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/SWEDEN/sweden_scraper.py',
        'output': '/mnt/hdd/SCRAPER_DATA/csv/SWEDEN/Sweden_MASTER_50.csv',
        'portals': ['arbetsformedlingen.se'],
        'gaps': ['blocket.se', 'indeed.se'],
    },
    'NO': {
        'name': 'Norway',
        'scraper': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/NORWAY/arbeidsplassen_scraper.py',
        'output': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/NORWAY/OUTPUT/Norway_MASTER_50.csv',
        'portals': ['arbeidsplassen.nav.no', 'finn.no'],
        'gaps': ['indeed.no'],
        'extra_scrapers': ['/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/NORWAY/finn_scraper.py'],
    },
    'FI': {
        'name': 'Finland',
        'scraper': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/FINLAND/run_working_scrapers.py',
        'output': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/FINLAND/output/',
        'portals': ['te-palvelut.fi', 'tyomarkkinatori.fi', 'valtiolle.fi', 'kuntarekry.fi', 'duunitori.fi'],
        'gaps': ['oikotie.fi'],
        'extra_scrapers': ['/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/FINLAND/duunitori_scraper.py'],
    },
    'IS': {
        'name': 'Iceland',
        'scraper': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ICELAND/run_iceland.sh',
        'output': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ICELAND/ISLAND/OUTPUT/',
        'portals': ['island.is', 'alfred.is'],
        'gaps': ['vinnumalastofnun.is'],
    },
}

# EURES Nordic coverage
EURES_OUTPUT = '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/EURES/OUTPUT'


def get_file_stats(path: str) -> Dict:
    """Get file modification time and row count."""
    p = Path(path)
    if not p.exists():
        return {'exists': False, 'rows': 0, 'age_hours': None, 'mtime': None}

    if p.is_dir():
        # Find most recent CSV in directory
        csvs = list(p.glob('*.csv'))
        if not csvs:
            return {'exists': False, 'rows': 0, 'age_hours': None, 'mtime': None}
        p = max(csvs, key=lambda x: x.stat().st_mtime)

    mtime = datetime.fromtimestamp(p.stat().st_mtime)
    age = datetime.now() - mtime

    # Count rows
    rows = 0
    try:
        with open(p, 'r', encoding='utf-8', errors='ignore') as f:
            rows = sum(1 for _ in f) - 1  # Subtract header
    except Exception:
        pass

    return {
        'exists': True,
        'rows': max(0, rows),
        'age_hours': age.total_seconds() / 3600,
        'mtime': mtime.strftime('%Y-%m-%d %H:%M'),
        'file': str(p),
    }


def get_eures_stats() -> Dict[str, Dict]:
    """Get EURES output stats per country."""
    stats = {}
    eures_path = Path(EURES_OUTPUT)

    for code, cfg in NORDIC_COUNTRIES.items():
        country_name = cfg['name']
        country_dir = eures_path / country_name
        if country_dir.exists():
            csvs = list(country_dir.glob('*_contacts_50.csv'))
            if csvs:
                latest = max(csvs, key=lambda x: x.stat().st_mtime)
                stats[code] = get_file_stats(str(latest))
            else:
                stats[code] = {'exists': False, 'rows': 0}
        else:
            stats[code] = {'exists': False, 'rows': 0}

    return stats


def show_status():
    """Show status of all Nordic scrapers."""
    print("=" * 70)
    print("NORDIC JOBS SCRAPER STATUS")
    print("=" * 70)
    print()

    # Country scrapers
    print("COUNTRY SCRAPERS:")
    print("-" * 70)
    print(f"{'Country':<12} {'Rows':>8} {'Last Update':<18} {'Age (hrs)':>10} {'Status':<10}")
    print("-" * 70)

    total_rows = 0
    stale_count = 0

    for code, cfg in NORDIC_COUNTRIES.items():
        stats = get_file_stats(cfg['output'])
        total_rows += stats['rows']

        if not stats['exists']:
            status = 'MISSING'
        elif stats['age_hours'] > 48:
            status = 'STALE'
            stale_count += 1
        elif stats['age_hours'] > 24:
            status = 'OLD'
        else:
            status = 'OK'

        age_str = f"{stats['age_hours']:.1f}" if stats.get('age_hours') else '-'
        mtime_str = stats.get('mtime') or '-'

        print(f"{cfg['name']:<12} {stats['rows']:>8} {mtime_str:<18} {age_str:>10} {status:<10}")

    print("-" * 70)
    print(f"{'TOTAL':<12} {total_rows:>8}")
    print()

    # EURES supplement
    print("EURES NORDIC (Supplement):")
    print("-" * 70)
    eures_stats = get_eures_stats()
    eures_total = 0

    for code, stats in eures_stats.items():
        country_name = NORDIC_COUNTRIES[code]['name']
        eures_total += stats['rows']
        mtime_str = stats.get('mtime', '-')
        print(f"{country_name:<12} {stats['rows']:>8} {mtime_str:<18}")

    print("-" * 70)
    print(f"{'EURES TOTAL':<12} {eures_total:>8}")
    print()

    # Summary
    print("SUMMARY:")
    print(f"  Total Nordic jobs: {total_rows + eures_total:,}")
    print(f"  Stale scrapers (>48h): {stale_count}")
    print()


def show_gaps():
    """Show coverage gaps for each country."""
    print("=" * 70)
    print("NORDIC JOB PORTAL COVERAGE GAPS")
    print("=" * 70)
    print()

    for code, cfg in NORDIC_COUNTRIES.items():
        print(f"{cfg['name'].upper()}")
        print(f"  Currently scraped: {', '.join(cfg['portals'])}")
        print(f"  NOT scraped:       {', '.join(cfg['gaps'])}")
        print()


def run_scraper(country_code: str) -> bool:
    """Run scraper for a specific country."""
    if country_code.upper() == 'ALL':
        success = True
        for code in NORDIC_COUNTRIES:
            if not run_scraper(code):
                success = False
        return success

    code = country_code.upper()
    if code not in NORDIC_COUNTRIES:
        print(f"Unknown country: {country_code}")
        print(f"Valid codes: {', '.join(NORDIC_COUNTRIES.keys())}")
        return False

    cfg = NORDIC_COUNTRIES[code]
    scraper = cfg['scraper']

    if not Path(scraper).exists():
        print(f"Scraper not found: {scraper}")
        return False

    print(f"Running {cfg['name']} scraper...")
    print(f"  Script: {scraper}")

    try:
        result = subprocess.run(
            ['/opt/ACTIVE/INFRA/venv/bin/python3', scraper],
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour timeout
            cwd=str(Path(scraper).parent)
        )

        if result.returncode == 0:
            print(f"  Status: SUCCESS")
            # Show new stats
            stats = get_file_stats(cfg['output'])
            print(f"  Rows: {stats['rows']}")
            return True
        else:
            print(f"  Status: FAILED")
            print(f"  Error: {result.stderr[:500] if result.stderr else 'Unknown'}")
            return False

    except subprocess.TimeoutExpired:
        print(f"  Status: TIMEOUT (>1h)")
        return False
    except Exception as e:
        print(f"  Status: ERROR - {e}")
        return False


def show_schedules():
    """Show current schedules for Nordic scrapers."""
    print("=" * 70)
    print("NORDIC SCRAPER SCHEDULES")
    print("=" * 70)
    print()

    schedules = {
        'DK': 'Not scheduled (manual)',
        'SE': 'Daily 05:43 (Node-RED)',
        'NO': 'Daily 10:47 + 23:08 (Node-RED)',
        'FI': 'Tue & Fri 07:00 (cron)',
        'IS': 'Not scheduled (manual)',
        'EURES': 'Continuous every 2h (systemd)',
    }

    print(f"{'Country':<12} {'Schedule':<40}")
    print("-" * 52)
    for code, schedule in schedules.items():
        name = NORDIC_COUNTRIES.get(code, {}).get('name', code)
        print(f"{name:<12} {schedule:<40}")
    print()

    print("RECOMMENDED DAILY SCHEDULE:")
    print("-" * 52)
    print("  02:00 - Denmark (Jobnet)")
    print("  03:00 - Iceland (Island.is, Alfred.is)")
    print("  04:00 - Norway (Arbeidsplassen)")
    print("  05:00 - Sweden (Arbetsformedlingen)")
    print("  06:00 - Finland (TE-palvelut + others)")
    print("  07:00 - EURES Nordic consolidation")
    print()


def main():
    parser = argparse.ArgumentParser(description='Nordic Jobs Skill')
    parser.add_argument('--status', action='store_true', help='Show status of all scrapers')
    parser.add_argument('--run', type=str, metavar='COUNTRY', help='Run scraper (DK/SE/NO/FI/IS/all)')
    parser.add_argument('--gaps', action='store_true', help='Show coverage gaps')
    parser.add_argument('--schedule', action='store_true', help='Show schedules')
    parser.add_argument('--json', action='store_true', help='Output as JSON')

    args = parser.parse_args()

    if args.run:
        run_scraper(args.run)
    elif args.gaps:
        show_gaps()
    elif args.schedule:
        show_schedules()
    else:
        show_status()


if __name__ == '__main__':
    main()
