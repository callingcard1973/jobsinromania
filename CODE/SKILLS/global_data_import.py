#!/usr/bin/env python3
"""
Global Data Import Skill - Wrapper for Global Data Orchestrator

Downloads and imports company registries and procurement data from global sources.

Usage:
    python3 global_data_import.py                    # Run all sources
    python3 global_data_import.py --source gleif     # Single source
    python3 global_data_import.py --stats            # Show DB counts
    python3 global_data_import.py --list             # List sources
    python3 global_data_import.py --dry-run          # Download only
"""
import os
import sys
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

ORCHESTRATOR = '/opt/ACTIVE/DB/GLOBAL/orchestrator.py'
LOG_DIR = '/opt/ACTIVE/INFRA/LOGS'

SOURCES = {
    'gleif': {'name': 'GLEIF LEI', 'type': 'registry', 'country': 'GLOBAL', 'records': '2.9M'},
    'uk_contracts': {'name': 'UK Contracts Finder', 'type': 'tender', 'country': 'GB', 'records': '46K'},
    'canada': {'name': 'Canada BuyanSell', 'type': 'tender', 'country': 'CA', 'records': '6K'},
    'gsa': {'name': 'GSA Auctions', 'type': 'tender', 'country': 'US', 'records': '900'},
    'hongkong': {'name': 'Hong Kong CR', 'type': 'registry', 'country': 'HK', 'records': '2K'},
    'singapore': {'name': 'Singapore ACRA', 'type': 'registry', 'country': 'SG', 'records': 'API'},
    'australia': {'name': 'Australia ASIC', 'type': 'registry', 'country': 'AU', 'records': '3M', 'status': 'WIP'},
    'usa_spending': {'name': 'USASpending', 'type': 'tender', 'country': 'US', 'records': '50M', 'status': 'WIP'},
}

SOURCE_MAP = {
    'gleif': 'global_lei',
    'uk_contracts': 'uk_contracts_finder',
    'canada': 'canada_buyandsell',
    'gsa': 'gsa_auctions',
    'hongkong': 'hongkong_cr',
    'singapore': 'singapore_acra',
    'australia': 'australia_asic',
    'usa_spending': 'usa_spending',
}


def run_orchestrator(sources=None, dry_run=False, stats=False, list_sources=False):
    """Run the global data orchestrator."""
    cmd = [sys.executable, ORCHESTRATOR]

    if stats:
        cmd.append('--stats')
    elif list_sources:
        cmd.append('--list')
    elif sources:
        cmd.extend(['--source'] + [SOURCE_MAP.get(s, s) for s in sources])
    else:
        cmd.append('--all')

    if dry_run and not stats and not list_sources:
        cmd.append('--dry-run')

    log_file = os.path.join(LOG_DIR, f'global_data_{datetime.now():%Y%m%d_%H%M}.log')

    print(f"Running: {' '.join(cmd)}")
    print(f"Log: {log_file}")
    print("-" * 60)

    with open(log_file, 'w') as f:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            print(line, end='')
            f.write(line)
        process.wait()

    return process.returncode


def show_status():
    """Show current data status."""
    import psycopg2

    print("\n=== GLOBAL DATA STATUS ===\n")

    # Check download files
    download_dir = Path('/opt/DATA_IMPORT/GLOBAL_DOWNLOADS')
    print("Downloads:")
    for subdir in sorted(download_dir.iterdir()):
        if subdir.is_dir():
            files = list(subdir.iterdir())
            total_size = sum(f.stat().st_size for f in files if f.is_file())
            print(f"  {subdir.name}: {len(files)} files, {total_size/1024/1024:.1f} MB")

    # Check database counts
    print("\nDatabase:")
    try:
        conn = psycopg2.connect(dbname='interjob_master', user='tudor')
        cur = conn.cursor()

        # Companies by source
        cur.execute("SELECT source, count(*) FROM companies WHERE source LIKE '%GLEIF%' OR source LIKE '%Hong Kong%' GROUP BY source ORDER BY count DESC")
        for row in cur.fetchall():
            print(f"  companies/{row[0]}: {row[1]:,}")

        # Procurement by source
        cur.execute("SELECT source, count(*) FROM procurement_awards GROUP BY source ORDER BY count DESC")
        for row in cur.fetchall():
            print(f"  procurement/{row[0]}: {row[1]:,}")

        conn.close()
    except Exception as e:
        print(f"  DB error: {e}")

    print()


def main():
    parser = argparse.ArgumentParser(description='Global Data Import')
    parser.add_argument('--source', '-s', nargs='+', choices=list(SOURCE_MAP.keys()),
                       help='Specific sources to run')
    parser.add_argument('--dry-run', '-n', action='store_true',
                       help='Download only, no import')
    parser.add_argument('--stats', action='store_true', help='Show database counts')
    parser.add_argument('--list', '-l', action='store_true', help='List available sources')
    parser.add_argument('--status', action='store_true', help='Show current data status')

    args = parser.parse_args()

    if args.status:
        show_status()
        return 0

    if args.list:
        print("\nAvailable sources:")
        print("-" * 60)
        for key, info in SOURCES.items():
            status = info.get('status', 'READY')
            print(f"  {key:15} {info['name']:25} {info['country']:6} {info['records']:>8}  [{status}]")
        print()
        return 0

    return run_orchestrator(
        sources=args.source,
        dry_run=args.dry_run,
        stats=args.stats,
        list_sources=args.list
    )


if __name__ == '__main__':
    sys.exit(main())
