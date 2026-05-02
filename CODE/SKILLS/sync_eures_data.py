#!/usr/bin/env python3
"""
Sync EURES data from raspibig to raspi for enrichment.

Syncs the EURES master contacts file and updates the enrichment index.

Usage:
    python3 sync_eures_data.py           # Sync and rebuild index
    python3 sync_eures_data.py --sync    # Sync only (no index rebuild)
    python3 sync_eures_data.py --status  # Show sync status
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RASPIBIG_HOST = 'raspibig'
EURES_SOURCE = '/mnt/hdd/SCRAPER_DATA/csv/EURES/master_contacts_50.csv'
EURES_LOCAL = '/opt/ACTIVE/OPENDATA/DATA/EURES_SYNC/master_contacts.csv'
INDEX_BUILDER = '/opt/ACTIVE/INFRA/SKILLS/build_enrichment_index.py'


def run_cmd(cmd: list, capture: bool = False) -> tuple:
    """Run a command and return (success, output)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            timeout=300
        )
        return result.returncode == 0, result.stdout if capture else ''
    except Exception as e:
        return False, str(e)


def sync_eures():
    """Sync EURES data from raspibig."""
    print(f"Syncing EURES data from {RASPIBIG_HOST}...")

    # Create local directory
    os.makedirs(os.path.dirname(EURES_LOCAL), exist_ok=True)

    # Check remote file exists
    check_cmd = ['ssh', RASPIBIG_HOST, f'test -f {EURES_SOURCE} && stat -c %s {EURES_SOURCE}']
    success, output = run_cmd(check_cmd, capture=True)
    if not success:
        print(f"ERROR: Remote file not found: {EURES_SOURCE}")
        return False

    # Sync file
    rsync_cmd = [
        'rsync', '-avz', '--progress',
        f'{RASPIBIG_HOST}:{EURES_SOURCE}',
        EURES_LOCAL
    ]
    print(f"  Running: rsync from {RASPIBIG_HOST}")
    success, _ = run_cmd(rsync_cmd)

    if success:
        local_size = os.path.getsize(EURES_LOCAL) / (1024 * 1024)
        print(f"  Synced: {EURES_LOCAL} ({local_size:.1f} MB)")
        return True
    else:
        print("  ERROR: rsync failed")
        return False


def show_status():
    """Show sync status."""
    print("EURES Sync Status")
    print("=" * 60)

    # Check local file
    if os.path.exists(EURES_LOCAL):
        stat = os.stat(EURES_LOCAL)
        size = stat.st_size / (1024 * 1024)
        mtime = datetime.fromtimestamp(stat.st_mtime)
        print(f"Local file: {EURES_LOCAL}")
        print(f"  Size: {size:.1f} MB")
        print(f"  Modified: {mtime.strftime('%Y-%m-%d %H:%M')}")

        # Count rows
        with open(EURES_LOCAL, 'r', encoding='utf-8', errors='ignore') as f:
            rows = sum(1 for _ in f) - 1  # minus header
        print(f"  Rows: {rows:,}")
    else:
        print(f"Local file: NOT FOUND ({EURES_LOCAL})")

    # Check remote file
    print()
    check_cmd = ['ssh', RASPIBIG_HOST, f'stat -c "%s %Y" {EURES_SOURCE}']
    success, output = run_cmd(check_cmd, capture=True)
    if success:
        parts = output.strip().split()
        if len(parts) == 2:
            remote_size = int(parts[0]) / (1024 * 1024)
            remote_mtime = datetime.fromtimestamp(int(parts[1]))
            print(f"Remote file: {RASPIBIG_HOST}:{EURES_SOURCE}")
            print(f"  Size: {remote_size:.1f} MB")
            print(f"  Modified: {remote_mtime.strftime('%Y-%m-%d %H:%M')}")
    else:
        print(f"Remote file: UNAVAILABLE")


def rebuild_index():
    """Rebuild the enrichment index."""
    print("\nRebuilding enrichment index...")
    cmd = [sys.executable, INDEX_BUILDER]
    success, _ = run_cmd(cmd)
    return success


def main():
    parser = argparse.ArgumentParser(description='Sync EURES data from raspibig')
    parser.add_argument('--sync', action='store_true', help='Sync only (no index rebuild)')
    parser.add_argument('--status', action='store_true', help='Show sync status')
    parser.add_argument('--no-rebuild', action='store_true', help='Skip index rebuild')

    args = parser.parse_args()

    if args.status:
        show_status()
        return

    # Sync
    if not sync_eures():
        sys.exit(1)

    # Rebuild index unless --sync or --no-rebuild
    if not args.sync and not args.no_rebuild:
        if not rebuild_index():
            print("WARNING: Index rebuild failed")
            sys.exit(1)

    print("\nDone!")


if __name__ == '__main__':
    main()
