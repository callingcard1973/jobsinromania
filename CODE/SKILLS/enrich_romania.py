#!/usr/bin/env python3
"""
Romania Company Enrichment

Adds email and phone data to Romanian company CSVs by matching against internal databases.

Usage:
    python3 enrich_romania.py input.csv --output enriched.csv
    python3 enrich_romania.py input.csv --fuzzy --threshold 85
    python3 enrich_romania.py input.csv --stats
    python3 enrich_romania.py input.csv --anaf  # Also query ANAF API (slower)

Sources (in priority order):
    1. ANAF API (phone, address) - if --anaf flag
    2. ANOFM (email, phone) - job postings
    3. MASTER_ALL (email, phone, website) - aggregated contacts
    4. DSVSA (phone, email) - food industry
    5. IAJOB (email, phone) - job portal

Output columns added:
    - enriched_email: Best email found
    - enriched_phone: Best phone found (normalized +40)
    - enriched_address: Address if found
    - enriched_source: Where contact came from
    - enriched_match_type: How matched (cui/name/fuzzy)
"""

import sys
import csv
import re
import argparse
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from collections import defaultdict

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii

# ============================================================
# TRIGRAM INDEX FOR FAST FUZZY MATCHING
# ============================================================

class TrigramIndex:
    """
    Fast fuzzy search using trigram (3-character substring) pre-filtering.

    Instead of comparing query against 2.2M names (slow), we:
    1. Extract trigrams from query: "LIMEX" -> {LIM, IME, MEX}
    2. Find names sharing ≥N trigrams (candidates)
    3. Only run expensive fuzzy match on candidates (~1-10K instead of 2.2M)

    Performance: ~50ms per lookup vs ~5s without filtering
    """

    def __init__(self, min_shared_trigrams: int = 2):
        """
        Args:
            min_shared_trigrams: Minimum trigrams a candidate must share with query.
                                Lower = more candidates (slower, fewer misses)
                                Higher = fewer candidates (faster, more misses)
        """
        self.min_shared = min_shared_trigrams
        self.trigram_to_names: Dict[str, set] = defaultdict(set)  # trigram -> {name1, name2, ...}
        self.all_names: set = set()
        self._built = False

    @staticmethod
    def extract_trigrams(text: str) -> set:
        """Extract all 3-character substrings from text."""
        if not text or len(text) < 3:
            return set()
        text = text.upper()
        return {text[i:i+3] for i in range(len(text) - 2)}

    def add_name(self, name: str):
        """Add a name to the index."""
        if not name or len(name) < 3:
            return
        name_upper = name.upper()
        self.all_names.add(name)
        for trigram in self.extract_trigrams(name_upper):
            self.trigram_to_names[trigram].add(name)

    def build_from_names(self, names: List[str]):
        """Build index from a list of names."""
        for name in names:
            self.add_name(name)
        self._built = True

    def get_candidates(self, query: str, max_candidates: int = 5000) -> List[str]:
        """
        Get candidate names that share enough trigrams with query.

        Uses adaptive filtering: requires more shared trigrams for longer queries.

        Args:
            query: Search query (company name)
            max_candidates: Maximum candidates to return

        Returns:
            List of candidate names for fuzzy matching
        """
        if not query or len(query) < 3:
            return []

        query_trigrams = self.extract_trigrams(query.upper())
        if not query_trigrams:
            return []

        # Adaptive threshold: require more shared trigrams for longer queries
        # Short query (3-5 chars, 1-3 trigrams): require 1 shared
        # Medium query (6-10 chars, 4-8 trigrams): require 2-3 shared
        # Long query (11+ chars, 9+ trigrams): require 30% of query trigrams
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
        return [name for name, _ in candidates[:max_candidates]]

    def __len__(self):
        return len(self.all_names)

    def stats(self) -> Dict:
        """Return index statistics."""
        return {
            'total_names': len(self.all_names),
            'total_trigrams': len(self.trigram_to_names),
            'avg_names_per_trigram': sum(len(v) for v in self.trigram_to_names.values()) / max(1, len(self.trigram_to_names)),
        }


# ============================================================
# CONFIGURATION
# ============================================================

SOURCES = [
    {
        "name": "ANOFM",
        "path": "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/ANOFM/anofm_latest.csv",
        "cui_col": "company_org_number",
        "name_col": "company_name",
        "email_cols": ["email_1", "email_2", "email_3"],
        "phone_cols": ["phone_1", "phone_2", "phone_3"],
        "address_col": "company_address",
        "priority": 1,
    },
    {
        "name": "EUFUNDS",
        "path": "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/EUFUNDS/eufunds_contacts.csv",
        "cui_col": "cui",
        "name_col": "company_name",
        "email_cols": ["email_1", "email_2", "email_3"],
        "phone_cols": ["phone"],
        "address_col": "address",
        "priority": 2,
    },
    {
        "name": "MASTER_ALL",
        "path": "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/MASTER_ALL.csv",
        "cui_col": "employer_tax_code",
        "name_col": "employer",
        "email_cols": ["email1", "email2", "email3"],
        "phone_cols": ["phone1", "phone2", "phone3"],
        "address_col": None,
        "priority": 3,
    },
    {
        "name": "ANAF_PHONES",
        "path": "/opt/ACTIVE/OPENDATA/FIRME_ROMANIA/DATA/anaf_all/all_phones.csv",
        "cui_col": "cui",
        "name_col": "name",
        "email_cols": [],
        "phone_cols": ["phone"],
        "address_col": "address",
        "priority": 4,
        "large": True,  # Skip unless --full flag
    },
    {
        "name": "DSVSA",
        "path": "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/DSVSA/DSVSA_WITH_CONTACTS.csv",
        "cui_col": None,
        "name_col": "company_name",
        "email_cols": ["best_email", "anofm_email", "web_email"],
        "phone_cols": ["best_phone", "anofm_phone", "web_phone", "phone"],
        "address_col": "best_address",
        "priority": 5,
    },
    {
        "name": "IAJOB",
        "path": "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/IAJOB/jobs.csv",
        "cui_col": None,
        "name_col": "company",
        "email_cols": ["contact_email"],
        "phone_cols": ["contact_phone", "contact_phone_2"],
        "address_col": None,
        "priority": 6,
    },
    {
        "name": "WEBSITE_CONTACTS",
        "path": "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/WEBSITE_CONTACTS/website_contacts.csv",
        "cui_col": "cui",
        "name_col": None,
        "email_cols": ["email_1", "email_2"],
        "phone_cols": ["phone_1", "phone_2"],
        "address_col": None,
        "priority": 7,
    },
]

# CUI column variations to detect
CUI_COLUMN_NAMES = ['cui', 'CUI', 'cod_fiscal', 'tax_id', 'tax_code', 'company_org_number', 'employer_tax_code']
NAME_COLUMN_NAMES = ['nume_firma', 'company_name', 'name', 'company', 'employer', 'denumire', 'firma']

# Company suffix patterns to remove for matching
COMPANY_SUFFIXES = re.compile(r'\b(S\.?R\.?L\.?|S\.?A\.?|S\.?C\.?|P\.?F\.?A\.?|I\.?I\.?|S\.?N\.?C\.?|S\.?C\.?S\.?|O\.?N\.?G\.?)\b', re.I)

# ============================================================
# PHONE NORMALIZATION
# ============================================================

def normalize_phone(phone: str) -> str:
    """Normalize Romanian phone to +40XXXXXXXXX format."""
    if not phone:
        return ""

    # Remove all non-digit characters
    digits = re.sub(r'\D', '', str(phone))

    if not digits:
        return ""

    # Handle various formats
    if digits.startswith('40') and len(digits) >= 11:
        digits = digits[2:]  # Remove country code
    elif digits.startswith('0040'):
        digits = digits[4:]
    elif digits.startswith('004'):
        digits = digits[3:]

    # Remove leading zeros
    digits = digits.lstrip('0')

    # Romanian mobile: 7XXXXXXXX (9 digits after 0)
    # Romanian landline: 2X-3X (varies by region)
    if len(digits) >= 9:
        # Add back leading digit if stripped
        if digits[0] not in '237':
            # Try to infer - most likely mobile
            if len(digits) == 9:
                digits = '7' + digits[-8:]  # Assume mobile
        return f"+40{digits[:10]}"

    return ""


def normalize_company_name(name: str) -> str:
    """Normalize company name for matching."""
    if not name:
        return ""

    # Convert to ASCII
    name = to_ascii(str(name).upper().strip())

    # Remove company suffixes
    name = COMPANY_SUFFIXES.sub('', name)

    # Remove punctuation
    name = re.sub(r'[^\w\s]', ' ', name)

    # Collapse whitespace
    name = ' '.join(name.split())

    return name


def extract_cui(value: str) -> str:
    """Extract numeric CUI from various formats."""
    if not value:
        return ""

    # Remove 'RO' prefix if present
    value = str(value).upper().strip()
    if value.startswith('RO'):
        value = value[2:]

    # Extract digits only
    digits = re.sub(r'\D', '', value)

    # Valid CUI is 2-10 digits
    if 2 <= len(digits) <= 10:
        return digits

    return ""


def is_valid_email(email: str) -> bool:
    """Basic email validation."""
    if not email:
        return False
    email = str(email).strip().lower()
    return bool(re.match(r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$', email))


# ============================================================
# DUCKDB SUPPORT FOR LARGE FILES
# ============================================================

class DuckDBSource:
    """DuckDB-based lookup for large CSV files (e.g., ANAF_PHONES 2.4M rows)."""

    def __init__(self, csv_path: str, config: dict):
        self.csv_path = csv_path
        self.config = config
        self.db = None
        self.db_path = csv_path.replace('.csv', '.duckdb')
        self._init_db()

    def _init_db(self):
        """Initialize DuckDB - create index if needed."""
        try:
            import duckdb
            self.db = duckdb.connect(self.db_path)

            # Check if table exists
            tables = self.db.execute("SHOW TABLES").fetchall()
            if not any('contacts' in t[0] for t in tables):
                print(f"    Creating DuckDB index (one-time)...")
                # Import CSV and create indexed table
                self.db.execute(f"""
                    CREATE TABLE contacts AS
                    SELECT * FROM read_csv_auto('{self.csv_path}')
                """)
                # Create index on CUI column
                cui_col = self.config.get('cui_col', 'cui')
                self.db.execute(f"CREATE INDEX idx_cui ON contacts({cui_col})")
                print(f"    DuckDB index created at {self.db_path}")
            else:
                print(f"    Using existing DuckDB index")

        except ImportError:
            print("    Warning: DuckDB not available, falling back to memory")
            self.db = None
        except Exception as e:
            print(f"    DuckDB error: {e}")
            self.db = None

    def lookup_cui(self, cui: str) -> Optional[Dict]:
        """Lookup contact by CUI using SQL."""
        if not self.db or not cui:
            return None

        cui_col = self.config.get('cui_col', 'cui')
        try:
            result = self.db.execute(f"""
                SELECT * FROM contacts WHERE CAST({cui_col} AS VARCHAR) = ?
                LIMIT 1
            """, [str(cui)]).fetchone()

            if result:
                columns = [desc[0] for desc in self.db.description]
                row = dict(zip(columns, result))
                return self._to_contact(row)
        except Exception as e:
            pass
        return None

    def lookup_cuis_batch(self, cuis: List[str]) -> Dict[str, Dict]:
        """Batch lookup multiple CUIs."""
        if not self.db or not cuis:
            return {}

        cui_col = self.config.get('cui_col', 'cui')
        results = {}
        try:
            # Batch query
            placeholders = ','.join(['?' for _ in cuis])
            rows = self.db.execute(f"""
                SELECT * FROM contacts
                WHERE CAST({cui_col} AS VARCHAR) IN ({placeholders})
            """, [str(c) for c in cuis]).fetchall()

            columns = [desc[0] for desc in self.db.description]
            for row in rows:
                row_dict = dict(zip(columns, row))
                contact = self._to_contact(row_dict)
                if contact and contact['cui']:
                    results[contact['cui']] = contact
        except Exception as e:
            print(f"    DuckDB batch error: {e}")
        return results

    def _to_contact(self, row: dict) -> Optional[Dict]:
        """Convert row to contact dict."""
        cui = extract_cui(str(row.get(self.config.get('cui_col', 'cui'), '')))
        name = row.get(self.config.get('name_col', ''), '')

        phone = ""
        for col in self.config.get('phone_cols', []):
            if col in row:
                normalized = normalize_phone(str(row.get(col, '')))
                if normalized:
                    phone = normalized
                    break

        email = ""
        for col in self.config.get('email_cols', []):
            if col in row and is_valid_email(str(row.get(col, ''))):
                email = str(row[col]).strip().lower()
                break

        address = ""
        if self.config.get('address_col') and self.config['address_col'] in row:
            address = to_ascii(str(row.get(self.config['address_col'], '')))

        if not (cui or name) or not (email or phone):
            return None

        return {
            'cui': cui,
            'name': name,
            'normalized_name': normalize_company_name(name),
            'email': email,
            'phone': phone,
            'address': address,
            'source': self.config['name'],
            'priority': self.config['priority'],
        }

    def get_record_count(self) -> int:
        """Get total records in database."""
        if not self.db:
            return 0
        try:
            return self.db.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
        except:
            return 0

    def close(self):
        """Close database connection."""
        if self.db:
            self.db.close()

    def load_names_for_fuzzy(self, cache_path: str = None) -> int:
        """
        Load company names into memory for fuzzy matching with trigram index.

        Creates:
        - normalized_name -> CUI index for lookups
        - TrigramIndex for fast candidate pre-filtering

        Args:
            cache_path: Optional path to pickle file for caching the index.
                       If exists and valid, loads from cache instead of DB.

        Returns:
            Number of names loaded
        """
        import pickle
        from pathlib import Path

        self.name_index: Dict[str, str] = {}  # normalized_name -> CUI
        self.trigram_index: TrigramIndex = TrigramIndex(min_shared_trigrams=2)

        # Derive trigram cache path from name cache path
        trigram_cache_path = cache_path.replace('.pkl', '_trigrams.pkl') if cache_path else None

        # Try to load from cache first
        if cache_path:
            cache_file = Path(cache_path)
            trigram_file = Path(trigram_cache_path) if trigram_cache_path else None

            if cache_file.exists():
                try:
                    with open(cache_file, 'rb') as f:
                        cached = pickle.load(f)
                        if isinstance(cached, dict) and len(cached) > 0:
                            self.name_index = cached

                            # Try to load trigram index from cache
                            if trigram_file and trigram_file.exists():
                                with open(trigram_file, 'rb') as tf:
                                    self.trigram_index = pickle.load(tf)
                                print(f"    Loaded {len(self.name_index):,} names + trigram index from cache")
                            else:
                                # Rebuild trigram index from name_index
                                print(f"    Loaded {len(self.name_index):,} names, rebuilding trigram index...")
                                self.trigram_index.build_from_names(list(self.name_index.keys()))
                                # Save trigram index
                                if trigram_file:
                                    with open(trigram_file, 'wb') as tf:
                                        pickle.dump(self.trigram_index, tf)
                                    print(f"    Cached trigram index")

                            return len(self.name_index)
                except Exception as e:
                    print(f"    Cache load failed: {e}")

        if not self.db:
            return 0

        # Load names from DuckDB
        name_col = self.config.get('name_col', 'name')
        cui_col = self.config.get('cui_col', 'cui')

        try:
            print(f"    Loading names for fuzzy matching (this may take a minute)...")
            rows = self.db.execute(f"""
                SELECT CAST({cui_col} AS VARCHAR) as cui, {name_col} as name
                FROM contacts
                WHERE {name_col} IS NOT NULL AND {name_col} != ''
            """).fetchall()

            for cui, name in rows:
                if cui and name:
                    normalized = normalize_company_name(str(name))
                    if normalized and len(normalized) >= 3:
                        # Only keep first CUI for each normalized name (avoid duplicates)
                        if normalized not in self.name_index:
                            self.name_index[normalized] = str(cui)

            print(f"    Built name index: {len(self.name_index):,} unique company names")

            # Build trigram index for fast pre-filtering
            print(f"    Building trigram index...")
            self.trigram_index.build_from_names(list(self.name_index.keys()))
            stats = self.trigram_index.stats()
            print(f"    Trigram index: {stats['total_trigrams']:,} trigrams, "
                  f"avg {stats['avg_names_per_trigram']:.1f} names/trigram")

            # Save to cache if path provided
            if cache_path:
                try:
                    cache_file = Path(cache_path)
                    cache_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(cache_file, 'wb') as f:
                        pickle.dump(self.name_index, f)
                    print(f"    Cached name index to {cache_path}")

                    # Save trigram index
                    if trigram_cache_path:
                        with open(trigram_cache_path, 'wb') as tf:
                            pickle.dump(self.trigram_index, tf)
                        print(f"    Cached trigram index")
                except Exception as e:
                    print(f"    Cache save failed: {e}")

        except Exception as e:
            print(f"    Error loading names: {e}")

        return len(self.name_index)


# ============================================================
# SOURCE LOADING
# ============================================================

class ContactDatabase:
    """In-memory database of contacts from all sources."""

    def __init__(self):
        self.by_cui: Dict[str, Dict] = {}  # CUI -> contact info
        self.by_name: Dict[str, List[Dict]] = defaultdict(list)  # Normalized name -> [contact info]
        self.duckdb_sources: List[DuckDBSource] = []  # DuckDB sources for large files
        self.stats = {
            'sources_loaded': 0,
            'total_records': 0,
            'with_cui': 0,
            'with_email': 0,
            'with_phone': 0,
        }

    def load_source(self, source_config: dict, use_duckdb: bool = True, use_fuzzy: bool = False) -> int:
        """
        Load a single source file into the database.

        Args:
            source_config: Source configuration dict
            use_duckdb: Use DuckDB for large files
            use_fuzzy: Also load names for fuzzy matching (DuckDB sources)
        """
        path = Path(source_config['path'])
        if not path.exists():
            print(f"  Warning: {source_config['name']} not found at {path}")
            return 0

        # Use DuckDB for large sources
        if source_config.get('large') and use_duckdb:
            try:
                import duckdb
                print(f"  {source_config['name']}: Loading via DuckDB...")
                ddb = DuckDBSource(str(path), source_config)
                count = ddb.get_record_count()
                if count > 0:
                    self.duckdb_sources.append(ddb)
                    self.stats['sources_loaded'] += 1
                    self.stats['total_records'] += count
                    self.stats['with_phone'] += count  # ANAF_PHONES has all phones
                    print(f"  {source_config['name']}: {count:,} records indexed (DuckDB)")

                    # Load names for fuzzy matching if enabled
                    if use_fuzzy:
                        cache_path = source_config['path'].replace('.csv', '_name_index.pkl')
                        ddb.load_names_for_fuzzy(cache_path)
                        self.stats['with_cui'] += len(getattr(ddb, 'name_index', {}))

                    return count
            except ImportError:
                print(f"  {source_config['name']}: DuckDB not available, loading to memory...")
            except Exception as e:
                print(f"  {source_config['name']}: DuckDB error ({e}), loading to memory...")

        # Standard in-memory loading
        count = 0
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    contact = self._extract_contact(row, source_config)
                    if contact:
                        self._store_contact(contact)
                        count += 1

            self.stats['sources_loaded'] += 1
            self.stats['total_records'] += count
            print(f"  {source_config['name']}: {count:,} records loaded")

        except Exception as e:
            print(f"  Error loading {source_config['name']}: {e}")

        return count

    def _extract_contact(self, row: dict, config: dict) -> Optional[Dict]:
        """Extract contact info from a row."""
        # Get CUI
        cui = ""
        if config['cui_col'] and config['cui_col'] in row:
            cui = extract_cui(row.get(config['cui_col'], ''))

        # Get name
        name = ""
        if config['name_col'] and config['name_col'] in row:
            name = row.get(config['name_col'], '')

        normalized_name = normalize_company_name(name)

        # Get email (first valid one)
        email = ""
        for col in config.get('email_cols', []):
            if col in row and is_valid_email(row.get(col, '')):
                email = row[col].strip().lower()
                break

        # Get phone (first valid one)
        phone = ""
        for col in config.get('phone_cols', []):
            if col in row:
                normalized = normalize_phone(row.get(col, ''))
                if normalized:
                    phone = normalized
                    break

        # Get address
        address = ""
        if config.get('address_col') and config['address_col'] in row:
            address = to_ascii(row.get(config['address_col'], ''))

        # Must have at least name and either email or phone
        if not (normalized_name or cui) or not (email or phone):
            return None

        return {
            'cui': cui,
            'name': name,
            'normalized_name': normalized_name,
            'email': email,
            'phone': phone,
            'address': address,
            'source': config['name'],
            'priority': config['priority'],
        }

    def _store_contact(self, contact: Dict):
        """Store contact in the database indexes."""
        # Index by CUI if available
        if contact['cui']:
            existing = self.by_cui.get(contact['cui'])
            if not existing or existing['priority'] > contact['priority']:
                self.by_cui[contact['cui']] = contact
                self.stats['with_cui'] += 1

        # Index by normalized name
        if contact['normalized_name']:
            self.by_name[contact['normalized_name']].append(contact)

        if contact['email']:
            self.stats['with_email'] += 1
        if contact['phone']:
            self.stats['with_phone'] += 1

    def lookup_cui(self, cui: str) -> Optional[Dict]:
        """Lookup contact by CUI (exact match)."""
        cui = extract_cui(cui)
        if not cui:
            return None

        # Check in-memory first
        contact = self.by_cui.get(cui)
        if contact:
            return contact

        # Check DuckDB sources
        for ddb in self.duckdb_sources:
            contact = ddb.lookup_cui(cui)
            if contact:
                return contact

        return None

    def lookup_cuis_batch(self, cuis: List[str]) -> Dict[str, Dict]:
        """Batch lookup multiple CUIs (optimized for DuckDB)."""
        results = {}
        remaining = []

        # Check in-memory first
        for cui in cuis:
            cui = extract_cui(cui)
            if cui:
                if cui in self.by_cui:
                    results[cui] = self.by_cui[cui]
                else:
                    remaining.append(cui)

        # Batch lookup in DuckDB sources
        for ddb in self.duckdb_sources:
            if remaining:
                ddb_results = ddb.lookup_cuis_batch(remaining)
                results.update(ddb_results)
                remaining = [c for c in remaining if c not in ddb_results]

        return results

    def lookup_name_exact(self, name: str) -> Optional[Dict]:
        """Lookup contact by exact normalized name."""
        normalized = normalize_company_name(name)
        matches = self.by_name.get(normalized, [])
        if matches:
            # Return highest priority (lowest number)
            return min(matches, key=lambda x: x['priority'])
        return None

    def lookup_name_fuzzy(self, name: str, threshold: int = 85, max_candidates: int = 10000) -> Optional[Tuple[Dict, int]]:
        """
        Lookup contact by fuzzy name matching using trigram pre-filtering + WRatio.

        For large datasets (2M+ names), uses trigram index to pre-filter candidates
        before running expensive fuzzy matching. This makes search ~100x faster.

        Args:
            name: Company name to search for
            threshold: Minimum match score (0-100)
            max_candidates: Maximum candidates after trigram filtering (default 10K)
        """
        try:
            from rapidfuzz import fuzz, process
        except ImportError:
            return None

        normalized = normalize_company_name(name)
        if not normalized:
            return None

        # Get candidates from in-memory index (small, always included)
        all_candidates = list(self.by_name.keys())

        # For DuckDB sources, use trigram index to pre-filter candidates
        for ddb in self.duckdb_sources:
            if hasattr(ddb, 'trigram_index') and ddb.trigram_index:
                # Use trigram index to get relevant candidates only
                ddb_candidates = ddb.trigram_index.get_candidates(
                    normalized,
                    max_candidates=max_candidates
                )
                all_candidates.extend(ddb_candidates)
            elif hasattr(ddb, 'name_index') and ddb.name_index:
                # Fallback: include limited names if no trigram index
                remaining = max(0, max_candidates - len(all_candidates))
                if remaining > 0:
                    all_candidates.extend(list(ddb.name_index.keys())[:remaining])

        if not all_candidates:
            return None

        # Use WRatio - rapidfuzz's built-in weighted combination scorer
        # It automatically combines ratio, partial_ratio, token_sort_ratio, token_set_ratio
        result = process.extractOne(
            normalized,
            all_candidates,
            scorer=fuzz.WRatio,
            score_cutoff=threshold
        )

        if result:
            match_name, score, _ = result

            # Check in-memory index first
            matches = self.by_name.get(match_name, [])
            if matches:
                return (min(matches, key=lambda x: x['priority']), int(score))

            # Check DuckDB sources for the matched name
            for ddb in self.duckdb_sources:
                if hasattr(ddb, 'name_index') and ddb.name_index:
                    cui = ddb.name_index.get(match_name)
                    if cui:
                        contact = ddb.lookup_cui(cui)
                        if contact:
                            return (contact, int(score))

        return None


# ============================================================
# MAIN ENRICHMENT
# ============================================================

def detect_columns(fieldnames: List[str]) -> Tuple[Optional[str], Optional[str]]:
    """Detect CUI and company name columns in input CSV."""
    cui_col = None
    name_col = None

    for col in fieldnames:
        col_lower = col.lower().strip()
        if not cui_col and col_lower in [c.lower() for c in CUI_COLUMN_NAMES]:
            cui_col = col
        if not name_col and col_lower in [c.lower() for c in NAME_COLUMN_NAMES]:
            name_col = col

    return cui_col, name_col


def enrich_file(
    input_path: str,
    output_path: Optional[str] = None,
    use_fuzzy: bool = False,
    fuzzy_threshold: int = 85,
    use_anaf: bool = False,
    stats_only: bool = False,
    load_all: bool = False
) -> Dict:
    """
    Enrich a CSV file with contact information.

    Args:
        input_path: Path to input CSV
        output_path: Path to output CSV (default: input_enriched.csv)
        use_fuzzy: Enable fuzzy name matching
        fuzzy_threshold: Minimum fuzzy match score (0-100)
        use_anaf: Query ANAF API for missing data (slower)
        stats_only: Only show stats, don't write output
        load_all: Load all sources including large ones (ANAF_PHONES 2.4M)

    Returns:
        Dict with enrichment statistics
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if not output_path:
        output_path = input_path.with_name(f"{input_path.stem}_enriched{input_path.suffix}")
    output_path = Path(output_path)

    print(f"\n=== Romania Company Enrichment ===")
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    print(f"Fuzzy matching: {use_fuzzy} (threshold: {fuzzy_threshold})")
    print(f"ANAF API: {use_anaf}")
    print(f"Load all sources: {load_all}")
    print()

    # Load contact database
    print("Loading contact sources...")
    db = ContactDatabase()
    for source in SOURCES:
        # Skip large sources unless --full flag
        if source.get('large') and not load_all:
            print(f"  Skipping {source['name']} (use --full to include)")
            continue
        # Pass use_fuzzy to enable name loading for DuckDB sources
        db.load_source(source, use_fuzzy=use_fuzzy)

    print(f"\nDatabase stats:")
    print(f"  Sources: {db.stats['sources_loaded']}")
    print(f"  Records: {db.stats['total_records']:,}")
    print(f"  With CUI: {db.stats['with_cui']:,}")
    print(f"  With email: {db.stats['with_email']:,}")
    print(f"  With phone: {db.stats['with_phone']:,}")
    print()

    # Read input and detect columns
    with open(input_path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    cui_col, name_col = detect_columns(fieldnames)
    print(f"Detected columns:")
    print(f"  CUI column: {cui_col or 'NOT FOUND'}")
    print(f"  Name column: {name_col or 'NOT FOUND'}")
    print(f"  Input rows: {len(rows):,}")
    print()

    if not cui_col and not name_col:
        raise ValueError("Could not detect CUI or company name column in input CSV")

    # Prepare ANAF lookup if enabled
    anaf_results = {}
    if use_anaf and cui_col:
        try:
            sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS')
            from anaf_api import lookup as anaf_lookup

            print("Querying ANAF API...")
            cuis_to_lookup = [extract_cui(row.get(cui_col, '')) for row in rows]
            cuis_to_lookup = [c for c in cuis_to_lookup if c]

            if cuis_to_lookup:
                results = anaf_lookup(cuis_to_lookup)
                for r in results:
                    if r.get('cui'):
                        anaf_results[str(r['cui'])] = r
                print(f"  ANAF returned {len(anaf_results):,} results")
        except Exception as e:
            print(f"  ANAF API error: {e}")

    # Enrich rows
    print("\nEnriching records...")
    stats = {
        'total': len(rows),
        'enriched': 0,
        'with_email': 0,
        'with_phone': 0,
        'by_cui': 0,
        'by_name_exact': 0,
        'by_name_fuzzy': 0,
        'by_anaf': 0,
        'sources': defaultdict(int),
    }

    # Pre-fetch CUI lookups in batch (optimizes DuckDB queries)
    all_cuis = [extract_cui(row.get(cui_col, '')) for row in rows] if cui_col else []
    all_cuis = [c for c in all_cuis if c]
    if all_cuis and db.duckdb_sources:
        print(f"  Batch fetching {len(all_cuis):,} CUIs from DuckDB...")
        cui_cache = db.lookup_cuis_batch(all_cuis)
        print(f"  Found {len(cui_cache):,} matches")
    else:
        cui_cache = {}

    enriched_rows = []
    for row in rows:
        enriched = {
            'enriched_email': '',
            'enriched_phone': '',
            'enriched_address': '',
            'enriched_source': '',
            'enriched_match_type': '',
        }

        cui = extract_cui(row.get(cui_col, '')) if cui_col else ''
        name = row.get(name_col, '') if name_col else ''

        contact = None
        match_type = ''

        # 1. Try CUI lookup first (use pre-fetched cache if available)
        if cui:
            contact = cui_cache.get(cui) or db.lookup_cui(cui)
            if contact:
                match_type = 'cui'
                stats['by_cui'] += 1

        # 2. Try exact name match
        if not contact and name:
            contact = db.lookup_name_exact(name)
            if contact:
                match_type = 'name_exact'
                stats['by_name_exact'] += 1

        # 3. Try fuzzy name match
        if not contact and name and use_fuzzy:
            result = db.lookup_name_fuzzy(name, fuzzy_threshold)
            if result:
                contact, score = result
                match_type = f'fuzzy_{score}'
                stats['by_name_fuzzy'] += 1

        # 4. Check ANAF results
        if use_anaf and cui and cui in anaf_results:
            anaf = anaf_results[cui]
            if anaf.get('phone') and not enriched['enriched_phone']:
                enriched['enriched_phone'] = normalize_phone(anaf['phone'])
                if not contact:
                    match_type = 'anaf'
                    stats['by_anaf'] += 1
            if anaf.get('address') and not enriched['enriched_address']:
                enriched['enriched_address'] = to_ascii(anaf['address'])

        # Apply contact data
        if contact:
            if contact['email']:
                enriched['enriched_email'] = contact['email']
            if contact['phone']:
                enriched['enriched_phone'] = contact['phone']
            if contact['address']:
                enriched['enriched_address'] = contact['address']
            enriched['enriched_source'] = contact['source']
            enriched['enriched_match_type'] = match_type

            stats['enriched'] += 1
            stats['sources'][contact['source']] += 1

        if enriched['enriched_email']:
            stats['with_email'] += 1
        if enriched['enriched_phone']:
            stats['with_phone'] += 1

        # Merge enriched data into row
        enriched_row = {**row, **enriched}
        enriched_rows.append(enriched_row)

    # Print stats
    print(f"\nEnrichment results:")
    print(f"  Total records: {stats['total']:,}")
    print(f"  Enriched: {stats['enriched']:,} ({100*stats['enriched']/max(1,stats['total']):.1f}%)")
    print(f"  With email: {stats['with_email']:,} ({100*stats['with_email']/max(1,stats['total']):.1f}%)")
    print(f"  With phone: {stats['with_phone']:,} ({100*stats['with_phone']/max(1,stats['total']):.1f}%)")
    print(f"\nMatch types:")
    print(f"  By CUI: {stats['by_cui']:,}")
    print(f"  By name (exact): {stats['by_name_exact']:,}")
    print(f"  By name (fuzzy): {stats['by_name_fuzzy']:,}")
    if use_anaf:
        print(f"  By ANAF: {stats['by_anaf']:,}")
    print(f"\nBy source:")
    for source, count in sorted(stats['sources'].items(), key=lambda x: -x[1]):
        print(f"  {source}: {count:,}")

    # Write output
    if not stats_only:
        output_fieldnames = list(fieldnames) + [
            'enriched_email', 'enriched_phone', 'enriched_address',
            'enriched_source', 'enriched_match_type'
        ]

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=output_fieldnames)
            writer.writeheader()
            writer.writerows(enriched_rows)

        print(f"\nOutput written to: {output_path}")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Enrich Romanian company CSVs with contact data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 enrich_romania.py companies.csv
  python3 enrich_romania.py companies.csv --output enriched.csv
  python3 enrich_romania.py companies.csv --fuzzy --threshold 80
  python3 enrich_romania.py companies.csv --anaf
  python3 enrich_romania.py companies.csv --stats
  python3 enrich_romania.py companies.csv --full  # Include ANAF_PHONES (2.4M CUIs)

Performance Notes:
  --fuzzy alone is fast (searches ~50K names from ANOFM, EUFUNDS, etc.)
  --full alone is fast (CUI lookup in ANAF_PHONES via DuckDB index)
  --full --fuzzy is SLOW (fuzzy search on 2.2M company names, ~5s per record)

Recommended for best balance:
  python3 enrich_romania.py companies.csv --full  # CUI matches from ANAF_PHONES
  python3 enrich_romania.py companies.csv --fuzzy  # Fuzzy from smaller sources
        """
    )

    parser.add_argument('input', help='Input CSV file')
    parser.add_argument('--output', '-o', help='Output CSV file')
    parser.add_argument('--fuzzy', '-f', action='store_true',
                        help='Enable fuzzy company name matching')
    parser.add_argument('--threshold', '-t', type=int, default=85,
                        help='Fuzzy match threshold (default: 85)')
    parser.add_argument('--anaf', '-a', action='store_true',
                        help='Also query ANAF API for phones (slower)')
    parser.add_argument('--full', action='store_true',
                        help='Load all sources including ANAF_PHONES (2.4M records, slow)')
    parser.add_argument('--stats', '-s', action='store_true',
                        help='Show stats only, do not write output')

    args = parser.parse_args()

    try:
        enrich_file(
            input_path=args.input,
            output_path=args.output,
            use_fuzzy=args.fuzzy,
            fuzzy_threshold=args.threshold,
            use_anaf=args.anaf,
            stats_only=args.stats,
            load_all=args.full
        )
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
