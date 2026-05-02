#!/usr/bin/env python3
"""
Data Freshness Tracker - Track when datasets were last updated.

Usage:
    python3 data_freshness_tracker.py --check          # Show stale data
    python3 data_freshness_tracker.py --alert          # Alert for stale scrapers
    python3 data_freshness_tracker.py --full           # Full freshness report
"""

import argparse
import os
import re
import psycopg2
from datetime import datetime, timedelta
from pathlib import Path

DB_CONFIG = {'dbname': 'csv_raw', 'user': 'tudor'}

# Data directories to track
DATA_DIRS = [
    '/opt/ACTIVE/OPENDATA/DATA',
    '/mnt/hdd/OPENDATA/DATA',
    '/mnt/hdd/SCRAPER_DATA',
    '/home/tudor/SCRAPER_DATA'
]

# Scraper expectations (name: max_days_old)
SCRAPER_FRESHNESS = {
    'anofm': 1,
    'eures': 7,
    'norway': 3,
    'denmark': 3,
    'sweden': 3,
    'finland': 7,
    'germany': 7,
    'poland': 7,
    'france': 7,
    'italy': 14,
    'spain': 14,
    'anaf': 30
}

# Stale thresholds
STALE_DAYS = 7
CRITICAL_DAYS = 30


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def parse_table_date(table_name):
    """Extract date from table name pattern {name}_{YYYYMMDD}_{hash}."""
    match = re.search(r'_(\d{8})_[a-f0-9]{8}$', table_name)
    if match:
        try:
            return datetime.strptime(match.group(1), '%Y%m%d')
        except:
            pass
    return None


def check_database_freshness():
    """Check freshness of database tables."""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT relname, n_live_tup
        FROM pg_stat_user_tables
        WHERE n_live_tup > 0
        ORDER BY relname
    """)
    tables = cur.fetchall()

    # Group by prefix and find latest date
    prefix_dates = {}
    for table_name, rows in tables:
        date = parse_table_date(table_name)
        if date:
            # Extract prefix (everything before date)
            prefix = re.sub(r'_\d{8}_[a-f0-9]{8}$', '', table_name)
            if prefix not in prefix_dates or date > prefix_dates[prefix]['date']:
                prefix_dates[prefix] = {'date': date, 'table': table_name, 'rows': rows}

    cur.close()
    conn.close()
    return prefix_dates


def check_file_freshness():
    """Check freshness of data files."""
    file_dates = {}

    for data_dir in DATA_DIRS:
        if not os.path.exists(data_dir):
            continue

        for root, dirs, files in os.walk(data_dir):
            for f in files:
                if f.endswith(('.csv', '.json', '.xlsx')):
                    filepath = os.path.join(root, f)
                    try:
                        mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                        size = os.path.getsize(filepath)

                        # Extract category from path
                        rel_path = os.path.relpath(root, data_dir)
                        category = rel_path.split('/')[0] if '/' in rel_path else rel_path

                        if category not in file_dates or mtime > file_dates[category]['date']:
                            file_dates[category] = {
                                'date': mtime,
                                'file': f,
                                'size': size,
                                'path': filepath
                            }
                    except:
                        pass

    return file_dates


def format_age(date):
    """Format age in human readable form."""
    if not date:
        return "unknown"
    delta = datetime.now() - date
    days = delta.days
    if days == 0:
        return "today"
    elif days == 1:
        return "yesterday"
    elif days < 7:
        return f"{days} days ago"
    elif days < 30:
        return f"{days // 7} weeks ago"
    else:
        return f"{days // 30} months ago"


def get_status(date, expected_days=None):
    """Get freshness status."""
    if not date:
        return "UNKNOWN"
    days = (datetime.now() - date).days

    if expected_days and days > expected_days:
        return "STALE"
    elif days > CRITICAL_DAYS:
        return "CRITICAL"
    elif days > STALE_DAYS:
        return "STALE"
    else:
        return "OK"


def check_freshness():
    """Check all data freshness."""
    print("=" * 80)
    print("DATA FRESHNESS CHECK")
    print("=" * 80)

    # Database tables
    print("\n=== DATABASE TABLES ===")
    print(f"{'Prefix':<40} {'Date':>12} {'Age':<15} {'Status':<10} {'Rows':>10}")
    print("-" * 90)

    db_data = check_database_freshness()
    stale_db = []

    for prefix in sorted(db_data.keys()):
        info = db_data[prefix]
        date_str = info['date'].strftime('%Y-%m-%d')
        age = format_age(info['date'])

        # Check expected freshness
        expected = None
        for scraper, days in SCRAPER_FRESHNESS.items():
            if scraper in prefix.lower():
                expected = days
                break

        status = get_status(info['date'], expected)
        if status in ['STALE', 'CRITICAL']:
            stale_db.append((prefix, info, status))

        print(f"{prefix[:40]:<40} {date_str:>12} {age:<15} {status:<10} {info['rows']:>10,}")

    # File data
    print("\n=== DATA FILES ===")
    print(f"{'Category':<30} {'Date':>12} {'Age':<15} {'Status':<10} {'File':<30}")
    print("-" * 100)

    file_data = check_file_freshness()
    stale_files = []

    for category in sorted(file_data.keys()):
        info = file_data[category]
        date_str = info['date'].strftime('%Y-%m-%d')
        age = format_age(info['date'])
        status = get_status(info['date'])

        if status in ['STALE', 'CRITICAL']:
            stale_files.append((category, info, status))

        print(f"{category[:30]:<30} {date_str:>12} {age:<15} {status:<10} {info['file'][:30]:<30}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Database prefixes: {len(db_data)} ({len(stale_db)} stale)")
    print(f"File categories: {len(file_data)} ({len(stale_files)} stale)")

    return stale_db, stale_files


def send_alert(stale_db, stale_files):
    """Send Telegram alert for stale data."""
    if not stale_db and not stale_files:
        print("All data is fresh. No alerts sent.")
        return

    message = "Data Freshness Alert:\n"

    if stale_db:
        message += "\nStale DB tables:\n"
        for prefix, info, status in stale_db[:5]:
            message += f"- {prefix}: {format_age(info['date'])} [{status}]\n"

    if stale_files:
        message += "\nStale files:\n"
        for category, info, status in stale_files[:5]:
            message += f"- {category}: {format_age(info['date'])} [{status}]\n"

    try:
        import sys
        sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
        from alerting import send_telegram
        send_telegram(message)
        print(f"Alert sent via Telegram")
    except Exception as e:
        print(f"Failed to send alert: {e}")
        print(message)


def main():
    parser = argparse.ArgumentParser(description='Data Freshness Tracker')
    parser.add_argument('--check', action='store_true', help='Check freshness')
    parser.add_argument('--alert', action='store_true', help='Send alerts for stale data')
    parser.add_argument('--full', action='store_true', help='Full report')
    parser.add_argument('--stale-days', type=int, default=7, help='Days before stale')
    args = parser.parse_args()

    global STALE_DAYS
    STALE_DAYS = args.stale_days

    stale_db, stale_files = check_freshness()

    if args.alert:
        send_alert(stale_db, stale_files)


if __name__ == '__main__':
    main()
