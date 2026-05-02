#!/usr/bin/env python3
"""
Name Matcher - Match company names across databases to find CUIs and contacts

Matches companies without CUI to all_romania_companies.csv to get CUIs,
then looks up phones in ANAF all_phones.csv.

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/name_matcher.py --input /path/to/companies.csv
    python3 /opt/ACTIVE/INFRA/SKILLS/name_matcher.py --input /opt/FERTILIZERS/agri_master_all.csv
    python3 /opt/ACTIVE/INFRA/SKILLS/name_matcher.py --dsvsa   # Match DSVSA directly

Matching strategy:
1. Exact normalized match
2. Without legal suffix (SRL, SA, etc.)
3. First N words match (for long names)
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import csv
import re
import argparse
from pathlib import Path
from collections import defaultdict
from skills_common import to_ascii

# Data sources
ONRC_FILE = Path('/opt/ACTIVE/OPENDATA/FIRME_ROMANIA/DATA/all_romania_companies.csv')
PHONES_FILE = Path('/opt/ACTIVE/OPENDATA/FIRME_ROMANIA/DATA/anaf_all/all_phones.csv')
DSVSA_FILE = Path('/opt/ACTIVE/OPENDATA/DATA/SCRAPERS/DSVSA/DSVSA_MASTER.csv')
AGRI_MASTER = Path('/opt/FERTILIZERS/agri_master_all.csv')
OUTPUT_DIR = Path('/opt/FERTILIZERS')


def normalize(name: str) -> str:
    """Normalize company name for matching."""
    if not name:
        return ""
    n = to_ascii(name).upper()
    # Remove legal suffixes
    for suffix in ['S.R.L.', 'SRL', 'S.A.', 'SA', 'S.C.', 'SC', 'P.F.A.', 'PFA',
                   'I.I.', 'II', 'I.F.', 'IF', 'S.N.C.', 'SNC', 'S.C.S.', 'SCS',
                   'O.N.G.', 'ONG', 'SOCIETATE COMERCIALA', 'SOCIETATEA']:
        n = n.replace(suffix, '')
    # Remove punctuation
    n = re.sub(r'[^\w\s]', ' ', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def normalize_aggressive(name: str) -> str:
    """More aggressive normalization - first 3 significant words."""
    n = normalize(name)
    words = [w for w in n.split() if len(w) > 2]
    return ' '.join(words[:3])


def load_onrc_lookup() -> dict:
    """Load ONRC into name->CUI lookup dict."""
    print("Loading ONRC (4.1M companies)...")
    lookup = {}
    lookup_aggressive = {}

    if not ONRC_FILE.exists():
        print(f"  ERROR: {ONRC_FILE} not found")
        return lookup, lookup_aggressive

    with open(ONRC_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            count += 1
            if count % 500000 == 0:
                print(f"  Loaded {count:,}...")

            name = row.get('company_name', '')
            cui = row.get('cui', '').strip()

            if not cui or not name:
                continue

            norm = normalize(name)
            if norm and norm not in lookup:
                lookup[norm] = cui

            # Aggressive match
            agg = normalize_aggressive(name)
            if agg and len(agg) > 5 and agg not in lookup_aggressive:
                lookup_aggressive[agg] = cui

    print(f"  Loaded {len(lookup):,} exact, {len(lookup_aggressive):,} aggressive")
    return lookup, lookup_aggressive


def load_phones() -> dict:
    """Load ANAF phones into CUI->phone lookup."""
    print("Loading ANAF phones...")
    phones = {}

    if not PHONES_FILE.exists():
        print(f"  WARNING: {PHONES_FILE} not found")
        return phones

    with open(PHONES_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cui = row.get('cui', '').strip()
            phone = row.get('phone', '').strip()
            if cui and phone:
                phones[cui] = phone

    print(f"  Loaded {len(phones):,} phones")
    return phones


def match_companies(input_file: Path, onrc_lookup: dict, onrc_aggressive: dict, phones: dict) -> list:
    """Match companies from input file to ONRC/ANAF."""
    print(f"Matching companies from {input_file}...")

    results = []
    stats = defaultdict(int)

    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])

        # Add new columns if not present
        for col in ['matched_cui', 'matched_phone', 'match_type']:
            if col not in fieldnames:
                fieldnames.append(col)

        for row in reader:
            stats['total'] += 1

            # Skip if already has phone
            if row.get('phone', '').strip():
                stats['already_has_phone'] += 1
                results.append(row)
                continue

            # Skip if already has CUI and we can lookup phone
            existing_cui = row.get('cui', '').strip()
            if existing_cui and existing_cui in phones:
                row['matched_phone'] = phones[existing_cui]
                row['match_type'] = 'existing_cui'
                stats['cui_phone_lookup'] += 1
                results.append(row)
                continue

            # Try name matching
            company = row.get('company', '') or row.get('company_name', '')
            norm = normalize(company)
            agg = normalize_aggressive(company)

            matched_cui = None
            match_type = None

            # Exact match
            if norm in onrc_lookup:
                matched_cui = onrc_lookup[norm]
                match_type = 'exact'
                stats['exact_match'] += 1
            # Aggressive match
            elif agg and len(agg) > 5 and agg in onrc_aggressive:
                matched_cui = onrc_aggressive[agg]
                match_type = 'aggressive'
                stats['aggressive_match'] += 1
            else:
                stats['no_match'] += 1

            if matched_cui:
                row['matched_cui'] = matched_cui
                if matched_cui in phones:
                    row['matched_phone'] = phones[matched_cui]
                    stats['phone_found'] += 1
                row['match_type'] = match_type

            results.append(row)

    return results, fieldnames, stats


def main():
    parser = argparse.ArgumentParser(description='Match company names to get CUIs and phones')
    parser.add_argument('--input', '-i', help='Input CSV file')
    parser.add_argument('--output', '-o', help='Output CSV file')
    parser.add_argument('--dsvsa', action='store_true', help='Match DSVSA directly')
    parser.add_argument('--agri', action='store_true', help='Match agri_master_all.csv')
    args = parser.parse_args()

    # Determine input file
    if args.dsvsa:
        input_file = DSVSA_FILE
    elif args.agri:
        input_file = AGRI_MASTER
    elif args.input:
        input_file = Path(args.input)
    else:
        print("Usage: name_matcher.py --input FILE or --dsvsa or --agri")
        return 1

    if not input_file.exists():
        print(f"ERROR: Input file not found: {input_file}")
        return 1

    # Determine output file
    if args.output:
        output_file = Path(args.output)
    else:
        output_file = OUTPUT_DIR / f"{input_file.stem}_matched.csv"

    print("=" * 60)
    print("NAME MATCHER - Company to CUI/Phone")
    print("=" * 60)

    # Load lookups
    onrc_lookup, onrc_aggressive = load_onrc_lookup()
    phones = load_phones()

    if not onrc_lookup:
        print("ERROR: Could not load ONRC data")
        return 1

    # Match
    results, fieldnames, stats = match_companies(input_file, onrc_lookup, onrc_aggressive, phones)

    # Save
    print(f"\nSaving to {output_file}...")
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(results)

    # Report
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Total records: {stats['total']:,}")
    print(f"Already had phone: {stats['already_has_phone']:,}")
    print(f"CUI phone lookup: {stats['cui_phone_lookup']:,}")
    print(f"Exact name match: {stats['exact_match']:,}")
    print(f"Aggressive match: {stats['aggressive_match']:,}")
    print(f"No match: {stats['no_match']:,}")
    print(f"Phones found: {stats['phone_found']:,}")
    print(f"\nOutput: {output_file}")

    # Calculate improvement
    new_phones = stats['cui_phone_lookup'] + stats['phone_found']
    total_phones = stats['already_has_phone'] + new_phones
    print(f"\n=== IMPROVEMENT ===")
    print(f"Before: {stats['already_has_phone']:,} phones")
    print(f"After: {total_phones:,} phones (+{new_phones:,})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
