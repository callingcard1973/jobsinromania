#!/usr/bin/env python3
"""
PostgreSQL Table Deduplication - Remove duplicate table versions.

Tables follow pattern: {name}_{YYYYMMDD}_{hash}
This script keeps only the latest version of each table prefix.

Usage:
    python3 pg_dedupe_tables.py --check              # Show duplicates
    python3 pg_dedupe_tables.py --auto               # Auto-remove old versions
    python3 pg_dedupe_tables.py --older-than 30      # Remove tables >30 days old
    python3 pg_dedupe_tables.py --prefix contacts    # Dedupe specific prefix
"""

import argparse
import re
import psycopg2
from datetime import datetime, timedelta
from collections import defaultdict

DB_CONFIG = {'dbname': 'csv_raw', 'user': 'tudor'}

# Tables to never delete (critical)
PROTECTED_TABLES = [
    'master_emails',
    'dnc_list',
    'bounces',
]


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def get_tables():
    """Get all tables with size and row count."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT relname, n_live_tup,
               pg_total_relation_size(quote_ident(relname)) as size
        FROM pg_stat_user_tables
        ORDER BY relname
    """)
    tables = cur.fetchall()
    cur.close()
    conn.close()
    return tables


def parse_table_name(name):
    """Parse table name into (prefix, date, hash)."""
    # Pattern: {prefix}_{YYYYMMDD}_{hash8}
    match = re.match(r'^(.+)_(\d{8})_([a-f0-9]{8})$', name)
    if match:
        prefix, date_str, hash_val = match.groups()
        try:
            date = datetime.strptime(date_str, '%Y%m%d')
            return prefix, date, hash_val
        except:
            pass
    return name, None, None


def find_duplicates(tables, prefix_filter=None):
    """Find duplicate tables (same prefix, different dates)."""
    # Group by prefix
    by_prefix = defaultdict(list)

    for name, rows, size in tables:
        prefix, date, hash_val = parse_table_name(name)
        if prefix_filter and prefix_filter not in prefix:
            continue
        by_prefix[prefix].append({
            'name': name,
            'prefix': prefix,
            'date': date,
            'hash': hash_val,
            'rows': rows,
            'size': size,
        })

    # Find prefixes with multiple versions
    duplicates = {}
    for prefix, versions in by_prefix.items():
        if len(versions) > 1:
            # Sort by date (newest first), then by rows (most first)
            versions.sort(key=lambda x: (x['date'] or datetime.min, x['rows']), reverse=True)
            duplicates[prefix] = versions

    return duplicates


def format_size(size):
    """Format size in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def check_duplicates(prefix_filter=None):
    """Check and report duplicates."""
    tables = get_tables()
    duplicates = find_duplicates(tables, prefix_filter)

    if not duplicates:
        print("No duplicate tables found.")
        return [], 0, 0

    print("=" * 70)
    print("DUPLICATE TABLES")
    print("=" * 70)

    total_tables = 0
    total_size = 0
    to_delete = []

    for prefix, versions in sorted(duplicates.items(), key=lambda x: -len(x[1])):
        print(f"\n{prefix} ({len(versions)} versions):")
        for i, v in enumerate(versions):
            date_str = v['date'].strftime('%Y-%m-%d') if v['date'] else 'unknown'
            size_str = format_size(v['size'])
            status = "KEEP" if i == 0 else "DELETE"

            if v['name'] in PROTECTED_TABLES:
                status = "PROTECTED"

            print(f"  [{status:9}] {v['name'][:50]:50} {date_str:12} {v['rows']:>10,} rows {size_str:>10}")

            if status == "DELETE":
                to_delete.append(v)
                total_tables += 1
                total_size += v['size']

    print("\n" + "=" * 70)
    print(f"SUMMARY: {total_tables} tables to delete, {format_size(total_size)} to free")
    print("=" * 70)

    return to_delete, total_tables, total_size


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
        if t['name'] in PROTECTED_TABLES:
            print(f"  SKIP (protected): {t['name']}")
            continue

        if dry_run:
            print(f"  [DRY RUN] Would delete: {t['name']}")
        else:
            try:
                cur.execute(f'DROP TABLE IF EXISTS "{t["name"]}"')
                print(f"  Deleted: {t['name']} ({format_size(t['size'])})")
                deleted += 1
                freed += t['size']
            except Exception as e:
                print(f"  Error deleting {t['name']}: {e}")

    cur.close()
    conn.close()

    if not dry_run:
        print(f"\nDeleted {deleted} tables, freed {format_size(freed)}")

        # Vacuum to reclaim space
        print("Running VACUUM ANALYZE...")
        conn = get_conn()
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("VACUUM ANALYZE")
        cur.close()
        conn.close()
        print("Done.")


def find_old_tables(days):
    """Find tables older than N days."""
    tables = get_tables()
    cutoff = datetime.now() - timedelta(days=days)

    old_tables = []
    for name, rows, size in tables:
        prefix, date, hash_val = parse_table_name(name)
        if date and date < cutoff:
            if name not in PROTECTED_TABLES:
                old_tables.append({
                    'name': name,
                    'date': date,
                    'rows': rows,
                    'size': size,
                })

    return old_tables


def main():
    parser = argparse.ArgumentParser(description='PostgreSQL Table Deduplication')
    parser.add_argument('--check', action='store_true', help='Show duplicates')
    parser.add_argument('--auto', action='store_true', help='Auto-remove old versions')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted')
    parser.add_argument('--older-than', type=int, help='Remove tables older than N days')
    parser.add_argument('--prefix', type=str, help='Filter by prefix')
    parser.add_argument('--vacuum', action='store_true', help='Just run vacuum analyze')
    args = parser.parse_args()

    if args.vacuum:
        print("Running VACUUM ANALYZE...")
        conn = get_conn()
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("VACUUM ANALYZE")
        cur.close()
        conn.close()
        print("Done.")
        return

    if args.older_than:
        print(f"Finding tables older than {args.older_than} days...")
        old_tables = find_old_tables(args.older_than)
        if old_tables:
            print(f"Found {len(old_tables)} old tables:")
            for t in old_tables[:20]:
                print(f"  {t['name']} ({t['date'].strftime('%Y-%m-%d')}, {format_size(t['size'])})")
            if len(old_tables) > 20:
                print(f"  ... and {len(old_tables) - 20} more")

            if args.auto:
                delete_tables(old_tables, dry_run=args.dry_run)
        else:
            print("No old tables found.")
        return

    # Default: check duplicates
    to_delete, count, size = check_duplicates(args.prefix)

    if args.auto and to_delete:
        print("\nProceeding with deletion...")
        delete_tables(to_delete, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
