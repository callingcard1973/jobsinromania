#!/usr/bin/env python3
"""
Cross-Database Deduplication - Find duplicate companies/contacts across databases.

Usage:
    python3 cross_db_dedup.py --scan                           # Scan all databases
    python3 cross_db_dedup.py --match-by email                 # Find by email
    python3 cross_db_dedup.py --match-by cui                   # Find by CUI
    python3 cross_db_dedup.py --databases csv_raw,romania      # Specific DBs
    python3 cross_db_dedup.py --report                         # Generate report
"""

import argparse
import psycopg2
from collections import defaultdict

# Databases to check
DATABASES = ['csv_raw', 'interjob_master', 'romania', 'romania_emails', 'norway_emails']

# Column mappings for different match types
MATCH_COLUMNS = {
    'email': ['email', 'e_mail', 'mail', 'email_address', 'company_email'],
    'cui': ['cui', 'cif', 'fiscal_code', 'vat', 'tax_id', 'company_id'],
    'company_name': ['company', 'company_name', 'companyname', 'employer', 'firma', 'nume_firma', 'organization'],
    'phone': ['phone', 'telephone', 'tel', 'mobile', 'telefon']
}


def get_conn(dbname):
    try:
        return psycopg2.connect(dbname=dbname, user='tudor')
    except:
        return None


def get_tables_with_column(conn, column_patterns):
    """Find tables that have matching columns."""
    cur = conn.cursor()
    tables = []

    for pattern in column_patterns:
        cur.execute("""
            SELECT DISTINCT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND LOWER(column_name) = LOWER(%s)
        """, (pattern,))
        tables.extend(cur.fetchall())

    cur.close()
    return tables


def get_unique_values(conn, table_name, column_name, limit=100000):
    """Get unique non-null values from a column."""
    cur = conn.cursor()
    try:
        cur.execute(f"""
            SELECT DISTINCT LOWER(TRIM("{column_name}"))
            FROM "{table_name}"
            WHERE "{column_name}" IS NOT NULL
            AND "{column_name}" != ''
            LIMIT {limit}
        """)
        values = set(row[0] for row in cur.fetchall() if row[0])
    except Exception as e:
        values = set()
    cur.close()
    return values


def scan_databases(databases, match_type):
    """Scan databases for matching columns."""
    column_patterns = MATCH_COLUMNS.get(match_type, [match_type])

    print("=" * 70)
    print(f"SCANNING FOR {match_type.upper()} COLUMNS")
    print("=" * 70)

    all_sources = []

    for dbname in databases:
        conn = get_conn(dbname)
        if not conn:
            print(f"  {dbname}: connection failed")
            continue

        tables = get_tables_with_column(conn, column_patterns)
        if tables:
            print(f"\n{dbname}:")
            for table, col in tables[:10]:
                cur = conn.cursor()
                cur.execute(f'SELECT COUNT(DISTINCT "{col}") FROM "{table}" WHERE "{col}" IS NOT NULL')
                count = cur.fetchone()[0]
                cur.close()
                print(f"  {table}.{col}: {count:,} unique values")
                all_sources.append((dbname, table, col, count))

        conn.close()

    return all_sources


def find_duplicates(databases, match_type, min_matches=2):
    """Find duplicate values across databases."""
    column_patterns = MATCH_COLUMNS.get(match_type, [match_type])

    print("=" * 70)
    print(f"FINDING DUPLICATE {match_type.upper()}S ACROSS DATABASES")
    print("=" * 70)

    # Collect all values with their sources
    value_sources = defaultdict(list)

    for dbname in databases:
        conn = get_conn(dbname)
        if not conn:
            continue

        tables = get_tables_with_column(conn, column_patterns)

        for table, col in tables:
            values = get_unique_values(conn, table, col, limit=50000)
            for val in values:
                if val and len(val) > 3:  # Skip very short values
                    value_sources[val].append(f"{dbname}.{table}")

        conn.close()

    # Find values in multiple sources
    duplicates = {k: v for k, v in value_sources.items() if len(set(v)) >= min_matches}

    print(f"\nFound {len(duplicates):,} {match_type}s in {min_matches}+ databases")

    if duplicates:
        print(f"\nSample duplicates:")
        for val, sources in list(duplicates.items())[:20]:
            unique_sources = list(set(sources))
            print(f"  {val[:40]:40} -> {', '.join(unique_sources[:3])}")

    return duplicates


def generate_report(databases, output_file=None):
    """Generate comprehensive deduplication report."""
    report = []
    report.append("=" * 70)
    report.append("CROSS-DATABASE DEDUPLICATION REPORT")
    report.append(f"Databases: {', '.join(databases)}")
    report.append("=" * 70)

    for match_type in ['email', 'cui', 'company_name']:
        duplicates = find_duplicates(databases, match_type)
        report.append(f"\n{match_type.upper()}: {len(duplicates):,} duplicates found")

    report_text = "\n".join(report)
    print(report_text)

    if output_file:
        with open(output_file, 'w') as f:
            f.write(report_text)
        print(f"\nReport saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Cross-Database Deduplication')
    parser.add_argument('--scan', action='store_true', help='Scan for matching columns')
    parser.add_argument('--match-by', choices=['email', 'cui', 'company_name', 'phone'], help='Match type')
    parser.add_argument('--databases', help='Comma-separated database list')
    parser.add_argument('--report', action='store_true', help='Generate full report')
    parser.add_argument('--output', '-o', help='Output file')
    parser.add_argument('--min-matches', type=int, default=2, help='Minimum sources for duplicate')
    args = parser.parse_args()

    databases = args.databases.split(',') if args.databases else DATABASES

    if args.report:
        generate_report(databases, args.output)
    elif args.scan:
        for match_type in ['email', 'cui', 'company_name', 'phone']:
            scan_databases(databases, match_type)
    elif args.match_by:
        find_duplicates(databases, args.match_by, args.min_matches)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
