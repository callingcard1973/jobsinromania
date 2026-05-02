#!/usr/bin/env python3
"""
Fast Batch Fuzzy Enrichment - Uses rapidfuzz's optimized process functions.

Strategy:
1. CUI exact match (instant, ~17%)
2. Name exact match (instant, ~0.8%)
3. Batch fuzzy using rapidfuzz.process.extractOne (optimized C implementation)
   - Process in batches of 10,000 rows
   - Only for rows without CUI or exact name match
   - Uses score_cutoff for early termination

Expected runtime: 30-60 minutes for 425K rows
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import csv
import re
import sqlite3
import time
from collections import defaultdict
from skills_common import to_ascii

try:
    from rapidfuzz import fuzz, process
    FUZZY = True
except ImportError:
    FUZZY = False
    print("ERROR: rapidfuzz required. Install: pip install rapidfuzz")
    sys.exit(1)

INPUT = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/BUCHAREST_ILFOV_ESTABLISHED/buc_ilfov_with_phones.csv'
OUTPUT = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/BUCHAREST_ILFOV_ESTABLISHED/buc_ilfov_fuzzy_enriched.csv'
INDEX = '/opt/ACTIVE/OPENDATA/DATA/ENRICHMENT_INDEX/enrichment_index.db'
THRESHOLD = 85
BATCH_SIZE = 5000  # Process in batches

# Legal forms to strip from names
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
    print("Fast Batch Fuzzy Enrichment")
    print(f"Input: {INPUT}")
    print(f"Output: {OUTPUT}")
    print(f"Fuzzy threshold: {THRESHOLD}%")
    print(f"Batch size: {BATCH_SIZE:,}")

    # Load index into memory
    print("\n=== Phase 1: Loading index ===")
    start_load = time.time()

    conn = sqlite3.connect(INDEX)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Build CUI lookup
    cui_map = {}
    c.execute('SELECT cui, email, phone, address, city, website, source FROM companies WHERE cui IS NOT NULL AND cui != ""')
    for row in c.fetchall():
        cui_map[row['cui']] = dict(row)
    print(f"  Loaded {len(cui_map):,} CUI entries")

    # Build name lookup (exact match) and list for fuzzy
    name_exact = {}
    name_list = []  # For fuzzy matching
    name_to_data = {}

    c.execute('SELECT name_normalized, email, phone, address, city, website, source FROM companies WHERE name_normalized IS NOT NULL AND name_normalized != ""')
    for row in c.fetchall():
        name_norm = row['name_normalized']
        data = dict(row)
        name_exact[name_norm] = data
        if name_norm not in name_to_data:  # Avoid duplicates
            name_list.append(name_norm)
            name_to_data[name_norm] = data

    conn.close()

    print(f"  Loaded {len(name_exact):,} name entries")
    print(f"  Unique names for fuzzy: {len(name_list):,}")
    print(f"  Load time: {time.time() - start_load:.1f}s")

    # Load input file
    print("\n=== Phase 2: Loading input ===")
    with open(INPUT, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames)

    print(f"  Loaded {len(rows):,} rows")

    # Add output columns
    new_cols = ['enrich_email', 'enrich_phone', 'enrich_address',
                'enrich_city', 'enrich_website', 'enrich_source',
                'enrich_match_type', 'enrich_match_score']
    out_fields = fieldnames + [c for c in new_cols if c not in fieldnames]

    # Phase 3: CUI + Exact name matching (fast)
    print("\n=== Phase 3: CUI + Exact name matching ===")
    start_phase3 = time.time()
    stats = defaultdict(int)
    unmatched_indices = []

    for i, row in enumerate(rows):
        result = None

        # CUI match
        cui = normalize_cui(row.get('cui', ''))
        if cui and cui in cui_map:
            result = cui_map[cui].copy()
            result['match_type'] = 'cui'
            result['match_score'] = 100

        # Exact name match
        if not result:
            name = normalize_name(row.get('denumire', ''))
            if name and name in name_exact:
                result = name_exact[name].copy()
                result['match_type'] = 'name_exact'
                result['match_score'] = 100
            elif name and len(name) >= 3:
                # Save for fuzzy matching
                unmatched_indices.append((i, name))

        # Apply result
        if result:
            row['enrich_email'] = result.get('email', '') or ''
            row['enrich_phone'] = result.get('phone', '') or ''
            row['enrich_address'] = result.get('address', '') or ''
            row['enrich_city'] = result.get('city', '') or ''
            row['enrich_website'] = result.get('website', '') or ''
            row['enrich_source'] = result.get('source', '') or ''
            row['enrich_match_type'] = result.get('match_type', '')
            row['enrich_match_score'] = result.get('match_score', '')
            stats['matched'] += 1
            stats[result['match_type']] += 1
        else:
            for col in new_cols:
                row[col] = ''

    print(f"  CUI matches: {stats['cui']:,}")
    print(f"  Name exact: {stats['name_exact']:,}")
    print(f"  Unmatched (for fuzzy): {len(unmatched_indices):,}")
    print(f"  Time: {time.time() - start_phase3:.1f}s")

    # Phase 4: Fuzzy matching with rapidfuzz.process.extractOne
    print(f"\n=== Phase 4: Fuzzy matching ({len(unmatched_indices):,} rows) ===")
    start_phase4 = time.time()

    # Process in batches
    total_batches = (len(unmatched_indices) + BATCH_SIZE - 1) // BATCH_SIZE
    fuzzy_matches = 0

    for batch_num in range(total_batches):
        batch_start = batch_num * BATCH_SIZE
        batch_end = min(batch_start + BATCH_SIZE, len(unmatched_indices))
        batch = unmatched_indices[batch_start:batch_end]

        # Use rapidfuzz.process.extractOne for each query
        for idx, query_name in batch:
            # extractOne with score_cutoff for early termination
            match = process.extractOne(
                query_name,
                name_list,
                scorer=fuzz.token_sort_ratio,
                score_cutoff=THRESHOLD
            )

            if match:
                matched_name, score, _ = match
                result = name_to_data[matched_name]
                rows[idx]['enrich_email'] = result.get('email', '') or ''
                rows[idx]['enrich_phone'] = result.get('phone', '') or ''
                rows[idx]['enrich_address'] = result.get('address', '') or ''
                rows[idx]['enrich_city'] = result.get('city', '') or ''
                rows[idx]['enrich_website'] = result.get('website', '') or ''
                rows[idx]['enrich_source'] = result.get('source', '') or ''
                rows[idx]['enrich_match_type'] = 'fuzzy'
                rows[idx]['enrich_match_score'] = int(score)
                fuzzy_matches += 1
                stats['matched'] += 1
                stats['fuzzy'] += 1

        # Progress
        elapsed = time.time() - start_phase4
        processed = batch_end
        rate = processed / elapsed if elapsed > 0 else 0
        remaining = (len(unmatched_indices) - processed) / rate if rate > 0 else 0
        print(f"  Batch {batch_num+1}/{total_batches}: {processed:,}/{len(unmatched_indices):,} - {fuzzy_matches:,} fuzzy matches - {rate:.1f}/sec - ETA: {remaining/60:.1f}m")

    print(f"  Fuzzy matches: {fuzzy_matches:,}")
    print(f"  Time: {time.time() - start_phase4:.1f}s")

    # Save output
    print(f"\n=== Phase 5: Saving output ===")
    with open(OUTPUT, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(rows)

    # Summary
    total_time = time.time() - start_load
    print(f"\n{'='*60}")
    print(f"COMPLETE: {len(rows):,} rows in {total_time/60:.1f} minutes")
    print(f"{'='*60}")
    print(f"Matched: {stats['matched']:,} ({100*stats['matched']/len(rows):.1f}%)")
    print(f"  CUI exact: {stats['cui']:,}")
    print(f"  Name exact: {stats['name_exact']:,}")
    print(f"  Fuzzy: {stats['fuzzy']:,}")
    print(f"\nOutput: {OUTPUT}")


if __name__ == '__main__':
    main()
