#!/usr/bin/env python3
"""
PostgreSQL HDD Defaults - Ensure bulk databases are on HDD tablespace.

NVMe (pg_default): Hot data, frequently accessed, small DBs
HDD (hdd_storage): Bulk data, archives, large imports

Usage:
    python3 pg_hdd_defaults.py --check          # Check all databases
    python3 pg_hdd_defaults.py --move DB_NAME   # Move database to HDD
    python3 pg_hdd_defaults.py --auto           # Auto-move large DBs to HDD
"""

import argparse
import psycopg2
import sys

# Databases that should ALWAYS be on HDD (bulk/archive data)
HDD_DATABASES = [
    'csv_raw',           # Bulk CSV imports
    'opendata',          # Open data archive
    'interjob_master',   # Master company database
    'romania',           # Romania company data
]

# Databases that should stay on NVMe (frequently accessed)
NVME_DATABASES = [
    'romania_emails',    # Active campaign contacts
    'email_sender',      # Send logs (frequently written)
    'norway_emails',     # Active campaign
    'denmark_emails',    # Active campaign
]

# Auto-move threshold: databases larger than this go to HDD
SIZE_THRESHOLD_GB = 2.0

HDD_TABLESPACE = 'hdd_storage'
NVME_TABLESPACE = 'pg_default'


def get_conn():
    return psycopg2.connect(dbname='postgres', user='tudor')


def get_databases():
    """Get all databases with their tablespace and size."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT d.datname, t.spcname, pg_database_size(d.datname) as size
        FROM pg_database d
        JOIN pg_tablespace t ON d.dattablespace = t.oid
        WHERE d.datistemplate = false AND d.datname != 'postgres'
        ORDER BY pg_database_size(d.datname) DESC
    """)
    dbs = cur.fetchall()
    cur.close()
    conn.close()
    return dbs


def move_database(dbname, tablespace):
    """Move database to specified tablespace."""
    conn = get_conn()
    conn.autocommit = True
    cur = conn.cursor()

    try:
        print(f"Moving {dbname} to {tablespace}...")
        cur.execute(f"ALTER DATABASE {dbname} SET TABLESPACE {tablespace}")
        print(f"  Done: {dbname} -> {tablespace}")
        return True
    except Exception as e:
        print(f"  Error: {e}")
        return False
    finally:
        cur.close()
        conn.close()


def check_databases():
    """Check all databases and report issues."""
    dbs = get_databases()

    print("=" * 60)
    print("DATABASE TABLESPACE CHECK")
    print("=" * 60)
    print(f"{'Database':<25} {'Tablespace':<15} {'Size':>10} {'Status':<10}")
    print("-" * 60)

    issues = []

    for dbname, tablespace, size in dbs:
        size_gb = size / (1024**3)
        size_str = f"{size_gb:.1f} GB" if size_gb >= 1 else f"{size/(1024**2):.0f} MB"

        # Determine expected tablespace
        if dbname in HDD_DATABASES:
            expected = HDD_TABLESPACE
        elif dbname in NVME_DATABASES:
            expected = NVME_TABLESPACE
        elif size_gb > SIZE_THRESHOLD_GB:
            expected = HDD_TABLESPACE
        else:
            expected = NVME_TABLESPACE

        if tablespace == expected:
            status = "OK"
        else:
            status = f"WRONG (should be {expected})"
            issues.append((dbname, tablespace, expected))

        print(f"{dbname:<25} {tablespace:<15} {size_str:>10} {status}")

    print("-" * 60)

    if issues:
        print(f"\n{len(issues)} database(s) need to be moved:")
        for dbname, current, expected in issues:
            print(f"  {dbname}: {current} -> {expected}")
        print("\nRun with --auto to fix automatically")
    else:
        print("\nAll databases are on correct tablespaces.")

    return issues


def auto_move():
    """Automatically move databases to correct tablespaces."""
    issues = check_databases()

    if not issues:
        return

    print("\n" + "=" * 60)
    print("AUTO-MOVING DATABASES")
    print("=" * 60)

    for dbname, current, expected in issues:
        move_database(dbname, expected)


def main():
    parser = argparse.ArgumentParser(description='PostgreSQL HDD Defaults')
    parser.add_argument('--check', action='store_true', help='Check all databases')
    parser.add_argument('--move', type=str, help='Move specific database to HDD')
    parser.add_argument('--auto', action='store_true', help='Auto-move large DBs to HDD')
    parser.add_argument('--list', action='store_true', help='List HDD/NVMe assignments')
    args = parser.parse_args()

    if args.list:
        print("HDD Databases (bulk/archive):", HDD_DATABASES)
        print("NVMe Databases (hot/active):", NVME_DATABASES)
        print(f"Auto-move threshold: >{SIZE_THRESHOLD_GB} GB")
        return

    if args.move:
        move_database(args.move, HDD_TABLESPACE)
        return

    if args.auto:
        auto_move()
        return

    # Default: check
    check_databases()


if __name__ == '__main__':
    main()
