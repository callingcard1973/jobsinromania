#!/usr/bin/env python3
"""
Blacklist Cleaner - Automated cleanup of email blacklist

Removes:
- Typo domains (gamil.com, gmial.com, etc.) - should be FIXED not blocked
- Garbage entries (phone+email combos, malformed emails)
- Syncs changes to bounces.db

Usage:
    python3 blacklist_cleaner.py              # Run cleanup
    python3 blacklist_cleaner.py --dry-run    # Preview only
    python3 blacklist_cleaner.py --status     # Show current stats
    python3 blacklist_cleaner.py --report     # Detailed report

Schedule: Daily at 6 AM via Node-RED
"""

import os
import sys
import re
import sqlite3
import argparse
from datetime import datetime
from pathlib import Path

# Paths
BLACKLIST_FILE = "/opt/ACTIVE/EMAIL/CAMPAIGNS/EMAIL_CLEANUP/blacklist.txt"
BOUNCES_DB = "/opt/ACTIVE/OPENDATA/DATA/bounces.db"
BACKUP_DIR = "/opt/ACTIVE/EMAIL/CAMPAIGNS/EMAIL_CLEANUP/backups"
LOG_FILE = "/opt/ACTIVE/INFRA/LOGS/blacklist_cleaner.log"

# Typo domains - these should be FIXED, not blocked
TYPO_PATTERNS = [
    r'@gamil\.', r'@gmial\.', r'@gmal\.', r'@gnail\.', r'@gmai\.',
    r'@gmail\.ro$', r'@gmail\.co$',  # Wrong TLD
    r'@hotmal\.', r'@hotmai\.', r'@hotmial\.',
    r'@yahooo\.', r'@yaho\.', r'@yhoo\.',
    r'@outlok\.', r'@outloo\.',
]

# Garbage patterns - malformed entries
GARBAGE_PATTERNS = [
    r'^[+0-9]{5,}[a-z]',  # Starts with 5+ digits then letter (phone prefix)
    r'^[0-9]{2}[a-z]',    # Starts with 2 digits then letter
    r'@\.',               # @ followed by dot
    r'\s@|@\s',           # Space around @
    r'@[^.]+$',           # No dot in domain (missing TLD)
]

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
try:
    from alerting import send_telegram
    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False


def log(msg: str):
    """Log message to file and stdout."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{timestamp}] {msg}"
    print(line)

    Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')


def load_blacklist() -> list:
    """Load blacklist entries."""
    if not os.path.exists(BLACKLIST_FILE):
        return []
    with open(BLACKLIST_FILE) as f:
        return [line.strip() for line in f if line.strip()]


def save_blacklist(entries: list):
    """Save blacklist entries."""
    with open(BLACKLIST_FILE, 'w') as f:
        for entry in sorted(set(entries)):
            f.write(entry + '\n')


def backup_blacklist():
    """Create timestamped backup."""
    Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{BACKUP_DIR}/blacklist_{timestamp}.txt"

    if os.path.exists(BLACKLIST_FILE):
        import shutil
        shutil.copy(BLACKLIST_FILE, backup_path)
        log(f"Backup created: {backup_path}")

        # Keep only last 30 backups
        backups = sorted(Path(BACKUP_DIR).glob("blacklist_*.txt"))
        if len(backups) > 30:
            for old in backups[:-30]:
                old.unlink()
                log(f"Removed old backup: {old}")

    return backup_path


def is_typo_domain(email: str) -> bool:
    """Check if email has a typo domain."""
    email_lower = email.lower()
    return any(re.search(p, email_lower) for p in TYPO_PATTERNS)


def is_garbage_entry(email: str) -> bool:
    """Check if entry is garbage (malformed)."""
    email_lower = email.lower()
    return any(re.search(p, email_lower) for p in GARBAGE_PATTERNS)


def clean_blacklist(dry_run: bool = False) -> dict:
    """
    Clean blacklist by removing typo domains and garbage entries.
    Returns dict with stats.
    """
    entries = load_blacklist()
    original_count = len(entries)

    removed_typos = []
    removed_garbage = []
    clean_entries = []

    for entry in entries:
        if is_typo_domain(entry):
            removed_typos.append(entry)
        elif is_garbage_entry(entry):
            removed_garbage.append(entry)
        else:
            clean_entries.append(entry)

    stats = {
        'original': original_count,
        'removed_typos': len(removed_typos),
        'removed_garbage': len(removed_garbage),
        'remaining': len(clean_entries),
        'typo_samples': removed_typos[:10],
        'garbage_samples': removed_garbage[:10],
    }

    if not dry_run and (removed_typos or removed_garbage):
        backup_blacklist()
        save_blacklist(clean_entries)
        log(f"Blacklist cleaned: {original_count} -> {len(clean_entries)}")

    return stats


def sync_bounces_db(dry_run: bool = False) -> dict:
    """
    Sync bounces.db with current blacklist.
    Removes entries that are no longer in blacklist.
    """
    if not os.path.exists(BOUNCES_DB):
        return {'removed': 0, 'db_count': 0}

    # Load current blacklist
    blacklist = set(e.lower() for e in load_blacklist())

    conn = sqlite3.connect(BOUNCES_DB)
    cur = conn.cursor()

    # Get entries with "DNC blacklist" reason
    cur.execute("SELECT email FROM bounces WHERE reason LIKE '%DNC blacklist%'")
    dnc_entries = [row[0] for row in cur.fetchall()]

    # Find stale entries
    to_remove = [e for e in dnc_entries if e.lower() not in blacklist]

    if not dry_run and to_remove:
        for email in to_remove:
            cur.execute("DELETE FROM bounces WHERE email = ?", (email,))
        conn.commit()
        log(f"Removed {len(to_remove)} stale entries from bounces.db")

    cur.execute("SELECT COUNT(*) FROM bounces")
    db_count = cur.fetchone()[0]

    conn.close()

    return {
        'removed': len(to_remove),
        'db_count': db_count,
        'stale_samples': to_remove[:10],
    }


def get_status() -> dict:
    """Get current blacklist status."""
    entries = load_blacklist()

    typo_count = sum(1 for e in entries if is_typo_domain(e))
    garbage_count = sum(1 for e in entries if is_garbage_entry(e))

    db_count = 0
    if os.path.exists(BOUNCES_DB):
        conn = sqlite3.connect(BOUNCES_DB)
        cur = conn.execute("SELECT COUNT(*) FROM bounces")
        db_count = cur.fetchone()[0]
        conn.close()

    return {
        'blacklist_total': len(entries),
        'typo_domains': typo_count,
        'garbage_entries': garbage_count,
        'valid_entries': len(entries) - typo_count - garbage_count,
        'bounces_db': db_count,
    }


def run_cleanup(dry_run: bool = False, send_alert: bool = True) -> dict:
    """Run full cleanup and optionally send Telegram alert."""
    log(f"Starting blacklist cleanup ({'DRY RUN' if dry_run else 'LIVE'})")

    # Clean blacklist
    bl_stats = clean_blacklist(dry_run)

    # Sync bounces.db
    db_stats = sync_bounces_db(dry_run)

    # Combine stats
    stats = {
        **bl_stats,
        'db_removed': db_stats['removed'],
        'db_count': db_stats['db_count'],
    }

    # Log results
    total_removed = bl_stats['removed_typos'] + bl_stats['removed_garbage'] + db_stats['removed']

    if total_removed > 0:
        log(f"Cleanup complete: removed {total_removed} entries")
        log(f"  Typo domains: {bl_stats['removed_typos']}")
        log(f"  Garbage: {bl_stats['removed_garbage']}")
        log(f"  DB stale: {db_stats['removed']}")

        # Send Telegram alert if significant cleanup
        if send_alert and HAS_TELEGRAM and total_removed >= 5 and not dry_run:
            msg = (
                f"Blacklist Cleanup Complete\n"
                f"Removed: {total_removed} entries\n"
                f"- Typo domains: {bl_stats['removed_typos']}\n"
                f"- Garbage: {bl_stats['removed_garbage']}\n"
                f"- DB stale: {db_stats['removed']}\n"
                f"Remaining: {bl_stats['remaining']} blacklist, {db_stats['db_count']} bounces.db"
            )
            try:
                send_telegram(msg)
            except Exception as e:
                log(f"Failed to send Telegram: {e}")
    else:
        log("Cleanup complete: no entries to remove")

    return stats


def main():
    parser = argparse.ArgumentParser(description='Blacklist Cleaner')
    parser.add_argument('--dry-run', action='store_true', help='Preview only, no changes')
    parser.add_argument('--status', action='store_true', help='Show current stats')
    parser.add_argument('--report', action='store_true', help='Detailed report')
    parser.add_argument('--no-alert', action='store_true', help='Skip Telegram alert')
    args = parser.parse_args()

    if args.status:
        status = get_status()
        print("=" * 50)
        print("BLACKLIST STATUS")
        print("=" * 50)
        print(f"Blacklist total: {status['blacklist_total']}")
        print(f"  Valid entries: {status['valid_entries']}")
        print(f"  Typo domains: {status['typo_domains']}")
        print(f"  Garbage entries: {status['garbage_entries']}")
        print(f"Bounces.db: {status['bounces_db']}")
        return

    if args.report:
        entries = load_blacklist()
        typos = [e for e in entries if is_typo_domain(e)]
        garbage = [e for e in entries if is_garbage_entry(e)]

        print("=" * 50)
        print("BLACKLIST DETAILED REPORT")
        print("=" * 50)
        print(f"\nTotal entries: {len(entries)}")

        print(f"\nTypo domains ({len(typos)}):")
        for e in typos[:20]:
            print(f"  {e}")
        if len(typos) > 20:
            print(f"  ... and {len(typos) - 20} more")

        print(f"\nGarbage entries ({len(garbage)}):")
        for e in garbage[:20]:
            print(f"  {e}")
        if len(garbage) > 20:
            print(f"  ... and {len(garbage) - 20} more")
        return

    # Run cleanup
    stats = run_cleanup(dry_run=args.dry_run, send_alert=not args.no_alert)

    print("\n" + "=" * 50)
    print("CLEANUP RESULTS" + (" (DRY RUN)" if args.dry_run else ""))
    print("=" * 50)
    print(f"Original blacklist: {stats['original']}")
    print(f"Removed typo domains: {stats['removed_typos']}")
    print(f"Removed garbage: {stats['removed_garbage']}")
    print(f"Remaining blacklist: {stats['remaining']}")
    print(f"Removed from DB: {stats['db_removed']}")
    print(f"Final DB count: {stats['db_count']}")

    if stats['typo_samples']:
        print(f"\nTypo samples: {', '.join(stats['typo_samples'][:5])}")
    if stats['garbage_samples']:
        print(f"Garbage samples: {', '.join(stats['garbage_samples'][:5])}")


if __name__ == "__main__":
    main()
