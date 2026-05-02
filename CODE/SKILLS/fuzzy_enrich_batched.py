#!/usr/bin/env python3
"""
Batched Fuzzy Enrichment - Process large CSVs in chunks with progress saving.

Processes companies in batches, saving progress after each batch.
Can resume from last checkpoint if interrupted.

Usage:
    python3 fuzzy_enrich_batched.py                    # Run with defaults
    python3 fuzzy_enrich_batched.py --batch-size 5000  # Custom batch size
    python3 fuzzy_enrich_batched.py --resume           # Resume from checkpoint
    python3 fuzzy_enrich_batched.py --status           # Show progress
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import argparse
import csv
import json
import os
import re
import sqlite3
import time
from pathlib import Path
from collections import defaultdict

try:
    from rapidfuzz import fuzz, process
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False
    print("WARNING: rapidfuzz not available, fuzzy matching disabled")

from skills_common import to_ascii

# Configuration
INPUT_FILE = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/BUCHAREST_ILFOV_ESTABLISHED/buc_ilfov_with_phones.csv'
OUTPUT_FILE = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/BUCHAREST_ILFOV_ESTABLISHED/buc_ilfov_fuzzy_enriched.csv'
STATE_FILE = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/BUCHAREST_ILFOV_ESTABLISHED/fuzzy_state.json'
INDEX_PATH = '/opt/ACTIVE/OPENDATA/DATA/ENRICHMENT_INDEX/enrichment_index.db'

BATCH_SIZE = 10000
FUZZY_THRESHOLD = 85

# Legal forms to strip from names
LEGAL_FORMS = [
    'S.R.L.', 'SRL', 'S.A.', 'SA', 'S.C.', 'SC', 'P.F.A.', 'PFA',
    'I.I.', 'II', 'O.N.G.', 'ONG', 'IMPEX', 'GRUP', 'GROUP',
    'HOLDING', 'INTERNATIONAL', 'ROMANIA', 'LTD', 'LIMITED',
]


def normalize_company_name(name: str) -> str:
    """Normalize company name for matching."""
    if not name:
        return ''
    name = to_ascii(str(name)).upper().strip()
    for form in LEGAL_FORMS:
        name = re.sub(rf'\b{re.escape(form)}\b\.?', '', name)
    name = re.sub(r'[^\w\s]', ' ', name)
    name = ' '.join(name.split())
    return name.strip()


def normalize_cui(cui: str) -> str:
    """Normalize CUI to digits only."""
    if not cui:
        return ''
    digits = re.sub(r'\D', '', str(cui))
    return digits if len(digits) >= 4 else ''


def load_state():
    """Load processing state."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {'processed': 0, 'matched': 0, 'match_types': {}}


def save_state(state):
    """Save processing state."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


class BatchEnricher:
    """Batched fuzzy enrichment with progress saving."""

    def __init__(self, batch_size=BATCH_SIZE, fuzzy_threshold=FUZZY_THRESHOLD):
        self.batch_size = batch_size
        self.fuzzy_threshold = fuzzy_threshold
        self.conn = None
        self._name_index = None
        self._cui_cache = {}

    def connect(self):
        """Connect to the index database."""
        if not os.path.exists(INDEX_PATH):
            raise FileNotFoundError(f"Index not found: {INDEX_PATH}")
        self.conn = sqlite3.connect(INDEX_PATH)
        self.conn.row_factory = sqlite3.Row

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def _load_fuzzy_index(self):
        """Load normalized names for fuzzy matching."""
        if self._name_index is not None:
            return

        if not FUZZY_AVAILABLE:
            self._name_index = {}
            return

        print("  Loading fuzzy index...")
        c = self.conn.cursor()
        c.execute('''
            SELECT DISTINCT name_normalized
            FROM companies
            WHERE name_normalized != '' AND name_normalized IS NOT NULL
        ''')

        self._name_index = [row[0] for row in c.fetchall()]
        print(f"  Loaded {len(self._name_index):,} unique names for fuzzy matching")

    def _load_cui_cache(self, cuis: list):
        """Pre-load CUI lookups for a batch."""
        c = self.conn.cursor()
        placeholders = ','.join('?' * len(cuis))
        c.execute(f'''
            SELECT cui, name, email, phone, address, city, website, source
            FROM companies
            WHERE cui IN ({placeholders})
        ''', cuis)

        self._cui_cache = {}
        for row in c.fetchall():
            self._cui_cache[row['cui']] = dict(row)

    def lookup(self, cui: str = None, name: str = None) -> dict:
        """Look up a company using CUI or name."""
        c = self.conn.cursor()

        # 1. CUI exact match (from cache)
        if cui:
            cui_clean = normalize_cui(cui)
            if cui_clean and cui_clean in self._cui_cache:
                row = self._cui_cache[cui_clean]
                return {
                    'email': row['email'] or '',
                    'phone': row['phone'] or '',
                    'address': row['address'] or '',
                    'city': row['city'] or '',
                    'website': row['website'] or '',
                    'source': row['source'],
                    'match_type': 'cui',
                    'match_score': 100
                }

        # 2. Name exact match
        if name:
            name_norm = normalize_company_name(name)
            if name_norm and len(name_norm) >= 3:
                c.execute('''
                    SELECT email, phone, address, city, website, source
                    FROM companies
                    WHERE name_normalized = ?
                    ORDER BY priority ASC
                    LIMIT 1
                ''', (name_norm,))
                row = c.fetchone()
                if row:
                    return {
                        'email': row['email'] or '',
                        'phone': row['phone'] or '',
                        'address': row['address'] or '',
                        'city': row['city'] or '',
                        'website': row['website'] or '',
                        'source': row['source'],
                        'match_type': 'name_exact',
                        'match_score': 100
                    }

                # 3. Fuzzy name match
                if FUZZY_AVAILABLE and self._name_index:
                    results = process.extract(
                        name_norm,
                        self._name_index,
                        scorer=fuzz.token_sort_ratio,
                        limit=1
                    )
                    if results and results[0][1] >= self.fuzzy_threshold:
                        matched_name = results[0][0]
                        score = results[0][1]

                        c.execute('''
                            SELECT email, phone, address, city, website, source
                            FROM companies
                            WHERE name_normalized = ?
                            ORDER BY priority ASC
                            LIMIT 1
                        ''', (matched_name,))
                        row = c.fetchone()
                        if row:
                            return {
                                'email': row['email'] or '',
                                'phone': row['phone'] or '',
                                'address': row['address'] or '',
                                'city': row['city'] or '',
                                'website': row['website'] or '',
                                'source': row['source'],
                                'match_type': 'fuzzy',
                                'match_score': score
                            }

        return None

    def process_batch(self, rows: list, name_col: str, cui_col: str) -> list:
        """Process a batch of rows."""
        # Pre-load CUIs for batch
        cuis = [normalize_cui(r.get(cui_col, '')) for r in rows if r.get(cui_col)]
        cuis = [c for c in cuis if c]
        if cuis:
            self._load_cui_cache(cuis)

        results = []
        for row in rows:
            result = self.lookup(
                cui=row.get(cui_col),
                name=row.get(name_col)
            )

            if result:
                row['enrich_email'] = result.get('email', '')
                row['enrich_phone'] = result.get('phone', '')
                row['enrich_address'] = result.get('address', '')
                row['enrich_city'] = result.get('city', '')
                row['enrich_website'] = result.get('website', '')
                row['enrich_source'] = result.get('source', '')
                row['enrich_match_type'] = result.get('match_type', '')
                row['enrich_match_score'] = result.get('match_score', '')
            else:
                row['enrich_email'] = ''
                row['enrich_phone'] = ''
                row['enrich_address'] = ''
                row['enrich_city'] = ''
                row['enrich_website'] = ''
                row['enrich_source'] = ''
                row['enrich_match_type'] = ''
                row['enrich_match_score'] = ''

            results.append(row)

        return results

    def run(self, resume: bool = False):
        """Run batched enrichment."""
        print(f"Batched Fuzzy Enrichment")
        print(f"  Input: {INPUT_FILE}")
        print(f"  Output: {OUTPUT_FILE}")
        print(f"  Batch size: {self.batch_size:,}")
        print()

        self.connect()
        self._load_fuzzy_index()

        # Load input
        with open(INPUT_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            all_rows = list(reader)
            fieldnames = list(reader.fieldnames)

        # Add enrichment columns
        new_cols = ['enrich_email', 'enrich_phone', 'enrich_address',
                    'enrich_city', 'enrich_website', 'enrich_source',
                    'enrich_match_type', 'enrich_match_score']
        out_fieldnames = fieldnames + [c for c in new_cols if c not in fieldnames]

        total = len(all_rows)
        print(f"  Total rows: {total:,}")

        # Load state for resume
        state = load_state() if resume else {'processed': 0, 'matched': 0, 'match_types': defaultdict(int)}
        start_row = state['processed'] if resume else 0

        if resume and start_row > 0:
            print(f"  Resuming from row {start_row:,}")

        # Detect columns
        name_col = 'denumire'
        cui_col = 'cui'

        stats = defaultdict(int)
        stats['matched'] = state.get('matched', 0)
        for k, v in state.get('match_types', {}).items():
            stats[k] = v

        start_time = time.time()

        # Open output file (append if resuming, write if new)
        mode = 'a' if (resume and start_row > 0) else 'w'
        with open(OUTPUT_FILE, mode, newline='', encoding='utf-8') as f_out:
            writer = csv.DictWriter(f_out, fieldnames=out_fieldnames)

            if mode == 'w':
                writer.writeheader()

            # Process in batches
            for batch_start in range(start_row, total, self.batch_size):
                batch_end = min(batch_start + self.batch_size, total)
                batch = all_rows[batch_start:batch_end]

                # Process batch
                results = self.process_batch(batch, name_col, cui_col)

                # Write results
                for row in results:
                    writer.writerow(row)
                    if row.get('enrich_match_type'):
                        stats['matched'] += 1
                        stats[row['enrich_match_type']] += 1

                # Update state
                state['processed'] = batch_end
                state['matched'] = stats['matched']
                state['match_types'] = dict(stats)
                save_state(state)

                # Progress
                elapsed = time.time() - start_time
                rate = (batch_end - start_row) / elapsed if elapsed > 0 else 0
                remaining = (total - batch_end) / rate if rate > 0 else 0

                print(f"  {batch_end:,}/{total:,} ({100*batch_end/total:.1f}%) "
                      f"- {stats['matched']:,} matched "
                      f"- {rate:.0f} rows/sec "
                      f"- ETA: {remaining/60:.1f}m")

        self.close()

        # Final report
        print()
        print(f"Complete: {total:,} rows, {stats['matched']:,} matched ({100*stats['matched']/total:.1f}%)")
        print("Match types:")
        for key in ['cui', 'name_exact', 'fuzzy']:
            if stats.get(key):
                print(f"  {key}: {stats[key]:,}")
        print(f"\nOutput: {OUTPUT_FILE}")

        return OUTPUT_FILE


def show_status():
    """Show current processing status."""
    state = load_state()
    if not state or state.get('processed', 0) == 0:
        print("No processing started yet.")
        return

    # Get total rows
    with open(INPUT_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        total = sum(1 for _ in f) - 1  # minus header

    processed = state.get('processed', 0)
    matched = state.get('matched', 0)
    pct = 100 * processed / total if total > 0 else 0

    print(f"Fuzzy Enrichment Status")
    print(f"  Processed: {processed:,}/{total:,} ({pct:.1f}%)")
    print(f"  Matched: {matched:,} ({100*matched/processed:.1f}% of processed)" if processed > 0 else "")
    print(f"  Match types:")
    for k, v in state.get('match_types', {}).items():
        if k not in ['matched'] and v > 0:
            print(f"    {k}: {v:,}")


def main():
    parser = argparse.ArgumentParser(description='Batched Fuzzy Enrichment')
    parser.add_argument('--batch-size', type=int, default=BATCH_SIZE,
                        help=f'Batch size (default: {BATCH_SIZE})')
    parser.add_argument('--resume', action='store_true',
                        help='Resume from last checkpoint')
    parser.add_argument('--status', action='store_true',
                        help='Show processing status')
    parser.add_argument('--reset', action='store_true',
                        help='Reset processing state')

    args = parser.parse_args()

    if args.status:
        show_status()
        return 0

    if args.reset:
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
            print("State reset.")
        if os.path.exists(OUTPUT_FILE):
            os.remove(OUTPUT_FILE)
            print("Output file removed.")
        return 0

    enricher = BatchEnricher(batch_size=args.batch_size)
    enricher.run(resume=args.resume)

    return 0


if __name__ == '__main__':
    sys.exit(main())
