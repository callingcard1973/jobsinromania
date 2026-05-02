#!/usr/bin/env python3
"""
System Cleaner - Automated cleanup for raspi and raspibig
Runs daily via cron to prevent disk filling

Retention Policy:
- PostgreSQL backups: 3 days
- Code backups: 7 days
- Logs: 7 days
- Temp files: 1 day
- Journal: 3 days
"""

import subprocess
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
MACHINES = {
    'raspibig': {
        'host': 'localhost',
        'backup_dirs': ['/opt/BACKUPS'],
        'log_dirs': ['/opt/LOGS', '/var/log'],
        'temp_dirs': ['/tmp'],
        'postgres_backup': None,  # raspibig is source, not backup
    },
    'raspi': {
        'host': 'raspi',
        'backup_dirs': ['/opt/BACKUPS'],
        'log_dirs': ['/opt/LOGS', '/var/log'],
        'temp_dirs': ['/tmp'],
        'postgres_backup': '/opt/BACKUPS/raspibig/daily',
    }
}

RETENTION = {
    'postgres_days': 3,
    'backup_days': 7,
    'log_days': 7,
    'temp_days': 1,
    'journal_days': 3,
}


def run_cmd(cmd: str, host: str = 'localhost', timeout: int = 60) -> tuple:
    """Run command and return (success, output)"""
    try:
        if host == 'localhost':
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        else:
            result = subprocess.run(['ssh', host, cmd], capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)


def get_disk_usage(host: str) -> dict:
    """Get disk usage"""
    ok, output = run_cmd("df -B1 / | tail -1", host)
    if ok:
        parts = output.split()
        if len(parts) >= 5:
            return {
                'total': int(parts[1]),
                'used': int(parts[2]),
                'avail': int(parts[3]),
                'percent': int(parts[4].replace('%', ''))
            }
    return {'total': 0, 'used': 0, 'avail': 0, 'percent': 0}


def format_bytes(b: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(b) < 1024.0:
            return f"{b:.1f}{unit}"
        b /= 1024.0
    return f"{b:.1f}PB"


def clean_old_files(host: str, directory: str, pattern: str, days: int, dry_run: bool = False) -> int:
    """Delete files older than N days matching pattern"""
    cmd = f"find {directory} -name '{pattern}' -type f -mtime +{days}"
    if dry_run:
        cmd += " -print"
    else:
        cmd += " -delete -print"

    ok, output = run_cmd(cmd, host, timeout=120)
    if ok and output:
        files = [f for f in output.split('\n') if f.strip()]
        return len(files)
    return 0


def clean_postgres_backups(host: str, directory: str, keep_days: int, dry_run: bool = False) -> tuple:
    """Keep only last N days of postgres backups"""
    freed = 0
    count = 0

    # List postgres backup files sorted by date (newest first)
    cmd = f"ls -1t {directory}/postgres_*.gz 2>/dev/null"
    ok, output = run_cmd(cmd, host)

    if ok and output:
        files = output.split('\n')
        # Keep first N files (most recent), delete rest
        to_delete = files[keep_days:]

        for f in to_delete:
            if not f.strip():
                continue
            # Get file size
            ok, size_output = run_cmd(f"stat -c%s {f}", host)
            if ok:
                freed += int(size_output)

            if not dry_run:
                run_cmd(f"rm -f {f}", host)
            count += 1

    return count, freed


def clean_journal(host: str, days: int, dry_run: bool = False) -> bool:
    """Clean systemd journal"""
    if dry_run:
        return True
    cmd = f"sudo journalctl --vacuum-time={days}d 2>/dev/null"
    ok, _ = run_cmd(cmd, host)
    return ok


def clean_apt_cache(host: str, dry_run: bool = False) -> bool:
    """Clean apt cache"""
    if dry_run:
        return True
    ok, _ = run_cmd("sudo apt clean 2>/dev/null", host)
    return ok


def clean_machine(machine_name: str, config: dict, dry_run: bool = False) -> dict:
    """Clean a single machine"""
    host = config['host']
    results = {
        'machine': machine_name,
        'before': get_disk_usage(host),
        'actions': [],
        'freed_bytes': 0
    }

    # Clean postgres backups (raspi only)
    if config.get('postgres_backup'):
        count, freed = clean_postgres_backups(
            host, config['postgres_backup'],
            RETENTION['postgres_days'], dry_run
        )
        if count > 0:
            results['actions'].append(f"Postgres backups: {count} files ({format_bytes(freed)})")
            results['freed_bytes'] += freed

    # Clean old log files
    for log_dir in config.get('log_dirs', []):
        count = clean_old_files(host, log_dir, '*.log', RETENTION['log_days'], dry_run)
        count += clean_old_files(host, log_dir, '*.log.*', RETENTION['log_days'], dry_run)
        if count > 0:
            results['actions'].append(f"Logs in {log_dir}: {count} files")

    # Clean temp files
    for temp_dir in config.get('temp_dirs', []):
        count = clean_old_files(host, temp_dir, '*', RETENTION['temp_days'], dry_run)
        if count > 0:
            results['actions'].append(f"Temp in {temp_dir}: {count} files")

    # Clean journal
    if clean_journal(host, RETENTION['journal_days'], dry_run):
        results['actions'].append(f"Journal vacuumed ({RETENTION['journal_days']} days)")

    # Clean apt cache
    if clean_apt_cache(host, dry_run):
        results['actions'].append("APT cache cleaned")

    results['after'] = get_disk_usage(host)
    results['freed_bytes'] += results['before']['used'] - results['after']['used']

    return results


def print_report(results: list, dry_run: bool = False):
    """Print cleanup report"""
    print("\n" + "=" * 60)
    print(f"  SYSTEM CLEANUP REPORT {'(DRY RUN)' if dry_run else ''}")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    for r in results:
        print(f"\n{'─' * 60}")
        print(f"  {r['machine'].upper()}")
        print(f"{'─' * 60}")

        before = r['before']
        after = r['after']

        print(f"  Before: {before['percent']}% ({format_bytes(before['used'])} / {format_bytes(before['total'])})")
        print(f"  After:  {after['percent']}% ({format_bytes(after['used'])} / {format_bytes(after['total'])})")

        freed = r['freed_bytes']
        if freed > 0:
            print(f"  Freed:  {format_bytes(freed)}")

        if r['actions']:
            print(f"\n  Actions:")
            for action in r['actions']:
                print(f"    - {action}")
        else:
            print(f"\n  No cleanup needed")

    print("\n" + "=" * 60)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='System cleaner for raspi/raspibig')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Show what would be deleted')
    parser.add_argument('--raspi', action='store_true', help='Clean raspi only')
    parser.add_argument('--raspibig', action='store_true', help='Clean raspibig only')
    parser.add_argument('--cron', action='store_true', help='Quiet mode for cron')
    args = parser.parse_args()

    machines = MACHINES
    if args.raspi:
        machines = {'raspi': MACHINES['raspi']}
    elif args.raspibig:
        machines = {'raspibig': MACHINES['raspibig']}

    results = []
    for name, config in machines.items():
        result = clean_machine(name, config, args.dry_run)
        results.append(result)

    if not args.cron:
        print_report(results, args.dry_run)
    else:
        # Cron mode: only output if something was cleaned
        total_freed = sum(r['freed_bytes'] for r in results)
        if total_freed > 1024 * 1024:  # More than 1MB
            for r in results:
                if r['freed_bytes'] > 0:
                    print(f"{r['machine']}: freed {format_bytes(r['freed_bytes'])}")


if __name__ == '__main__':
    main()
