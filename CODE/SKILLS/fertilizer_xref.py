#!/usr/bin/env python3
"""
Fertilizer Cross-Reference Skill

Cross-references fertilizer companies with internal databases:
- ANOFM: Romanian job postings with company contacts
- MASTER_ALL: 65K EU employers
- EU_AGRI: Agriculture cooperatives and contacts

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/fertilizer_xref.py
    python3 /opt/ACTIVE/INFRA/SKILLS/fertilizer_xref.py --output /opt/FERTILIZERS/enriched.csv
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import csv
import re
import subprocess
from pathlib import Path
from collections import defaultdict
from skills_common import to_ascii

# Data sources
ANOFM = Path('/opt/ACTIVE/OPENDATA/DATA/ANOFM/anofm_master.csv')
MASTER_ALL = Path('/opt/ACTIVE/OPENDATA/DATA/MASTER_ALL.csv')
EU_AGRI = Path('/opt/ACTIVE/OPENDATA/DATA/EU_AGRI_DATABASE/eu_agri_coops_contacts.csv')
PDF_FILE = Path('/opt/FERTILIZERS/Lista-îngrășăminte-chimice-și-biologice-autorizate-actualizată-la-data-de-1.06.2024.pdf')
OUTPUT = Path('/opt/FERTILIZERS/fertilizer_companies_enriched.csv')


def normalize(name: str) -> str:
    """Normalize company name for matching."""
    if not name:
        return ""
    n = to_ascii(name).upper()
    # Remove legal suffixes
    for suffix in ['S.R.L.', 'SRL', 'S.A.', 'SA', 'S.C.', 'SC', 'PFA', 'II', 'IF']:
        n = n.replace(suffix, '')
    # Remove punctuation
    n = re.sub(r'[^\w\s]', ' ', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def extract_companies_from_pdf() -> list:
    """Extract company names from fertilizer PDF."""
    try:
        result = subprocess.run(
            ['pdftotext', str(PDF_FILE), '-'],
            capture_output=True, text=True, timeout=60
        )
        text = result.stdout
    except Exception as e:
        print(f"PDF error: {e}")
        return []

    # Extract company patterns
    patterns = [
        r'SC\s+([A-Z][A-Za-z\s\-\.]+)\s*S\.?R\.?L\.?',
        r'S\.C\.\s+([A-Z][A-Za-z\s\-\.]+)\s*S\.?[RA]\.?',
        r'([A-Z][A-Za-z\s\-\.]+)\s+SRL',
        r'([A-Z][A-Za-z\s\-\.]+)\s+S\.A\.',
    ]

    companies = set()
    for pattern in patterns:
        for match in re.findall(pattern, text):
            name = to_ascii(match.strip())
            if len(name) > 3 and name not in ['ROMANIA', 'BUCURESTI', 'ITALIA']:
                companies.add(name)

    return list(companies)


def load_anofm() -> dict:
    """Load ANOFM database into lookup dict."""
    lookup = {}
    if not ANOFM.exists():
        return lookup

    with open(ANOFM, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = normalize(row.get('company_name', ''))
            if name:
                lookup[name] = {
                    'email': row.get('email_1', ''),
                    'phone': row.get('phone_1', ''),
                    'cui': row.get('company_org_number', ''),
                    'city': row.get('company_city', ''),
                    'source': 'ANOFM'
                }
    return lookup


def load_master_all() -> dict:
    """Load MASTER_ALL database."""
    lookup = {}
    if not MASTER_ALL.exists():
        return lookup

    with open(MASTER_ALL, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('country', '').upper() not in ['RO', 'ROMANIA']:
                continue
            name = normalize(row.get('employer', ''))
            if name and name not in lookup:
                lookup[name] = {
                    'email': row.get('email1', ''),
                    'phone': row.get('phone1', ''),
                    'cui': row.get('employer_tax_code', ''),
                    'city': row.get('city', ''),
                    'source': 'MASTER_ALL'
                }
    return lookup


def load_eu_agri() -> dict:
    """Load EU Agri database."""
    lookup = {}
    if not EU_AGRI.exists():
        return lookup

    with open(EU_AGRI, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('country', '').upper() not in ['RO', 'ROMANIA']:
                continue
            name = normalize(row.get('name', ''))
            if name and name not in lookup:
                lookup[name] = {
                    'email': row.get('email', ''),
                    'phone': row.get('phone', ''),
                    'cui': '',
                    'city': row.get('city', ''),
                    'source': 'EU_AGRI'
                }
    return lookup


def cross_reference(companies: list, lookups: list) -> list:
    """Cross-reference companies against all lookups (exact match only)."""
    results = []

    for company in companies:
        norm = normalize(company)
        match = None

        # Exact match only
        for lookup in lookups:
            if norm in lookup:
                match = lookup[norm]
                break

        results.append({
            'company': company,
            'company_normalized': norm,
            'email': match['email'] if match else '',
            'phone': match['phone'] if match else '',
            'cui': match['cui'] if match else '',
            'city': match['city'] if match else '',
            'source': match['source'] if match else '',
            'matched': 'YES' if match else 'NO'
        })

    return results


def find_agri_sector_companies() -> list:
    """Find agriculture/zootechnie sector companies from ANOFM."""
    results = []
    if not ANOFM.exists():
        return results

    with open(ANOFM, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        seen = set()
        for row in reader:
            sector = row.get('sector', '').lower()
            if 'agri' in sector or 'zooteh' in sector or 'farm' in sector:
                name = row.get('company_name', '')
                if name and name not in seen:
                    seen.add(name)
                    results.append({
                        'company': to_ascii(name),
                        'email': row.get('email_1', ''),
                        'phone': row.get('phone_1', ''),
                        'cui': row.get('company_org_number', ''),
                        'city': row.get('company_city', ''),
                        'sector': row.get('sector', ''),
                        'source': 'ANOFM_AGRI'
                    })
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Fertilizer cross-reference')
    parser.add_argument('--output', '-o', default=str(OUTPUT))
    parser.add_argument('--sector', '-s', action='store_true', help='Find agri sector companies')
    args = parser.parse_args()

    print("=== FERTILIZER CROSS-REFERENCE ===\n")

    if args.sector:
        # Mode 2: Find all agriculture sector companies
        print("Finding agriculture sector companies...")
        agri_companies = find_agri_sector_companies()
        print(f"  Found: {len(agri_companies)} agriculture companies\n")

        with_email = sum(1 for r in agri_companies if r['email'])
        with_phone = sum(1 for r in agri_companies if r['phone'])

        print(f"=== RESULTS ===")
        print(f"Total: {len(agri_companies)}")
        print(f"With email: {with_email}")
        print(f"With phone: {with_phone}")

        output_path = Path(args.output).with_name('agri_sector_companies.csv')
        if agri_companies:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=agri_companies[0].keys())
                writer.writeheader()
                writer.writerows(agri_companies)
            print(f"\nSaved: {output_path}")

            print(f"\n=== SAMPLE (with contacts) ===")
            for r in agri_companies[:15]:
                if r['email'] or r['phone']:
                    print(f"  {r['company'][:35]}: {r['email'] or r['phone']}")
        return

    # Mode 1: Cross-reference PDF companies
    print("Extracting companies from PDF...")
    companies = extract_companies_from_pdf()
    print(f"  Found: {len(companies)} companies\n")

    print("Loading databases...")
    anofm = load_anofm()
    print(f"  ANOFM: {len(anofm)} companies")
    master = load_master_all()
    print(f"  MASTER_ALL (RO): {len(master)} companies")
    eu_agri = load_eu_agri()
    print(f"  EU_AGRI (RO): {len(eu_agri)} companies\n")

    print("Cross-referencing...")
    results = cross_reference(companies, [anofm, master, eu_agri])

    matched = sum(1 for r in results if r['matched'] == 'YES')
    with_email = sum(1 for r in results if r['email'])
    with_phone = sum(1 for r in results if r['phone'])

    print(f"\n=== RESULTS ===")
    print(f"Total companies: {len(results)}")
    print(f"Matched: {matched} ({100*matched/len(results) if results else 0:.1f}%)")
    print(f"With email: {with_email}")
    print(f"With phone: {with_phone}")

    output_path = Path(args.output)
    if results:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        print(f"\nSaved: {output_path}")

    print(f"\n=== MATCHED COMPANIES ===")
    for r in results[:20]:
        if r['matched'] == 'YES':
            print(f"  {r['company'][:40]}: {r['email'] or r['phone']} ({r['source']})")


if __name__ == "__main__":
    main()
