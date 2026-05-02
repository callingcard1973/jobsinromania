#!/usr/bin/env python3
"""
EU Funding Scrapers - Unified skill to manage all Romania EU funding scrapers
Usage:
    python3 eu_funding_scrapers.py --status       # Show all scrapers status
    python3 eu_funding_scrapers.py --run all      # Run all scrapers
    python3 eu_funding_scrapers.py --run pnrr     # Run specific scraper
    python3 eu_funding_scrapers.py --data         # Show data counts
"""
import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path

SCRAPERS = {
    'beneficiar': {
        'name': 'beneficiar.fonduri-ue.ro',
        'path': '/opt/ACTIVE/EU_FUNDING/CODE/SCRAPERS/SCRAPER_beneficiar.fonduri-ue/beneficiar_fonduri_ue_scraper.py',
        'cron': 'Daily 2 AM',
        'data': 'DB: european_funds.beneficiari_privati (21.5K) + proiecte (16K)',
        'commands': {
            '--status': 'Check DB counts',
            '--both --workers 30': 'Full parallel scrape',
            '--fix-desc --workers 20': 'Fix missing descriptions (~14/min)',
            '--anunturi --recent 5': 'Scrape recent anunturi',
            '--proiecte --recent 5': 'Scrape recent proiecte'
        }
    },
    'datagov': {
        'name': 'data.gov.ro',
        'path': '/opt/ACTIVE/EU_FUNDING/CODE/SCRAPERS/data_gov_eu_funds.py',
        'cron': 'Monthly 1st 6 AM',
        'data': '/opt/ACTIVE/EU_FUNDING/DATA/DATA_GOV_RO/*.csv'
    },
    'programmes': {
        'name': 'RO Programmes (POR/POCU/POIM)',
        'path': '/opt/ACTIVE/EU_FUNDING/CODE/SCRAPERS/RO_PROGRAMMES/scrape_all_programmes.py',
        'cron': 'Weekly Monday 7 AM',
        'data': '/opt/ACTIVE/EU_FUNDING/DATA/RO_PROGRAMMES/*.csv'
    },
    'pnrr': {
        'name': 'PNRR Payments',
        'path': '/opt/ACTIVE/EU_FUNDING/CODE/SCRAPERS/PNRR/import_payments.py',
        'cron': 'Weekly',
        'data': '/opt/ACTIVE/EU_FUNDING/DATA/PNRR/pnrr_payments_all.csv'
    },
    'afir': {
        'name': 'AFIR Agriculture',
        'path': '/opt/ACTIVE/SCRAPERS/ROMANIA/SCRAPERS/AFIR/CODE/afir_opendata_scraper.py',
        'cron': 'Daily 14:30',
        'data': '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/AFIR/'
    }
}

def get_file_stats(pattern):
    """Get row counts from CSV files matching pattern"""
    import glob
    total = 0
    files = []
    for f in glob.glob(pattern):
        try:
            with open(f) as fp:
                count = sum(1 for _ in fp) - 1  # minus header
                total += count
                files.append((os.path.basename(f), count))
        except:
            pass
    return total, files

def get_db_counts():
    """Get counts from european_funds database"""
    try:
        result = subprocess.run(
            ['psql', '-d', 'european_funds', '-t', '-A', '-c',
             "SELECT 'beneficiari_privati', COUNT(*) FROM beneficiari_privati UNION ALL SELECT 'proiecte', COUNT(*) FROM proiecte"],
            capture_output=True, text=True, timeout=10
        )
        counts = {}
        for line in result.stdout.strip().split('\n'):
            if '|' in line:
                tbl, cnt = line.split('|')
                counts[tbl] = int(cnt)
        return counts
    except:
        return {}

def show_status():
    """Show status of all scrapers"""
    print("=" * 60)
    print("ROMANIA EU FUNDING SCRAPERS")
    print("=" * 60)

    for key, info in SCRAPERS.items():
        path = Path(info['path'])
        exists = path.exists()
        mtime = datetime.fromtimestamp(path.stat().st_mtime).strftime('%Y-%m-%d %H:%M') if exists else 'N/A'

        print(f"\n[{key.upper()}] {info['name']}")
        print(f"  Path: {info['path']}")
        print(f"  Exists: {'Yes' if exists else 'NO'}")
        print(f"  Modified: {mtime}")
        print(f"  Cron: {info['cron']}")
        print(f"  Data: {info['data']}")

def show_data():
    """Show data counts"""
    print("=" * 60)
    print("EU FUNDING DATA COUNTS")
    print("=" * 60)

    # Database
    db_counts = get_db_counts()
    print(f"\n[DATABASE: european_funds]")
    for tbl, cnt in db_counts.items():
        print(f"  {tbl}: {cnt:,}")

    # CSV files
    csv_sources = [
        ('/opt/ACTIVE/EU_FUNDING/DATA/DATA_GOV_RO/*.csv', 'data.gov.ro'),
        ('/opt/ACTIVE/EU_FUNDING/DATA/RO_PROGRAMMES/*.csv', 'RO Programmes'),
        ('/opt/ACTIVE/EU_FUNDING/DATA/PNRR/*.csv', 'PNRR'),
    ]

    total_all = sum(db_counts.values())

    for pattern, name in csv_sources:
        total, files = get_file_stats(pattern)
        print(f"\n[{name}] Total: {total:,}")
        for fname, cnt in sorted(files):
            print(f"  {fname}: {cnt:,}")
        total_all += total

    print(f"\n{'=' * 60}")
    print(f"GRAND TOTAL: {total_all:,} records")
    print("=" * 60)

def run_scraper(name):
    """Run a specific scraper"""
    if name == 'all':
        for key in SCRAPERS:
            run_scraper(key)
        return

    if name not in SCRAPERS:
        print(f"Unknown scraper: {name}")
        print(f"Available: {', '.join(SCRAPERS.keys())}")
        return

    info = SCRAPERS[name]
    path = info['path']

    if not os.path.exists(path):
        print(f"[{name}] Script not found: {path}")
        return

    print(f"\n[{name}] Running {info['name']}...")
    print("-" * 40)

    try:
        result = subprocess.run(
            ['python3', path],
            cwd=os.path.dirname(path),
            timeout=600
        )
        print(f"[{name}] Exit code: {result.returncode}")
    except subprocess.TimeoutExpired:
        print(f"[{name}] Timeout after 10 minutes")
    except Exception as e:
        print(f"[{name}] Error: {e}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='EU Funding Scrapers Manager')
    parser.add_argument('--status', action='store_true', help='Show scraper status')
    parser.add_argument('--data', action='store_true', help='Show data counts')
    parser.add_argument('--run', type=str, help='Run scraper (name or "all")')
    parser.add_argument('--list', action='store_true', help='List available scrapers')

    args = parser.parse_args()

    if args.list:
        for key, info in SCRAPERS.items():
            print(f"{key}: {info['name']}")
    elif args.status:
        show_status()
    elif args.data:
        show_data()
    elif args.run:
        run_scraper(args.run)
    else:
        show_status()
        print()
        show_data()

if __name__ == '__main__':
    main()

# Additional scrapers added
SCRAPERS['datagov_all'] = {
    'name': 'data.gov.ro ALL datasets',
    'path': '/opt/ACTIVE/EU_FUNDING/CODE/SCRAPERS/data_gov_all_eu.py',
    'cron': 'Monthly 1st 6 AM',
    'data': '/opt/ACTIVE/EU_FUNDING/DATA/DATA_GOV_ALL/'
}
SCRAPERS['ministries'] = {
    'name': 'Ministry websites',
    'path': '/opt/ACTIVE/EU_FUNDING/CODE/SCRAPERS/ministry_scrapers.py',
    'cron': 'Weekly Monday 8 AM',
    'data': '/opt/ACTIVE/EU_FUNDING/DATA/MINISTRIES/'
}
