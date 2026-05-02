#!/usr/bin/env python3
"""
Gumroad Data Packager - Package datasets for sale on Gumroad/Payhip/etc.

Usage:
    python3 gumroad_packager.py --list
    python3 gumroad_packager.py --source norway --tiers all
    python3 gumroad_packager.py --source ted --country DEU
    python3 gumroad_packager.py --source norway --tier starter --output /tmp/
"""

import argparse
import csv
import os
import sys
import zipfile
import unicodedata
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

# Data sources
SOURCES = {
    'norway': {
        'table': 'contacts',
        'db': 'norway',
        'name': 'Norway Business Directory',
        'rows': 16979,
        'columns': ['name', 'email', 'phone', 'website', 'city', 'sector', 'sector_name', 'employees_count', 'org_number'],
    },
    'ted': {
        'table': 'ted_winners',
        'db': 'interjob_master',
        'name': 'EU Contract Winners',
        'rows': 1570000,
        'columns': ['contractor', 'contractor_city', 'contractor_country', 'contractor_email', 'contractor_website', 'contract_value', 'cpv'],
    },
}

# Product tiers (adjust based on dataset size)
TIERS = {
    'sample': {'rows': 100, 'price': 0},
    'starter': {'rows': 1000, 'price': 19},
    'pro': {'rows': 5000, 'price': 49},
    'enterprise': {'rows': None, 'price': 99},  # Full dataset
}

# TED country codes
TED_COUNTRIES = {
    'ROU': 285572, 'DEU': 156825, 'POL': 136439, 'FRA': 132433,
    'ESP': 96161, 'CZE': 93084, 'SWE': 73011, 'HUN': 56098,
    'BGR': 45727, 'SVN': 30686, 'ITA': 28166, 'NOR': 13383,
}

OUTPUT_DIR = '/opt/ACTIVE/IDEAS/GUMROAD/products'


def to_ascii(text):
    """Convert text to ASCII."""
    if not text:
        return ''
    normalized = unicodedata.normalize('NFKD', str(text))
    return normalized.encode('ascii', 'ignore').decode('ascii')


def create_readme(source_name, tier, row_count, columns):
    """Generate README for product."""
    return f"""# {source_name} - {tier.title()} Pack

## Dataset Info
- Records: {row_count:,}
- Format: CSV (UTF-8, ASCII-safe)
- Updated: {datetime.now().strftime('%Y-%m-%d')}

## Columns
{chr(10).join(f'- {col}' for col in columns)}

## Usage
This data is sourced from public records (EURES, TED).
For business/research use only.

## License
- Commercial use: Allowed
- Redistribution: Not allowed
- Attribution: Appreciated

## Support
Questions? Contact via Gumroad message.

---
Packaged by InterJob Data Services
"""


def package_db_source(source_key, tier, output_dir, country=None):
    """Package a database-based data source."""
    if not HAS_PSYCOPG2:
        print("Error: psycopg2 not installed")
        return None

    source = SOURCES[source_key]
    tier_config = TIERS[tier]
    limit = tier_config['rows']

    try:
        conn = psycopg2.connect(
            dbname=source['db'],
            user='tudor',
            host='localhost'
        )
        cur = conn.cursor()

        cols = source['columns']
        limit_clause = f"LIMIT {limit}" if limit else ""

        query = f"""
            SELECT {', '.join(cols)}
            FROM {source['table']}
            WHERE email IS NOT NULL AND email != ''
            {limit_clause}
        """

        cur.execute(query)
        rows = cur.fetchall()
        conn.close()

    except Exception as e:
        print(f"Database error: {e}")
        return None

    if not rows:
        print("Error: No data found")
        return None

    # Convert to dicts
    data = []
    for row in rows:
        clean_row = {cols[i]: to_ascii(str(row[i]) if row[i] else '') for i in range(len(cols))}
        data.append(clean_row)

    # Output paths
    product_name = f"{source_key}_{tier}_{len(data)}"
    csv_path = os.path.join(output_dir, f"{product_name}.csv")
    readme_path = os.path.join(output_dir, f"{product_name}_README.txt")
    zip_path = os.path.join(output_dir, f"{product_name}.zip")

    # Write CSV
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        writer.writerows(data)

    # Write README
    with open(readme_path, 'w') as f:
        f.write(create_readme(source['name'], tier, len(data), cols))

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(csv_path, os.path.basename(csv_path))
        zf.write(readme_path, 'README.txt')

    os.remove(csv_path)
    os.remove(readme_path)

    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"Created: {zip_path}")
    print(f"  Rows: {len(data):,}")
    print(f"  Size: {size_mb:.1f} MB")
    print(f"  Price: ${tier_config['price']}")

    return zip_path


def package_ted_source(tier, output_dir, country=None):
    """Package TED database source."""
    if not HAS_PSYCOPG2:
        print("Error: psycopg2 not installed")
        return None

    tier_config = TIERS[tier]
    limit = tier_config['rows']

    try:
        conn = psycopg2.connect(
            dbname='interjob_master',
            user='tudor',
            host='localhost'
        )
        cur = conn.cursor()

        # Build query
        cols = ['contractor', 'contractor_city', 'contractor_country',
                'contractor_email', 'contractor_website', 'contract_value', 'cpv']

        where = ""
        params = []
        if country:
            where = "WHERE contractor_country = %s"
            params = [country]

        limit_clause = f"LIMIT {limit}" if limit else ""

        query = f"""
            SELECT {', '.join(cols)}
            FROM ted_winners
            {where}
            {limit_clause}
        """

        cur.execute(query, params)
        rows = cur.fetchall()

        conn.close()

    except Exception as e:
        print(f"Database error: {e}")
        return None

    if not rows:
        print("Error: No data found")
        return None

    # Convert to dicts
    data = []
    for row in rows:
        clean_row = {cols[i]: to_ascii(str(row[i]) if row[i] else '') for i in range(len(cols))}
        data.append(clean_row)

    # Output paths
    country_suffix = f"_{country}" if country else ""
    product_name = f"ted{country_suffix}_{tier}_{len(data)}"
    csv_path = os.path.join(output_dir, f"{product_name}.csv")
    readme_path = os.path.join(output_dir, f"{product_name}_README.txt")
    zip_path = os.path.join(output_dir, f"{product_name}.zip")

    # Write CSV
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        writer.writerows(data)

    # Write README
    source_name = f"EU Contract Winners ({country})" if country else "EU Contract Winners"
    with open(readme_path, 'w') as f:
        f.write(create_readme(source_name, tier, len(data), cols))

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(csv_path, os.path.basename(csv_path))
        zf.write(readme_path, 'README.txt')

    os.remove(csv_path)
    os.remove(readme_path)

    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"Created: {zip_path}")
    print(f"  Rows: {len(data):,}")
    print(f"  Size: {size_mb:.1f} MB")
    print(f"  Price: ${tier_config['price']}")

    return zip_path


def list_sources():
    """List available data sources."""
    print("\n=== Available Data Sources ===\n")

    for key, source in SOURCES.items():
        print(f"{key}:")
        print(f"  Name: {source['name']}")
        print(f"  Rows: {source['rows']:,}")
        if 'path' in source:
            exists = os.path.exists(source['path'])
            print(f"  Path: {source['path']} ({'OK' if exists else 'MISSING'})")
        if 'table' in source:
            print(f"  Table: {source['table']} (DB: {source['db']})")
        print()

    print("=== TED Countries ===\n")
    for code, count in sorted(TED_COUNTRIES.items(), key=lambda x: -x[1]):
        print(f"  {code}: {count:,}")

    print("\n=== Tiers ===\n")
    for tier, config in TIERS.items():
        rows = config['rows'] or 'Full'
        print(f"  {tier}: {rows} rows @ ${config['price']}")


def main():
    parser = argparse.ArgumentParser(description='Package data for Gumroad')
    parser.add_argument('--list', action='store_true', help='List available sources')
    parser.add_argument('--source', choices=['norway', 'ted'], help='Data source')
    parser.add_argument('--tier', choices=list(TIERS.keys()), default='starter', help='Product tier')
    parser.add_argument('--tiers', choices=['all'], help='Create all tiers')
    parser.add_argument('--country', help='Country code for TED (e.g., DEU, FRA)')
    parser.add_argument('--output', default=OUTPUT_DIR, help='Output directory')

    args = parser.parse_args()

    if args.list:
        list_sources()
        return

    if not args.source:
        parser.print_help()
        return

    # Ensure output dir exists
    os.makedirs(args.output, exist_ok=True)

    # Determine tiers to create
    tiers_to_create = list(TIERS.keys()) if args.tiers == 'all' else [args.tier]

    for tier in tiers_to_create:
        print(f"\n--- Creating {tier} tier ---")

        if args.source == 'norway':
            package_db_source('norway', tier, args.output)
        elif args.source == 'ted':
            package_ted_source(tier, args.output, args.country)


if __name__ == '__main__':
    main()
