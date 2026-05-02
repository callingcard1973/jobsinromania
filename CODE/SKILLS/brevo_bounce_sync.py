#!/usr/bin/env python3
"""
Brevo Bounce Sync - Sync bounces from all Brevo accounts to blacklist.

Run daily to keep blacklist updated and prevent re-sending to bounced emails.

Usage:
    python3 brevo_bounce_sync.py           # Sync all accounts
    python3 brevo_bounce_sync.py --status  # Show bounce stats
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import sqlite3
import requests
from datetime import datetime
from pathlib import Path
from collections import Counter
from dotenv import load_dotenv

load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

BOUNCES_DB = Path("/opt/ACTIVE/OPENDATA/DATA/email_sender/bounces.db")
BLACKLIST_FILE = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/EMAIL_CLEANUP/blacklist.txt")

ACCOUNTS = {
    'BUILDJOBS': 'BREVO_BUILDJOBS_API_KEY',
    'FACTORYJOBS': 'BREVO_FACTORYJOBS_API_KEY',
    'CAREWORKERS': 'BREVO_CAREWORKERS_API_KEY',
    'WAREHOUSEWORKERS': 'BREVO_WAREHOUSEWORKERS_API_KEY',
    'MIVROMANIA': 'BREVO_MIVROMANIA_API_KEY',
    'MIVROMANIA_ONLINE': 'BREVO_MIVROMANIA_ONLINE_API_KEY',
    'CIFN': 'BREVO_CIFN_API_KEY',
    'INTERJOB': 'BREVO_INTERJOB_API_KEY',
    'NEPALEZI': 'BREVO_NEPALEZI_API_KEY',
    'CUMPARLEGUME': 'BREVO_CUMPARLEGUME_API_KEY',
}


def init_db():
    """Initialize bounces database."""
    BOUNCES_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(BOUNCES_DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bounces (
            email TEXT PRIMARY KEY,
            reason TEXT,
            bounce_count INTEGER DEFAULT 1,
            first_bounce TEXT,
            last_bounce TEXT,
            campaign TEXT
        )
    """)
    conn.commit()
    return conn


def sync_account(account, api_key, conn):
    """Sync bounces from one Brevo account."""
    cur = conn.cursor()
    headers = {"api-key": api_key}
    added = 0
    hard_bounces = set()

    for event_type in ["hardBounces", "softBounces", "blocked"]:
        try:
            resp = requests.get(
                "https://api.brevo.com/v3/smtp/statistics/events",
                headers=headers,
                params={"event": event_type, "limit": 100, "days": 30},
                timeout=30
            )
            if resp.status_code != 200:
                continue

            events = resp.json().get("events", [])
            for e in events:
                email = e.get("email", "").lower().strip()
                if not email or '@' not in email:
                    continue

                reason = e.get("reason", event_type)[:200]
                date = datetime.now().isoformat()

                cur.execute("""
                    INSERT INTO bounces (email, reason, bounce_count, first_bounce, last_bounce, campaign)
                    VALUES (?, ?, 1, ?, ?, ?)
                    ON CONFLICT(email) DO UPDATE SET
                        bounce_count = bounce_count + 1,
                        last_bounce = ?
                """, (email, reason, date, date, account, date))
                added += 1

                if event_type == "hardBounces":
                    hard_bounces.add(email)

        except Exception as e:
            print(f"  {event_type}: Error - {e}")

    conn.commit()
    return added, hard_bounces


def update_blacklist(emails):
    """Add emails to blacklist file."""
    existing = set()
    if BLACKLIST_FILE.exists():
        with open(BLACKLIST_FILE) as f:
            existing = set(l.strip().lower() for l in f if l.strip() and not l.startswith('#'))

    new_emails = emails - existing
    if new_emails:
        with open(BLACKLIST_FILE, 'a') as f:
            for email in sorted(new_emails):
                f.write(f"{email}\n")

    return len(new_emails)


def sync_all():
    """Sync bounces from all accounts."""
    print(f"=== BREVO BOUNCE SYNC - {datetime.now().strftime('%Y-%m-%d %H:%M')} ===\n")

    conn = init_db()
    total_added = 0
    all_hard_bounces = set()

    for account, env_key in ACCOUNTS.items():
        api_key = os.getenv(env_key)
        if not api_key:
            continue

        added, hard = sync_account(account, api_key, conn)
        if added > 0:
            print(f"{account}: {added} bounces synced")
        total_added += added
        all_hard_bounces.update(hard)

    # Update blacklist
    new_blacklist = update_blacklist(all_hard_bounces)

    # Stats
    cur = conn.cursor()
    cur.execute("SELECT COUNT(DISTINCT email) FROM bounces")
    unique = cur.fetchone()[0]

    print(f"\n=== SUMMARY ===")
    print(f"Total events synced: {total_added}")
    print(f"New to blacklist: {new_blacklist}")
    print(f"Unique bounces in DB: {unique}")

    conn.close()


def show_status():
    """Show bounce statistics."""
    print("=== BOUNCE STATISTICS ===\n")

    if not BOUNCES_DB.exists():
        print("No bounces database found. Run sync first.")
        return

    conn = sqlite3.connect(BOUNCES_DB)
    cur = conn.cursor()

    # Total count
    cur.execute("SELECT COUNT(DISTINCT email) FROM bounces")
    total = cur.fetchone()[0]
    print(f"Total unique bounced emails: {total}")

    # By campaign
    cur.execute("""
        SELECT campaign, COUNT(DISTINCT email) as cnt
        FROM bounces
        GROUP BY campaign
        ORDER BY cnt DESC
    """)
    print("\nBy campaign:")
    for campaign, cnt in cur.fetchall():
        print(f"  {campaign}: {cnt}")

    # Top domains
    cur.execute("SELECT email FROM bounces")
    domains = Counter()
    for row in cur.fetchall():
        domain = row[0].split('@')[-1] if '@' in row[0] else 'unknown'
        domains[domain] += 1

    print("\nTop bouncing domains:")
    for domain, count in domains.most_common(10):
        print(f"  {domain}: {count}")

    # Blacklist count
    if BLACKLIST_FILE.exists():
        with open(BLACKLIST_FILE) as f:
            blacklist_count = sum(1 for l in f if l.strip() and not l.startswith('#'))
        print(f"\nBlacklist entries: {blacklist_count}")

    conn.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Brevo Bounce Sync")
    parser.add_argument('--status', '-s', action='store_true', help='Show bounce stats')
    args = parser.parse_args()

    if args.status:
        show_status()
    else:
        sync_all()
