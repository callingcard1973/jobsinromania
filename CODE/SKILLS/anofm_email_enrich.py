#!/usr/bin/env python3
"""
ANOFM Email Enrichment - Match companies against ANOFM's ~3.6K email records.

Since ANOFM only has ~3.6K companies with emails, fuzzy matching is fast.
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import csv
import re
import time
from collections import defaultdict
from skills_common import to_ascii

try:
    from rapidfuzz import fuzz, process
    FUZZY = True
except ImportError:
    FUZZY = False
    print("WARNING: rapidfuzz not available")

INPUT = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/BUCHAREST_ILFOV_ESTABLISHED/buc_ilfov_with_phones.csv'
OUTPUT = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/BUCHAREST_ILFOV_ESTABLISHED/oldest_companies_enriched.csv'
ANOFM_FILE = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/ANOFM/anofm_latest.csv'
THRESHOLD = 85

LEGAL_FORMS = ['S.R.L.', 'SRL', 'S.A.', 'SA', 'S.C.', 'SC', 'P.F.A.', 'PFA',
               'I.I.', 'II', 'O.N.G.', 'ONG', 'IMPEX', 'GRUP', 'GROUP',
               'HOLDING', 'INTERNATIONAL', 'ROMANIA', 'LTD', 'LIMITED']


def normalize_name(name):
    if not name: return ''
    name = to_ascii(str(name)).upper().strip()
    for form in LEGAL_FORMS:
        name = re.sub(rf'\b{re.escape(form)}\b\.?', '', name)
    name = re.sub(r'[^\w\s]', ' ', name)
    return ' '.join(name.split()).strip()


def normalize_cui(cui):
    if not cui: return ''
    return re.sub(r'\D', '', str(cui))


def main():
    print("ANOFM Email Enrichment")
    print(f"Input: {INPUT}")
    print(f"Output: {OUTPUT}")
    print(f"ANOFM: {ANOFM_FILE}")

    # Load ANOFM data
    print("\n=== Loading ANOFM emails ===")
    anofm_cui = {}  # cui -> {email, website}
    anofm_name = {}  # normalized_name -> {email, website}
    anofm_names_list = []

    with open(ANOFM_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        for row in csv.DictReader(f):
            cui = normalize_cui(row.get('company_org_number', ''))
            name = normalize_name(row.get('company_name', ''))
            email = (row.get('email_1') or '').strip()
            website = (row.get('company_website') or '').strip()

            if email and '@' in email:
                data = {'email': email, 'website': website}
                if cui:
                    anofm_cui[cui] = data
                if name and name not in anofm_name:
                    anofm_name[name] = data
                    anofm_names_list.append(name)

    print(f"  ANOFM CUI->email: {len(anofm_cui):,}")
    print(f"  ANOFM name->email: {len(anofm_name):,}")

    # Load input file
    print("\n=== Loading input ===")
    with open(INPUT, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames)

    print(f"  Loaded {len(rows):,} rows")

    # Add output columns
    new_cols = ['anofm_email', 'anofm_website', 'anofm_match_type', 'anofm_match_score']
    out_fields = fieldnames + [c for c in new_cols if c not in fieldnames]

    # Process with CUI, exact name, then fuzzy name
    print("\n=== Enriching ===")
    start = time.time()
    stats = defaultdict(int)

    for i, row in enumerate(rows):
        result = None

        # 1. CUI match
        cui = normalize_cui(row.get('cui', ''))
        if cui and cui in anofm_cui:
            result = anofm_cui[cui].copy()
            result['match_type'] = 'cui'
            result['match_score'] = 100

        # 2. Exact name match
        if not result:
            name = normalize_name(row.get('denumire', ''))
            if name in anofm_name:
                result = anofm_name[name].copy()
                result['match_type'] = 'name_exact'
                result['match_score'] = 100
            elif FUZZY and len(name) >= 3:
                # 3. Fuzzy match against 3.6K ANOFM names (fast!)
                match = process.extractOne(
                    name,
                    anofm_names_list,
                    scorer=fuzz.token_sort_ratio,
                    score_cutoff=THRESHOLD
                )
                if match:
                    matched_name, score, _ = match
                    result = anofm_name[matched_name].copy()
                    result['match_type'] = 'fuzzy'
                    result['match_score'] = int(score)

        # Apply result
        if result:
            row['anofm_email'] = result.get('email', '') or ''
            row['anofm_website'] = result.get('website', '') or ''
            row['anofm_match_type'] = result.get('match_type', '')
            row['anofm_match_score'] = result.get('match_score', '')
            stats['matched'] += 1
            stats[result['match_type']] += 1
        else:
            for col in new_cols:
                row[col] = ''

        # Progress
        if (i + 1) % 50000 == 0:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed
            print(f"  {i+1:,}/{len(rows):,} - {stats['matched']:,} matched - {rate:.0f}/sec")

    # Save
    print(f"\n=== Saving {len(rows):,} rows ===")
    with open(OUTPUT, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(rows)

    # Summary
    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"COMPLETE in {elapsed:.1f}s")
    print(f"{'='*60}")
    print(f"Email matches: {stats['matched']:,} ({100*stats['matched']/len(rows):.2f}%)")
    print(f"  CUI: {stats['cui']:,}")
    print(f"  Name exact: {stats['name_exact']:,}")
    print(f"  Fuzzy: {stats['fuzzy']:,}")

    # Overall enrichment stats
    print(f"\n=== OVERALL ENRICHMENT SUMMARY ===")
    phone_count = sum(1 for r in rows if r.get('anaf_phone', '').strip())
    email_count = sum(1 for r in rows if r.get('anofm_email', '').strip())
    website_count = sum(1 for r in rows if r.get('website', '').strip() or r.get('anofm_website', '').strip())

    print(f"Total companies: {len(rows):,}")
    print(f"With phone (ANAF): {phone_count:,} ({100*phone_count/len(rows):.1f}%)")
    print(f"With email (ANOFM): {email_count:,} ({100*email_count/len(rows):.2f}%)")
    print(f"With website: {website_count:,} ({100*website_count/len(rows):.1f}%)")
    print(f"\nOutput: {OUTPUT}")


if __name__ == '__main__':
    main()
