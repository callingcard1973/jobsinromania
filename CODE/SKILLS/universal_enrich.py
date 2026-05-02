#!/usr/bin/env python3
"""
Universal Enrichment Script - Enrich any CSV with contact data from unified index.

Uses SQLite index built by build_enrichment_index.py for fast lookups.

Match Priority:
1. CUI (exact) - highest confidence
2. Phone (exact, normalized)
3. Email domain (exact)
4. Company name (exact normalized)
5. Company name (fuzzy, 85%+ threshold)

Usage:
    # Enrich CSV file
    python3 universal_enrich.py /path/to/input.csv

    # Specify columns
    python3 universal_enrich.py input.csv --name-col company --cui-col tax_id

    # Test single company lookup
    python3 universal_enrich.py --test "KFC Romania"

    # Lookup by CUI
    python3 universal_enrich.py --cui 36067923

    # Dry run (show what would be enriched)
    python3 universal_enrich.py input.csv --dry-run

    # Auto-detect columns
    python3 universal_enrich.py input.csv --auto
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import argparse
import csv
import os
import re
import sqlite3
import unicodedata
from collections import defaultdict
from pathlib import Path

try:
    from rapidfuzz import fuzz, process
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False

from skills_common import to_ascii

# === CONFIGURATION ===

INDEX_PATH = '/opt/ACTIVE/OPENDATA/DATA/ENRICHMENT_INDEX/enrichment_index.db'

# Common column name patterns
NAME_COLUMNS = ['company_name', 'company', 'nume_firma', 'employer', 'firma', 'name', 'denumire']
CUI_COLUMNS = ['cui', 'cif', 'tax_id', 'employer_tax_code', 'company_org_number', 'org_number']
PHONE_COLUMNS = ['phone', 'phone_1', 'telefon', 'phone1', 'tel']
EMAIL_COLUMNS = ['email', 'email_1', 'email1', 'e-mail', 'contact_email']

# === NORMALIZATION FUNCTIONS ===

def normalize_phone(phone: str) -> str:
    """Normalize phone to digits only."""
    if not phone:
        return ''
    digits = re.sub(r'\D', '', str(phone))
    if digits.startswith('40') and len(digits) > 10:
        digits = digits[2:]
    if digits.startswith('0') and len(digits) == 10:
        digits = digits[1:]
    return digits if len(digits) >= 8 else ''


def normalize_cui(cui: str) -> str:
    """Normalize CUI to digits only."""
    if not cui:
        return ''
    digits = re.sub(r'\D', '', str(cui))
    return digits if len(digits) >= 4 else ''


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


def extract_domain(text: str) -> str:
    """Extract domain from URL or email."""
    if not text:
        return ''
    text = str(text).lower().strip()
    if '@' in text:
        return text.split('@')[-1].split('/')[0]
    text = re.sub(r'^https?://', '', text)
    text = re.sub(r'^www\.', '', text)
    return text.split('/')[0].split('?')[0]


# === ENRICHER CLASS ===

class UniversalEnricher:
    """Enriches CSV files using unified SQLite index."""

    def __init__(self, index_path: str = INDEX_PATH, fuzzy_threshold: int = 85):
        self.index_path = index_path
        self.fuzzy_threshold = fuzzy_threshold
        self.conn = None
        self._name_index = None  # For fuzzy matching

    def connect(self):
        """Connect to the index database."""
        if not os.path.exists(self.index_path):
            raise FileNotFoundError(
                f"Index not found: {self.index_path}\n"
                f"Run: python3 /opt/ACTIVE/INFRA/SKILLS/build_enrichment_index.py"
            )
        self.conn = sqlite3.connect(self.index_path)
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
            SELECT DISTINCT name_normalized, MIN(id) as id
            FROM companies
            WHERE name_normalized != ''
            GROUP BY name_normalized
        ''')

        self._name_index = {}
        for row in c.fetchall():
            self._name_index[row['name_normalized']] = row['id']

        print(f"  Loaded {len(self._name_index):,} unique names for fuzzy matching")

    def lookup(self, cui: str = None, name: str = None, phone: str = None,
               email: str = None, use_fuzzy: bool = True) -> dict:
        """
        Look up a company using multiple fields.

        Returns dict with: email, phone, address, city, website, match_type, match_score
        """
        c = self.conn.cursor()

        # 1. CUI exact match (highest priority)
        if cui:
            cui_clean = normalize_cui(cui)
            if cui_clean:
                c.execute('''
                    SELECT name, email, phone, address, city, website, source
                    FROM companies
                    WHERE cui = ?
                    ORDER BY priority ASC
                    LIMIT 1
                ''', (cui_clean,))
                row = c.fetchone()
                if row:
                    return {
                        'name': row['name'],
                        'email': row['email'] or '',
                        'phone': row['phone'] or '',
                        'address': row['address'] or '',
                        'city': row['city'] or '',
                        'website': row['website'] or '',
                        'source': row['source'],
                        'match_type': 'cui',
                        'match_score': 100
                    }

        # 2. Phone exact match
        if phone:
            phone_norm = normalize_phone(phone)
            if phone_norm:
                c.execute('''
                    SELECT name, cui, email, phone, address, city, website, source
                    FROM companies
                    WHERE phone_normalized = ?
                    ORDER BY priority ASC
                    LIMIT 1
                ''', (phone_norm,))
                row = c.fetchone()
                if row:
                    return {
                        'name': row['name'],
                        'cui': row['cui'] or '',
                        'email': row['email'] or '',
                        'phone': row['phone'] or '',
                        'address': row['address'] or '',
                        'city': row['city'] or '',
                        'website': row['website'] or '',
                        'source': row['source'],
                        'match_type': 'phone',
                        'match_score': 100
                    }

        # 3. Email domain match
        if email and '@' in email:
            domain = extract_domain(email)
            if domain and '.' in domain:
                c.execute('''
                    SELECT name, cui, email, phone, address, city, website, source
                    FROM companies
                    WHERE website_domain = ?
                    ORDER BY priority ASC
                    LIMIT 1
                ''', (domain,))
                row = c.fetchone()
                if row:
                    return {
                        'name': row['name'],
                        'cui': row['cui'] or '',
                        'email': row['email'] or '',
                        'phone': row['phone'] or '',
                        'address': row['address'] or '',
                        'city': row['city'] or '',
                        'website': row['website'] or '',
                        'source': row['source'],
                        'match_type': 'email_domain',
                        'match_score': 95
                    }

        # 4. Name exact match
        if name:
            name_norm = normalize_company_name(name)
            if name_norm and len(name_norm) >= 3:
                c.execute('''
                    SELECT name, cui, email, phone, address, city, website, source
                    FROM companies
                    WHERE name_normalized = ?
                    ORDER BY priority ASC
                    LIMIT 1
                ''', (name_norm,))
                row = c.fetchone()
                if row:
                    return {
                        'name': row['name'],
                        'cui': row['cui'] or '',
                        'email': row['email'] or '',
                        'phone': row['phone'] or '',
                        'address': row['address'] or '',
                        'city': row['city'] or '',
                        'website': row['website'] or '',
                        'source': row['source'],
                        'match_type': 'name_exact',
                        'match_score': 100
                    }

                # 5. Fuzzy name match
                if use_fuzzy and FUZZY_AVAILABLE:
                    self._load_fuzzy_index()
                    if self._name_index:
                        results = process.extract(
                            name_norm,
                            list(self._name_index.keys()),
                            scorer=fuzz.token_sort_ratio,
                            limit=1
                        )
                        if results and results[0][1] >= self.fuzzy_threshold:
                            matched_name = results[0][0]
                            score = results[0][1]

                            c.execute('''
                                SELECT name, cui, email, phone, address, city, website, source
                                FROM companies
                                WHERE name_normalized = ?
                                ORDER BY priority ASC
                                LIMIT 1
                            ''', (matched_name,))
                            row = c.fetchone()
                            if row:
                                return {
                                    'name': row['name'],
                                    'cui': row['cui'] or '',
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

    def detect_columns(self, fieldnames: list) -> dict:
        """Auto-detect column names from common patterns."""
        detected = {}
        fieldnames_lower = [f.lower() for f in fieldnames]

        for name_col in NAME_COLUMNS:
            if name_col.lower() in fieldnames_lower:
                idx = fieldnames_lower.index(name_col.lower())
                detected['name'] = fieldnames[idx]
                break

        for cui_col in CUI_COLUMNS:
            if cui_col.lower() in fieldnames_lower:
                idx = fieldnames_lower.index(cui_col.lower())
                detected['cui'] = fieldnames[idx]
                break

        for phone_col in PHONE_COLUMNS:
            if phone_col.lower() in fieldnames_lower:
                idx = fieldnames_lower.index(phone_col.lower())
                detected['phone'] = fieldnames[idx]
                break

        for email_col in EMAIL_COLUMNS:
            if email_col.lower() in fieldnames_lower:
                idx = fieldnames_lower.index(email_col.lower())
                detected['email'] = fieldnames[idx]
                break

        return detected

    def enrich_csv(self, input_path: str, output_path: str = None,
                   name_col: str = None, cui_col: str = None,
                   phone_col: str = None, email_col: str = None,
                   auto_detect: bool = True, dry_run: bool = False,
                   use_fuzzy: bool = True):
        """
        Enrich a CSV file with contact data from the index.

        Returns tuple: (output_path, stats_dict)
        """
        input_path = Path(input_path)
        if output_path:
            output_path = Path(output_path)
        else:
            output_path = input_path.with_suffix('.enriched.csv')

        print(f"Enriching: {input_path}")
        self.connect()

        # Read input to detect columns
        with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames)

            # Auto-detect columns if needed
            detected = self.detect_columns(fieldnames) if auto_detect else {}
            name_col = name_col or detected.get('name')
            cui_col = cui_col or detected.get('cui')
            phone_col = phone_col or detected.get('phone')
            email_col = email_col or detected.get('email')

            print(f"  Columns: name={name_col}, cui={cui_col}, phone={phone_col}, email={email_col}")

            if not name_col and not cui_col:
                print("  WARNING: No name or CUI column found. Cannot enrich.")
                return None, {}

        # Output columns
        new_cols = [
            'enrich_email', 'enrich_phone', 'enrich_address',
            'enrich_city', 'enrich_website', 'enrich_source',
            'enrich_match_type', 'enrich_match_score'
        ]
        out_fieldnames = fieldnames + [c for c in new_cols if c not in fieldnames]

        # Stats
        stats = defaultdict(int)
        stats['total'] = 0

        # Process
        with open(input_path, 'r', encoding='utf-8', errors='ignore') as f_in:
            reader = csv.DictReader(f_in)

            if dry_run:
                print("\nDRY RUN - showing first 10 matches:\n")
                for row in reader:
                    stats['total'] += 1
                    if stats['total'] > 10:
                        continue

                    result = self.lookup(
                        cui=row.get(cui_col) if cui_col else None,
                        name=row.get(name_col) if name_col else None,
                        phone=row.get(phone_col) if phone_col else None,
                        email=row.get(email_col) if email_col else None,
                        use_fuzzy=use_fuzzy
                    )

                    if result:
                        stats['matched'] += 1
                        stats[result['match_type']] += 1
                        company = row.get(name_col, '') or row.get(cui_col, '')
                        print(f"  {company[:40]:40} -> {result['match_type']} ({result['match_score']}%)")
                        if result.get('email'):
                            print(f"    Email: {result['email']}")
                        if result.get('phone'):
                            print(f"    Phone: {result['phone']}")

                # Count remaining
                for row in reader:
                    stats['total'] += 1

                print(f"\nTotal rows: {stats['total']:,}")
                print("Run without --dry-run to enrich.")
                self.close()
                return None, dict(stats)

            # Actual enrichment
            with open(output_path, 'w', newline='', encoding='utf-8') as f_out:
                writer = csv.DictWriter(f_out, fieldnames=out_fieldnames)
                writer.writeheader()

                for row in reader:
                    stats['total'] += 1

                    result = self.lookup(
                        cui=row.get(cui_col) if cui_col else None,
                        name=row.get(name_col) if name_col else None,
                        phone=row.get(phone_col) if phone_col else None,
                        email=row.get(email_col) if email_col else None,
                        use_fuzzy=use_fuzzy
                    )

                    if result:
                        stats['matched'] += 1
                        stats[result['match_type']] += 1

                        # Only add if not already present
                        row['enrich_email'] = result.get('email', '')
                        row['enrich_phone'] = result.get('phone', '')
                        row['enrich_address'] = result.get('address', '')
                        row['enrich_city'] = result.get('city', '')
                        row['enrich_website'] = result.get('website', '')
                        row['enrich_source'] = result.get('source', '')
                        row['enrich_match_type'] = result.get('match_type', '')
                        row['enrich_match_score'] = result.get('match_score', '')
                    else:
                        for col in new_cols:
                            row[col] = ''

                    writer.writerow(row)

                    if stats['total'] % 10000 == 0:
                        print(f"  Processed {stats['total']:,} ({stats['matched']:,} matched)...")

        self.close()

        # Report
        rate = 100 * stats['matched'] / stats['total'] if stats['total'] else 0
        print(f"\nComplete: {stats['total']:,} rows, {stats['matched']:,} matched ({rate:.1f}%)")
        print("Match types:")
        for key in ['cui', 'phone', 'email_domain', 'name_exact', 'fuzzy']:
            if stats[key]:
                print(f"  {key}: {stats[key]:,}")
        print(f"\nOutput: {output_path}")

        return str(output_path), dict(stats)


def test_lookup(name: str, enricher: UniversalEnricher):
    """Test lookup for a company name."""
    print(f"Testing lookup: {name}")
    print(f"Normalized: {normalize_company_name(name)}")
    print("=" * 60)

    result = enricher.lookup(name=name)
    if result:
        print(f"Match type: {result['match_type']} ({result['match_score']}%)")
        print(f"Source: {result['source']}")
        print()
        for key in ['name', 'cui', 'email', 'phone', 'address', 'city', 'website']:
            if result.get(key):
                print(f"  {key}: {result[key]}")
    else:
        print("No match found")


def test_cui(cui: str, enricher: UniversalEnricher):
    """Test lookup by CUI."""
    print(f"Testing CUI: {cui}")
    print("=" * 60)

    result = enricher.lookup(cui=cui)
    if result:
        print(f"Match type: {result['match_type']} ({result['match_score']}%)")
        print(f"Source: {result['source']}")
        print()
        for key in ['name', 'email', 'phone', 'address', 'city', 'website']:
            if result.get(key):
                print(f"  {key}: {result[key]}")
    else:
        print("No match found")


def main():
    parser = argparse.ArgumentParser(description='Universal CSV Enrichment')
    parser.add_argument('input', nargs='?', help='Input CSV file to enrich')
    parser.add_argument('-o', '--output', help='Output CSV path')
    parser.add_argument('--name-col', help='Company name column')
    parser.add_argument('--cui-col', help='CUI column')
    parser.add_argument('--phone-col', help='Phone column')
    parser.add_argument('--email-col', help='Email column')
    parser.add_argument('--auto', action='store_true', help='Auto-detect columns')
    parser.add_argument('--dry-run', action='store_true', help='Show preview without writing')
    parser.add_argument('--no-fuzzy', action='store_true', help='Disable fuzzy matching')
    parser.add_argument('--test', metavar='NAME', help='Test lookup for company name')
    parser.add_argument('--cui', metavar='CUI', help='Test lookup by CUI')
    parser.add_argument('--threshold', type=int, default=85, help='Fuzzy match threshold (default: 85)')

    args = parser.parse_args()

    enricher = UniversalEnricher(fuzzy_threshold=args.threshold)

    if args.test:
        enricher.connect()
        test_lookup(args.test, enricher)
        enricher.close()
    elif args.cui:
        enricher.connect()
        test_cui(args.cui, enricher)
        enricher.close()
    elif args.input:
        enricher.enrich_csv(
            args.input,
            output_path=args.output,
            name_col=args.name_col,
            cui_col=args.cui_col,
            phone_col=args.phone_col,
            email_col=args.email_col,
            auto_detect=args.auto or not (args.name_col or args.cui_col),
            dry_run=args.dry_run,
            use_fuzzy=not args.no_fuzzy
        )
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
