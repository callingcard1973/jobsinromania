#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
Sync unsubscribes from interjob.ro/unsubscribe.log to master blacklist.
Run via cron daily.

Usage:
    python3 sync_unsubscribes.py       # Sync and add to blacklist

[AI: Claude Code]
"""

import os
import sys
import csv
import subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS')
from consolidate_blacklist import add_email

A2_HOST = 'loaiidil@nl1-cl8-ats1.a2hosting.com'
A2_PORT = '7822'
A2_REMOTE_LOG = '~/interjob.ro/unsubscribe.log'
LOCAL_LOG = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/unsubscribe_synced.log')
MASTER_BLACKLIST = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/master_blacklist.csv')


def fetch_unsubscribes():
    """Fetch unsubscribe.log from A2 hosting."""
    try:
        result = subprocess.run(
            ['ssh', '-p', A2_PORT, A2_HOST, f'cat {A2_REMOTE_LOG} 2>/dev/null'],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout.strip()
    except Exception as e:
        print(f"Error fetching: {e}")
        return ''


def get_already_synced():
    """Get emails already synced."""
    synced = set()
    if LOCAL_LOG.exists():
        with open(LOCAL_LOG) as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) >= 2:
                    synced.add(parts[1].lower().strip())
    return synced


def main():
    print("Fetching unsubscribes from interjob.ro...")
    raw = fetch_unsubscribes()

    if not raw:
        print("No unsubscribes found.")
        return

    already = get_already_synced()
    new_count = 0

    for line in raw.strip().split('\n'):
        parts = line.strip().split(',')
        if len(parts) < 2:
            continue
        timestamp, email = parts[0], parts[1].lower().strip()

        if email in already:
            continue

        # Add to master blacklist
        add_email(email, reason='unsubscribed', source='interjob.ro')

        # Record as synced
        with open(LOCAL_LOG, 'a') as f:
            f.write(f"{timestamp},{email}\n")

        new_count += 1
        print(f"  Added: {email}")

    print(f"Synced: {new_count} new unsubscribes")


if __name__ == '__main__':
    main()
