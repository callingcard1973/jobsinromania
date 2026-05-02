#!/usr/bin/env python3
"""
Build Unified Enrichment Index from All Romanian Data Sources.

Creates a SQLite database with indexes for fast lookups by:
- CUI (exact match) - 2.4M records from ANAF
- Company name (normalized) - for fuzzy matching
- Phone (normalized)
- Email

Data Sources (in priority order):
1. ANAF All Phones - 2.4M CUI -> phone, name, address
2. ANOFM Master - 18K+ companies with email/phone
3. Romania BILANT Master - 1M companies with phone
4. MASTER_ALL - 65K multi-country contacts

Usage:
    python3 build_enrichment_index.py              # Full rebuild
    python3 build_enrichment_index.py --status     # Show index stats
    python3 build_enrichment_index.py --lookup 36067923  # Test CUI lookup
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import argparse
import csv
import os
import re
import sqlite3
import unicodedata
from datetime import datetime
from pathlib import Path

# === CONFIGURATION ===

INDEX_PATH = '/opt/ACTIVE/OPENDATA/DATA/ENRICHMENT_INDEX/enrichment_index.db'

# Data sources with their field mappings
DATA_SOURCES = [
    {
        'name': 'ANAF_PHONES',
        'path': '/opt/ACTIVE/OPENDATA/FIRME_ROMANIA/DATA/anaf_all/all_phones.csv',
        'priority': 1,
        'fields': {
            'cui': 'cui',
            'name': 'name',
            'phone': 'phone',
            'address': 'address',
            'caen': 'caen',
        }
    },
    {
        'name': 'ANOFM_MASTER',
        'path': '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/ANOFM/anofm_master.csv',
        'priority': 2,
        'fields': {
            'cui': 'company_org_number',
            'name': 'company_name',
            'email': 'email_1',
            'phone': 'phone_1',
            'website': 'company_website',
            'address': 'company_address',
        }
    },
    {
        'name': 'BILANT_MASTER',
        'path': '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/BILANT/romania_companies_master.csv',
        'priority': 3,
        'fields': {
            'cui': 'cui',
            'name': 'nume_firma',
            'phone': 'telefon',
            'address': 'adresa',
            'j_number': 'cod_j',
            'caen': 'caen',
            'city': 'localitate',
            'county': 'judet',
        }
    },
    {
        'name': 'MASTER_ALL',
        'path': '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/MASTER_ALL.csv',
        'priority': 4,
        'fields': {
            'cui': 'employer_tax_code',
            'name': 'employer',
            'email': 'email1',
            'phone': 'phone1',
            'website': 'company_website',
            'address': 'address',
            'city': 'city',
        }
    },
    {
        'name': 'EURES_MASTER',
        'path': '/opt/ACTIVE/OPENDATA/DATA/EURES_SYNC/master_contacts.csv',
        'priority': 5,
        'fields': {
            'cui': 'company_org_number',
            'name': 'company_name',
            'email': 'email_1',
            'phone': 'phone_1',
            'website': 'company_website',
            'address': 'company_address',
            'city': 'company_city',
        }
    },
]

# === NORMALIZATION FUNCTIONS ===

def to_ascii(text: str) -> str:
    """Convert text to ASCII, removing diacritics."""
    if not text:
        return ''
    return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii')


def normalize_phone(phone: str) -> str:
    """Normalize phone to digits only, remove country code."""
    if not phone:
        return ''
    digits = re.sub(r'\D', '', str(phone))
    # Remove +40/0040 prefix
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


# === DATABASE FUNCTIONS ===

def create_database(db_path: str):
    """Create SQLite database with indexes."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Main company table
    c.execute('''
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cui TEXT,
            name TEXT,
            name_normalized TEXT,
            email TEXT,
            phone TEXT,
            phone_normalized TEXT,
            website TEXT,
            website_domain TEXT,
            address TEXT,
            city TEXT,
            county TEXT,
            caen TEXT,
            j_number TEXT,
            source TEXT,
            priority INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create indexes
    c.execute('CREATE INDEX IF NOT EXISTS idx_cui ON companies(cui)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_name_norm ON companies(name_normalized)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_phone_norm ON companies(phone_normalized)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_email ON companies(email)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_website_domain ON companies(website_domain)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_source ON companies(source)')

    # Metadata table
    c.execute('''
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    return conn


def load_source(conn: sqlite3.Connection, source: dict, batch_size: int = 10000):
    """Load a data source into the database."""
    path = Path(source['path'])
    if not path.exists():
        print(f"  SKIP: {source['name']} - file not found: {path}")
        return 0

    name = source['name']
    priority = source['priority']
    fields = source['fields']

    print(f"  Loading {name} from {path}...")

    c = conn.cursor()
    count = 0
    batch = []

    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)

        for row in reader:
            # Extract fields
            cui = normalize_cui(row.get(fields.get('cui', ''), ''))
            raw_name = row.get(fields.get('name', ''), '').strip()
            name_normalized = normalize_company_name(raw_name)
            email = row.get(fields.get('email', ''), '').strip().lower() if 'email' in fields else ''
            phone = row.get(fields.get('phone', ''), '').strip() if 'phone' in fields else ''
            phone_normalized = normalize_phone(phone)
            website = row.get(fields.get('website', ''), '').strip() if 'website' in fields else ''
            website_domain = extract_domain(website)
            address = row.get(fields.get('address', ''), '').strip() if 'address' in fields else ''
            city = row.get(fields.get('city', ''), '').strip() if 'city' in fields else ''
            county = row.get(fields.get('county', ''), '').strip() if 'county' in fields else ''
            caen = row.get(fields.get('caen', ''), '').strip() if 'caen' in fields else ''
            j_number = row.get(fields.get('j_number', ''), '').strip() if 'j_number' in fields else ''

            # Skip if no useful data
            if not cui and not name_normalized and not phone_normalized and not email:
                continue

            # Validate email
            if email and '@' not in email:
                email = ''

            batch.append((
                cui, raw_name, name_normalized, email, phone, phone_normalized,
                website, website_domain, address, city, county, caen, j_number,
                source['name'], priority
            ))
            count += 1

            if len(batch) >= batch_size:
                c.executemany('''
                    INSERT INTO companies (
                        cui, name, name_normalized, email, phone, phone_normalized,
                        website, website_domain, address, city, county, caen, j_number,
                        source, priority
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', batch)
                conn.commit()
                batch = []
                if count % 100000 == 0:
                    print(f"    {count:,} records...")

    # Insert remaining
    if batch:
        c.executemany('''
            INSERT INTO companies (
                cui, name, name_normalized, email, phone, phone_normalized,
                website, website_domain, address, city, county, caen, j_number,
                source, priority
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', batch)
        conn.commit()

    print(f"    Loaded {count:,} records from {name}")
    return count


def build_index():
    """Build the enrichment index from all sources."""
    print(f"Building enrichment index at {INDEX_PATH}")
    print("=" * 60)

    # Remove existing database
    if os.path.exists(INDEX_PATH):
        os.remove(INDEX_PATH)

    conn = create_database(INDEX_PATH)
    total = 0

    for source in DATA_SOURCES:
        count = load_source(conn, source)
        total += count

    # Update metadata
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)',
              ('last_rebuild', datetime.now().isoformat()))
    c.execute('INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)',
              ('total_records', str(total)))
    conn.commit()

    # Show stats
    print("=" * 60)
    print("Index Statistics:")

    c.execute('SELECT COUNT(DISTINCT cui) FROM companies WHERE cui != ""')
    cui_count = c.fetchone()[0]

    c.execute('SELECT COUNT(DISTINCT email) FROM companies WHERE email != ""')
    email_count = c.fetchone()[0]

    c.execute('SELECT COUNT(DISTINCT phone_normalized) FROM companies WHERE phone_normalized != ""')
    phone_count = c.fetchone()[0]

    c.execute('SELECT COUNT(DISTINCT name_normalized) FROM companies WHERE name_normalized != ""')
    name_count = c.fetchone()[0]

    c.execute('SELECT source, COUNT(*) FROM companies GROUP BY source')
    source_stats = c.fetchall()

    print(f"  Total records: {total:,}")
    print(f"  Unique CUIs: {cui_count:,}")
    print(f"  Unique emails: {email_count:,}")
    print(f"  Unique phones: {phone_count:,}")
    print(f"  Unique names: {name_count:,}")
    print("\nRecords by source:")
    for src, cnt in source_stats:
        print(f"  {src}: {cnt:,}")

    # Vacuum to optimize
    print("\nOptimizing database...")
    conn.execute('VACUUM')

    conn.close()

    db_size = os.path.getsize(INDEX_PATH) / (1024 * 1024)
    print(f"\nDatabase size: {db_size:.1f} MB")
    print(f"Index built successfully: {INDEX_PATH}")


def show_status():
    """Show index status and statistics."""
    if not os.path.exists(INDEX_PATH):
        print("Index not found. Run: python3 build_enrichment_index.py")
        return

    conn = sqlite3.connect(INDEX_PATH)
    c = conn.cursor()

    print(f"Enrichment Index: {INDEX_PATH}")
    print("=" * 60)

    # Metadata
    c.execute('SELECT key, value FROM metadata')
    for key, value in c.fetchall():
        print(f"  {key}: {value}")

    # Stats
    c.execute('SELECT COUNT(*) FROM companies')
    total = c.fetchone()[0]
    print(f"\nTotal records: {total:,}")

    c.execute('SELECT COUNT(DISTINCT cui) FROM companies WHERE cui != ""')
    print(f"Unique CUIs: {c.fetchone()[0]:,}")

    c.execute('SELECT COUNT(DISTINCT email) FROM companies WHERE email != ""')
    print(f"Unique emails: {c.fetchone()[0]:,}")

    c.execute('SELECT COUNT(DISTINCT phone_normalized) FROM companies WHERE phone_normalized != ""')
    print(f"Unique phones: {c.fetchone()[0]:,}")

    print("\nRecords by source:")
    c.execute('SELECT source, COUNT(*) FROM companies GROUP BY source ORDER BY COUNT(*) DESC')
    for src, cnt in c.fetchall():
        print(f"  {src}: {cnt:,}")

    db_size = os.path.getsize(INDEX_PATH) / (1024 * 1024)
    print(f"\nDatabase size: {db_size:.1f} MB")

    conn.close()


def lookup_cui(cui: str):
    """Test lookup by CUI."""
    if not os.path.exists(INDEX_PATH):
        print("Index not found. Run: python3 build_enrichment_index.py")
        return

    conn = sqlite3.connect(INDEX_PATH)
    c = conn.cursor()

    cui_clean = normalize_cui(cui)
    print(f"Looking up CUI: {cui} (normalized: {cui_clean})")
    print("=" * 60)

    c.execute('''
        SELECT name, email, phone, address, city, website, source, priority
        FROM companies
        WHERE cui = ?
        ORDER BY priority ASC
    ''', (cui_clean,))

    results = c.fetchall()
    if not results:
        print("No results found")
        return

    print(f"Found {len(results)} record(s):\n")
    for i, (name, email, phone, address, city, website, source, priority) in enumerate(results, 1):
        print(f"Result {i} (source: {source}, priority: {priority}):")
        print(f"  Name: {name}")
        if email:
            print(f"  Email: {email}")
        if phone:
            print(f"  Phone: {phone}")
        if address:
            print(f"  Address: {address}")
        if city:
            print(f"  City: {city}")
        if website:
            print(f"  Website: {website}")
        print()

    conn.close()


def lookup_name(name: str):
    """Test lookup by company name."""
    if not os.path.exists(INDEX_PATH):
        print("Index not found. Run: python3 build_enrichment_index.py")
        return

    conn = sqlite3.connect(INDEX_PATH)
    c = conn.cursor()

    name_norm = normalize_company_name(name)
    print(f"Looking up name: {name}")
    print(f"Normalized: {name_norm}")
    print("=" * 60)

    # Exact match first
    c.execute('''
        SELECT cui, name, email, phone, address, source
        FROM companies
        WHERE name_normalized = ?
        ORDER BY priority ASC
        LIMIT 10
    ''', (name_norm,))

    results = c.fetchall()
    if results:
        print(f"Exact matches: {len(results)}\n")
        for cui, name, email, phone, address, source in results:
            print(f"  [{source}] {name}")
            if cui:
                print(f"    CUI: {cui}")
            if email:
                print(f"    Email: {email}")
            if phone:
                print(f"    Phone: {phone}")
    else:
        # Try partial match
        c.execute('''
            SELECT cui, name, email, phone, source
            FROM companies
            WHERE name_normalized LIKE ?
            ORDER BY priority ASC
            LIMIT 10
        ''', (f'%{name_norm}%',))

        results = c.fetchall()
        if results:
            print(f"Partial matches: {len(results)}\n")
            for cui, name, email, phone, source in results:
                print(f"  [{source}] {name}")
                if email:
                    print(f"    Email: {email}")
                if phone:
                    print(f"    Phone: {phone}")
        else:
            print("No results found")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description='Build Unified Enrichment Index')
    parser.add_argument('--status', action='store_true', help='Show index status')
    parser.add_argument('--lookup', metavar='CUI', help='Test CUI lookup')
    parser.add_argument('--name', metavar='NAME', help='Test name lookup')

    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.lookup:
        lookup_cui(args.lookup)
    elif args.name:
        lookup_name(args.name)
    else:
        build_index()


if __name__ == '__main__':
    main()
