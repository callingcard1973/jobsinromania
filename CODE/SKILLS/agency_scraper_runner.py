#!/usr/bin/env python3
"""
Agency Scraper Runner - Run all agency scrapers and merge results

Usage:
    python3 agency_scraper_runner.py                    # Run all scrapers
    python3 agency_scraper_runner.py --test             # Test mode (quick run)
    python3 agency_scraper_runner.py --scraper germany  # Single scraper
    python3 agency_scraper_runner.py --merge-only       # Just merge existing files
    python3 agency_scraper_runner.py --status           # Show scraper status
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import csv
import glob
import argparse
import subprocess
from datetime import datetime
from collections import Counter
from skills_common import to_ascii

SCRAPERS = {
    'netherlands': {
        'name': 'Netherlands ABU',
        'script': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/NETHERLANDS/abu_scraper.py',
        'output_pattern': 'agencies_netherlands_abu_*.csv',
    },
    'uk': {
        'name': 'UK REC',
        'script': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/UK/rec_scraper.py',
        'output_pattern': 'agencies_uk_rec_*.csv',
    },
    'europages': {
        'name': 'Europages (Multi-EU)',
        'script': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/MULTI/europages_scraper.py',
        'output_pattern': 'agencies_europages_*.csv',
    },
    'italy': {
        'name': 'Italy ANPAL',
        'script': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ITALY/anpal_scraper.py',
        'output_pattern': 'agencies_italy_anpal_*.csv',
    },
    'germany': {
        'name': 'Germany Bundesagentur',
        'script': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/GERMANY/bundesagentur_scraper.py',
        'output_pattern': 'agencies_germany_ba_*.csv',
    },
}

OUTPUT_DIR = '/opt/ACTIVE/OPENDATA/DATA/AGENCIES/SCRAPED'
MASTER_FILE = '/opt/ACTIVE/OPENDATA/DATA/AGENCIES/AGENCIES_MASTER_ALL.csv'


def run_scraper(name, test_mode=False):
    """Run a single scraper."""
    info = SCRAPERS.get(name)
    if not info:
        print(f"Unknown scraper: {name}")
        return False

    script = info['script']
    if not os.path.exists(script):
        print(f"Script not found: {script}")
        return False

    print(f"\n{'='*50}")
    print(f"Running: {info['name']}")
    print(f"{'='*50}")

    cmd = ['/opt/ACTIVE/INFRA/venv/bin/python3', script]
    if test_mode:
        cmd.append('--test')

    try:
        result = subprocess.run(cmd, capture_output=False, timeout=3600)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"Timeout running {name}")
        return False
    except Exception as e:
        print(f"Error running {name}: {e}")
        return False


def merge_results():
    """Merge all scraped files into master."""
    print(f"\n{'='*50}")
    print("Merging Results")
    print(f"{'='*50}")

    all_agencies = []
    files_processed = []

    # Read existing master file
    if os.path.exists(MASTER_FILE):
        with open(MASTER_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                all_agencies.append(row)
        print(f"Loaded {len(all_agencies)} existing agencies from master")

    # Read new scraped files
    for scraper_name, info in SCRAPERS.items():
        pattern = os.path.join(OUTPUT_DIR, info['output_pattern'])
        files = sorted(glob.glob(pattern), reverse=True)

        if files:
            latest_file = files[0]
            print(f"  Reading: {os.path.basename(latest_file)}")

            with open(latest_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    # Standardize fields
                    agency = {
                        'company_name': to_ascii(row.get('company_name', '')),
                        'email': row.get('email', ''),
                        'phone': row.get('phone', ''),
                        'country': row.get('country', ''),
                        'address': to_ascii(row.get('address', '')),
                        'city': to_ascii(row.get('city', '')),
                        'website': row.get('website', ''),
                        'source_file': row.get('source_file', os.path.basename(latest_file)),
                    }
                    all_agencies.append(agency)
                    count += 1

                files_processed.append((os.path.basename(latest_file), count))

    # Deduplicate by company_name + country
    seen = set()
    unique = []
    for agency in all_agencies:
        key = (agency.get('company_name', '').lower().strip(), agency.get('country', '').lower())
        if key[0] and key not in seen:
            seen.add(key)
            unique.append(agency)

    print(f"\nTotal before dedup: {len(all_agencies)}")
    print(f"Total after dedup: {len(unique)}")

    # Count by country
    countries = Counter(a.get('country', 'Unknown') for a in unique)
    print("\nBy country:")
    for country, count in countries.most_common(15):
        print(f"  {country}: {count:,}")

    # Write master file
    fieldnames = ['company_name', 'email', 'phone', 'country', 'address', 'city', 'website', 'source_file']

    with open(MASTER_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(unique)

    print(f"\nSaved to: {MASTER_FILE}")

    return unique


def show_status():
    """Show status of scrapers and data."""
    print(f"\n{'='*50}")
    print("Agency Scraper Status")
    print(f"{'='*50}")

    print("\nScrapers:")
    for name, info in SCRAPERS.items():
        exists = os.path.exists(info['script'])
        status = "OK" if exists else "MISSING"
        print(f"  [{status}] {info['name']}: {info['script']}")

    print("\nLatest scraped files:")
    for name, info in SCRAPERS.items():
        pattern = os.path.join(OUTPUT_DIR, info['output_pattern'])
        files = sorted(glob.glob(pattern), reverse=True)
        if files:
            latest = files[0]
            stat = os.stat(latest)
            size = stat.st_size
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')

            # Count rows
            with open(latest, 'r') as f:
                rows = sum(1 for _ in f) - 1

            print(f"  {info['name']}: {rows:,} agencies ({mtime})")
        else:
            print(f"  {info['name']}: No files found")

    # Master file
    if os.path.exists(MASTER_FILE):
        with open(MASTER_FILE, 'r') as f:
            rows = sum(1 for _ in f) - 1
        stat = os.stat(MASTER_FILE)
        mtime = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
        print(f"\nMaster file: {rows:,} agencies ({mtime})")


def main():
    parser = argparse.ArgumentParser(description='Run agency scrapers')
    parser.add_argument('--test', action='store_true', help='Test mode')
    parser.add_argument('--scraper', help='Run single scraper (germany, uk, netherlands, italy, europages)')
    parser.add_argument('--merge-only', action='store_true', help='Just merge existing files')
    parser.add_argument('--status', action='store_true', help='Show status')
    parser.add_argument('--all', action='store_true', help='Run all scrapers')

    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.merge_only:
        merge_results()
        return

    if args.scraper:
        success = run_scraper(args.scraper, test_mode=args.test)
        if success:
            merge_results()
        return

    if args.all or not args.scraper:
        # Run all scrapers
        results = {}
        for name in SCRAPERS:
            results[name] = run_scraper(name, test_mode=args.test)

        print(f"\n{'='*50}")
        print("Summary")
        print(f"{'='*50}")
        for name, success in results.items():
            status = "SUCCESS" if success else "FAILED"
            print(f"  {SCRAPERS[name]['name']}: {status}")

        # Merge all results
        merge_results()


if __name__ == '__main__':
    main()
