#!/usr/bin/env python3
"""
storage_monitor.py - Monitor storage across raspibig, raspi, HDD, USB
Sends Telegram alerts when thresholds exceeded.

Usage:
    python3 storage_monitor.py          # Check all
    python3 storage_monitor.py --alert  # Only show alerts
    python3 storage_monitor.py --json   # JSON output
"""

import os
import sys
import json
import shutil
import subprocess
from datetime import datetime

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
try:
    from alerting import send_telegram
except ImportError:
    def send_telegram(msg):
        print(f"ALERT: {msg}")

# Thresholds (percentage)
THRESHOLDS = {
    '/': 85,                    # NVMe root
    '/mnt/hdd': 90,             # HDD
    '/mnt/usb2': 95,            # USB1
    '/media/devmon/USB1': 95,   # USB2
}

# Remote mounts to check
REMOTE_MOUNTS = {
    'raspi:/': 'ssh tudor@192.168.100.20 "df -B1 / | tail -1"',
    'raspi:/opt/BACKUPS': 'ssh tudor@192.168.100.20 "du -sb /opt/BACKUPS 2>/dev/null | cut -f1"',
}

# PostgreSQL databases to monitor
PG_DATABASES = [
    'interjob_master',
    'romania',
    'opendata',
    'csv_raw',
    'firme_romania',
]


def get_disk_usage(path):
    """Get disk usage for a local path."""
    try:
        usage = shutil.disk_usage(path)
        return {
            'total': usage.total,
            'used': usage.used,
            'free': usage.free,
            'percent': round((usage.used / usage.total) * 100, 1)
        }
    except (OSError, FileNotFoundError):
        return None


def get_mount_status(path):
    """Check if path is mounted and writable."""
    try:
        if not os.path.ismount(path) and path not in ['/', '/mnt/hdd']:
            return 'not_mounted'
        # For root and HDD, check mount options instead of access()
        if path in ['/', '/mnt/hdd']:
            result = subprocess.run(['mount'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if f' on {path} ' in line:
                    if '(ro,' in line or ',ro)' in line or ',ro,' in line:
                        return 'read_only'
                    return 'ok'
            return 'ok'
        if not os.access(path, os.W_OK):
            return 'read_only'
        return 'ok'
    except Exception:
        return 'error'


def get_pg_sizes():
    """Get PostgreSQL database sizes."""
    sizes = {}
    try:
        result = subprocess.run(
            ['sudo', '-u', 'postgres', 'psql', '-t', '-c',
             "SELECT datname, pg_database_size(datname) FROM pg_database WHERE datname NOT LIKE 'template%'"],
            capture_output=True, text=True, timeout=30
        )
        for line in result.stdout.strip().split('\n'):
            if '|' in line:
                name, size = line.split('|')
                sizes[name.strip()] = int(size.strip())
    except Exception as e:
        print(f"Error getting PG sizes: {e}")
    return sizes


def get_remote_usage():
    """Get storage info from raspi."""
    results = {}
    for name, cmd in REMOTE_MOUNTS.items():
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split()
                if len(parts) >= 4:  # df output
                    results[name] = {
                        'total': int(parts[1]),
                        'used': int(parts[2]),
                        'free': int(parts[3]),
                        'percent': float(parts[4].replace('%', ''))
                    }
                else:  # du output
                    results[name] = {'used': int(parts[0])}
        except Exception:
            results[name] = None
    return results


def format_size(bytes_val):
    """Format bytes to human readable."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(bytes_val) < 1024:
            return f"{bytes_val:.1f}{unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f}PB"


def check_alerts(results):
    """Check for alert conditions and send notifications."""
    alerts = []

    for path, threshold in THRESHOLDS.items():
        if path in results and results[path]:
            usage = results[path]
            if usage.get('percent', 0) > threshold:
                alerts.append(f"{path}: {usage['percent']}% (>{threshold}%)")

    # Check USB write status
    for usb in ['/mnt/usb2', '/media/devmon/USB1']:
        status = get_mount_status(usb)
        if status == 'read_only':
            alerts.append(f"{usb}: READ-ONLY (flip write-protect switch)")
        elif status == 'not_mounted':
            alerts.append(f"{usb}: NOT MOUNTED")

    return alerts


def main():
    alert_only = '--alert' in sys.argv
    json_output = '--json' in sys.argv

    results = {
        'timestamp': datetime.now().isoformat(),
        'local': {},
        'remote': {},
        'postgresql': {},
        'alerts': []
    }

    # Local storage
    for path in THRESHOLDS.keys():
        usage = get_disk_usage(path)
        if usage:
            usage['status'] = get_mount_status(path)
            results['local'][path] = usage

    # Remote storage
    results['remote'] = get_remote_usage()

    # PostgreSQL
    results['postgresql'] = get_pg_sizes()

    # Check alerts
    results['alerts'] = check_alerts(results['local'])

    if json_output:
        print(json.dumps(results, indent=2))
        return

    # Text output
    if not alert_only:
        print("=== STORAGE MONITOR ===")
        print(f"Time: {results['timestamp']}")
        print()

        print("LOCAL STORAGE:")
        for path, usage in results['local'].items():
            if usage:
                status = f" [{usage['status']}]" if usage['status'] != 'ok' else ''
                print(f"  {path:25} {usage['percent']:5.1f}%  {format_size(usage['free']):>8} free{status}")
        print()

        print("REMOTE (raspi):")
        for name, usage in results['remote'].items():
            if usage:
                if 'percent' in usage:
                    print(f"  {name:25} {usage['percent']:5.1f}%  {format_size(usage['free']):>8} free")
                else:
                    print(f"  {name:25} {format_size(usage['used']):>8} used")
        print()

        print("POSTGRESQL (top 5):")
        sorted_dbs = sorted(results['postgresql'].items(), key=lambda x: x[1], reverse=True)[:5]
        for name, size in sorted_dbs:
            print(f"  {name:25} {format_size(size):>10}")
        print()

    # Alerts
    if results['alerts']:
        print("ALERTS:")
        for alert in results['alerts']:
            print(f"  ! {alert}")

        # Send Telegram
        if results['alerts']:
            msg = "STORAGE ALERTS:\n" + "\n".join(results['alerts'])
            send_telegram(msg)
    elif not alert_only:
        print("No alerts.")


if __name__ == '__main__':
    main()
