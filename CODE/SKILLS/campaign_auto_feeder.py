#!/usr/bin/env python3
"""
Campaign Auto Feeder - Auto-feed csv_raw tables to campaigns based on rules.

Usage:
    python3 campaign_auto_feeder.py --status                   # Show current state
    python3 campaign_auto_feeder.py --rules rules.json         # Load rules
    python3 campaign_auto_feeder.py --dry-run                  # Preview what would be fed
    python3 campaign_auto_feeder.py --feed                     # Execute feed
    python3 campaign_auto_feeder.py --create-rules             # Create default rules
"""

import argparse
import csv
import json
import os
import re
import psycopg2
from datetime import datetime, timedelta
from pathlib import Path

# Default rules file
RULES_FILE = '/opt/ACTIVE/INFRA/SKILLS/campaign_feed_rules.json'

# Default rules
DEFAULT_RULES = {
    "rules": [
        {
            "name": "Norway to norway_emails",
            "source_pattern": "norway.*",
            "target_db": "norway_emails",
            "target_table": "contacts",
            "email_col": "email",
            "company_col": "company",
            "country_filter": ["NO", "Norway", "norge"],
            "min_rows": 100,
            "enabled": True
        },
        {
            "name": "Denmark to denmark_emails",
            "source_pattern": "denmark.*|dk_.*",
            "target_db": "denmark_emails",
            "target_table": "contacts",
            "email_col": "email",
            "company_col": "company",
            "country_filter": ["DK", "Denmark", "danmark"],
            "min_rows": 100,
            "enabled": True
        },
        {
            "name": "Romania to romania_emails",
            "source_pattern": "romania.*|anofm.*|ro_.*",
            "target_db": "romania_emails",
            "target_table": "contacts",
            "email_col": "email",
            "company_col": "company_name",
            "country_filter": ["RO", "Romania"],
            "min_rows": 100,
            "enabled": True
        },
        {
            "name": "HORECA CAEN to romania_emails",
            "source_pattern": ".*horeca.*|.*hotel.*|.*restaurant.*",
            "target_db": "romania_emails",
            "target_table": "contacts",
            "email_col": "email",
            "company_col": "company",
            "caen_filter": ["55*", "56*"],
            "min_rows": 50,
            "enabled": True
        }
    ],
    "global": {
        "skip_existing": True,
        "batch_size": 1000,
        "dedupe_on_insert": True
    }
}


def get_conn(dbname='csv_raw'):
    return psycopg2.connect(dbname=dbname, user='tudor')


def load_rules(rules_file=RULES_FILE):
    """Load feed rules from file."""
    if os.path.exists(rules_file):
        with open(rules_file) as f:
            return json.load(f)
    return DEFAULT_RULES


def save_rules(rules, rules_file=RULES_FILE):
    """Save rules to file."""
    with open(rules_file, 'w') as f:
        json.dump(rules, f, indent=2)
    print(f"Rules saved to: {rules_file}")


def get_source_tables():
    """Get all tables from csv_raw with row counts."""
    conn = get_conn('csv_raw')
    cur = conn.cursor()
    cur.execute("""
        SELECT relname, n_live_tup
        FROM pg_stat_user_tables
        WHERE n_live_tup > 0
        ORDER BY relname
    """)
    tables = cur.fetchall()
    cur.close()
    conn.close()
    return tables


def get_table_columns(dbname, table_name):
    """Get column names for a table."""
    conn = get_conn(dbname)
    cur = conn.cursor()
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
    """, (table_name,))
    columns = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return columns


def find_email_column(columns):
    """Find email column in list."""
    for col in columns:
        if 'email' in col.lower() or 'mail' in col.lower():
            return col
    return None


def find_company_column(columns):
    """Find company column in list."""
    for pattern in ['company', 'firma', 'employer', 'organization', 'companyname']:
        for col in columns:
            if pattern in col.lower():
                return col
    return None


def check_existing_emails(target_db, target_table, emails):
    """Check which emails already exist in target."""
    if not emails:
        return set()

    conn = get_conn(target_db)
    cur = conn.cursor()

    # Get email column
    columns = get_table_columns(target_db, target_table)
    email_col = find_email_column(columns)

    if not email_col:
        cur.close()
        conn.close()
        return set()

    # Check in batches
    existing = set()
    for i in range(0, len(emails), 1000):
        batch = list(emails)[i:i+1000]
        cur.execute(f"""
            SELECT LOWER("{email_col}") FROM "{target_table}"
            WHERE LOWER("{email_col}") = ANY(%s)
        """, (batch,))
        existing.update(row[0] for row in cur.fetchall())

    cur.close()
    conn.close()
    return existing


def match_rule(table_name, rule):
    """Check if table matches rule pattern."""
    pattern = rule.get('source_pattern', '.*')
    return bool(re.match(pattern, table_name, re.IGNORECASE))


def extract_data(source_table, rule):
    """Extract data from source table matching rule."""
    conn = get_conn('csv_raw')
    cur = conn.cursor()

    columns = get_table_columns('csv_raw', source_table)
    email_col = find_email_column(columns)
    company_col = find_company_column(columns)

    if not email_col:
        cur.close()
        conn.close()
        return []

    # Build query
    select_cols = [f'LOWER(TRIM("{email_col}")) as email']
    if company_col:
        select_cols.append(f'"{company_col}" as company')

    query = f"""
        SELECT DISTINCT {', '.join(select_cols)}
        FROM "{source_table}"
        WHERE "{email_col}" IS NOT NULL
        AND "{email_col}" != ''
        AND "{email_col}" ~ '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{{2,}}$'
    """

    cur.execute(query)
    rows = cur.fetchall()

    cur.close()
    conn.close()
    return rows


def feed_to_target(data, rule, dry_run=False):
    """Feed data to target database."""
    target_db = rule['target_db']
    target_table = rule['target_table']

    if not data:
        return 0

    # Check existing emails
    emails = set(row[0] for row in data)
    existing = check_existing_emails(target_db, target_table, emails)

    # Filter out existing
    new_data = [row for row in data if row[0] not in existing]

    if not new_data:
        return 0

    if dry_run:
        print(f"  Would insert {len(new_data)} new rows (skipped {len(existing)} existing)")
        return len(new_data)

    # Insert new data
    conn = get_conn(target_db)
    cur = conn.cursor()

    inserted = 0
    for row in new_data:
        email = row[0]
        company = row[1] if len(row) > 1 else None

        try:
            cur.execute(f"""
                INSERT INTO "{target_table}" (email, company_name, source, created_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT DO NOTHING
            """, (email, company, 'auto_feeder'))
            inserted += 1
        except Exception as e:
            pass  # Skip errors

    conn.commit()
    cur.close()
    conn.close()

    print(f"  Inserted {inserted} new rows (skipped {len(existing)} existing)")
    return inserted


def run_feed(rules_file=RULES_FILE, dry_run=False):
    """Run the auto-feed process."""
    rules = load_rules(rules_file)
    source_tables = get_source_tables()

    print("=" * 70)
    print("CAMPAIGN AUTO FEEDER")
    print("=" * 70)

    total_fed = 0

    for rule in rules['rules']:
        if not rule.get('enabled', True):
            continue

        print(f"\n=== Rule: {rule['name']} ===")
        print(f"Pattern: {rule['source_pattern']}")
        print(f"Target: {rule['target_db']}.{rule['target_table']}")

        matched_tables = []
        for table_name, rows in source_tables:
            if match_rule(table_name, rule) and rows >= rule.get('min_rows', 100):
                matched_tables.append((table_name, rows))

        if not matched_tables:
            print("  No matching tables found")
            continue

        print(f"  Matched {len(matched_tables)} tables")

        for table_name, rows in matched_tables[:10]:  # Limit to 10 tables per rule
            print(f"\n  Processing: {table_name} ({rows:,} rows)")
            data = extract_data(table_name, rule)
            if data:
                fed = feed_to_target(data, rule, dry_run)
                total_fed += fed

    print("\n" + "=" * 70)
    print(f"TOTAL: {'Would feed' if dry_run else 'Fed'} {total_fed} contacts")


def show_status():
    """Show current feed status."""
    rules = load_rules()
    source_tables = get_source_tables()

    print("=" * 70)
    print("CAMPAIGN AUTO FEEDER STATUS")
    print("=" * 70)

    print(f"\nRules file: {RULES_FILE}")
    print(f"Source tables: {len(source_tables)}")

    print("\nEnabled rules:")
    for rule in rules['rules']:
        status = "ENABLED" if rule.get('enabled', True) else "DISABLED"
        print(f"  [{status}] {rule['name']}")
        print(f"    Pattern: {rule['source_pattern']} -> {rule['target_db']}.{rule['target_table']}")


def main():
    parser = argparse.ArgumentParser(description='Campaign Auto Feeder')
    parser.add_argument('--status', action='store_true', help='Show status')
    parser.add_argument('--rules', help='Rules file path')
    parser.add_argument('--dry-run', action='store_true', help='Preview without changes')
    parser.add_argument('--feed', action='store_true', help='Execute feed')
    parser.add_argument('--create-rules', action='store_true', help='Create default rules')
    args = parser.parse_args()

    rules_file = args.rules or RULES_FILE

    if args.create_rules:
        save_rules(DEFAULT_RULES, rules_file)
    elif args.status:
        show_status()
    elif args.feed or args.dry_run:
        run_feed(rules_file, dry_run=args.dry_run)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
