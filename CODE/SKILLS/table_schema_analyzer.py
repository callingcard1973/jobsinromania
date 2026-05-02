#!/usr/bin/env python3
"""
Table Schema Analyzer - Discover email/phone columns in csv_raw tables.

Usage:
    python3 table_schema_analyzer.py --scan                    # Find all valuable columns
    python3 table_schema_analyzer.py --table TABLE             # Analyze specific table
    python3 table_schema_analyzer.py --sample 100              # Sample rows
    python3 table_schema_analyzer.py --report                  # Full report
"""

import argparse
import re
import psycopg2
from collections import defaultdict

DB_CONFIG = {'dbname': 'csv_raw', 'user': 'tudor'}

# Patterns to detect column types
COLUMN_PATTERNS = {
    'email': {
        'names': ['email', 'e_mail', 'mail', 'contact_email', 'company_email'],
        'regex': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    },
    'phone': {
        'names': ['phone', 'tel', 'telephone', 'mobile', 'fax', 'telefon'],
        'regex': r'^[\d\s\-\+\(\)]{7,20}$'
    },
    'website': {
        'names': ['website', 'url', 'web', 'homepage', 'site'],
        'regex': r'^https?://|^www\.'
    },
    'company': {
        'names': ['company', 'company_name', 'employer', 'organization', 'firma', 'nume_firma'],
        'regex': None
    },
    'address': {
        'names': ['address', 'street', 'city', 'country', 'postal', 'zip', 'adresa'],
        'regex': None
    },
    'identifier': {
        'names': ['cui', 'cif', 'vat', 'tax_id', 'reg_no', 'id', 'code'],
        'regex': r'^\d{5,15}$'
    }
}


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def classify_column(column_name, sample_values):
    """Classify a column by name and content."""
    col_lower = column_name.lower()

    # Check by name first
    for col_type, patterns in COLUMN_PATTERNS.items():
        for name_pattern in patterns['names']:
            if name_pattern in col_lower:
                return col_type

    # Check by content regex
    if sample_values:
        valid_values = [v for v in sample_values if v]
        if valid_values:
            for col_type, patterns in COLUMN_PATTERNS.items():
                if patterns['regex']:
                    regex = re.compile(patterns['regex'])
                    matches = sum(1 for v in valid_values[:100] if regex.match(str(v)))
                    if matches > len(valid_values[:100]) * 0.5:
                        return col_type

    return 'other'


def analyze_table(conn, table_name, sample_size=100):
    """Analyze a single table's schema and content."""
    cur = conn.cursor()

    # Get columns
    cur.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
    """, (table_name,))
    columns = cur.fetchall()

    # Get row count
    cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
    row_count = cur.fetchone()[0]

    results = {
        'table': table_name,
        'rows': row_count,
        'columns': [],
        'valuable_columns': {}
    }

    for col_name, data_type in columns:
        # Sample values
        try:
            cur.execute(f"""
                SELECT "{col_name}" FROM "{table_name}"
                WHERE "{col_name}" IS NOT NULL AND "{col_name}" != ''
                LIMIT {sample_size}
            """)
            sample_values = [row[0] for row in cur.fetchall()]
        except Exception as e:
            conn.rollback()  # Reset transaction on error
            sample_values = []

        col_type = classify_column(col_name, sample_values)
        col_info = {
            'name': col_name,
            'data_type': data_type,
            'classified_as': col_type,
            'non_null_sample': len(sample_values)
        }

        results['columns'].append(col_info)

        if col_type in ['email', 'phone', 'website', 'identifier']:
            results['valuable_columns'][col_type] = col_name

    cur.close()
    return results


def scan_all_tables(min_rows=100):
    """Scan all tables for valuable columns."""
    conn = get_conn()
    cur = conn.cursor()

    # Get tables with row counts
    cur.execute("""
        SELECT relname, n_live_tup
        FROM pg_stat_user_tables
        WHERE n_live_tup >= %s
        ORDER BY n_live_tup DESC
    """, (min_rows,))
    tables = cur.fetchall()

    print("=" * 90)
    print("TABLE SCHEMA ANALYSIS")
    print("=" * 90)
    print(f"{'Table':<45} {'Rows':>10} {'Email':^8} {'Phone':^8} {'Web':^8} {'ID':^8}")
    print("-" * 90)

    valuable_tables = []

    for table_name, rows in tables:
        result = analyze_table(conn, table_name, sample_size=50)
        vc = result['valuable_columns']

        email = 'Yes' if 'email' in vc else '-'
        phone = 'Yes' if 'phone' in vc else '-'
        web = 'Yes' if 'website' in vc else '-'
        identifier = 'Yes' if 'identifier' in vc else '-'

        if any(x == 'Yes' for x in [email, phone, web, identifier]):
            print(f"{table_name[:45]:<45} {rows:>10,} {email:^8} {phone:^8} {web:^8} {identifier:^8}")
            valuable_tables.append(result)

    print("-" * 90)
    print(f"Found {len(valuable_tables)} tables with valuable columns")

    cur.close()
    conn.close()
    return valuable_tables


def detailed_table_report(table_name):
    """Generate detailed report for a table."""
    conn = get_conn()
    result = analyze_table(conn, table_name, sample_size=100)
    conn.close()

    print("=" * 60)
    print(f"TABLE: {table_name}")
    print(f"ROWS: {result['rows']:,}")
    print("=" * 60)

    print("\nCOLUMNS:")
    print(f"{'Column':<30} {'Type':<15} {'Classification':<15} {'Samples'}")
    print("-" * 70)

    for col in result['columns']:
        print(f"{col['name'][:30]:<30} {col['data_type'][:15]:<15} {col['classified_as']:<15} {col['non_null_sample']}")

    if result['valuable_columns']:
        print("\nVALUABLE COLUMNS:")
        for col_type, col_name in result['valuable_columns'].items():
            print(f"  {col_type}: {col_name}")

    return result


def generate_report(output_file=None):
    """Generate full analysis report."""
    results = scan_all_tables(min_rows=100)

    # Summary statistics
    email_tables = sum(1 for r in results if 'email' in r['valuable_columns'])
    phone_tables = sum(1 for r in results if 'phone' in r['valuable_columns'])
    total_rows = sum(r['rows'] for r in results)

    report = [
        "=" * 60,
        "SCHEMA ANALYSIS SUMMARY",
        "=" * 60,
        f"Total tables analyzed: {len(results)}",
        f"Tables with email: {email_tables}",
        f"Tables with phone: {phone_tables}",
        f"Total rows: {total_rows:,}",
        "",
        "TOP TABLES BY EMAIL POTENTIAL:",
    ]

    email_tables_list = [r for r in results if 'email' in r['valuable_columns']]
    email_tables_list.sort(key=lambda x: x['rows'], reverse=True)

    for r in email_tables_list[:20]:
        report.append(f"  {r['table']}: {r['rows']:,} rows")

    report_text = "\n".join(report)
    print(report_text)

    if output_file:
        with open(output_file, 'w') as f:
            f.write(report_text)


def main():
    parser = argparse.ArgumentParser(description='Table Schema Analyzer')
    parser.add_argument('--scan', action='store_true', help='Scan all tables')
    parser.add_argument('--table', '-t', help='Analyze specific table')
    parser.add_argument('--sample', type=int, default=100, help='Sample size')
    parser.add_argument('--report', action='store_true', help='Generate full report')
    parser.add_argument('--min-rows', type=int, default=100, help='Minimum rows')
    parser.add_argument('--output', '-o', help='Output file')
    args = parser.parse_args()

    if args.table:
        detailed_table_report(args.table)
    elif args.report:
        generate_report(args.output)
    else:
        scan_all_tables(args.min_rows)


if __name__ == '__main__':
    main()
