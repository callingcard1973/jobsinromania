#!/usr/bin/env python3
"""
Internal Database Enrichment - Romanian Companies

Enriches any CSV with Romanian companies using internal data sources:
- ANOFM: ~2K companies with CUI, ~4.5K with email
- ANOFM_HORECA: ~15K companies by name
- MASTER_ALL: 65K employers (237 Romanian)

Matching strategy:
1. CUI exact match (most reliable)
2. Normalized company name match (removes SRL, SA, etc.)

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/firme_internal_enrich.py --input companies.csv
    python3 /opt/ACTIVE/INFRA/SKILLS/firme_internal_enrich.py --input companies.csv --output enriched.csv

Input CSV must have columns: cui, company_name
Output adds: internal_email, internal_phone, internal_website, internal_source

Reuses: skills_common.to_ascii, normalize_company_name from eu_internal_enrichment.py
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import csv
import re
import argparse
from pathlib import Path
from typing import Dict, Tuple, Optional
from collections import defaultdict

from skills_common import to_ascii

# Paths
INPUT_FILE = '/opt/ACTIVE/OPENDATA/FIRME_ROMANIA/DATA/firme_2016_anaf_enriched.csv'
OUTPUT_FILE = '/opt/ACTIVE/OPENDATA/FIRME_ROMANIA/DATA/firme_2016_internal_enriched.csv'

# Internal data sources
ANOFM_CSV = Path('/opt/ACTIVE/OPENDATA/DATA/ANOFM/anofm_master.csv')
MASTER_ALL = Path('/opt/ACTIVE/OPENDATA/DATA/MASTER_ALL.csv')
ANOFM_HORECA = Path('/opt/ACTIVE/OPENDATA/DATA/ANOFM_HORECA.csv')

# ============================================================
# REUSED FROM eu_internal_enrichment.py
# ============================================================

def normalize_company_name(name: str) -> str:
    """Normalize company name for matching."""
    if not name:
        return ''

    # Convert to ASCII lowercase
    name = to_ascii(name).lower().strip()

    # Remove common suffixes
    suffixes = [
        r'\s+(s\.?r\.?l\.?|s\.?a\.?|s\.?c\.?s\.?|ltd\.?|gmbh|ag|bv|nv|ab|as|oy|a/s)',
        r'\s+(limited|inc\.?|corp\.?|llc|plc|co\.?|company)',
        r'\s+(srl|sa|spa|sarl|eurl|sas|snc)',
        r'\s+(intreprindere\s+individuala|persoana\s+fizica\s+autorizata|pfa|ii)',
    ]
    for suffix in suffixes:
        name = re.sub(suffix + r'$', '', name, flags=re.IGNORECASE)

    # Remove punctuation and extra spaces
    name = re.sub(r'[^\w\s]', ' ', name)
    name = ' '.join(name.split())

    return name


def extract_cui(text: str) -> Optional[str]:
    """Extract Romanian CUI/tax code."""
    if not text:
        return None

    text = str(text).strip()

    # RO prefix
    if text.upper().startswith('RO'):
        text = text[2:]

    # Extract numeric CUI (6-10 digits)
    match = re.search(r'\b(\d{6,10})\b', text)
    if match:
        return match.group(1)

    return None


# ============================================================
# DATA LOADERS
# ============================================================

def load_anofm() -> Tuple[Dict[str, dict], Dict[str, dict]]:
    """Load ANOFM data - returns (name_index, cui_index)."""
    name_index = {}
    cui_index = {}

    if not ANOFM_CSV.exists():
        print(f"  Warning: {ANOFM_CSV} not found")
        return name_index, cui_index

    with open(ANOFM_CSV, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            company = row.get('company_name', '') or row.get('company_normalized', '')
            if not company:
                continue

            # Get emails
            emails = []
            for col in ['email_1', 'email_2', 'email_3']:
                email = row.get(col, '').strip().lower()
                if email and '@' in email and '.' in email:
                    emails.append(email)

            # Get phones
            phones = []
            for col in ['phone_1', 'phone_2']:
                phone = row.get(col, '').strip()
                if phone and len(phone) >= 9:
                    phones.append(phone)

            website = row.get('company_website', '').strip()

            if not emails and not phones:
                continue

            info = {
                'emails': emails,
                'phones': phones,
                'website': website,
                'source': 'ANOFM',
            }

            # Index by name
            norm_name = normalize_company_name(company)
            if norm_name and len(norm_name) >= 3:
                if norm_name not in name_index:
                    name_index[norm_name] = info

            # Index by CUI
            cui = extract_cui(row.get('company_org_number', ''))
            if cui:
                cui_index[cui] = info

    print(f"  ANOFM: {len(name_index):,} by name, {len(cui_index):,} by CUI")
    return name_index, cui_index


def load_anofm_horeca() -> Dict[str, dict]:
    """Load ANOFM HORECA data."""
    name_index = {}

    if not ANOFM_HORECA.exists():
        print(f"  Warning: {ANOFM_HORECA} not found")
        return name_index

    with open(ANOFM_HORECA, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            company = row.get('company_name', '')
            if not company:
                continue

            emails = []
            for col in ['email', 'email2']:
                email = row.get(col, '').strip().lower()
                if email and '@' in email:
                    emails.append(email)

            phones = []
            for col in ['phone1', 'phone2']:
                phone = row.get(col, '').strip()
                if phone and len(phone) >= 9:
                    phones.append(phone)

            if not emails and not phones:
                continue

            info = {
                'emails': emails,
                'phones': phones,
                'website': '',
                'source': 'ANOFM_HORECA',
            }

            norm_name = normalize_company_name(company)
            if norm_name and len(norm_name) >= 3:
                if norm_name not in name_index:
                    name_index[norm_name] = info

    print(f"  ANOFM_HORECA: {len(name_index):,} by name")
    return name_index


def load_master_all() -> Dict[str, dict]:
    """Load MASTER_ALL - company name -> contact info (Romanian only)."""
    contacts = {}

    if not MASTER_ALL.exists():
        print(f"  Warning: {MASTER_ALL} not found")
        return contacts

    with open(MASTER_ALL, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Romanian only
            if row.get('country', '').upper() != 'RO':
                continue

            company = row.get('employer', '') or row.get('employer_normalized', '')
            if not company:
                continue

            norm_name = normalize_company_name(company)
            if not norm_name or len(norm_name) < 3:
                continue

            # Get emails
            emails = []
            for col in ['email1', 'email2', 'email3']:
                email = row.get(col, '').strip().lower()
                if email and '@' in email:
                    emails.append(email)

            # Get phones
            phones = []
            for col in ['phone1', 'phone2']:
                phone = row.get(col, '').strip()
                if phone and len(phone) >= 9:
                    phones.append(phone)

            if emails and norm_name not in contacts:
                contacts[norm_name] = {
                    'emails': emails,
                    'phones': phones,
                    'website': row.get('company_website', ''),
                    'source': 'MASTER_ALL',
                }

    print(f"  MASTER_ALL (RO): {len(contacts):,} by name")
    return contacts


# ============================================================
# ENRICHMENT
# ============================================================

def enrich_companies(input_file: str, output_file: str):
    """Enrich companies with internal data."""

    print("=" * 60)
    print("FIRME ROMANIA - Internal Database Enrichment")
    print("=" * 60)

    # Load internal data
    print("\nLoading internal databases...")
    anofm_name, anofm_cui = load_anofm()
    horeca_name = load_anofm_horeca()
    master_name = load_master_all()

    # Load companies
    print(f"\nLoading companies from {Path(input_file).name}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        companies = list(reader)
        fieldnames = list(reader.fieldnames)

    print(f"  Loaded: {len(companies):,} companies")

    # Add new columns if not present
    new_cols = ['internal_email', 'internal_phone', 'internal_website', 'internal_source']
    for col in new_cols:
        if col not in fieldnames:
            fieldnames.append(col)

    # Stats
    stats = {
        'total': 0,
        'cui_match': 0,
        'name_match': 0,
        'with_email': 0,
        'with_phone': 0,
    }

    # Enrich
    print("\nEnriching...")
    for company in companies:
        stats['total'] += 1
        cui = company.get('cui', '').strip()
        name = company.get('company_name', '')
        norm_name = normalize_company_name(name)

        match_info = None
        match_type = None

        # 1. CUI match (most reliable)
        if cui and cui in anofm_cui:
            match_info = anofm_cui[cui]
            match_type = 'cui'
            stats['cui_match'] += 1

        # 2. Name match
        elif norm_name:
            if norm_name in anofm_name:
                match_info = anofm_name[norm_name]
                match_type = 'name_anofm'
                stats['name_match'] += 1
            elif norm_name in horeca_name:
                match_info = horeca_name[norm_name]
                match_type = 'name_horeca'
                stats['name_match'] += 1
            elif norm_name in master_name:
                match_info = master_name[norm_name]
                match_type = 'name_master'
                stats['name_match'] += 1

        # Apply match
        if match_info:
            emails = match_info.get('emails', [])
            phones = match_info.get('phones', [])

            company['internal_email'] = to_ascii(';'.join(emails[:2])) if emails else ''
            company['internal_phone'] = to_ascii(';'.join(phones[:2])) if phones else ''
            company['internal_website'] = to_ascii(match_info.get('website', ''))
            company['internal_source'] = f"{match_info['source']}:{match_type}"

            if emails:
                stats['with_email'] += 1
            if phones:
                stats['with_phone'] += 1
        else:
            company['internal_email'] = ''
            company['internal_phone'] = ''
            company['internal_website'] = ''
            company['internal_source'] = ''

    # Save
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(companies)

    # Report
    print(f"\n{'=' * 40}")
    print("RESULTS")
    print(f"{'=' * 40}")
    print(f"Total: {stats['total']:,}")
    print(f"CUI matches: {stats['cui_match']:,} ({stats['cui_match']/stats['total']*100:.1f}%)")
    print(f"Name matches: {stats['name_match']:,} ({stats['name_match']/stats['total']*100:.1f}%)")
    print(f"With email: {stats['with_email']:,} ({stats['with_email']/stats['total']*100:.1f}%)")
    print(f"With phone: {stats['with_phone']:,} ({stats['with_phone']/stats['total']*100:.1f}%)")
    print(f"\nSaved: {output_file}")

    # Samples
    print("\nSample matches:")
    samples = [c for c in companies if c.get('internal_email')][:5]
    for s in samples:
        print(f"  {s['company_name'][:35]}: {s.get('internal_email', '')[:30]}")

    return stats


def main():
    parser = argparse.ArgumentParser(description='Internal Database Enrichment')
    parser.add_argument('--input', '-i', default=INPUT_FILE, help='Input CSV')
    parser.add_argument('--output', '-o', default=OUTPUT_FILE, help='Output CSV')
    args = parser.parse_args()

    enrich_companies(args.input, args.output)
    return 0


if __name__ == '__main__':
    sys.exit(main())
