#!/usr/bin/env python3
"""
Trigram-Based Fuzzy Enrichment - Fast fuzzy matching using trigram pre-filtering.

Strategy:
1. CUI exact match (instant)
2. Name exact match (instant)
3. Trigram-filtered fuzzy match (fast: ~100x speedup vs brute force)

Trigram approach is better than prefix buckets because:
- "GLOBAL LIMEX" vs "LIMEX GLOBAL" share many trigrams (GLO, LOB, OBA, BAL, LIM, IME, MEX)
- Prefix buckets would miss this since prefixes differ ("GLO" vs "LIM")
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import csv
import re
import sqlite3
import time
from collections import defaultdict
from typing import Dict, List, Tuple
from skills_common import to_ascii

try:
    from rapidfuzz import fuzz
    FUZZY = True
except ImportError:
    FUZZY = False
    print("ERROR: rapidfuzz required. Install: pip install rapidfuzz")
    sys.exit(1)

INPUT = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/BUCHAREST_ILFOV_ESTABLISHED/buc_ilfov_with_phones.csv'
OUTPUT = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/BUCHAREST_ILFOV_ESTABLISHED/buc_ilfov_trigram_enriched.csv'
INDEX = '/opt/ACTIVE/OPENDATA/DATA/ENRICHMENT_INDEX/enrichment_index.db'
THRESHOLD = 85
MAX_CANDIDATES = 3000  # Max names to fuzzy check per query


class TrigramIndex:
    """
    Fast fuzzy search using trigram (3-character substring) pre-filtering.

    Instead of comparing query against 758K names (slow), we:
    1. Extract trigrams from query: "LIMEX" -> {LIM, IME, MEX}
    2. Find names sharing >=N trigrams (candidates)
    3. Only run expensive fuzzy match on candidates (~1-3K instead of 758K)

    Performance: ~50ms per lookup vs ~5s without filtering
    """

    def __init__(self):
        self.trigram_to_names: Dict[str, set] = defaultdict(set)
        self.name_to_data: Dict[str, dict] = {}
        self.all_names: set = set()

    @staticmethod
    def extract_trigrams(text: str) -> set:
        """Extract all 3-character substrings from text."""
        if not text or len(text) < 3:
            return set()
        text = text.upper()
        return {text[i:i+3] for i in range(len(text) - 2)}

    def add_name(self, name: str, data: dict):
        """Add a name and its data to the index."""
        if not name or len(name) < 3:
            return
        name_upper = name.upper()
        self.all_names.add(name)
        self.name_to_data[name] = data
        for trigram in self.extract_trigrams(name_upper):
            self.trigram_to_names[trigram].add(name)

    def get_candidates(self, query: str, max_candidates: int = MAX_CANDIDATES) -> List[Tuple[str, dict]]:
        """
        Get candidate names that share enough trigrams with query.
        Uses adaptive filtering: requires more shared trigrams for longer queries.
        """
        if not query or len(query) < 3:
            return []

        query_trigrams = self.extract_trigrams(query.upper())
        if not query_trigrams:
            return []

        # Adaptive threshold based on query length
        num_query_trigrams = len(query_trigrams)
        if num_query_trigrams <= 3:
            min_required = 1
        elif num_query_trigrams <= 8:
            min_required = max(2, num_query_trigrams // 3)
        else:
            min_required = max(3, num_query_trigrams // 3)

        # Count how many query trigrams each name shares
        name_scores: Dict[str, int] = defaultdict(int)
        for trigram in query_trigrams:
            for name in self.trigram_to_names.get(trigram, set()):
                name_scores[name] += 1

        # Filter to names with enough shared trigrams
        candidates = [
            (name, score) for name, score in name_scores.items()
            if score >= min_required
        ]

        # Sort by score (most shared trigrams first) and limit
        candidates.sort(key=lambda x: x[1], reverse=True)

        return [(name, self.name_to_data[name]) for name, _ in candidates[:max_candidates]]

    def stats(self) -> dict:
        """Return index statistics."""
        if not self.trigram_to_names:
            return {"names": 0, "trigrams": 0, "avg_names_per_trigram": 0}
        avg_names = sum(len(names) for names in self.trigram_to_names.values()) / len(self.trigram_to_names)
        return {
            "names": len(self.all_names),
            "trigrams": len(self.trigram_to_names),
            "avg_names_per_trigram": round(avg_names, 1)
        }


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
    print("Trigram-Based Fuzzy Enrichment")
    print(f"Input: {INPUT}")
    print(f"Output: {OUTPUT}")
    print(f"Fuzzy threshold: {THRESHOLD}%")
    print(f"Max candidates per query: {MAX_CANDIDATES:,}")

    # Load index into memory
    print("\nLoading index into memory...")
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

    # Build name lookup (exact) and trigram index
    name_exact = {}
    trigram_idx = TrigramIndex()

    c.execute('SELECT name_normalized, email, phone, address, city, website, source FROM companies WHERE name_normalized IS NOT NULL AND name_normalized != ""')
    for row in c.fetchall():
        name_norm = row['name_normalized']
        data = dict(row)
        name_exact[name_norm] = data
        trigram_idx.add_name(name_norm, data)

    conn.close()

    idx_stats = trigram_idx.stats()
    print(f"  Loaded {len(name_exact):,} name entries")
    print(f"  Trigram index: {idx_stats['trigrams']:,} trigrams, {idx_stats['avg_names_per_trigram']:.0f} avg names/trigram")
    print(f"  Load time: {time.time() - start_load:.1f}s")

    # Load input file
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

    # Process rows
    print("\nProcessing with trigram-filtered fuzzy matching...")
    stats = defaultdict(int)
    start = time.time()
    fuzzy_checks = 0
    candidates_checked = 0

    for i, row in enumerate(rows):
        result = None

        # 1. Try CUI match first (instant)
        cui = normalize_cui(row.get('cui', ''))
        if cui and cui in cui_map:
            result = cui_map[cui].copy()
            result['match_type'] = 'cui'
            result['match_score'] = 100

        # 2. Try exact name match (instant)
        if not result:
            name = normalize_name(row.get('denumire', ''))
            if name:
                if name in name_exact:
                    result = name_exact[name].copy()
                    result['match_type'] = 'name_exact'
                    result['match_score'] = 100
                elif len(name) >= 3:
                    # 3. Trigram-filtered fuzzy match
                    candidates = trigram_idx.get_candidates(name)
                    candidates_checked += len(candidates)

                    if candidates:
                        best_match = None
                        best_score = 0

                        for cand_name, cand_data in candidates:
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

        # Progress
        if (i + 1) % 10000 == 0:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed
            remaining = (len(rows) - i - 1) / rate
            avg_cand = candidates_checked / max(1, stats.get('fuzzy', 0) + (len(rows) - stats['matched'] - stats.get('cui', 0) - stats.get('name_exact', 0)))
            print(f"  {i+1:,}/{len(rows):,} - {stats['matched']:,} matched ({stats.get('fuzzy', 0):,} fuzzy) - {rate:.0f}/sec - avg {avg_cand:.0f} candidates - ETA: {remaining/60:.1f}m")

    # Save output
    print(f"\nSaving {len(rows):,} rows...")
    with open(OUTPUT, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(rows)

    # Summary
    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"COMPLETE: {len(rows):,} rows in {elapsed/60:.1f} minutes")
    print(f"{'='*60}")
    print(f"Matched: {stats['matched']:,} ({100*stats['matched']/len(rows):.1f}%)")
    print(f"  CUI exact: {stats['cui']:,}")
    print(f"  Name exact: {stats['name_exact']:,}")
    print(f"  Fuzzy: {stats['fuzzy']:,}")
    print(f"")
    print(f"Fuzzy checks: {fuzzy_checks:,}")
    print(f"Avg candidates per unmatched: {candidates_checked / max(1, len(rows) - stats['cui'] - stats['name_exact']):.0f}")
    print(f"Speedup vs brute force: ~{(len(rows) - stats['cui'] - stats['name_exact']) * len(name_exact) / max(1, fuzzy_checks):.0f}x")
    print(f"\nOutput: {OUTPUT}")


if __name__ == '__main__':
    main()
