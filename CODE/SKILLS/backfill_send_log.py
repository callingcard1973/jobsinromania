#!/usr/bin/env python3
"""
Backfill send_log database with sender info from campaign logs.

Parses existing campaign log files and updates send_log rows where sender='unknown'.

Usage:
    python3 backfill_send_log.py --dry-run        # Preview changes
    python3 backfill_send_log.py --backfill       # Actually update DB
    python3 backfill_send_log.py --status         # Show current status
"""

import os
import sys
import re
import glob
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import psycopg2

# Database configuration
DB_CONFIG = {
    "host": os.getenv('PGHOST', 'localhost'),
    "database": os.getenv('PGDATABASE', 'email_sender'),
    "user": os.getenv('PGUSER', 'tudor'),
    "password": os.getenv('PGPASSWORD', os.getenv('PG_PASSWORD', 'scraper123'))
}

# Campaign to sender mapping (derived from campaign configs)
CAMPAIGN_SENDERS = {
    # Norway campaigns
    "NORWAY_HORECA_2026": "a2_horecaworkers",
    "NORWAY_CARE_2026": "brevo_careworkers",
    "NORWAY_RETAIL_2026": "brevo_warehouseworkers",
    "NORWAY_RECRUITMENT_2026": "brevo_nepalezi",
    # Other campaigns
    "ANOFM": "brevo_cifn",
    "MALTA": "a2_meatworkers",
    "BULGARIA": "a2_factoryjobs",
    "FACTORY_EU": "brevo_buildjobs",
    "EU_CONTRACTORS": "brevo_buildjobs",
    "CONSTRUCT2026": "a2_warehouseworkers",
    "EURES_AGENCIES_NORDIC": "brevo_expatsinromania",
    "EURES_AGENCIES_GERMANY": "brevo_expatsinromania",
    "EURES_AGENCIES_OTHER": "brevo_expatsinromania",
    "GERMANY_AGENCIES": "brevo_mivromania",
    # Legacy/other campaigns
    "TOURISM_RO": "brevo_expatsinromania",
    "FACTORY": "brevo_factoryjobs",
    "HORECA2026": "brevo_mivromania",
    "CAREWORKERS": "brevo_careworkers",
    "POLAND": "brevo_mivromania",
    "AGRI": "brevo_cifn",
    "NORDIC": "brevo_expatsinromania",
    "TRANSPORT_EU": "brevo_buildjobs",
}

# Campaign log directories
CAMPAIGNS_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/CAMPAIGNS")
LEGACY_CAMPAIGNS_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS")


def get_connection():
    """Get database connection."""
    return psycopg2.connect(**DB_CONFIG)


def get_unknown_sender_stats():
    """Get stats on unknown sender records."""
    conn = get_connection()
    cur = conn.cursor()

    # Overall stats
    cur.execute("""
        SELECT
            sender,
            COUNT(*) as count,
            MIN(sent_at_utc) as first_send,
            MAX(sent_at_utc) as last_send
        FROM send_log
        GROUP BY sender
        ORDER BY count DESC
    """)

    stats = cur.fetchall()
    conn.close()
    return stats


def get_unknown_emails():
    """Get all emails with unknown sender."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, email, campaign, sent_at_utc
        FROM send_log
        WHERE sender = 'unknown'
        ORDER BY sent_at_utc
    """)

    results = cur.fetchall()
    conn.close()
    return results


def parse_log_line(line, campaign_dir):
    """Parse a log line and extract email and status.

    Formats:
    - "YYYY-MM-DD HH:MM:SS | STATUS | email | msg"
    - "YYYY-MM-DDTHH:MM:SS,email,status"
    """
    line = line.strip()
    if not line:
        return None

    # Format 1: timestamp | status | email | msg
    match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s*\|\s*(\w+)\s*\|\s*([^\|]+)\s*\|?', line)
    if match:
        timestamp_str, status, email = match.groups()
        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        return {
            'email': email.strip().lower(),
            'timestamp': timestamp,
            'status': status.strip()
        }

    # Format 2: timestamp,email,status
    match = re.match(r'(\d{4}-\d{2}-\d{2}T[\d:]+),([^,]+),(\w+)', line)
    if match:
        timestamp_str, email, status = match.groups()
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except:
            timestamp = None
        return {
            'email': email.strip().lower(),
            'timestamp': timestamp,
            'status': status.strip()
        }

    # Format 3: [timestamp] msg with email
    match = re.match(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\].*-> ([^\s]+@[^\s]+)', line)
    if match:
        timestamp_str, email = match.groups()
        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        return {
            'email': email.strip().lower(),
            'timestamp': timestamp,
            'status': 'OK' if 'OK' in line else 'FAIL'
        }

    return None


def find_campaign_logs():
    """Find all campaign log directories and files."""
    logs = []

    # Check CAMPAIGNS directory
    for campaign_dir in CAMPAIGNS_DIR.iterdir():
        if campaign_dir.is_dir():
            log_dir = campaign_dir / 'logs'
            if log_dir.exists():
                campaign_name = campaign_dir.name.upper()
                for log_file in log_dir.glob('sent_*.log'):
                    logs.append((campaign_name, log_file))

    return logs


def build_email_sender_map():
    """Build a map of email -> sender from campaign logs."""
    email_sender_map = {}

    campaign_logs = find_campaign_logs()
    print(f"Found {len(campaign_logs)} log files")

    for campaign_name, log_file in campaign_logs:
        sender = CAMPAIGN_SENDERS.get(campaign_name, f"campaign_{campaign_name.lower()}")

        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    parsed = parse_log_line(line, campaign_name)
                    if parsed and parsed['email']:
                        email = parsed['email']
                        if email not in email_sender_map:
                            email_sender_map[email] = {
                                'sender': sender,
                                'campaign': campaign_name,
                                'timestamp': parsed.get('timestamp')
                            }
        except Exception as e:
            print(f"  Error reading {log_file}: {e}")

    return email_sender_map


def backfill_senders(dry_run=True):
    """Backfill sender info for unknown senders."""
    print("Building email->sender map from campaign logs...")
    email_sender_map = build_email_sender_map()
    print(f"Found {len(email_sender_map)} unique emails in logs")

    print("\nFetching unknown sender records from database...")
    unknown_emails = get_unknown_emails()
    print(f"Found {len(unknown_emails)} records with unknown sender")

    # Match and update
    updates = []
    for row_id, email, campaign, sent_at in unknown_emails:
        email_lower = email.lower()
        if email_lower in email_sender_map:
            mapped = email_sender_map[email_lower]
            updates.append({
                'id': row_id,
                'email': email,
                'old_campaign': campaign,
                'new_sender': mapped['sender'],
                'new_campaign': mapped['campaign'] if campaign == 'unknown' else campaign
            })

    print(f"\nMatched {len(updates)} records for update")

    if dry_run:
        print("\n[DRY RUN] Would update:")
        for u in updates[:20]:
            print(f"  {u['email']}: sender={u['new_sender']}, campaign={u['new_campaign']}")
        if len(updates) > 20:
            print(f"  ... and {len(updates) - 20} more")
        return

    # Actually update
    print("\nUpdating database...")
    conn = get_connection()
    cur = conn.cursor()

    updated = 0
    for u in updates:
        try:
            cur.execute("""
                UPDATE send_log
                SET sender = %s,
                    campaign = CASE WHEN campaign = 'unknown' THEN %s ELSE campaign END
                WHERE id = %s
            """, (u['new_sender'], u['new_campaign'], u['id']))
            updated += 1
        except Exception as e:
            print(f"  Error updating {u['email']}: {e}")

    conn.commit()
    conn.close()

    print(f"Updated {updated} records")


def show_status():
    """Show current sender distribution."""
    stats = get_unknown_sender_stats()

    print("=" * 60)
    print("SEND_LOG SENDER DISTRIBUTION")
    print("=" * 60)
    print(f"{'Sender':<30} {'Count':>8} {'First Send':<12} {'Last Send':<12}")
    print("-" * 60)

    total = 0
    for sender, count, first_send, last_send in stats:
        total += count
        first_str = first_send.strftime('%Y-%m-%d') if first_send else 'N/A'
        last_str = last_send.strftime('%Y-%m-%d') if last_send else 'N/A'
        print(f"{sender:<30} {count:>8} {first_str:<12} {last_str:<12}")

    print("-" * 60)
    print(f"{'TOTAL':<30} {total:>8}")

    # Show unknown percentage
    unknown = next((c for s, c, _, _ in stats if s == 'unknown'), 0)
    if total > 0:
        pct = (unknown / total) * 100
        print(f"\nUnknown sender: {unknown}/{total} ({pct:.1f}%)")


def main():
    parser = argparse.ArgumentParser(description='Backfill send_log with sender info')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without updating')
    parser.add_argument('--backfill', action='store_true', help='Actually update database')
    parser.add_argument('--status', action='store_true', help='Show current status')
    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.backfill:
        backfill_senders(dry_run=False)
    elif args.dry_run:
        backfill_senders(dry_run=True)
    else:
        print("Usage: python3 backfill_send_log.py [--dry-run|--backfill|--status]")
        show_status()


if __name__ == '__main__':
    main()
