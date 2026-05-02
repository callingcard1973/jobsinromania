#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
Nordic Data Integrator - Merge EURES and country scraper data.

Combines data from:
- EURES (pan-European job portal)
- Country-specific scrapers (Jobnet, Finn.no, etc.)

Usage:
    python3 nordic_integrator.py --status           # Show data sources
    python3 nordic_integrator.py --merge DK         # Merge Denmark data
    python3 nordic_integrator.py --merge all        # Merge all countries
    python3 nordic_integrator.py --export           # Export unified file
    python3 nordic_integrator.py --dedupe           # Deduplicate by email

See /opt/CLAUDE.md for shared code rules.
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import csv
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Optional
import argparse
import json

from skills_common import to_ascii, sanitize
from nordic_utils import NORDIC_SCHEMA_50, normalize_nordic_text

# Paths
OUTPUT_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/NORDIC_UNIFIED')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Data sources configuration
DATA_SOURCES = {
    'DK': {
        'name': 'Denmark',
        'eures': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/EURES/OUTPUT/Denmark/Denmark_contacts_50.csv',
        'country': [
            '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/DENMARK/OUTPUT/Denmark_ULTIMATE_MASTER.csv',
            '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/DENMARK/OUTPUT/Denmark_JOBINDEX_MASTER.csv',
        ],
    },
    'SE': {
        'name': 'Sweden',
        'eures': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/EURES/OUTPUT/Sweden/Sweden_contacts_50.csv',
        'country': [
            '/mnt/hdd/SCRAPER_DATA/csv/SWEDEN/Sweden_MASTER_50.csv',
        ],
    },
    'NO': {
        'name': 'Norway',
        'eures': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/EURES/OUTPUT/Norway/Norway_contacts_50.csv',
        'country': [
            '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/NORWAY/OUTPUT/Norway_MASTER_50.csv',
            '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/NORWAY/OUTPUT/Norway_FINN_MASTER.csv',
        ],
    },
    'FI': {
        'name': 'Finland',
        'eures': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/EURES/OUTPUT/Finland/Finland_contacts_50.csv',
        'country': [
            '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/FINLAND/output/',  # Directory
            '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/FINLAND/output/Finland_DUUNITORI_MASTER.csv',
        ],
    },
    'IS': {
        'name': 'Iceland',
        'eures': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/EURES/OUTPUT/Iceland/Iceland_contacts_50.csv',
        'country': [
            '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ICELAND/ISLAND/OUTPUT/',
            '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ICELAND/ALFRED/OUTPUT/',
        ],
    },
}


def get_file_stats(path: str) -> Dict:
    """Get file stats (rows, mtime)."""
    p = Path(path)
    if not p.exists():
        return {'exists': False, 'rows': 0}

    if p.is_dir():
        csvs = list(p.glob('*.csv'))
        if not csvs:
            return {'exists': False, 'rows': 0}
        # Sum all CSVs in directory
        total_rows = 0
        for csv_file in csvs:
            try:
                with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
                    total_rows += sum(1 for _ in f) - 1
            except Exception:
                pass
        return {'exists': True, 'rows': total_rows, 'files': len(csvs)}

    try:
        with open(p, 'r', encoding='utf-8', errors='ignore') as f:
            rows = sum(1 for _ in f) - 1
        mtime = datetime.fromtimestamp(p.stat().st_mtime)
        return {'exists': True, 'rows': max(0, rows), 'mtime': mtime.strftime('%Y-%m-%d')}
    except Exception:
        return {'exists': False, 'rows': 0}


def read_csv_rows(path: str) -> List[Dict]:
    """Read CSV file(s) and return list of dicts."""
    rows = []
    p = Path(path)

    if not p.exists():
        return rows

    files = list(p.glob('*.csv')) if p.is_dir() else [p]

    for csv_file in files:
        try:
            with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row['_source_file'] = str(csv_file)
                    rows.append(row)
        except Exception as e:
            print(f"Warning: Could not read {csv_file}: {e}")

    return rows


def generate_dedup_key(row: Dict) -> str:
    """Generate deduplication key from row data."""
    # Primary: email
    email = (row.get('contact_email') or row.get('email') or row.get('email1') or '').strip().lower()
    if email and '@' in email:
        return f"email:{email}"

    # Secondary: company + job title + city
    company = normalize_nordic_text(row.get('company_name') or row.get('company') or '')
    title = normalize_nordic_text(row.get('job_title') or row.get('title') or '')
    city = normalize_nordic_text(row.get('location_city') or row.get('city') or '')

    if company and title:
        combo = f"{company}|{title}|{city}".lower()
        return f"combo:{hashlib.md5(combo.encode()).hexdigest()[:12]}"

    # Tertiary: job URL
    url = row.get('job_url') or row.get('source_url') or ''
    if url:
        return f"url:{hashlib.md5(url.encode()).hexdigest()[:12]}"

    return f"unknown:{hashlib.md5(str(row).encode()).hexdigest()[:12]}"


def normalize_row(row: Dict, source_type: str) -> Dict:
    """Normalize row to standard schema."""
    normalized = {col: '' for col in NORDIC_SCHEMA_50}

    # Map common field variations
    field_mappings = {
        'company_name': ['company_name', 'company', 'employer', 'organisation'],
        'contact_email': ['contact_email', 'email', 'email1', 'e_mail'],
        'contact_phone': ['contact_phone', 'phone', 'phone1', 'telephone'],
        'job_title': ['job_title', 'title', 'position', 'job_name'],
        'job_description': ['job_description', 'description', 'details'],
        'job_url': ['job_url', 'url', 'link', 'source_url'],
        'location_city': ['location_city', 'city', 'location', 'place'],
        'location_country': ['location_country', 'country'],
        'company_website': ['company_website', 'website', 'homepage'],
        'job_posted_date': ['job_posted_date', 'posted', 'date', 'published'],
        'source_portal': ['source_portal', 'source', 'portal'],
        'scrape_date': ['scrape_date', 'scraped_at'],
    }

    for target, sources in field_mappings.items():
        for source in sources:
            if row.get(source):
                normalized[target] = str(row[source]).strip()
                break

    # Add metadata
    normalized['source_portal'] = normalized.get('source_portal') or source_type
    normalized['scrape_date'] = normalized.get('scrape_date') or datetime.now().strftime('%Y-%m-%d')

    # Normalize text to ASCII
    for field in ['company_name', 'job_title', 'location_city', 'contact_name']:
        if normalized.get(field):
            normalized[field] = normalize_nordic_text(normalized[field])

    return normalized


def merge_country(country_code: str) -> Dict:
    """Merge EURES and country data for one country."""
    if country_code not in DATA_SOURCES:
        return {'error': f'Unknown country: {country_code}'}

    config = DATA_SOURCES[country_code]
    seen_keys: Set[str] = set()
    merged_rows: List[Dict] = []
    stats = {'eures': 0, 'country': 0, 'duplicates': 0, 'total': 0}

    # Load EURES data first (typically more standardized)
    eures_rows = read_csv_rows(config['eures'])
    for row in eures_rows:
        normalized = normalize_row(row, 'eures')
        key = generate_dedup_key(normalized)
        if key not in seen_keys:
            seen_keys.add(key)
            merged_rows.append(normalized)
            stats['eures'] += 1
        else:
            stats['duplicates'] += 1

    # Add country-specific data
    for source_path in config['country']:
        country_rows = read_csv_rows(source_path)
        for row in country_rows:
            source_name = Path(source_path).stem if Path(source_path).is_file() else Path(source_path).name
            normalized = normalize_row(row, source_name)
            key = generate_dedup_key(normalized)
            if key not in seen_keys:
                seen_keys.add(key)
                merged_rows.append(normalized)
                stats['country'] += 1
            else:
                stats['duplicates'] += 1

    stats['total'] = len(merged_rows)

    # Save merged file
    output_file = OUTPUT_DIR / f"{config['name']}_UNIFIED.csv"
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=NORDIC_SCHEMA_50, extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        for row in merged_rows:
            writer.writerow(row)

    print(f"{config['name']}: EURES={stats['eures']}, Country={stats['country']}, Dupes={stats['duplicates']}, Total={stats['total']}")
    print(f"  Saved to: {output_file}")

    return stats


def show_status():
    """Show status of all data sources."""
    print("=" * 70)
    print("NORDIC DATA SOURCES STATUS")
    print("=" * 70)
    print()

    for code, config in DATA_SOURCES.items():
        print(f"{config['name'].upper()} ({code})")
        print("-" * 40)

        # EURES
        eures_stats = get_file_stats(config['eures'])
        eures_str = f"{eures_stats['rows']:,}" if eures_stats['exists'] else "MISSING"
        print(f"  EURES:   {eures_str:>10} rows")

        # Country sources
        total_country = 0
        for source in config['country']:
            stats = get_file_stats(source)
            if stats['exists']:
                total_country += stats['rows']
        print(f"  Country: {total_country:>10} rows")

        # Unified (if exists)
        unified = OUTPUT_DIR / f"{config['name']}_UNIFIED.csv"
        unified_stats = get_file_stats(str(unified))
        if unified_stats['exists']:
            print(f"  Unified: {unified_stats['rows']:>10} rows ({unified_stats.get('mtime', '')})")
        else:
            print(f"  Unified: NOT YET MERGED")

        print()


def export_all():
    """Export all countries to single file."""
    all_rows = []

    for code, config in DATA_SOURCES.items():
        unified = OUTPUT_DIR / f"{config['name']}_UNIFIED.csv"
        if unified.exists():
            rows = read_csv_rows(str(unified))
            all_rows.extend(rows)

    if not all_rows:
        print("No unified files found. Run --merge all first.")
        return

    output_file = OUTPUT_DIR / f"NORDIC_ALL_{datetime.now().strftime('%Y%m%d')}.csv"
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=NORDIC_SCHEMA_50, extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)

    print(f"Exported {len(all_rows):,} total Nordic jobs to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Nordic Data Integrator')
    parser.add_argument('--status', action='store_true', help='Show data source status')
    parser.add_argument('--merge', type=str, metavar='COUNTRY', help='Merge data (DK/SE/NO/FI/IS/all)')
    parser.add_argument('--export', action='store_true', help='Export all to single file')
    parser.add_argument('--dedupe', action='store_true', help='Deduplicate existing unified files')

    args = parser.parse_args()

    if args.merge:
        if args.merge.upper() == 'ALL':
            for code in DATA_SOURCES:
                merge_country(code)
        else:
            merge_country(args.merge.upper())
    elif args.export:
        export_all()
    elif args.dedupe:
        print("Re-running merge to deduplicate...")
        for code in DATA_SOURCES:
            merge_country(code)
    else:
        show_status()


if __name__ == '__main__':
    main()
