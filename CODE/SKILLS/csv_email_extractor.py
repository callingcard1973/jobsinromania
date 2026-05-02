#!/usr/bin/env python3
"""
CSV Email Extractor - Extract emails from csv_raw tables to campaign-ready format.

Usage:
    python3 csv_email_extractor.py --table TABLE_NAME           # Extract from specific table
    python3 csv_email_extractor.py --scan                       # Find tables with emails
    python3 csv_email_extractor.py --table TABLE -o output.csv  # Export to file
    python3 csv_email_extractor.py --all-with-emails            # Extract from all tables with emails
"""

import argparse
import csv
import re
import psycopg2
from datetime import datetime

DB_CONFIG = {'dbname': 'csv_raw', 'user': 'tudor'}
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

# Columns likely to contain emails
EMAIL_COLUMN_NAMES = [
    'email', 'e_mail', 'mail', 'email_address', 'emailaddress',
    'contact_email', 'company_email', 'work_email', 'business_email',
    'employer_email', 'recruiter_email', 'hr_email'
]

# Columns for company info
COMPANY_COLUMNS = ['company', 'company_name', 'companyname', 'employer', 'employer_name', 'organization', 'firma', 'nume_firma']
NAME_COLUMNS = ['name', 'contact_name', 'contact', 'person', 'full_name', 'firstname', 'lastname']
PHONE_COLUMNS = ['phone', 'telephone', 'tel', 'mobile', 'phone_number', 'telefon']
COUNTRY_COLUMNS = ['country', 'country_code', 'nation', 'tara']
CITY_COLUMNS = ['city', 'location', 'oras', 'localitate', 'town']


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


def find_email_column(columns):
    """Find the email column in a list of columns."""
    columns_lower = [c.lower() for c in columns]
    for email_col in EMAIL_COLUMN_NAMES:
        if email_col in columns_lower:
            idx = columns_lower.index(email_col)
            return columns[idx]
    # Fuzzy match
    for col in columns:
        if 'email' in col.lower() or 'mail' in col.lower():
            return col
    return None


def find_column(columns, candidates):
    """Find a column from candidate list."""
    columns_lower = [c.lower() for c in columns]
    for candidate in candidates:
        if candidate in columns_lower:
            idx = columns_lower.index(candidate)
            return columns[idx]
    return None


def scan_tables():
    """Scan all tables for email columns."""
    conn = get_conn()
    cur = conn.cursor()

    # Get all tables with row counts
    cur.execute("""
        SELECT relname, n_live_tup
        FROM pg_stat_user_tables
        WHERE n_live_tup > 0
        ORDER BY n_live_tup DESC
    """)
    tables = cur.fetchall()

    print("=" * 80)
    print("TABLES WITH EMAIL COLUMNS")
    print("=" * 80)
    print(f"{'Table':<50} {'Rows':>10} {'Email Column':<20}")
    print("-" * 80)

    tables_with_email = []
    for table_name, rows in tables:
        columns = get_table_columns(conn, table_name)
        email_col = find_email_column(columns)
        if email_col:
            print(f"{table_name[:50]:<50} {rows:>10,} {email_col:<20}")
            tables_with_email.append((table_name, rows, email_col))

    print("-" * 80)
    print(f"Found {len(tables_with_email)} tables with email columns")

    cur.close()
    conn.close()
    return tables_with_email


def count_valid_emails(conn, table_name, email_col):
    """Count valid emails in a table."""
    cur = conn.cursor()
    cur.execute(f"""
        SELECT COUNT(*) FROM "{table_name}"
        WHERE "{email_col}" IS NOT NULL
        AND "{email_col}" != ''
        AND "{email_col}" ~ '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{{2,}}$'
    """)
    count = cur.fetchone()[0]
    cur.close()
    return count


def extract_emails(table_name, output_file=None, limit=None):
    """Extract emails from a table."""
    conn = get_conn()
    columns = get_table_columns(conn, table_name)

    email_col = find_email_column(columns)
    if not email_col:
        print(f"No email column found in {table_name}")
        print(f"Available columns: {columns[:10]}...")
        conn.close()
        return []

    company_col = find_column(columns, COMPANY_COLUMNS)
    name_col = find_column(columns, NAME_COLUMNS)
    phone_col = find_column(columns, PHONE_COLUMNS)
    country_col = find_column(columns, COUNTRY_COLUMNS)
    city_col = find_column(columns, CITY_COLUMNS)

    # Build SELECT query
    select_cols = [f'"{email_col}" as email']
    if company_col:
        select_cols.append(f'"{company_col}" as company')
    if name_col:
        select_cols.append(f'"{name_col}" as name')
    if phone_col:
        select_cols.append(f'"{phone_col}" as phone')
    if country_col:
        select_cols.append(f'"{country_col}" as country')
    if city_col:
        select_cols.append(f'"{city_col}" as city')

    query = f"""
        SELECT DISTINCT {', '.join(select_cols)}
        FROM "{table_name}"
        WHERE "{email_col}" IS NOT NULL
        AND "{email_col}" != ''
        AND "{email_col}" ~ '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{{2,}}$'
    """

    if limit:
        query += f" LIMIT {limit}"

    cur = conn.cursor()
    cur.execute(query)

    # Get column names from description
    col_names = [desc[0] for desc in cur.description]
    rows = cur.fetchall()

    print(f"Extracted {len(rows)} unique emails from {table_name}")
    print(f"Columns: {col_names}")

    if output_file:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(col_names)
            writer.writerows(rows)
        print(f"Saved to: {output_file}")

    cur.close()
    conn.close()
    return rows


def extract_all_with_emails(output_dir='/opt/DATA/extracted_emails'):
    """Extract emails from all tables that have them."""
    import os
    os.makedirs(output_dir, exist_ok=True)

    tables = scan_tables()
    print(f"\nExtracting from {len(tables)} tables...")

    total_emails = 0
    for table_name, rows, email_col in tables:
        if rows < 100:  # Skip tiny tables
            continue

        output_file = os.path.join(output_dir, f"{table_name}_emails.csv")
        extracted = extract_emails(table_name, output_file)
        total_emails += len(extracted)

    print(f"\n=== SUMMARY ===")
    print(f"Total unique emails extracted: {total_emails}")
    print(f"Output directory: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description='CSV Email Extractor')
    parser.add_argument('--table', '-t', help='Table name to extract from')
    parser.add_argument('--scan', action='store_true', help='Scan for tables with emails')
    parser.add_argument('--output', '-o', help='Output CSV file')
    parser.add_argument('--limit', type=int, help='Limit rows extracted')
    parser.add_argument('--all-with-emails', action='store_true', help='Extract from all tables')
    parser.add_argument('--count', action='store_true', help='Just count valid emails')
    args = parser.parse_args()

    if args.scan:
        scan_tables()
    elif args.all_with_emails:
        extract_all_with_emails()
    elif args.table:
        if args.count:
            conn = get_conn()
            columns = get_table_columns(conn, args.table)
            email_col = find_email_column(columns)
            if email_col:
                count = count_valid_emails(conn, args.table, email_col)
                print(f"{args.table}: {count:,} valid emails")
            conn.close()
        else:
            extract_emails(args.table, args.output, args.limit)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
