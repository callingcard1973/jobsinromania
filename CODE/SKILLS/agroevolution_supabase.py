#!/usr/bin/env python3
"""
AgroEvolution Supabase Management Skill

Manage agricultural land listings from MADR data: sync to Supabase, query, filter.

Data source: /opt/ACTIVE/SCRAPERS/ROMANIA/MADR/DATA/madr_lands.csv (9,470 rows)

Usage:
    python3 agroevolution_supabase.py status         # Show stats by judet/categorie
    python3 agroevolution_supabase.py sync           # Read CSV and push to Supabase
    python3 agroevolution_supabase.py search TERM    # Search by localitate, judet, vanzator
    python3 agroevolution_supabase.py category CAT   # Filter by categorie (ARABIL, PASUNI, etc.)
    python3 agroevolution_supabase.py setup          # Print SQL to create table
"""

import os
import sys
import csv
import argparse
import requests
from datetime import datetime
from decimal import Decimal, InvalidOperation

# Supabase config - USER FILLS IN AFTER CREATING PROJECT
SUPABASE_URL = "https://jaurgtjadyiannbalhhb.supabase.co"  # User fills in
SUPABASE_ANON_KEY = "sb_publishable_ENEVh0UgF2Pe98AM7TMJiA_LWzI7l1w"  # User fills in
SUPABASE_SERVICE_KEY = "sb_secret_6M9Pf8i46lvXMjSN3wvBYA_Zr2qiO7R"  # User fills in

# Data source
CSV_PATH = "/opt/ACTIVE/SCRAPERS/ROMANIA/MADR/DATA/madr_lands.csv"

# Valid categories
VALID_CATEGORIES = ['ARABIL', 'PASUNI', 'VII', 'LIVEZI', 'FANEATA', 'PADURI', 'ALTELE']


def get_headers(service=False):
    """Get request headers"""
    key = SUPABASE_SERVICE_KEY if service else SUPABASE_ANON_KEY
    return {
        'apikey': key,
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
        'Prefer': 'count=exact'
    }


def is_configured():
    """Check if Supabase is configured"""
    return (
        SUPABASE_URL != "https://YOUR_PROJECT.supabase.co" and
        SUPABASE_ANON_KEY != "YOUR_ANON_KEY"
    )


def parse_date(date_str):
    """Convert DD.MM.YYYY to YYYY-MM-DD"""
    if not date_str or date_str == '-':
        return None
    try:
        # Try DD.MM.YYYY format
        dt = datetime.strptime(date_str.strip(), '%d.%m.%Y')
        return dt.strftime('%Y-%m-%d')
    except ValueError:
        try:
            # Try ISO format (from scraped_at)
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d')
        except:
            return None


def parse_decimal(value_str):
    """Parse decimal value, handling Romanian format (comma as decimal separator)"""
    if not value_str or value_str == '-':
        return None
    try:
        # Remove currency suffix and whitespace
        clean = value_str.strip().replace(' lei', '').replace(' ', '')
        # Handle Romanian format: 70.638,00 -> 70638.00
        if ',' in clean and '.' in clean:
            # Format like "70.638,00" - thousands separator is dot
            clean = clean.replace('.', '').replace(',', '.')
        elif ',' in clean:
            # Format like "1,4200" - comma is decimal separator
            clean = clean.replace(',', '.')
        return float(clean)
    except (ValueError, InvalidOperation):
        return None


def parse_timestamp(ts_str):
    """Parse ISO timestamp"""
    if not ts_str or ts_str == '-':
        return None
    try:
        return ts_str.replace('T', ' ').split('.')[0]
    except:
        return None


def read_csv():
    """Read CSV file and return rows"""
    if not os.path.exists(CSV_PATH):
        print(f"Error: CSV not found at {CSV_PATH}")
        return []

    rows = []
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def cmd_status(args):
    """Show Supabase stats"""
    print("=" * 60)
    print("AgroEvolution Supabase Status")
    print("=" * 60)

    if not is_configured():
        print("\nSupabase NOT configured. Run 'setup' to get SQL schema.")
        print("Then edit this file to add your Supabase credentials.\n")

        # Show local CSV stats instead
        print("Local CSV Stats:")
        print(f"  Path: {CSV_PATH}")

        rows = read_csv()
        if not rows:
            return 1

        print(f"  Total rows: {len(rows):,}")

        # Count by judet
        by_judet = {}
        by_cat = {}
        for row in rows:
            judet = row.get('judet', '-')
            cat = row.get('categorie', '-')
            by_judet[judet] = by_judet.get(judet, 0) + 1
            by_cat[cat] = by_cat.get(cat, 0) + 1

        print(f"\nBy judet (top 10):")
        for judet, count in sorted(by_judet.items(), key=lambda x: -x[1])[:10]:
            print(f"  {judet}: {count:,}")

        print(f"\nBy categorie:")
        for cat, count in sorted(by_cat.items(), key=lambda x: -x[1]):
            print(f"  {cat}: {count:,}")

        return 0

    print(f"URL: {SUPABASE_URL}")
    print()

    # Total count
    try:
        response = requests.get(
            f'{SUPABASE_URL}/rest/v1/land_listings?select=count',
            headers=get_headers(),
            timeout=10
        )
    except requests.RequestException as e:
        print(f"Connection error: {e}")
        return 1

    if response.status_code in [200, 206]:
        range_header = response.headers.get('content-range', '0-0/0')
        total = int(range_header.split('/')[1])
        print(f"Total listings: {total:,}")
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return 1

    # Count by judet
    print("\nBy judet (top 10):")
    response = requests.get(
        f'{SUPABASE_URL}/rest/v1/land_listings?select=judet',
        headers=get_headers()
    )
    if response.status_code in [200, 206]:
        data = response.json()
        by_judet = {}
        for row in data:
            judet = row.get('judet', '-')
            by_judet[judet] = by_judet.get(judet, 0) + 1
        for judet, count in sorted(by_judet.items(), key=lambda x: -x[1])[:10]:
            print(f"  {judet}: {count:,}")

    # Count by category
    print("\nBy categorie:")
    for cat in VALID_CATEGORIES:
        response = requests.get(
            f'{SUPABASE_URL}/rest/v1/land_listings?select=count&categorie=eq.{cat}',
            headers=get_headers()
        )
        if response.status_code in [200, 206]:
            range_header = response.headers.get('content-range', '0-0/0')
            count = int(range_header.split('/')[1])
            if count > 0:
                print(f"  {cat}: {count:,}")

    return 0


def cmd_sync(args):
    """Sync data from CSV to Supabase"""
    if not is_configured():
        print("Error: Supabase not configured. Run 'setup' first.")
        return 1

    print("Reading CSV...")
    rows = read_csv()
    if not rows:
        return 1

    print(f"Found {len(rows):,} rows in CSV")

    # Clear existing data
    print("Clearing existing Supabase data...")
    headers = get_headers(service=True)
    headers['Prefer'] = 'return=minimal'

    try:
        response = requests.delete(
            f'{SUPABASE_URL}/rest/v1/land_listings?id=gt.0',
            headers=headers,
            timeout=30
        )
        if response.status_code not in [200, 204]:
            print(f"Warning: Clear failed - {response.status_code}")
    except requests.RequestException as e:
        print(f"Warning: Clear request failed - {e}")

    # Insert in batches
    batch_size = 500
    success = 0
    errors = 0

    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        batch_num = i // batch_size + 1

        data = []
        for row in batch:
            # Parse and normalize data
            categorie = row.get('categorie', '').upper().strip()
            if categorie not in VALID_CATEGORIES:
                categorie = 'ALTELE'

            record = {
                'judet': row.get('judet', '-').strip() or '-',
                'localitate': row.get('localitate', '-').strip() or '-',
                'uat': row.get('uat', '-').strip() or '-',
                'nume_vanzator': row.get('nume_vanzator', '-').strip() or '-',
                'telefon': row.get('telefon', '-').strip() or '-',
                'suprafata_ha': parse_decimal(row.get('suprafata_ha', '')),
                'pret_ron': parse_decimal(row.get('pret_ron', '')),
                'categorie': categorie,
                'data_afisarii': parse_date(row.get('data_afisarii', '')),
                'termen': parse_date(row.get('termen', '')),
                'nr_cadastral': row.get('nr_cadastral', '-').strip() or '-',
                'nr_carte_funciara': row.get('nr_carte_funciara', '-').strip() or '-',
                'tarla': row.get('tarla', '-').strip() or '-',
                'parcela': row.get('parcela', '-').strip() or '-',
                'observatii': row.get('observatii', '').strip() or None,
                'scraped_at': parse_timestamp(row.get('scraped_at', ''))
            }
            data.append(record)

        try:
            response = requests.post(
                f'{SUPABASE_URL}/rest/v1/land_listings',
                headers=headers,
                json=data,
                timeout=60
            )

            if response.status_code in [200, 201]:
                success += len(batch)
                print(f"Batch {batch_num}: {len(batch)} inserted")
            else:
                errors += len(batch)
                print(f"Batch {batch_num} error: {response.status_code} - {response.text[:100]}")
        except requests.RequestException as e:
            errors += len(batch)
            print(f"Batch {batch_num} failed: {e}")

    print()
    print(f"Sync complete: {success:,} inserted, {errors:,} errors")
    return 0 if errors == 0 else 1


def cmd_search(args):
    """Search listings by term"""
    term = args.term
    limit = args.limit or 10

    if not is_configured():
        # Search in local CSV
        print(f"Searching locally for: {term}")
        rows = read_csv()

        term_lower = term.lower()
        matches = []
        for row in rows:
            if (term_lower in row.get('localitate', '').lower() or
                term_lower in row.get('judet', '').lower() or
                term_lower in row.get('nume_vanzator', '').lower() or
                term_lower in row.get('uat', '').lower()):
                matches.append(row)

        print(f"Found {len(matches)} results (showing {min(len(matches), limit)})\n")

        for row in matches[:limit]:
            print(f"Judet: {row.get('judet')}")
            print(f"  Localitate: {row.get('localitate')}")
            print(f"  Vanzator: {row.get('nume_vanzator')[:50]}...")
            print(f"  Telefon: {row.get('telefon')}")
            print(f"  Suprafata: {row.get('suprafata_ha')} ha")
            print(f"  Pret: {row.get('pret_ron')} RON")
            print(f"  Categorie: {row.get('categorie')}")
            print()
        return 0

    print(f"Searching Supabase for: {term}")

    try:
        response = requests.get(
            f'{SUPABASE_URL}/rest/v1/land_listings?select=*&or='
            f'(localitate.ilike.*{term}*,judet.ilike.*{term}*,nume_vanzator.ilike.*{term}*,uat.ilike.*{term}*)&limit={limit}',
            headers=get_headers(),
            timeout=10
        )
    except requests.RequestException as e:
        print(f"Error: {e}")
        return 1

    if response.status_code in [200, 206]:
        range_header = response.headers.get('content-range', '0-0/0')
        total = int(range_header.split('/')[1])
        listings = response.json()

        print(f"Found {total} results (showing {len(listings)})\n")

        for listing in listings:
            print(f"ID: {listing.get('id')}")
            print(f"  Judet: {listing.get('judet')}")
            print(f"  Localitate: {listing.get('localitate')}")
            print(f"  Vanzator: {listing.get('nume_vanzator', '-')[:50]}...")
            print(f"  Telefon: {listing.get('telefon')}")
            print(f"  Suprafata: {listing.get('suprafata_ha')} ha")
            print(f"  Pret: {listing.get('pret_ron')} RON")
            print(f"  Categorie: {listing.get('categorie')}")
            print()
    else:
        print(f"Error: {response.status_code}")
        return 1

    return 0


def cmd_category(args):
    """Filter by category"""
    cat = args.category.upper()
    limit = args.limit or 10

    if cat not in VALID_CATEGORIES:
        print(f"Invalid category. Valid: {', '.join(VALID_CATEGORIES)}")
        return 1

    if not is_configured():
        # Search in local CSV
        print(f"Filtering locally by category: {cat}")
        rows = read_csv()

        matches = [r for r in rows if r.get('categorie', '').upper() == cat]
        print(f"Total: {len(matches)} listings (showing {min(len(matches), limit)})\n")

        for row in matches[:limit]:
            vanzator = row.get('nume_vanzator', '-')[:30]
            judet = row.get('judet', '-')
            suprafata = row.get('suprafata_ha', '-')
            pret = row.get('pret_ron', '-')
            print(f"- {vanzator} | {judet} | {suprafata} ha | {pret} RON")
        return 0

    print(f"Category: {cat}")

    try:
        response = requests.get(
            f'{SUPABASE_URL}/rest/v1/land_listings?select=*&categorie=eq.{cat}&limit={limit}',
            headers=get_headers(),
            timeout=10
        )
    except requests.RequestException as e:
        print(f"Error: {e}")
        return 1

    if response.status_code in [200, 206]:
        range_header = response.headers.get('content-range', '0-0/0')
        total = int(range_header.split('/')[1])
        listings = response.json()

        print(f"Total: {total} listings (showing {len(listings)})\n")

        for listing in listings:
            vanzator = listing.get('nume_vanzator', '-')[:30]
            judet = listing.get('judet', '-')
            suprafata = listing.get('suprafata_ha', '-')
            pret = listing.get('pret_ron', '-')
            print(f"- {vanzator} | {judet} | {suprafata} ha | {pret} RON")
    else:
        print(f"Error: {response.status_code}")
        return 1

    return 0


def cmd_setup(args):
    """Print SQL to create table"""
    print("=" * 60)
    print("AgroEvolution Supabase Setup")
    print("=" * 60)
    print()
    print("1. Create a new Supabase project at https://supabase.com")
    print()
    print("2. Run this SQL in the SQL Editor:")
    print()
    print("-" * 60)
    print("""
-- Create land_listings table for MADR agricultural land data
CREATE TABLE land_listings (
    id SERIAL PRIMARY KEY,
    judet VARCHAR(50),
    localitate VARCHAR(100),
    uat VARCHAR(100),
    nume_vanzator VARCHAR(500),
    telefon VARCHAR(200),
    suprafata_ha DECIMAL(10,4),
    pret_ron DECIMAL(15,2),
    categorie VARCHAR(50),  -- ARABIL, PASUNI, VII, LIVEZI, FANEATA, PADURI, ALTELE
    data_afisarii DATE,
    termen DATE,
    nr_cadastral VARCHAR(100),
    nr_carte_funciara VARCHAR(100),
    tarla VARCHAR(100),
    parcela VARCHAR(200),
    observatii TEXT,
    scraped_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX idx_land_judet ON land_listings(judet);
CREATE INDEX idx_land_categorie ON land_listings(categorie);
CREATE INDEX idx_land_localitate ON land_listings(localitate);
CREATE INDEX idx_land_termen ON land_listings(termen);

-- Enable Row Level Security
ALTER TABLE land_listings ENABLE ROW LEVEL SECURITY;

-- Allow public read access
CREATE POLICY "Allow public read" ON land_listings
    FOR SELECT USING (true);

-- Allow service role full access
CREATE POLICY "Allow service role all" ON land_listings
    FOR ALL USING (auth.role() = 'service_role');

-- Grant access
GRANT SELECT ON land_listings TO anon;
GRANT ALL ON land_listings TO service_role;
GRANT USAGE, SELECT ON SEQUENCE land_listings_id_seq TO service_role;
""")
    print("-" * 60)
    print()
    print("3. Get your credentials from Settings > API:")
    print("   - Project URL")
    print("   - anon (public) key")
    print("   - service_role key")
    print()
    print("4. Edit this file and replace the placeholder values:")
    print(f"   File: {__file__}")
    print()
    print("   SUPABASE_URL = 'https://YOUR_PROJECT.supabase.co'")
    print("   SUPABASE_ANON_KEY = 'YOUR_ANON_KEY'")
    print("   SUPABASE_SERVICE_KEY = 'YOUR_SERVICE_KEY'")
    print()
    print("5. Run 'python3 agroevolution_supabase.py sync' to upload data")
    print()

    return 0


def main():
    parser = argparse.ArgumentParser(
        description='AgroEvolution Supabase Management - Agricultural Land Listings',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 agroevolution_supabase.py status
    python3 agroevolution_supabase.py search Timis
    python3 agroevolution_supabase.py category ARABIL
    python3 agroevolution_supabase.py sync
    python3 agroevolution_supabase.py setup
        """
    )
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # status
    subparsers.add_parser('status', help='Show stats by judet and categorie')

    # sync
    subparsers.add_parser('sync', help='Read CSV and push to Supabase')

    # search
    search_parser = subparsers.add_parser('search', help='Search by localitate, judet, vanzator')
    search_parser.add_argument('term', help='Search term')
    search_parser.add_argument('--limit', type=int, default=10, help='Max results')

    # category
    cat_parser = subparsers.add_parser('category', help='Filter by categorie')
    cat_parser.add_argument('category', help='Category (ARABIL, PASUNI, VII, LIVEZI, FANEATA)')
    cat_parser.add_argument('--limit', type=int, default=10, help='Max results')

    # setup
    subparsers.add_parser('setup', help='Print SQL to create table')

    args = parser.parse_args()

    if args.command == 'status':
        return cmd_status(args)
    elif args.command == 'sync':
        return cmd_sync(args)
    elif args.command == 'search':
        return cmd_search(args)
    elif args.command == 'category':
        return cmd_category(args)
    elif args.command == 'setup':
        return cmd_setup(args)
    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    sys.exit(main())
