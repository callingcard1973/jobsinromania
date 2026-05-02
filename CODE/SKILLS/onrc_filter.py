#!/usr/bin/env python3
"""
ONRC Filter - Filter Romanian companies by year, county, and status

Usage:
  python3 onrc_filter.py --year 2016 --county Bucuresti Ilfov --active
  python3 onrc_filter.py --year 2015 --county Cluj --active
  python3 onrc_filter.py --year 2016 --all-counties --active
  python3 onrc_filter.py --download  # Force re-download ONRC data

Data source: data.gov.ro/organization/onrc (FREE, Open Government License)
Format: ^ delimiter, DD/MM/YYYY dates, utf-8-sig encoding

Status codes:
  1048 = functiune (active)
  1084 = radiata (dissolved)
  See n_stare_firma.csv for full list
"""

import sys
import csv
import os
import argparse
from datetime import date
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii

# Paths
CACHE_DIR = '/opt/ACTIVE/OPENDATA/DATA/ONRC_CACHE'
FIRME_URL = 'https://data.gov.ro/dataset/f7374920-a656-4e34-85dd-a61c6e6e5603/resource/488a8d00-90df-4f37-b5f4-6c9111e6f1e7/download/od_firme.csv'
STATUS_URL = 'https://data.gov.ro/dataset/f7374920-a656-4e34-85dd-a61c6e6e5603/resource/9ab6d186-6cf9-4330-b2ee-430469501f9d/download/od_stare_firma.csv'

FIRME_FILE = f'{CACHE_DIR}/od_firme.csv'
STATUS_FILE = f'{CACHE_DIR}/od_stare_firma.csv'

# Status codes
ACTIVE_STATUS = '1048'

# Romanian county name variants (with/without diacritics)
COUNTY_VARIANTS = {
    'bucuresti': ['Bucuresti', 'BUCURESTI', 'bucuresti', 'Bucureşti', 'BUCUREŞTI'],
    'ilfov': ['Ilfov', 'ILFOV', 'ilfov'],
    'cluj': ['Cluj', 'CLUJ', 'cluj'],
    'timis': ['Timis', 'TIMIS', 'timis', 'Timiş', 'TIMIŞ'],
    'iasi': ['Iasi', 'IASI', 'iasi', 'Iaşi', 'IAŞI'],
    'constanta': ['Constanta', 'CONSTANTA', 'constanta', 'Constanţa', 'CONSTANŢA'],
    'brasov': ['Brasov', 'BRASOV', 'brasov', 'Braşov', 'BRAŞOV'],
    'dolj': ['Dolj', 'DOLJ', 'dolj'],
    'prahova': ['Prahova', 'PRAHOVA', 'prahova'],
    'bihor': ['Bihor', 'BIHOR', 'bihor'],
}

OUTPUT_COLUMNS = [
    'cui', 'company_name', 'registration_code', 'founding_date',
    'anniversary_date', 'legal_form', 'county', 'city', 'street',
    'street_number', 'postal_code', 'sector', 'status', 'source', 'scraped_date'
]


def download_files(force=False):
    """Download ONRC files if needed"""
    import subprocess

    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

    for url, path, name in [
        (FIRME_URL, FIRME_FILE, 'companies'),
        (STATUS_URL, STATUS_FILE, 'status')
    ]:
        if os.path.exists(path) and not force:
            size_mb = os.path.getsize(path) / (1024 * 1024)
            print(f'Using cached {name}: {size_mb:.1f} MB')
        else:
            print(f'Downloading {name}...')
            result = subprocess.run(['wget', '-c', '-O', path, url], capture_output=True)
            if result.returncode != 0:
                print(f'Download failed: {name}')
                return False
            size_mb = os.path.getsize(path) / (1024 * 1024)
            print(f'Downloaded {name}: {size_mb:.1f} MB')

    return True


def get_county_set(counties):
    """Build set of county name variants"""
    result = set()
    for county in counties:
        county_lower = county.lower().replace('ş', 's').replace('ţ', 't')
        if county_lower in COUNTY_VARIANTS:
            result.update(COUNTY_VARIANTS[county_lower])
        else:
            result.add(county)
    return result


def load_active_companies():
    """Load set of registration codes with active status"""
    print('Loading active company status...')
    active = set()

    with open(STATUS_FILE, 'r', encoding='utf-8-sig', errors='replace') as f:
        reader = csv.DictReader(f, delimiter='^')
        for row in reader:
            if row.get('COD') == ACTIVE_STATUS:
                active.add(row.get('COD_INMATRICULARE', ''))

    print(f'  Found {len(active):,} active companies')
    return active


def filter_companies(year, counties=None, active_only=False, output_dir=None):
    """Filter companies by criteria"""
    if output_dir is None:
        output_dir = CACHE_DIR

    # Build county set
    county_set = None
    if counties:
        county_set = get_county_set(counties)
        print(f'Filtering counties: {counties}')

    # Load active status if needed
    active_set = None
    if active_only:
        active_set = load_active_companies()

    print(f'Filtering for year {year}...')

    filtered = []
    total = 0
    stats = {'year': 0, 'county': 0, 'active': 0}

    with open(FIRME_FILE, 'r', encoding='utf-8-sig', errors='replace') as f:
        reader = csv.DictReader(f, delimiter='^')

        for row in reader:
            total += 1
            if total % 500000 == 0:
                print(f'  {total:,} rows, {len(filtered):,} matches')

            # Check year
            date_str = row.get('DATA_INMATRICULARE', '')
            if not date_str or '/' not in date_str:
                continue

            parts = date_str.split('/')
            if len(parts) != 3:
                continue

            try:
                row_year = int(parts[2])
            except ValueError:
                continue

            if row_year != year:
                continue
            stats['year'] += 1

            # Check county
            county = row.get('ADR_JUDET', '')
            if county_set and county not in county_set:
                continue
            stats['county'] += 1

            # Check active status
            reg_code = row.get('COD_INMATRICULARE', '')
            if active_set and reg_code not in active_set:
                continue
            stats['active'] += 1

            # Add to results
            anniversary = f'{parts[0]}/{parts[1]}/{row_year + 10}'

            filtered.append({
                'cui': row.get('CUI', ''),
                'company_name': to_ascii(row.get('DENUMIRE', '')),
                'registration_code': reg_code,
                'founding_date': date_str,
                'anniversary_date': anniversary,
                'legal_form': to_ascii(row.get('FORMA_JURIDICA', '')),
                'county': to_ascii(county),
                'city': to_ascii(row.get('ADR_LOCALITATE', '')),
                'street': to_ascii(row.get('ADR_DEN_STRADA', '')),
                'street_number': row.get('ADR_DEN_NR_STRADA', ''),
                'postal_code': row.get('ADR_COD_POSTAL', ''),
                'sector': row.get('ADR_SECTOR', ''),
                'status': 'ACTIVE' if active_only else '',
                'source': 'data.gov.ro/ONRC',
                'scraped_date': date.today().isoformat()
            })

    print(f'\nStats:')
    print(f'  Total rows: {total:,}')
    print(f'  Year {year}: {stats["year"]:,}')
    if county_set:
        print(f'  In counties: {stats["county"]:,}')
    if active_only:
        print(f'  Active: {stats["active"]:,}')
    print(f'  Final: {len(filtered):,}')

    # Save results
    county_suffix = '_'.join(sorted(counties)) if counties else 'all'
    status_suffix = '_active' if active_only else ''
    output_file = f'{output_dir}/firme_{year}_{county_suffix}{status_suffix}.csv'

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(filtered)

    print(f'\nSaved: {output_file}')

    return filtered, output_file


def main():
    parser = argparse.ArgumentParser(description='ONRC Filter - Romanian companies')
    parser.add_argument('--year', type=int, default=2016, help='Founding year')
    parser.add_argument('--county', nargs='+', help='Counties to include')
    parser.add_argument('--active', action='store_true', help='Only active companies')
    parser.add_argument('--download', action='store_true', help='Force re-download')
    parser.add_argument('--output', '-o', help='Output directory')
    args = parser.parse_args()

    if not download_files(force=args.download):
        return 1

    companies, output_file = filter_companies(
        year=args.year,
        counties=args.county,
        active_only=args.active,
        output_dir=args.output
    )

    if not companies:
        print('No matching companies!')
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
