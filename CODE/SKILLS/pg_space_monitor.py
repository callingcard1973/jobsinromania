#!/usr/bin/env python3
"""
PostgreSQL Space Monitor - Track disk usage trends and alert.

Usage:
    python3 pg_space_monitor.py --check           # Current usage
    python3 pg_space_monitor.py --daily-report    # Size changes
    python3 pg_space_monitor.py --forecast        # Predict when full
    python3 pg_space_monitor.py --alert           # Send alerts if >threshold
"""

import argparse
import json
import os
import psycopg2
from datetime import datetime, timedelta
from pathlib import Path

HISTORY_FILE = '/opt/ACTIVE/INFRA/GOVERNOR/pg_space_history.json'
ALERT_THRESHOLD_PERCENT = 85
CRITICAL_THRESHOLD_PERCENT = 95

# Tablespace paths
TABLESPACES = {
    'pg_default': '/var/lib/postgresql/15/main',
    'hdd_storage': '/mnt/hdd/postgresql'
}


def get_conn():
    return psycopg2.connect(dbname='postgres', user='tudor')


def format_size(size_bytes):
    """Format bytes to human readable."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def get_database_sizes():
    """Get all database sizes."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT d.datname, t.spcname, pg_database_size(d.datname)
        FROM pg_database d
        JOIN pg_tablespace t ON d.dattablespace = t.oid
        WHERE d.datistemplate = false
        ORDER BY pg_database_size(d.datname) DESC
    """)
    results = cur.fetchall()
    cur.close()
    conn.close()
    return results


def get_tablespace_sizes():
    """Get tablespace disk usage."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT spcname, pg_tablespace_size(oid)
        FROM pg_tablespace
        WHERE spcname != 'pg_global'
    """)
    results = cur.fetchall()
    cur.close()
    conn.close()
    return results


def get_disk_usage(path):
    """Get disk usage for a path."""
    try:
        stat = os.statvfs(path)
        total = stat.f_blocks * stat.f_frsize
        free = stat.f_bavail * stat.f_frsize
        used = total - free
        return {'total': total, 'used': used, 'free': free, 'percent': (used / total) * 100}
    except:
        return None


def load_history():
    """Load historical data."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return {'entries': []}


def save_history(data):
    """Save historical data."""
    Path(HISTORY_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def record_snapshot():
    """Record current state for historical tracking."""
    history = load_history()

    dbs = get_database_sizes()
    snapshot = {
        'timestamp': datetime.now().isoformat(),
        'databases': {name: size for name, ts, size in dbs},
        'tablespaces': {name: size for name, size in get_tablespace_sizes()}
    }

    history['entries'].append(snapshot)
    # Keep last 90 days
    cutoff = (datetime.now() - timedelta(days=90)).isoformat()
    history['entries'] = [e for e in history['entries'] if e['timestamp'] > cutoff]

    save_history(history)
    return snapshot


def check_usage():
    """Check current usage."""
    print("=" * 60)
    print("POSTGRESQL SPACE MONITOR")
    print("=" * 60)

    # Database sizes
    print("\n=== DATABASES ===")
    print(f"{'Database':<25} {'Tablespace':<15} {'Size':>12}")
    print("-" * 55)

    total_size = 0
    dbs = get_database_sizes()
    for name, tablespace, size in dbs:
        total_size += size
        print(f"{name:<25} {tablespace:<15} {format_size(size):>12}")

    print("-" * 55)
    print(f"{'TOTAL':<25} {'':<15} {format_size(total_size):>12}")

    # Disk usage
    print("\n=== DISK USAGE ===")
    for ts_name, path in TABLESPACES.items():
        usage = get_disk_usage(path)
        if usage:
            status = "OK"
            if usage['percent'] > CRITICAL_THRESHOLD_PERCENT:
                status = "CRITICAL"
            elif usage['percent'] > ALERT_THRESHOLD_PERCENT:
                status = "WARNING"

            print(f"{ts_name} ({path}):")
            print(f"  Used: {format_size(usage['used'])} / {format_size(usage['total'])} ({usage['percent']:.1f}%) [{status}]")
            print(f"  Free: {format_size(usage['free'])}")

    # Record snapshot
    record_snapshot()

    return dbs


def daily_report():
    """Show daily size changes."""
    history = load_history()
    if len(history['entries']) < 2:
        print("Not enough history for daily report. Run --check first.")
        return

    print("=" * 70)
    print("DAILY SIZE CHANGES")
    print("=" * 70)

    # Compare last two entries
    latest = history['entries'][-1]

    # Find entry from ~24h ago
    yesterday = datetime.now() - timedelta(hours=24)
    previous = None
    for entry in reversed(history['entries'][:-1]):
        entry_time = datetime.fromisoformat(entry['timestamp'])
        if entry_time < yesterday:
            previous = entry
            break

    if not previous:
        previous = history['entries'][0]

    print(f"\nComparing: {previous['timestamp'][:16]} -> {latest['timestamp'][:16]}")
    print(f"\n{'Database':<30} {'Previous':>12} {'Current':>12} {'Change':>12}")
    print("-" * 70)

    all_dbs = set(latest['databases'].keys()) | set(previous['databases'].keys())
    total_change = 0

    for db in sorted(all_dbs):
        prev_size = previous['databases'].get(db, 0)
        curr_size = latest['databases'].get(db, 0)
        change = curr_size - prev_size
        total_change += change

        if abs(change) > 1024 * 1024:  # Only show if >1MB change
            sign = "+" if change > 0 else ""
            print(f"{db:<30} {format_size(prev_size):>12} {format_size(curr_size):>12} {sign}{format_size(abs(change)):>11}")

    print("-" * 70)
    sign = "+" if total_change > 0 else ""
    print(f"{'TOTAL CHANGE':<30} {'':<12} {'':<12} {sign}{format_size(abs(total_change)):>11}")


def forecast():
    """Predict when disk will be full."""
    history = load_history()
    if len(history['entries']) < 7:
        print("Need at least 7 days of history for forecast.")
        return

    print("=" * 60)
    print("DISK USAGE FORECAST")
    print("=" * 60)

    for ts_name, path in TABLESPACES.items():
        usage = get_disk_usage(path)
        if not usage:
            continue

        # Calculate growth rate from history
        ts_history = []
        for entry in history['entries']:
            if ts_name in entry.get('tablespaces', {}):
                ts_history.append({
                    'time': datetime.fromisoformat(entry['timestamp']),
                    'size': entry['tablespaces'][ts_name]
                })

        if len(ts_history) < 2:
            continue

        # Linear regression for growth rate
        first = ts_history[0]
        last = ts_history[-1]
        days = (last['time'] - first['time']).total_seconds() / 86400

        if days < 1:
            continue

        growth_per_day = (last['size'] - first['size']) / days

        print(f"\n{ts_name} ({path}):")
        print(f"  Current: {format_size(usage['used'])} / {format_size(usage['total'])} ({usage['percent']:.1f}%)")
        print(f"  Growth rate: {format_size(abs(growth_per_day))}/day")

        if growth_per_day > 0:
            free_bytes = usage['free']
            days_until_full = free_bytes / growth_per_day
            full_date = datetime.now() + timedelta(days=days_until_full)

            if days_until_full < 30:
                status = "CRITICAL"
            elif days_until_full < 90:
                status = "WARNING"
            else:
                status = "OK"

            print(f"  Days until full: {days_until_full:.0f} days ({full_date.strftime('%Y-%m-%d')}) [{status}]")
        else:
            print(f"  Trend: Shrinking or stable")


def send_alert(message):
    """Send Telegram alert."""
    try:
        import sys
        sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
        from alerting import send_telegram
        send_telegram(message)
        print(f"Alert sent: {message}")
    except Exception as e:
        print(f"Failed to send alert: {e}")


def check_alerts():
    """Check and send alerts if thresholds exceeded."""
    alerts = []

    for ts_name, path in TABLESPACES.items():
        usage = get_disk_usage(path)
        if not usage:
            continue

        if usage['percent'] > CRITICAL_THRESHOLD_PERCENT:
            alerts.append(f"CRITICAL: {ts_name} at {usage['percent']:.1f}% ({format_size(usage['free'])} free)")
        elif usage['percent'] > ALERT_THRESHOLD_PERCENT:
            alerts.append(f"WARNING: {ts_name} at {usage['percent']:.1f}% ({format_size(usage['free'])} free)")

    if alerts:
        message = "PostgreSQL Space Alert:\n" + "\n".join(alerts)
        send_alert(message)
    else:
        print("All tablespaces within thresholds.")


def main():
    parser = argparse.ArgumentParser(description='PostgreSQL Space Monitor')
    parser.add_argument('--check', action='store_true', help='Check current usage')
    parser.add_argument('--daily-report', action='store_true', help='Show daily changes')
    parser.add_argument('--forecast', action='store_true', help='Predict when full')
    parser.add_argument('--alert', action='store_true', help='Send alerts if threshold exceeded')
    parser.add_argument('--threshold', type=int, default=85, help='Alert threshold percent')
    args = parser.parse_args()

    global ALERT_THRESHOLD_PERCENT
    ALERT_THRESHOLD_PERCENT = args.threshold

    if args.daily_report:
        daily_report()
    elif args.forecast:
        forecast()
    elif args.alert:
        check_alerts()
    else:
        check_usage()


if __name__ == '__main__':
    main()
