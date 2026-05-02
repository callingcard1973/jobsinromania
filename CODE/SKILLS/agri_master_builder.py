#!/usr/bin/env python3
"""
Agriculture Master Builder - Comprehensive cross-reference

Combines ALL agriculture-related data sources into one master CSV:
- ANOFM (agriculture sector)
- MASTER_ALL (RO companies)
- EU_AGRI coops
- DSVSA food establishments (82K)
- RO EU fund beneficiaries (12K)
- AGRICULTURE_JOBS

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/agri_master_builder.py
    python3 /opt/ACTIVE/INFRA/SKILLS/agri_master_builder.py --output /opt/FERTILIZERS/master.csv
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import csv
import re
from pathlib import Path
from collections import defaultdict
from skills_common import to_ascii

# All data sources
SOURCES = {
    'ANOFM': Path('/opt/ACTIVE/OPENDATA/DATA/ANOFM/anofm_master.csv'),
    'MASTER_ALL': Path('/opt/ACTIVE/OPENDATA/DATA/MASTER_ALL.csv'),
    'EU_AGRI': Path('/opt/ACTIVE/OPENDATA/DATA/EU_AGRI_DATABASE/eu_agri_coops_contacts.csv'),
    'DSVSA': Path('/opt/ACTIVE/OPENDATA/DATA/SCRAPERS/DSVSA/DSVSA_MASTER.csv'),
    'EU_SUBSIDY': Path('/opt/ACTIVE/OPENDATA/DATA/EU_SUBSIDY/RO_romania_beneficiaries.csv'),
    'AGRI_JOBS': Path('/opt/ACTIVE/OPENDATA/DATA/AGRICULTURE_JOBS.csv'),
}

OUTPUT = Path('/opt/FERTILIZERS/agri_master_all.csv')

AGRI_KEYWORDS = ['agri', 'farm', 'zooteh', 'veter', 'fito', 'fertil', 'cereal', 'legum',
                 'fruct', 'vita', 'vin', 'apicol', 'piscicol', 'sera', 'depozit aliment']


def normalize(name: str) -> str:
    if not name:
        return ""
    n = to_ascii(name).upper()
    for suffix in ['S.R.L.', 'SRL', 'S.A.', 'SA', 'S.C.', 'SC', 'PFA', 'II', 'IF']:
        n = n.replace(suffix, '')
    n = re.sub(r'[^\w\s]', ' ', n)
    return re.sub(r'\s+', ' ', n).strip()


def is_agri_related(row: dict) -> bool:
    """Check if company is agriculture related."""
    text = ' '.join(str(v).lower() for v in row.values())
    return any(kw in text for kw in AGRI_KEYWORDS)


def load_anofm() -> list:
    results = []
    if not SOURCES['ANOFM'].exists():
        return results
    with open(SOURCES['ANOFM'], 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if is_agri_related(row):
                results.append({
                    'company': to_ascii(row.get('company_name', '')),
                    'company_norm': normalize(row.get('company_name', '')),
                    'cui': row.get('company_org_number', ''),
                    'email': row.get('email_1', ''),
                    'phone': row.get('phone_1', ''),
                    'city': row.get('company_city', ''),
                    'county': '',
                    'address': row.get('company_address', ''),
                    'category': row.get('sector', ''),
                    'source': 'ANOFM'
                })
    return results


def load_master_all() -> list:
    results = []
    if not SOURCES['MASTER_ALL'].exists():
        return results
    with open(SOURCES['MASTER_ALL'], 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row.get('country', '').upper() not in ['RO', 'ROMANIA']:
                continue
            if is_agri_related(row):
                results.append({
                    'company': to_ascii(row.get('employer', '')),
                    'company_norm': normalize(row.get('employer', '')),
                    'cui': row.get('employer_tax_code', ''),
                    'email': row.get('email1', ''),
                    'phone': row.get('phone1', ''),
                    'city': row.get('city', ''),
                    'county': row.get('region', ''),
                    'address': row.get('address', ''),
                    'category': row.get('sector', ''),
                    'source': 'MASTER_ALL'
                })
    return results


def load_eu_agri() -> list:
    results = []
    if not SOURCES['EU_AGRI'].exists():
        return results
    with open(SOURCES['EU_AGRI'], 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row.get('country', '').upper() not in ['RO', 'ROMANIA']:
                continue
            results.append({
                'company': to_ascii(row.get('name', '')),
                'company_norm': normalize(row.get('name', '')),
                'cui': '',
                'email': row.get('email', ''),
                'phone': row.get('phone', ''),
                'city': row.get('city', ''),
                'county': '',
                'address': row.get('address', ''),
                'category': 'EU_AGRI_COOP',
                'source': 'EU_AGRI'
            })
    return results


def load_dsvsa() -> list:
    results = []
    if not SOURCES['DSVSA'].exists():
        return results
    with open(SOURCES['DSVSA'], 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if is_agri_related(row):
                results.append({
                    'company': to_ascii(row.get('company_name', '')),
                    'company_norm': normalize(row.get('company_name', '')),
                    'cui': row.get('registration_number', ''),
                    'email': '',
                    'phone': '',
                    'city': row.get('city', ''),
                    'county': row.get('county', ''),
                    'address': row.get('address', ''),
                    'category': row.get('category', ''),
                    'source': 'DSVSA'
                })
    return results


def load_eu_subsidy() -> list:
    results = []
    if not SOURCES['EU_SUBSIDY'].exists():
        return results
    with open(SOURCES['EU_SUBSIDY'], 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if is_agri_related(row):
                results.append({
                    'company': to_ascii(row.get('company_name', '')),
                    'company_norm': normalize(row.get('company_name', '')),
                    'cui': row.get('company_id', ''),
                    'email': row.get('contact_email', ''),
                    'phone': row.get('contact_phone', ''),
                    'city': row.get('location_city', ''),
                    'county': row.get('location_region', ''),
                    'address': row.get('location_address', ''),
                    'category': 'EU_SUBSIDY',
                    'source': 'EU_SUBSIDY'
                })
    return results


def load_agri_jobs() -> list:
    results = []
    if not SOURCES['AGRI_JOBS'].exists():
        return results
    with open(SOURCES['AGRI_JOBS'], 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row.get('country', '').upper() not in ['RO', 'ROMANIA', '']:
                continue
            results.append({
                'company': to_ascii(row.get('company', '')),
                'company_norm': normalize(row.get('company', '')),
                'cui': '',
                'email': row.get('email', ''),
                'phone': row.get('phone', ''),
                'city': row.get('city', ''),
                'county': row.get('region', ''),
                'address': '',
                'category': 'AGRICULTURE',
                'source': 'AGRI_JOBS'
            })
    return results


def merge_records(records: list) -> list:
    """Merge records by normalized company name, keeping best data."""
    merged = {}

    for r in records:
        key = r['company_norm']
        if not key:
            continue

        if key not in merged:
            merged[key] = r.copy()
            merged[key]['sources'] = r['source']
        else:
            # Merge: prefer non-empty values
            existing = merged[key]
            for field in ['email', 'phone', 'cui', 'city', 'county', 'address']:
                if not existing[field] and r[field]:
                    existing[field] = r[field]
            existing['sources'] += ',' + r['source']

    return list(merged.values())


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', '-o', default=str(OUTPUT))
    args = parser.parse_args()

    print("=== AGRICULTURE MASTER BUILDER ===\n")

    all_records = []

    # Load all sources
    loaders = [
        ('ANOFM', load_anofm),
        ('MASTER_ALL', load_master_all),
        ('EU_AGRI', load_eu_agri),
        ('DSVSA', load_dsvsa),
        ('EU_SUBSIDY', load_eu_subsidy),
        ('AGRI_JOBS', load_agri_jobs),
    ]

    for name, loader in loaders:
        print(f"Loading {name}...", end=' ')
        records = loader()
        print(f"{len(records)} agri records")
        all_records.extend(records)

    print(f"\nTotal raw: {len(all_records)}")

    # Merge duplicates
    print("Merging duplicates...")
    merged = merge_records(all_records)
    print(f"After merge: {len(merged)}")

    # Stats
    with_email = sum(1 for r in merged if r.get('email'))
    with_phone = sum(1 for r in merged if r.get('phone'))
    with_cui = sum(1 for r in merged if r.get('cui'))
    with_contact = sum(1 for r in merged if r.get('email') or r.get('phone'))

    print(f"\n=== RESULTS ===")
    print(f"Total companies: {len(merged)}")
    print(f"With email: {with_email}")
    print(f"With phone: {with_phone}")
    print(f"With CUI: {with_cui}")
    print(f"With any contact: {with_contact}")

    # Save
    output_path = Path(args.output)
    fieldnames = ['company', 'company_norm', 'cui', 'email', 'phone', 'city', 'county', 'address', 'category', 'sources']

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in merged:
            row = {k: r.get(k, '') for k in fieldnames}
            writer.writerow(row)

    print(f"\nSaved: {output_path}")

    # Sample with contacts
    print(f"\n=== SAMPLE (with contacts) ===")
    shown = 0
    for r in merged:
        if r.get('email') or r.get('phone'):
            print(f"  {r['company'][:40]}: {r.get('email') or r.get('phone')} [{r.get('sources')}]")
            shown += 1
            if shown >= 15:
                break


if __name__ == "__main__":
    main()
