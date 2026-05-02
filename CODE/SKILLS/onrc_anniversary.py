#!/usr/bin/env python3
"""
ONRC Anniversary Filter - Find companies by founding year
Usage: python3 onrc_anniversary.py [YEAR] [--download]

Source: data.gov.ro/organization/onrc (FREE, Open Government License)
Format: ^ delimiter, DD/MM/YYYY dates

Examples:
  python3 onrc_anniversary.py 2016           # Companies founded 2016 (10yr anniversary in 2026)
  python3 onrc_anniversary.py 2015           # Companies founded 2015 (11yr anniversary in 2026)
  python3 onrc_anniversary.py 2016 --download  # Force re-download
"""

import sys
import csv
import os
import argparse
from datetime import date
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

from skills_common import to_ascii, sanitize, FIELD_LIMITS
from alerting import send_telegram

# Configuration
DATA_URL = 'https://data.gov.ro/dataset/64d3f306-91ef-4c75-babf-56378e3bb3ae/resource/f0a12fb5-4b83-441d-8e05-709fa7769663/download/od_firme.csv'
CACHE_DIR = '/opt/ACTIVE/OPENDATA/DATA/ONRC_CACHE'
RAW_FILE = f'{CACHE_DIR}/od_firme_raw.csv'

OUTPUT_COLUMNS = [
    'cui', 'company_name', 'registration_code', 'founding_date',
    'anniversary_date', 'legal_form', 'county', 'city', 'street',
    'street_number', 'postal_code', 'sector', 'euid', 'source', 'scraped_date'
]


def download_csv(force=False):
    """Download ONRC CSV from data.gov.ro"""
    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

    if os.path.exists(RAW_FILE) and not force:
        size_mb = os.path.getsize(RAW_FILE) / (1024 * 1024)
        print(f'Using cached: {RAW_FILE} ({size_mb:.1f} MB)')
        return True

    print(f'Downloading ONRC data...')
    import subprocess
    result = subprocess.run(['wget', '-c', '-O', RAW_FILE, DATA_URL], capture_output=True)

    if result.returncode != 0:
        print(f'Download failed!')
        return False

    size_mb = os.path.getsize(RAW_FILE) / (1024 * 1024)
    print(f'Downloaded: {size_mb:.1f} MB')
    return True


def filter_by_year(target_year: int, output_dir: str = None):
    """Filter companies by founding year"""
    if output_dir is None:
        output_dir = CACHE_DIR

    output_file = f'{output_dir}/firme_{target_year}.csv'
    anniversary_year = date.today().year

    print(f'Filtering for year {target_year}...')

    filtered = []
    total = 0

    with open(RAW_FILE, 'r', encoding='utf-8-sig', errors='replace') as f:
        # utf-8-sig handles BOM, ^ is ONRC delimiter
        reader = csv.DictReader(f, delimiter='^')

        for row in reader:
            total += 1
            if total % 500000 == 0:
                print(f'  {total:,} rows, {len(filtered):,} matches')

            try:
                date_str = row.get('DATA_INMATRICULARE', '')
                if not date_str or '/' not in date_str:
                    continue

                parts = date_str.split('/')
                if len(parts) != 3:
                    continue

                year = int(parts[2])
                if year != target_year:
                    continue

                anniversary = f'{parts[0]}/{parts[1]}/{anniversary_year}'

                filtered.append({
                    'cui': row.get('CUI', ''),
                    'company_name': to_ascii(row.get('DENUMIRE', '')),
                    'registration_code': row.get('COD_INMATRICULARE', ''),
                    'founding_date': date_str,
                    'anniversary_date': anniversary,
                    'legal_form': to_ascii(row.get('FORMA_JURIDICA', '')),
                    'county': to_ascii(row.get('ADR_JUDET', '')),
                    'city': to_ascii(row.get('ADR_LOCALITATE', '')),
                    'street': to_ascii(row.get('ADR_DEN_STRADA', '')),
                    'street_number': row.get('ADR_DEN_NR_STRADA', ''),
                    'postal_code': row.get('ADR_COD_POSTAL', ''),
                    'sector': row.get('ADR_SECTOR', ''),
                    'euid': row.get('EUID', ''),
                    'source': 'data.gov.ro/ONRC',
                    'scraped_date': date.today().isoformat()
                })
            except (ValueError, IndexError):
                continue

    print(f'Total: {total:,}, Matches: {len(filtered):,}')

    if filtered:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
            writer.writeheader()
            writer.writerows(filtered)

        print(f'Saved: {output_file}')

        # Top counties
        counties = {}
        for c in filtered:
            county = c['county'] or 'UNKNOWN'
            counties[county] = counties.get(county, 0) + 1

        print('\nTop 5 counties:')
        for county, count in sorted(counties.items(), key=lambda x: -x[1])[:5]:
            print(f'  {county}: {count:,}')

    return filtered, output_file


def main():
    parser = argparse.ArgumentParser(description='ONRC Anniversary Filter')
    parser.add_argument('year', type=int, nargs='?', default=2016, help='Founding year')
    parser.add_argument('--download', action='store_true', help='Force re-download')
    parser.add_argument('--output', '-o', help='Output directory')
    parser.add_argument('--notify', action='store_true', help='Send Telegram notification')
    args = parser.parse_args()

    if not download_csv(force=args.download):
        return 1

    companies, output_file = filter_by_year(args.year, args.output)

    if companies and args.notify:
        years_old = date.today().year - args.year
        send_telegram(
            f'ONRC: {len(companies):,} companies from {args.year} ({years_old}yr anniversary)\n'
            f'Output: {output_file}'
        )

    return 0 if companies else 1


if __name__ == '__main__':
    sys.exit(main())
