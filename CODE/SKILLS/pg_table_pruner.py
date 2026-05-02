#!/usr/bin/env python3
"""
PostgreSQL Table Pruner - Auto-cleanup old tables based on retention rules.

Usage:
    python3 pg_table_pruner.py --check                   # Show pruneable tables
    python3 pg_table_pruner.py --older-than 60           # Tables older than 60 days
    python3 pg_table_pruner.py --size-under 1            # Tables smaller than 1MB
    python3 pg_table_pruner.py --empty                   # Empty tables only
    python3 pg_table_pruner.py --auto-delete             # Delete matching tables
"""

import argparse
import re
import psycopg2
from datetime import datetime, timedelta

DB_CONFIG = {'dbname': 'csv_raw', 'user': 'tudor'}

# Tables to NEVER delete
PROTECTED_TABLES = [
    'master_emails',
    'dnc_list',
    'bounces',
    'contacts',
    'companies',
    'sent_emails'
]

# Default retention
DEFAULT_RETENTION_DAYS = 90
DEFAULT_MIN_SIZE_MB = 0.01  # 10KB


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def format_size(size_bytes):
    """Format bytes to human readable."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def parse_table_date(table_name):
    """Extract date from table name pattern {name}_{YYYYMMDD}_{hash}."""
    match = re.search(r'_(\d{8})_[a-f0-9]{8}$', table_name)
    if match:
        try:
            return datetime.strptime(match.group(1), '%Y%m%d')
        except:
            pass
    return None


def is_protected(table_name):
    """Check if table is protected from deletion."""
    for protected in PROTECTED_TABLES:
        if protected in table_name.lower():
            return True
    return False


def get_tables():
    """Get all tables with metadata."""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT relname, n_live_tup, pg_total_relation_size(quote_ident(relname))
        FROM pg_stat_user_tables
        ORDER BY relname
    """)
    tables = []
    for name, rows, size in cur.fetchall():
        date = parse_table_date(name)
        age_days = (datetime.now() - date).days if date else None
        tables.append({
            'name': name,
            'rows': rows,
            'size': size,
            'date': date,
            'age_days': age_days,
            'protected': is_protected(name)
        })

    cur.close()
    conn.close()
    return tables


def find_pruneable(older_than=None, size_under=None, empty_only=False):
    """Find tables matching prune criteria."""
    tables = get_tables()
    pruneable = []

    for t in tables:
        if t['protected']:
            continue

        reasons = []

        # Age check
        if older_than and t['age_days'] and t['age_days'] > older_than:
            reasons.append(f"older than {older_than} days")

        # Size check (in MB)
        if size_under and t['size'] < size_under * 1024 * 1024:
            reasons.append(f"smaller than {size_under}MB")

        # Empty check
        if empty_only and t['rows'] == 0:
            reasons.append("empty")

        if reasons:
            t['reasons'] = reasons
            pruneable.append(t)

    return pruneable


def check_pruneable(older_than=None, size_under=None, empty_only=False):
    """Check and report pruneable tables."""
    print("=" * 80)
    print("TABLE PRUNER - PRUNEABLE TABLES")
    print("=" * 80)

    criteria = []
    if older_than:
        criteria.append(f"older than {older_than} days")
    if size_under:
        criteria.append(f"smaller than {size_under}MB")
    if empty_only:
        criteria.append("empty tables")

    print(f"Criteria: {', '.join(criteria) if criteria else 'default (>90 days or empty)'}")
    print()

    pruneable = find_pruneable(older_than, size_under, empty_only)

    if not pruneable:
        print("No tables match pruning criteria.")
        return [], 0

    print(f"{'Table':<50} {'Rows':>10} {'Size':>10} {'Age':>8} Reason")
    print("-" * 90)

    total_size = 0
    for t in pruneable[:50]:  # Show first 50
        age_str = f"{t['age_days']}d" if t['age_days'] else "?"
        reason = ', '.join(t['reasons'])
        print(f"{t['name'][:50]:<50} {t['rows']:>10,} {format_size(t['size']):>10} {age_str:>8} {reason}")
        total_size += t['size']

    if len(pruneable) > 50:
        print(f"... and {len(pruneable) - 50} more")

    print("-" * 90)
    print(f"Total: {len(pruneable)} tables, {format_size(total_size)} to free")

    return pruneable, total_size


def delete_tables(tables, dry_run=False):
    """Delete specified tables."""
    if not tables:
        print("No tables to delete.")
        return

    conn = get_conn()
    conn.autocommit = True
    cur = conn.cursor()

    deleted = 0
    freed = 0

    for t in tables:
        if t['protected']:
            print(f"  SKIP (protected): {t['name']}")
            continue

        if dry_run:
            print(f"  [DRY RUN] Would delete: {t['name']} ({format_size(t['size'])})")
        else:
            try:
                cur.execute(f'DROP TABLE IF EXISTS "{t["name"]}"')
                print(f"  Deleted: {t['name']} ({format_size(t['size'])})")
                deleted += 1
                freed += t['size']
            except Exception as e:
                print(f"  Error: {t['name']}: {e}")

    cur.close()
    conn.close()

    if not dry_run and deleted > 0:
        print(f"\nDeleted {deleted} tables, freed {format_size(freed)}")

        # Run vacuum
        print("Running VACUUM ANALYZE...")
        conn = get_conn()
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("VACUUM ANALYZE")
        cur.close()
        conn.close()
        print("Done.")


def main():
    parser = argparse.ArgumentParser(description='PostgreSQL Table Pruner')
    parser.add_argument('--check', action='store_true', help='Check pruneable tables')
    parser.add_argument('--older-than', type=int, help='Tables older than N days')
    parser.add_argument('--size-under', type=float, help='Tables smaller than N MB')
    parser.add_argument('--empty', action='store_true', help='Empty tables only')
    parser.add_argument('--auto-delete', action='store_true', help='Delete matching tables')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted')
    args = parser.parse_args()

    # Default criteria if none specified
    older_than = args.older_than
    size_under = args.size_under
    empty_only = args.empty

    if not any([older_than, size_under, empty_only]):
        # Default: old or empty
        older_than = DEFAULT_RETENTION_DAYS
        empty_only = True

    pruneable, total_size = check_pruneable(older_than, size_under, empty_only)

    if args.auto_delete and pruneable:
        print("\nProceeding with deletion...")
        delete_tables(pruneable, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
