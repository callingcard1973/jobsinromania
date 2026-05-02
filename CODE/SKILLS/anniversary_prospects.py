#!/usr/bin/env python3
"""
Anniversary Prospects - Find companies celebrating milestone anniversaries

Use case: B2B outreach for corporate events (restaurants, venues, catering)

Usage:
  python3 anniversary_prospects.py --years 5 10 15 20 --county Bucuresti Ilfov
  python3 anniversary_prospects.py --years 10 --min-employees 20 --output prospects.csv
  python3 anniversary_prospects.py --venue "Twisted Olives" --capacity 70
  python3 anniversary_prospects.py --enrich  # Add emails from internal databases

Data source: /opt/ACTIVE/OPENDATA/DATA/ROMANIA/BILANT/romania_companies_master.csv
Email sources: ANOFM, CCIB, MASTER_ALL, virgil_schema
"""

import sys
import csv
import argparse
from datetime import date
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii

MASTER_DB = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/BILANT/romania_companies_master.csv'
CURRENT_YEAR = date.today().year

# Email enrichment sources
EMAIL_SOURCES = {
    'anofm': '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/ANOFM/anofm_master.csv',
    'ccib': '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/CCIB/ccib_companies.csv',
    'master_all': '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/MASTER_ALL.csv',
    'virgil': '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/BILANT/virgil_schema_enriched.csv'
}

# Industry categories
CAEN_LABELS = {
    '62': 'IT/Software',
    '63': 'Information Services',
    '64': 'Finance',
    '65': 'Insurance',
    '66': 'Financial Services',
    '68': 'Real Estate',
    '69': 'Legal/Accounting',
    '70': 'Management Consulting',
    '71': 'Engineering/Architecture',
    '73': 'Advertising/Marketing',
    '74': 'Professional Services',
    '46': 'Wholesale Trade',
    '80': 'Security Services',
    '82': 'Office Support'
}

# Industries good for corporate events
GOOD_B2B_CAEN = list(CAEN_LABELS.keys())

# Exclude HoReCa (competitors for restaurants/venues)
EXCLUDE_CAEN = ['55', '56']


def load_email_sources():
    """Load email lookup from all internal databases"""
    email_by_name = {}
    email_by_cui = {}

    # 1. ANOFM
    try:
        with open(EMAIL_SOURCES['anofm'], 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get('email_1', '').strip()
                website = row.get('company_website', '').strip()
                name = row.get('company_name', '').strip().upper()
                if email and '@' in email:
                    email_by_name[name] = {'email': email, 'website': website, 'source': 'ANOFM'}
        print(f"  ANOFM: {len(email_by_name)} emails")
    except Exception as e:
        print(f"  ANOFM: error - {e}")

    # 2. CCIB
    try:
        ccib_count = 0
        with open(EMAIL_SOURCES['ccib'], 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get('email', '').strip()
                website = row.get('website', '').strip()
                name = row.get('name', '').strip().upper()
                if email and '@' in email and name not in email_by_name:
                    email_by_name[name] = {'email': email, 'website': website, 'source': 'CCIB'}
                    ccib_count += 1
        print(f"  CCIB: +{ccib_count} emails")
    except Exception as e:
        print(f"  CCIB: error - {e}")

    # 3. MASTER_ALL
    try:
        master_count = 0
        with open(EMAIL_SOURCES['master_all'], 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get('email1', '').strip()
                website = row.get('company_website', '').strip()
                name = row.get('employer', '').strip().upper()
                if email and '@' in email and name not in email_by_name:
                    email_by_name[name] = {'email': email, 'website': website, 'source': 'MASTER'}
                    master_count += 1
        print(f"  MASTER_ALL: +{master_count} emails")
    except Exception as e:
        print(f"  MASTER_ALL: error - {e}")

    # 4. virgil_schema by CUI
    try:
        with open(EMAIL_SOURCES['virgil'], 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cui = row.get('cui', '').strip()
                email = row.get('email', '').strip()
                if cui and email and '@' in email:
                    email_by_cui[cui] = email
        print(f"  Virgil (by CUI): {len(email_by_cui)} emails")
    except Exception as e:
        print(f"  Virgil: error - {e}")

    return email_by_name, email_by_cui


def normalize_company_name(name):
    """Normalize company name for matching"""
    import re
    name = name.upper()
    for suffix in [' SRL', ' SA', ' S.R.L.', ' S.A.', ' S.R.L', ' ROMANIA', ' RO']:
        name = name.replace(suffix, '')
    name = re.sub(r'[^\w\s]', '', name)
    return name.strip()


def enrich_with_emails(prospects, email_by_name, email_by_cui, use_fuzzy=True, fuzzy_threshold=85):
    """Add emails to prospects from lookup tables with optional fuzzy matching"""
    enriched = 0

    # Build normalized name lookup for fuzzy matching
    normalized_lookup = {}
    for name, data in email_by_name.items():
        norm = normalize_company_name(name)
        if norm:
            normalized_lookup[norm] = data

    # Try to import rapidfuzz for fuzzy matching
    fuzzy_available = False
    if use_fuzzy:
        try:
            from rapidfuzz import fuzz, process
            fuzzy_available = True
            lookup_names = list(normalized_lookup.keys())
            print(f"  Fuzzy matching enabled ({len(lookup_names)} names)")
        except ImportError:
            print("  Warning: rapidfuzz not installed, fuzzy matching disabled")

    for p in prospects:
        name = p['company_name'].upper()
        norm_name = normalize_company_name(name)
        cui = p.get('cui', '').strip()
        email = ''
        website = ''
        source = ''

        # 1. Try CUI match first (most accurate)
        if cui in email_by_cui:
            email = email_by_cui[cui]
            source = 'CUI'

        # 2. Try exact name match
        elif name in email_by_name:
            email = email_by_name[name]['email']
            website = email_by_name[name]['website']
            source = email_by_name[name]['source']

        # 3. Try normalized name match
        elif norm_name in normalized_lookup:
            email = normalized_lookup[norm_name]['email']
            website = normalized_lookup[norm_name]['website']
            source = normalized_lookup[norm_name]['source'] + '_NORM'

        # 4. Try fuzzy match
        elif fuzzy_available and norm_name:
            result = process.extractOne(norm_name, lookup_names, scorer=fuzz.ratio)
            if result and result[1] >= fuzzy_threshold:
                matched_name = result[0]
                email = normalized_lookup[matched_name]['email']
                website = normalized_lookup[matched_name]['website']
                source = f"FUZZY_{result[1]}"

        p['email'] = email
        p['website'] = website
        p['email_source'] = source
        if email:
            enriched += 1

    return enriched


def find_anniversary_companies(
    anniversary_years=[5, 10, 15, 20],
    counties=['Bucuresti', 'Ilfov'],
    min_employees=5,
    min_revenue=100000,
    include_caen=None,
    exclude_caen=None,
    require_phone=False
):
    """Find companies celebrating milestone anniversaries"""

    # Calculate founding years from anniversary
    target_years = {str(CURRENT_YEAR - y): y for y in anniversary_years}

    # Default filters
    if include_caen is None:
        include_caen = GOOD_B2B_CAEN
    if exclude_caen is None:
        exclude_caen = EXCLUDE_CAEN

    results = []

    with open(MASTER_DB, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Check founding year
            year = row.get('founding_year', '')
            if year not in target_years:
                continue

            # Check county
            judet = row.get('judet', '').upper()
            county_match = any(c.upper() in judet for c in counties)
            if not county_match:
                continue

            # Check industry
            caen = row.get('caen', '')[:2]
            if caen in exclude_caen:
                continue
            if include_caen and caen not in include_caen:
                continue

            # Check size filters
            employees = int(row.get('nr_angajati', '0') or 0)
            revenue = int(row.get('cifra_afaceri', '0') or 0)
            if employees < min_employees or revenue < min_revenue:
                continue

            # Check phone if required
            phone = row.get('telefon', '').strip()
            if require_phone and not phone:
                continue

            results.append({
                'cui': row['cui'],
                'company_name': to_ascii(row['nume_firma']),
                'caen': row['caen'],
                'industry': CAEN_LABELS.get(caen, 'Other'),
                'employees': employees,
                'revenue': revenue,
                'founding_year': year,
                'anniversary': target_years[year],
                'phone': phone,
                'address': to_ascii(row.get('adresa', '')),
                'county': row.get('judet', ''),
                'has_contact': 'Yes' if phone else 'No'
            })

    return sorted(results, key=lambda x: (-x['anniversary'], -x['revenue']))


def export_prospects(prospects, output_path, venue_name=None, venue_capacity=None, with_email=False):
    """Export prospects to CSV with outreach context"""

    fieldnames = [
        'company_name', 'anniversary', 'founding_year', 'industry',
        'employees', 'revenue', 'phone', 'email', 'website',
        'address', 'county', 'cui', 'has_contact', 'outreach_reason'
    ]
    if with_email:
        fieldnames.append('email_source')

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for p in prospects:
            p['outreach_reason'] = f"Celebrating {p['anniversary']} years in business"
            if venue_name and venue_capacity:
                p['outreach_reason'] += f" - {venue_name} ({venue_capacity} seats)"
            writer.writerow({k: p.get(k, '') for k in fieldnames})

    return len(prospects)


def print_summary(prospects, venue_name=None):
    """Print summary statistics"""

    print(f"\n{'='*60}")
    if venue_name:
        print(f"PROSPECTS FOR: {venue_name}")
    print(f"{'='*60}")

    total = len(prospects)
    with_phone = len([p for p in prospects if p['phone']])

    print(f"\nTotal prospects: {total}")
    print(f"With phone (enriched): {with_phone} ({100*with_phone//total if total else 0}%)")
    print(f"Without phone: {total - with_phone}")

    print(f"\n{'--- BY ANNIVERSARY ---'}")
    from collections import Counter
    anni_counts = Counter(p['anniversary'] for p in prospects)
    for anni in sorted(anni_counts.keys(), reverse=True):
        enriched = len([p for p in prospects if p['anniversary']==anni and p['phone']])
        print(f"  {anni} years: {anni_counts[anni]:4} total, {enriched:4} enriched")

    print(f"\n{'--- BY INDUSTRY ---'}")
    ind_counts = Counter(p['industry'] for p in prospects)
    for ind, cnt in ind_counts.most_common(8):
        print(f"  {ind[:25]:25} {cnt:4}")

    print(f"\n{'--- TOP 10 PROSPECTS ---'}")
    top = sorted(prospects, key=lambda x: x['revenue'], reverse=True)[:10]
    for p in top:
        phone = p['phone'][:12] + '...' if len(p.get('phone', '')) > 12 else p.get('phone', 'N/A')
        print(f"  {p['anniversary']:2}yr | {p['employees']:4} emp | {phone:15} | {p['company_name'][:35]}")


def main():
    parser = argparse.ArgumentParser(description='Find anniversary prospect companies')
    parser.add_argument('--years', nargs='+', type=int, default=[5, 10, 15, 20],
                       help='Anniversary years to search (default: 5 10 15 20)')
    parser.add_argument('--county', nargs='+', default=['Bucuresti', 'Ilfov'],
                       help='Counties to include (default: Bucuresti Ilfov)')
    parser.add_argument('--min-employees', type=int, default=5,
                       help='Minimum employees (default: 5)')
    parser.add_argument('--min-revenue', type=int, default=100000,
                       help='Minimum revenue in RON (default: 100000)')
    parser.add_argument('--require-phone', action='store_true',
                       help='Only include companies with phone numbers')
    parser.add_argument('--output', '-o', help='Output CSV path')
    parser.add_argument('--venue', help='Venue name for outreach context')
    parser.add_argument('--capacity', type=int, help='Venue capacity (seats)')
    parser.add_argument('--enrich', action='store_true',
                       help='Enrich with emails from internal databases')

    args = parser.parse_args()

    print(f"Searching for companies celebrating {args.years} year anniversaries...")
    print(f"Counties: {args.county}")
    print(f"Filters: min {args.min_employees} employees, min {args.min_revenue:,} RON revenue")

    prospects = find_anniversary_companies(
        anniversary_years=args.years,
        counties=args.county,
        min_employees=args.min_employees,
        min_revenue=args.min_revenue,
        require_phone=args.require_phone
    )

    # Enrich with emails if requested
    if args.enrich:
        print("\nLoading email sources...")
        email_by_name, email_by_cui = load_email_sources()
        enriched_count = enrich_with_emails(prospects, email_by_name, email_by_cui)
        print(f"\nEnriched {enriched_count}/{len(prospects)} with emails ({100*enriched_count//len(prospects) if prospects else 0}%)")

    print_summary(prospects, args.venue)

    if args.output:
        count = export_prospects(prospects, args.output, args.venue, args.capacity, args.enrich)
        print(f"\nExported {count} prospects to: {args.output}")
    else:
        default_output = f'/opt/ACTIVE/OPENDATA/DATA/ROMANIA/anniversary_prospects_{CURRENT_YEAR}.csv'
        count = export_prospects(prospects, default_output, args.venue, args.capacity, args.enrich)
        print(f"\nExported {count} prospects to: {default_output}")


if __name__ == '__main__':
    main()
