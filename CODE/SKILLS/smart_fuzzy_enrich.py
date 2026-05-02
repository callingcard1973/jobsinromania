#!/usr/bin/env python3
"""
Smart Fuzzy Enrichment - Optimized fuzzy matching using prefix buckets.

Instead of comparing each name against 758K names, we:
1. First try CUI exact match
2. Then try name exact match
3. Then fuzzy match only against names with same first 3 characters

This reduces comparisons from 758K to ~100-1000 per company.
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
    from rapidfuzz import fuzz
    FUZZY = True
except ImportError:
    FUZZY = False
    print("WARNING: rapidfuzz not available")

INPUT = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/BUCHAREST_ILFOV_ESTABLISHED/buc_ilfov_with_phones.csv'
OUTPUT = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/BUCHAREST_ILFOV_ESTABLISHED/buc_ilfov_fuzzy_enriched.csv'
INDEX = '/opt/ACTIVE/OPENDATA/DATA/ENRICHMENT_INDEX/enrichment_index.db'
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

def get_prefix(name, length=3):
    """Get first N chars for bucketing."""
    return name[:length] if len(name) >= length else name

print("Smart Fuzzy Enrichment (CUI + exact + prefix-bucketed fuzzy)")
print(f"Input: {INPUT}")
print(f"Output: {OUTPUT}")
print(f"Fuzzy threshold: {THRESHOLD}%")

# Load all companies from index into memory
print("\nLoading index into memory...")
conn = sqlite3.connect(INDEX)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Build CUI lookup
cui_map = {}
c.execute('SELECT cui, email, phone, address, city, website, source FROM companies WHERE cui IS NOT NULL AND cui != ""')
for row in c.fetchall():
    cui_map[row['cui']] = dict(row)
print(f"  Loaded {len(cui_map):,} CUI entries")

# Build name lookup (exact and prefix buckets)
name_exact = {}
name_buckets = defaultdict(list)  # prefix -> [(normalized_name, data), ...]

c.execute('SELECT name_normalized, email, phone, address, city, website, source FROM companies WHERE name_normalized IS NOT NULL AND name_normalized != ""')
for row in c.fetchall():
    name_norm = row['name_normalized']
    data = dict(row)
    name_exact[name_norm] = data

    # Add to prefix bucket
    prefix = get_prefix(name_norm)
    if prefix:
        name_buckets[prefix].append((name_norm, data))

print(f"  Loaded {len(name_exact):,} name entries")
print(f"  Created {len(name_buckets):,} prefix buckets")

# Calculate average bucket size
avg_bucket = sum(len(v) for v in name_buckets.values()) / len(name_buckets) if name_buckets else 0
print(f"  Average bucket size: {avg_bucket:.0f} names")

conn.close()

# Load input
print("\nLoading input file...")
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

# Process
print("\nProcessing...")
stats = defaultdict(int)
start = time.time()
fuzzy_checks = 0

for i, row in enumerate(rows):
    result = None

    # 1. Try CUI match first
    cui = normalize_cui(row.get('cui', ''))
    if cui and cui in cui_map:
        result = cui_map[cui].copy()
        result['match_type'] = 'cui'
        result['match_score'] = 100

    # 2. Try exact name match
    if not result:
        name = normalize_name(row.get('denumire', ''))
        if name:
            if name in name_exact:
                result = name_exact[name].copy()
                result['match_type'] = 'name_exact'
                result['match_score'] = 100
            elif FUZZY and len(name) >= 3:
                # 3. Fuzzy match against prefix bucket
                prefix = get_prefix(name)
                if prefix in name_buckets:
                    bucket = name_buckets[prefix]
                    best_match = None
                    best_score = 0

                    for cand_name, cand_data in bucket:
                        fuzzy_checks += 1
                        score = fuzz.token_sort_ratio(name, cand_name)
                        if score >= THRESHOLD and score > best_score:
                            best_score = score
                            best_match = cand_data

                    if best_match:
                        result = best_match.copy()
                        result['match_type'] = 'fuzzy'
                        result['match_score'] = best_score

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

    if (i + 1) % 25000 == 0:
        elapsed = time.time() - start
        rate = (i + 1) / elapsed
        remaining = (len(rows) - i - 1) / rate
        print(f"  {i+1:,}/{len(rows):,} - {stats['matched']:,} matched ({stats.get('fuzzy', 0):,} fuzzy) - {rate:.0f}/sec - ETA: {remaining/60:.1f}m")

# Save
print(f"\nSaving {len(rows):,} rows...")
with open(OUTPUT, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=out_fields)
    writer.writeheader()
    writer.writerows(rows)

elapsed = time.time() - start
print(f"\nComplete: {len(rows):,} rows in {elapsed/60:.1f} minutes")
print(f"Matched: {stats['matched']:,} ({100*stats['matched']/len(rows):.1f}%)")
print(f"  CUI: {stats['cui']:,}")
print(f"  Name exact: {stats['name_exact']:,}")
print(f"  Fuzzy: {stats['fuzzy']:,}")
print(f"Fuzzy comparisons: {fuzzy_checks:,}")
print(f"\nOutput: {OUTPUT}")
