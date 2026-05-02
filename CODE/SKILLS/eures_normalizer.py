#!/usr/bin/env python3
"""
EURES Normalizer - Normalize EURES imports to standard schema and extract emails.

Usage:
    python3 eures_normalizer.py --table TABLE              # Normalize specific table
    python3 eures_normalizer.py --scan                     # Find EURES tables
    python3 eures_normalizer.py --extract-emails TABLE     # Extract emails only
    python3 eures_normalizer.py --normalize-all            # Normalize all EURES tables
"""

import argparse
import re
import psycopg2
from datetime import datetime

DB_CONFIG = {'dbname': 'csv_raw', 'user': 'tudor'}

# Standard output schema
STANDARD_SCHEMA = {
    'email': None,
    'company_name': None,
    'phone': None,
    'country': None,
    'country_code': None,
    'city': None,
    'address': None,
    'website': None,
    'job_title': None,
    'sector': None,
    'source': None
}

# EURES column mappings (source -> standard)
EURES_MAPPINGS = {
    'email': ['email', 'e_mail', 'contact_email', 'employer_email', 'companyemail'],
    'company_name': ['company', 'company_name', 'employer', 'employer_name', 'organization', 'companyname', 'employername'],
    'phone': ['phone', 'telephone', 'tel', 'mobile', 'contact_phone', 'companyphone'],
    'country': ['country', 'country_name', 'nation', 'countryname'],
    'country_code': ['country_code', 'countrycode', 'iso_country', 'location_country'],
    'city': ['city', 'location', 'town', 'municipality', 'postaladdresscity'],
    'address': ['address', 'street', 'full_address', 'postaladdress', 'postaladdressstreetaddress'],
    'website': ['website', 'url', 'web', 'homepage', 'companyurl'],
    'job_title': ['title', 'job_title', 'jobtitle', 'position', 'labeljobvacancy'],
    'sector': ['sector', 'industry', 'nace', 'caen', 'sectorcode']
}


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def get_table_columns(conn, table_name):
    """Get column names for a table."""
    cur = conn.cursor()
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
    """, (table_name,))
    columns = [row[0] for row in cur.fetchall()]
    cur.close()
    return columns


def map_columns(source_columns):
    """Map source columns to standard schema."""
    mappings = {}

    for std_col, patterns in EURES_MAPPINGS.items():
        for pattern in patterns:
            for src_col in source_columns:
                if pattern.lower() == src_col.lower():
                    mappings[std_col] = src_col
                    break
            if std_col in mappings:
                break

    return mappings


def find_eures_tables():
    """Find tables that look like EURES imports."""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT relname, n_live_tup
        FROM pg_stat_user_tables
        WHERE n_live_tup > 0
        ORDER BY relname
    """)
    all_tables = cur.fetchall()

    eures_tables = []
    for table_name, rows in all_tables:
        # Check if it looks like EURES data
        if 'eures' in table_name.lower() or 'europe' in table_name.lower():
            eures_tables.append((table_name, rows))
            continue

        # Check columns for EURES-like structure
        columns = get_table_columns(conn, table_name)
        eures_indicators = ['employer', 'companyname', 'jobtitle', 'countrycode', 'labeljobvacancy']
        matches = sum(1 for ind in eures_indicators for col in columns if ind in col.lower())
        if matches >= 2:
            eures_tables.append((table_name, rows))

    cur.close()
    conn.close()
    return eures_tables


def scan_tables():
    """Scan and report EURES tables."""
    print("=" * 80)
    print("EURES TABLES SCAN")
    print("=" * 80)

    tables = find_eures_tables()

    print(f"{'Table':<50} {'Rows':>12}")
    print("-" * 65)

    total_rows = 0
    for table_name, rows in tables:
        print(f"{table_name[:50]:<50} {rows:>12,}")
        total_rows += rows

    print("-" * 65)
    print(f"Total: {len(tables)} tables, {total_rows:,} rows")

    return tables


def analyze_table(table_name):
    """Analyze a table and show column mapping."""
    conn = get_conn()
    columns = get_table_columns(conn, table_name)
    mappings = map_columns(columns)

    cur = conn.cursor()
    cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
    row_count = cur.fetchone()[0]
    cur.close()
    conn.close()

    print("=" * 60)
    print(f"TABLE: {table_name}")
    print(f"ROWS: {row_count:,}")
    print("=" * 60)

    print("\nCOLUMN MAPPING:")
    print(f"{'Standard':<20} {'Source Column':<30}")
    print("-" * 50)

    for std_col in STANDARD_SCHEMA.keys():
        src_col = mappings.get(std_col, '-')
        print(f"{std_col:<20} {src_col:<30}")

    print("\nUNMAPPED SOURCE COLUMNS:")
    mapped_cols = set(mappings.values())
    unmapped = [c for c in columns if c not in mapped_cols]
    for col in unmapped[:20]:
        print(f"  {col}")

    return mappings


def extract_emails(table_name, output_file=None):
    """Extract unique emails from EURES table."""
    conn = get_conn()
    columns = get_table_columns(conn, table_name)
    mappings = map_columns(columns)

    email_col = mappings.get('email')
    company_col = mappings.get('company_name')
    country_col = mappings.get('country_code') or mappings.get('country')

    if not email_col:
        print(f"No email column found in {table_name}")
        conn.close()
        return []

    # Build query
    select_parts = [f'DISTINCT LOWER(TRIM("{email_col}")) as email']
    if company_col:
        select_parts.append(f'"{company_col}" as company')
    if country_col:
        select_parts.append(f'"{country_col}" as country')

    cur = conn.cursor()
    cur.execute(f"""
        SELECT {', '.join(select_parts)}
        FROM "{table_name}"
        WHERE "{email_col}" IS NOT NULL
        AND "{email_col}" != ''
        AND "{email_col}" ~ '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{{2,}}$'
    """)

    rows = cur.fetchall()
    col_names = [desc[0] for desc in cur.description]

    print(f"Extracted {len(rows):,} unique emails from {table_name}")

    if output_file:
        import csv
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(col_names)
            writer.writerows(rows)
        print(f"Saved to: {output_file}")

    cur.close()
    conn.close()
    return rows


def normalize_table(table_name, output_table=None):
    """Normalize EURES table to standard schema."""
    conn = get_conn()
    columns = get_table_columns(conn, table_name)
    mappings = map_columns(columns)

    if not output_table:
        output_table = f"normalized_{table_name.split('_')[0]}"

    print(f"Normalizing {table_name} -> {output_table}")

    # Build SELECT with mapped columns
    select_parts = []
    for std_col in STANDARD_SCHEMA.keys():
        src_col = mappings.get(std_col)
        if src_col:
            select_parts.append(f'"{src_col}" as {std_col}')
        else:
            select_parts.append(f'NULL as {std_col}')

    cur = conn.cursor()

    # Create output table
    cur.execute(f'DROP TABLE IF EXISTS "{output_table}"')
    cur.execute(f"""
        CREATE TABLE "{output_table}" AS
        SELECT {', '.join(select_parts)},
               '{table_name}' as original_table,
               NOW() as normalized_at
        FROM "{table_name}"
    """)

    cur.execute(f'SELECT COUNT(*) FROM "{output_table}"')
    count = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    print(f"Created {output_table} with {count:,} rows")
    return output_table, count


def normalize_all():
    """Normalize all EURES tables."""
    tables = find_eures_tables()

    print("=" * 70)
    print("NORMALIZING ALL EURES TABLES")
    print("=" * 70)

    total_rows = 0
    for table_name, rows in tables:
        try:
            _, count = normalize_table(table_name)
            total_rows += count
        except Exception as e:
            print(f"Error normalizing {table_name}: {e}")

    print(f"\nTotal normalized: {total_rows:,} rows")


def main():
    parser = argparse.ArgumentParser(description='EURES Normalizer')
    parser.add_argument('--scan', action='store_true', help='Scan for EURES tables')
    parser.add_argument('--table', '-t', help='Specific table to analyze/normalize')
    parser.add_argument('--extract-emails', help='Extract emails from table')
    parser.add_argument('--normalize', action='store_true', help='Normalize table')
    parser.add_argument('--normalize-all', action='store_true', help='Normalize all EURES tables')
    parser.add_argument('--output', '-o', help='Output file/table')
    args = parser.parse_args()

    if args.scan:
        scan_tables()
    elif args.extract_emails:
        extract_emails(args.extract_emails, args.output)
    elif args.normalize_all:
        normalize_all()
    elif args.table:
        if args.normalize:
            normalize_table(args.table, args.output)
        else:
            analyze_table(args.table)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
