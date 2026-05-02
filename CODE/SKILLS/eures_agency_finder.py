#!/usr/bin/env python3
"""
EURES Agency Finder - Extract staffing agencies from EURES CSV files

Searches all EURES CSV files for companies that match agency keywords.
German law requires Impressum, so we can enrich with emails.

Usage:
    python3 eures_agency_finder.py                    # Search all EURES CSVs
    python3 eures_agency_finder.py --country Germany  # Filter by country
    python3 eures_agency_finder.py --enrich           # Also run impressum enrichment
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import csv
import re
import glob
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from skills_common import to_ascii

# Agency keywords (case-insensitive)
AGENCY_KEYWORDS = [
    # German
    'zeitarbeit', 'personalvermittlung', 'personaldienstleistung',
    'personalservice', 'personalleasing', 'arbeitsvermittlung',
    'leiharbeit', 'personalberatung', 'personalagentur',
    # English
    'staffing', 'recruitment', 'manpower', 'temporary work',
    'employment agency', 'job agency', 'temp agency',
    # Known agencies
    'randstad', 'adecco', 'hays', 'manpower', 'kelly services',
    'robert half', 'experis', 'modis', 'page personnel',
    'michael page', 'korn ferry', 'brunel', 'orizon', 'tempton',
    'unique', 'persona service', 'i-pers', 'aventa', 'actief',
    'start people', 'tempo-team', 'otto workforce', 'hofmann',
    'arwa', 'bindan', 'dab', 'piening', 'timepower', 'timepartner',
    # Dutch/Belgian
    'uitzendbureau', 'interimbureau', 'interim', 'uitzend',
    # French
    'interim', 'travail temporaire',
    # Polish
    'agencja pracy', 'praca tymczasowa',
]

# Compile regex patterns
AGENCY_PATTERNS = [re.compile(r'\b' + re.escape(kw) + r'\b', re.I) for kw in AGENCY_KEYWORDS]

OUTPUT_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/GERMANY_AGENCIES')
OUTPUT_DIR.mkdir(exist_ok=True)


def is_agency(company_name: str) -> bool:
    """Check if company name matches agency keywords."""
    if not company_name:
        return False
    name_lower = company_name.lower()
    for pattern in AGENCY_PATTERNS:
        if pattern.search(name_lower):
            return True
    return False


def find_eures_csvs() -> list:
    """Find all EURES CSV files."""
    patterns = [
        '/opt/ACTIVE/OPENDATA/DATA/DAILY/*/eures_*.csv',
        '/opt/ACTIVE/OPENDATA/DATA/EURES/*.csv',
        '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/EURES/CSV_RESULTS/*.csv',
    ]
    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern))
    return sorted(set(files), reverse=True)  # Newest first


def extract_agencies(csv_file: str, country_filter: str = None) -> list:
    """Extract agencies from a single CSV file."""
    agencies = []
    try:
        with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                company = row.get('company_name', '')
                if not company or not is_agency(company):
                    continue

                country = row.get('country_name', row.get('country', ''))
                if country_filter and country_filter.lower() not in country.lower():
                    continue

                agencies.append({
                    'company_name': to_ascii(company),
                    'city': to_ascii(row.get('company_city', row.get('city', ''))),
                    'country': to_ascii(country),
                    'website': row.get('company_website', ''),
                    'email': row.get('email_1', ''),
                    'phone': row.get('phone_1', ''),
                    'source_file': Path(csv_file).name,
                })
    except Exception as e:
        print(f"Error reading {csv_file}: {e}")
    return agencies


def main():
    parser = argparse.ArgumentParser(description='Find agencies in EURES data')
    parser.add_argument('--country', type=str, help='Filter by country name')
    parser.add_argument('--enrich', action='store_true', help='Run impressum enrichment')
    parser.add_argument('--limit-files', type=int, default=50, help='Max files to scan')
    args = parser.parse_args()

    print(f"EURES Agency Finder - {datetime.now()}")
    print("=" * 50)

    # Find CSV files
    csv_files = find_eures_csvs()
    print(f"Found {len(csv_files)} EURES CSV files")

    if args.limit_files:
        csv_files = csv_files[:args.limit_files]
        print(f"Scanning {len(csv_files)} files")

    # Extract agencies
    all_agencies = []
    seen = set()

    for i, csv_file in enumerate(csv_files):
        if i % 10 == 0:
            print(f"  Processing {i+1}/{len(csv_files)}...")
        agencies = extract_agencies(csv_file, args.country)
        for a in agencies:
            key = a['company_name'].lower().strip()
            if key and key not in seen:
                seen.add(key)
                all_agencies.append(a)

    print(f"\nFound {len(all_agencies)} unique agencies")

    # Stats by country
    by_country = defaultdict(int)
    for a in all_agencies:
        by_country[a['country'] or 'Unknown'] += 1

    print("\nBy country:")
    for country, count in sorted(by_country.items(), key=lambda x: -x[1])[:10]:
        print(f"  {country}: {count}")

    # Stats
    with_email = sum(1 for a in all_agencies if a.get('email'))
    with_website = sum(1 for a in all_agencies if a.get('website'))
    with_phone = sum(1 for a in all_agencies if a.get('phone'))
    print(f"\nWith email: {with_email}")
    print(f"With website: {with_website}")
    print(f"With phone: {with_phone}")

    # Save output
    suffix = f"_{args.country.lower()}" if args.country else ""
    output_file = OUTPUT_DIR / f"eures_agencies{suffix}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['company_name', 'city', 'country', 'website', 'email', 'phone', 'source_file']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_agencies)

    print(f"\nSaved: {output_file}")

    # Enrich if requested
    if args.enrich and all_agencies:
        print("\nRunning impressum enrichment...")
        import subprocess
        subprocess.run([
            '/opt/ACTIVE/INFRA/venv/bin/python3',
            '/opt/ACTIVE/INFRA/SKILLS/germany_impressum_enricher.py',
            '--input', str(output_file),
            '--output', str(OUTPUT_DIR / f"eures_agencies{suffix}_enriched.csv")
        ])


if __name__ == '__main__':
    main()
