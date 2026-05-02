#!/usr/bin/env python3
"""
Build Unified Romania Companies Database

Consolidates all Romanian company data sources into one master DB.

Usage:
  python3 build_romania_master.py --full          # Full rebuild
  python3 build_romania_master.py --stats         # Show current stats
  python3 build_romania_master.py --export-email  # Export only companies with email

Sources:
  - BILANT (1M with financials)
  - ANAF phones (2.4M)
  - ANOFM, CCIB, MASTER_ALL (emails)
  - Virgil enriched

Output:
  /opt/ACTIVE/OPENDATA/DATA/ROMANIA/MASTER/romania_unified.csv
  /opt/ACTIVE/OPENDATA/DATA/ROMANIA/MASTER/romania_unified.db (SQLite)
"""

import sys
import csv
import sqlite3
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii

# Paths
OUTPUT_DIR = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/MASTER'
BILANT_MASTER = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/BILANT/romania_companies_master.csv'
ANAF_PHONES = '/opt/ACTIVE/OPENDATA/FIRME_ROMANIA/DATA/anaf_all/all_phones.csv'
ANOFM_MASTER = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/ANOFM/anofm_master.csv'
CCIB = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/CCIB/ccib_companies.csv'
MASTER_ALL = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/MASTER_ALL.csv'
VIRGIL = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/BILANT/virgil_schema_enriched.csv'

# Output files
CSV_OUTPUT = f'{OUTPUT_DIR}/romania_unified.csv'
DB_OUTPUT = f'{OUTPUT_DIR}/romania_unified.db'
EMAIL_OUTPUT = f'{OUTPUT_DIR}/romania_with_email.csv'

# Schema
COLUMNS = [
    'cui', 'company_name', 'company_name_normalized', 'registration_code',
    'founding_year', 'status', 'county', 'city', 'address', 'postal_code',
    'revenue', 'employees', 'profit', 'caen', 'caen_description',
    'phone_1', 'phone_2', 'email_1', 'email_2', 'website',
    'email_source', 'phone_source', 'last_updated'
]


def normalize_name(name):
    """Normalize company name for matching"""
    import re
    if not name:
        return ''
    name = to_ascii(name).upper()
    for suffix in [' SRL', ' SA', ' S.R.L.', ' S.A.', ' S.R.L', ' ROMANIA', ' RO']:
        name = name.replace(suffix, '')
    name = re.sub(r'[^\w\s]', '', name)
    return name.strip()


def load_bilant_master():
    """Load base companies from BILANT master"""
    print("Loading BILANT master...")
    companies = {}

    with open(BILANT_MASTER, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cui = row.get('cui', '').strip()
            if not cui:
                continue

            companies[cui] = {
                'cui': cui,
                'company_name': to_ascii(row.get('nume_firma', '')),
                'company_name_normalized': normalize_name(row.get('nume_firma', '')),
                'registration_code': row.get('cod_j', ''),
                'founding_year': row.get('founding_year', ''),
                'status': 'active',
                'county': row.get('judet', ''),
                'city': row.get('localitate', ''),
                'address': to_ascii(row.get('adresa', '')),
                'postal_code': '',
                'revenue': row.get('cifra_afaceri', ''),
                'employees': row.get('nr_angajati', ''),
                'profit': row.get('profit_net', ''),
                'caen': row.get('caen', ''),
                'caen_description': '',
                'phone_1': row.get('telefon', ''),
                'phone_2': '',
                'email_1': '',
                'email_2': '',
                'website': '',
                'email_source': '',
                'phone_source': 'bilant' if row.get('telefon') else '',
                'last_updated': datetime.now().strftime('%Y-%m-%d')
            }

    print(f"  Loaded {len(companies):,} companies")
    return companies


def enrich_anaf_phones(companies):
    """Add phones from ANAF"""
    print("Enriching with ANAF phones...")
    added = 0

    try:
        with open(ANAF_PHONES, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cui = row.get('cui', '').strip()
                phone = row.get('phone', row.get('telefon', '')).strip()

                if cui in companies and phone:
                    if not companies[cui]['phone_1']:
                        companies[cui]['phone_1'] = phone
                        companies[cui]['phone_source'] = 'anaf'
                        added += 1
                    elif not companies[cui]['phone_2'] and phone != companies[cui]['phone_1']:
                        companies[cui]['phone_2'] = phone

        print(f"  Added {added:,} phones from ANAF")
    except Exception as e:
        print(f"  ANAF error: {e}")

    return companies


def load_email_sources():
    """Load all email sources into lookup tables"""
    print("Loading email sources...")

    email_by_cui = {}
    email_by_name = {}

    # 1. Virgil (by CUI)
    try:
        with open(VIRGIL, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cui = row.get('cui', '').strip()
                email = row.get('email', '').strip().lower()
                if cui and email and '@' in email:
                    email_by_cui[cui] = {'email': email, 'source': 'virgil'}
        print(f"  Virgil: {len(email_by_cui):,} by CUI")
    except Exception as e:
        print(f"  Virgil error: {e}")

    # 2. ANOFM
    try:
        with open(ANOFM_MASTER, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = normalize_name(row.get('company_name', ''))
                email = row.get('email_1', '').strip().lower()
                website = row.get('company_website', '').strip()
                if name and email and '@' in email:
                    email_by_name[name] = {'email': email, 'website': website, 'source': 'anofm'}
        print(f"  ANOFM: {len(email_by_name):,} by name")
    except Exception as e:
        print(f"  ANOFM error: {e}")

    # 3. CCIB
    try:
        ccib_count = 0
        with open(CCIB, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = normalize_name(row.get('name', ''))
                email = row.get('email', '').strip().lower()
                website = row.get('website', '').strip()
                if name and email and '@' in email and name not in email_by_name:
                    email_by_name[name] = {'email': email, 'website': website, 'source': 'ccib'}
                    ccib_count += 1
        print(f"  CCIB: +{ccib_count:,}")
    except Exception as e:
        print(f"  CCIB error: {e}")

    # 4. MASTER_ALL
    try:
        master_count = 0
        with open(MASTER_ALL, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = normalize_name(row.get('employer', ''))
                email = row.get('email1', '').strip().lower()
                website = row.get('company_website', '').strip()
                if name and email and '@' in email and name not in email_by_name:
                    email_by_name[name] = {'email': email, 'website': website, 'source': 'master_all'}
                    master_count += 1
        print(f"  MASTER_ALL: +{master_count:,}")
    except Exception as e:
        print(f"  MASTER_ALL error: {e}")

    return email_by_cui, email_by_name


def enrich_emails(companies, email_by_cui, email_by_name):
    """Add emails to companies"""
    print("Enriching with emails...")

    # Try fuzzy matching
    try:
        from rapidfuzz import fuzz, process
        fuzzy_available = True
        lookup_names = list(email_by_name.keys())
        print(f"  Fuzzy matching enabled ({len(lookup_names):,} names)")
    except ImportError:
        fuzzy_available = False
        print("  Fuzzy matching disabled (rapidfuzz not installed)")

    enriched = 0
    for cui, company in companies.items():
        if company['email_1']:  # Already has email
            continue

        norm_name = company['company_name_normalized']

        # 1. CUI match
        if cui in email_by_cui:
            company['email_1'] = email_by_cui[cui]['email']
            company['email_source'] = email_by_cui[cui]['source']
            enriched += 1
            continue

        # 2. Exact name match
        if norm_name in email_by_name:
            company['email_1'] = email_by_name[norm_name]['email']
            company['website'] = email_by_name[norm_name].get('website', '')
            company['email_source'] = email_by_name[norm_name]['source']
            enriched += 1
            continue

        # 3. Fuzzy match
        if fuzzy_available and norm_name:
            result = process.extractOne(norm_name, lookup_names, scorer=fuzz.ratio)
            if result and result[1] >= 88:
                matched_name = result[0]
                company['email_1'] = email_by_name[matched_name]['email']
                company['website'] = email_by_name[matched_name].get('website', '')
                company['email_source'] = f"fuzzy_{result[1]:.0f}"
                enriched += 1

    print(f"  Enriched {enriched:,} companies with emails")
    return companies


def export_csv(companies, output_path):
    """Export to CSV"""
    print(f"Exporting to {output_path}...")

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for company in companies.values():
            writer.writerow({k: company.get(k, '') for k in COLUMNS})

    print(f"  Wrote {len(companies):,} records")


def export_sqlite(companies, db_path):
    """Export to SQLite"""
    print(f"Exporting to {db_path}...")

    # Remove old DB
    Path(db_path).unlink(missing_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create table
    cursor.execute('''
        CREATE TABLE companies (
            cui TEXT PRIMARY KEY,
            company_name TEXT,
            company_name_normalized TEXT,
            registration_code TEXT,
            founding_year INTEGER,
            status TEXT,
            county TEXT,
            city TEXT,
            address TEXT,
            postal_code TEXT,
            revenue INTEGER,
            employees INTEGER,
            profit INTEGER,
            caen TEXT,
            caen_description TEXT,
            phone_1 TEXT,
            phone_2 TEXT,
            email_1 TEXT,
            email_2 TEXT,
            website TEXT,
            email_source TEXT,
            phone_source TEXT,
            last_updated TEXT
        )
    ''')

    # Insert data
    for company in companies.values():
        values = [company.get(col, '') for col in COLUMNS]
        placeholders = ','.join(['?' for _ in COLUMNS])
        cursor.execute(f'INSERT INTO companies VALUES ({placeholders})', values)

    # Create indexes
    cursor.execute('CREATE INDEX idx_county ON companies(county)')
    cursor.execute('CREATE INDEX idx_caen ON companies(caen)')
    cursor.execute('CREATE INDEX idx_employees ON companies(employees)')
    cursor.execute('CREATE INDEX idx_email ON companies(email_1)')
    cursor.execute('CREATE INDEX idx_name_norm ON companies(company_name_normalized)')

    conn.commit()
    conn.close()

    print(f"  Created SQLite DB with indexes")


def export_with_email(companies, output_path):
    """Export only companies with email"""
    print(f"Exporting companies with email to {output_path}...")

    with_email = [c for c in companies.values() if c.get('email_1')]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for company in with_email:
            writer.writerow({k: company.get(k, '') for k in COLUMNS})

    print(f"  Wrote {len(with_email):,} records with email")


def show_stats(companies):
    """Show statistics"""
    total = len(companies)
    with_phone = len([c for c in companies.values() if c.get('phone_1')])
    with_email = len([c for c in companies.values() if c.get('email_1')])
    with_website = len([c for c in companies.values() if c.get('website')])

    print(f"\n{'='*60}")
    print("UNIFIED DATABASE STATISTICS")
    print(f"{'='*60}")
    print(f"Total companies:     {total:>12,}")
    print(f"With phone:          {with_phone:>12,} ({100*with_phone//total}%)")
    print(f"With email:          {with_email:>12,} ({100*with_email//total}%)")
    print(f"With website:        {with_website:>12,} ({100*with_website//total}%)")

    # By county
    from collections import Counter
    counties = Counter(c.get('county', 'Unknown') for c in companies.values())
    print(f"\n--- TOP COUNTIES ---")
    for county, count in counties.most_common(10):
        print(f"  {county[:20]:20} {count:>10,}")

    # Email sources
    sources = Counter(c.get('email_source', '') for c in companies.values() if c.get('email_1'))
    print(f"\n--- EMAIL SOURCES ---")
    for source, count in sources.most_common():
        print(f"  {source[:20]:20} {count:>10,}")


def main():
    parser = argparse.ArgumentParser(description='Build unified Romania companies DB')
    parser.add_argument('--full', action='store_true', help='Full rebuild')
    parser.add_argument('--stats', action='store_true', help='Show stats only')
    parser.add_argument('--export-email', action='store_true', help='Export only with email')

    args = parser.parse_args()

    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    if args.stats:
        # Load existing and show stats
        print("Loading existing unified DB...")
        companies = {}
        try:
            with open(CSV_OUTPUT, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    companies[row['cui']] = row
            show_stats(companies)
        except FileNotFoundError:
            print("No unified DB found. Run with --full first.")
        return

    if args.full:
        print("="*60)
        print("BUILDING UNIFIED ROMANIA COMPANIES DATABASE")
        print("="*60)
        print()

        # Load base
        companies = load_bilant_master()

        # Enrich phones
        companies = enrich_anaf_phones(companies)

        # Load email sources
        email_by_cui, email_by_name = load_email_sources()

        # Enrich emails
        companies = enrich_emails(companies, email_by_cui, email_by_name)

        # Export
        export_csv(companies, CSV_OUTPUT)
        export_sqlite(companies, DB_OUTPUT)
        export_with_email(companies, EMAIL_OUTPUT)

        # Show stats
        show_stats(companies)

        print(f"\n{'='*60}")
        print("OUTPUT FILES:")
        print(f"  {CSV_OUTPUT}")
        print(f"  {DB_OUTPUT}")
        print(f"  {EMAIL_OUTPUT}")
        print(f"{'='*60}")

    elif args.export_email:
        print("Loading and exporting companies with email...")
        companies = {}
        with open(CSV_OUTPUT, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                companies[row['cui']] = row
        export_with_email(companies, EMAIL_OUTPUT)


if __name__ == '__main__':
    main()
