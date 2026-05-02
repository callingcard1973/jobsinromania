#!/usr/bin/env python3
"""
EU Funds Beneficiaries Enricher

Extracts contact information from EU funding beneficiaries data.

Usage:
  python3 eufunds_enricher.py --stats           # Show available data
  python3 eufunds_enricher.py --extract         # Extract all contacts
  python3 eufunds_enricher.py --enrich input.csv  # Enrich a CSV with EU funds data
  python3 eufunds_enricher.py --export          # Export all EU funds contacts

Data source: /opt/ACTIVE/OPENDATA/DATA/ROMANIA/FONDURIEUROPENE/
Output: /opt/ACTIVE/OPENDATA/DATA/ROMANIA/EUFUNDS/eufunds_contacts.csv
"""

import sys
import csv
import re
import argparse
from pathlib import Path
from collections import Counter
from datetime import datetime

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii

# Paths
EUFUNDS_DIR = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/FONDURIEUROPENE/ro/fonduri-ue'
OUTPUT_DIR = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/EUFUNDS'
DATAGOV_DIR = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/DATAGOV_ALL'

# Source files with contacts
SOURCE_FILES = {
    'hot_leads': f'{EUFUNDS_DIR}/hot_leads_eu_funds.csv',
    'private_companies': f'{EUFUNDS_DIR}/private_companies.csv',
    'private_in_progress': f'{EUFUNDS_DIR}/private_in_progress.csv',
    'beneficiaries': f'{EUFUNDS_DIR}/beneficiaries_summary.csv',
    'construction': f'{EUFUNDS_DIR}/construction_leads.csv',
    'manufacturing': f'{EUFUNDS_DIR}/segments/manufacturing_blue_collar.csv',
}

# Email regex
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')


def normalize_phone(phone):
    """Normalize Romanian phone to +40 format"""
    if not phone:
        return ''
    digits = re.sub(r'[^\d+]', '', str(phone))
    if digits.startswith('0040'):
        digits = '+40' + digits[4:]
    elif digits.startswith('00'):
        digits = '+' + digits[2:]
    elif digits.startswith('0') and len(digits) >= 10:
        digits = '+40' + digits[1:]
    elif not digits.startswith('+'):
        return ''
    return digits if len(digits) >= 10 else ''


def extract_emails(text):
    """Extract all emails from text, handling multiple emails"""
    if not text:
        return []
    # Handle semicolon/comma separated emails
    text = str(text).replace(';', ' ').replace(',', ' ')
    emails = EMAIL_PATTERN.findall(text)
    # Filter and dedupe
    valid = []
    seen = set()
    for email in emails:
        email = email.lower().strip()
        if email not in seen and '@' in email and '.' in email.split('@')[1]:
            if not any(x in email for x in ['example.com', 'test.com', 'noreply']):
                seen.add(email)
                valid.append(email)
    return valid[:3]


def normalize_company_name(name):
    """Normalize company name for matching"""
    if not name:
        return ''
    name = to_ascii(name).upper()
    for suffix in [' SRL', ' SA', ' S.R.L.', ' S.A.', ' PFA', ' II', ' IF']:
        name = name.replace(suffix, '')
    name = re.sub(r'[^A-Z0-9\s]', '', name)
    return ' '.join(name.split())


def load_source_file(filepath):
    """Load a source CSV file"""
    contacts = []

    if not Path(filepath).exists():
        return contacts

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Get company name
                company = row.get('company', row.get('beneficiary', row.get('name', ''))).strip()
                if not company:
                    continue

                # Get emails
                email_raw = row.get('email', row.get('contact_email', ''))
                emails = extract_emails(email_raw)

                # Get phone
                phone_raw = row.get('phone', row.get('telefon', row.get('contact_phone', '')))
                phone = normalize_phone(phone_raw)

                # Get location
                county = row.get('county', row.get('judet', '')).strip()
                city = row.get('city', row.get('localitate', '')).strip()
                address = row.get('address', row.get('adresa', '')).strip()

                # Get project info
                project = row.get('project_title', row.get('proiect', '')).strip()
                budget = row.get('budget_eur', row.get('valoare', '')).strip()
                status = row.get('status', '').strip()

                # Get company identifiers
                cui = row.get('cui', row.get('cif', row.get('cod_fiscal', ''))).strip()
                caen = row.get('caen', '').strip()

                if emails or phone:  # Only keep if has contact info
                    contacts.append({
                        'company_name': to_ascii(company),
                        'company_name_normalized': normalize_company_name(company),
                        'cui': cui,
                        'caen': caen,
                        'email_1': emails[0] if emails else '',
                        'email_2': emails[1] if len(emails) > 1 else '',
                        'email_3': emails[2] if len(emails) > 2 else '',
                        'phone': phone,
                        'county': to_ascii(county),
                        'city': to_ascii(city),
                        'address': to_ascii(address),
                        'project_title': to_ascii(project)[:100],
                        'budget_eur': budget,
                        'status': status,
                        'source_file': Path(filepath).stem
                    })
    except Exception as e:
        print(f"  Error loading {filepath}: {e}")

    return contacts


def load_all_sources():
    """Load contacts from all source files"""
    print("Loading EU funds data sources...")
    all_contacts = []

    for name, filepath in SOURCE_FILES.items():
        contacts = load_source_file(filepath)
        print(f"  {name}: {len(contacts):,} with contacts")
        all_contacts.extend(contacts)

    # Deduplicate by normalized name
    seen = {}
    unique = []
    for c in all_contacts:
        key = c['company_name_normalized']
        if not key:
            continue
        if key not in seen:
            seen[key] = c
            unique.append(c)
        else:
            # Merge: keep more complete record
            existing = seen[key]
            if not existing['email_1'] and c['email_1']:
                existing['email_1'] = c['email_1']
            if not existing['phone'] and c['phone']:
                existing['phone'] = c['phone']
            if not existing['cui'] and c['cui']:
                existing['cui'] = c['cui']

    print(f"\nTotal unique companies: {len(unique):,}")
    return unique


def show_stats():
    """Show statistics about EU funds data"""
    print("\n" + "="*60)
    print("EU FUNDS DATA STATISTICS")
    print("="*60)

    # Check each source
    total_rows = 0
    total_with_email = 0
    total_with_phone = 0

    for name, filepath in SOURCE_FILES.items():
        if Path(filepath).exists():
            contacts = load_source_file(filepath)
            rows = len(contacts)
            with_email = len([c for c in contacts if c['email_1']])
            with_phone = len([c for c in contacts if c['phone']])
            total_rows += rows
            total_with_email += with_email
            total_with_phone += with_phone
            print(f"\n{name}:")
            print(f"  Records: {rows:,}")
            print(f"  With email: {with_email:,}")
            print(f"  With phone: {with_phone:,}")
        else:
            print(f"\n{name}: NOT FOUND")

    print(f"\n{'='*60}")
    print(f"TOTAL with contacts: {total_rows:,}")
    print(f"TOTAL with email: {total_with_email:,}")
    print(f"TOTAL with phone: {total_with_phone:,}")


def export_contacts(output_path=None):
    """Export all EU funds contacts"""
    contacts = load_all_sources()

    if not output_path:
        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        output_path = f'{OUTPUT_DIR}/eufunds_contacts.csv'

    fieldnames = [
        'company_name', 'company_name_normalized', 'cui', 'caen',
        'email_1', 'email_2', 'email_3', 'phone',
        'county', 'city', 'address',
        'project_title', 'budget_eur', 'status', 'source_file'
    ]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(contacts)

    # Stats
    with_email = len([c for c in contacts if c['email_1']])
    with_phone = len([c for c in contacts if c['phone']])

    print(f"\nExported {len(contacts):,} companies to {output_path}")
    print(f"  With email: {with_email:,} ({100*with_email//len(contacts)}%)")
    print(f"  With phone: {with_phone:,} ({100*with_phone//len(contacts)}%)")

    # County breakdown
    counties = Counter(c['county'] for c in contacts if c['county'])
    print(f"\n--- TOP COUNTIES ---")
    for county, count in counties.most_common(10):
        print(f"  {county[:20]:20} {count:>6,}")

    return contacts


def enrich_csv(input_path, output_path=None):
    """Enrich a CSV with EU funds contact data"""
    print(f"Enriching {input_path}...")

    # Load EU funds lookup
    contacts = load_all_sources()

    # Build lookup tables
    by_name = {c['company_name_normalized']: c for c in contacts if c['company_name_normalized']}
    by_cui = {c['cui']: c for c in contacts if c['cui']}

    print(f"  Lookup: {len(by_name):,} by name, {len(by_cui):,} by CUI")

    # Try fuzzy matching
    try:
        from rapidfuzz import fuzz, process
        fuzzy_available = True
        lookup_names = list(by_name.keys())
        print(f"  Fuzzy matching enabled")
    except ImportError:
        fuzzy_available = False
        print(f"  Fuzzy matching disabled (install rapidfuzz)")

    # Process input
    enriched = 0
    total = 0
    rows = []

    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames + ['eufunds_email', 'eufunds_phone', 'eufunds_project', 'eufunds_match']

        for row in reader:
            total += 1
            cui = row.get('cui', row.get('CUI', '')).strip()
            name = row.get('company_name', row.get('nume_firma', row.get('DENUMIRE', ''))).strip()
            norm_name = normalize_company_name(name)

            match = None
            match_type = ''

            # 1. CUI match
            if cui and cui in by_cui:
                match = by_cui[cui]
                match_type = 'CUI'
            # 2. Exact name match
            elif norm_name and norm_name in by_name:
                match = by_name[norm_name]
                match_type = 'NAME_EXACT'
            # 3. Fuzzy match
            elif fuzzy_available and norm_name:
                result = process.extractOne(norm_name, lookup_names, scorer=fuzz.ratio)
                if result and result[1] >= 85:
                    match = by_name[result[0]]
                    match_type = f'FUZZY_{result[1]}'

            if match:
                row['eufunds_email'] = match.get('email_1', '')
                row['eufunds_phone'] = match.get('phone', '')
                row['eufunds_project'] = match.get('project_title', '')[:50]
                row['eufunds_match'] = match_type
                if match.get('email_1') or match.get('phone'):
                    enriched += 1
            else:
                row['eufunds_email'] = ''
                row['eufunds_phone'] = ''
                row['eufunds_project'] = ''
                row['eufunds_match'] = ''

            rows.append(row)

    # Save output
    if not output_path:
        output_path = input_path.replace('.csv', '_eufunds_enriched.csv')

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nEnriched {enriched:,}/{total:,} ({100*enriched//total}%) companies")
    print(f"Output: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='EU Funds contact enricher')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--extract', action='store_true', help='Extract all contacts')
    parser.add_argument('--export', action='store_true', help='Export contacts CSV')
    parser.add_argument('--enrich', metavar='CSV', help='Enrich a CSV file')
    parser.add_argument('--output', '-o', help='Output path')

    args = parser.parse_args()

    if args.stats:
        show_stats()
    elif args.extract or args.export:
        export_contacts(args.output)
    elif args.enrich:
        enrich_csv(args.enrich, args.output)
    else:
        # Default: show stats
        show_stats()


if __name__ == '__main__':
    main()
