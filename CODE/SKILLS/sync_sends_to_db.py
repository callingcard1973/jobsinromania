#!/usr/bin/env python3
"""
Sync email sends from log files to PostgreSQL database.
Parses sent*.log files and inserts into send_log table.
"""
import os
import sys
import re
import psycopg2
from pathlib import Path
from datetime import datetime

# Database config
DB_CONFIG = {
    "host": "localhost",
    "database": "email_sender",
    "user": "tudor",
    "password": "scraper123"
}

CAMPAIGNS_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/CAMPAIGNS")

# Log line pattern: 2026-01-06 08:29:31 | SENT | email@domain.com | sender_name
LOG_PATTERN = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \| (SENT|FAILED|SKIP) \| ([^\|]+) \| (.+)$')


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def get_existing_emails(conn, campaign):
    """Get emails already in DB for this campaign"""
    cur = conn.cursor()
    cur.execute("SELECT email FROM send_log WHERE campaign = %s", (campaign,))
    return {row[0].strip().lower() for row in cur.fetchall()}


def parse_log_file(log_path):
    """Parse a log file and yield send records"""
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            match = LOG_PATTERN.match(line)
            if match:
                timestamp_str, status, email, sender = match.groups()
                if status == 'SENT':
                    try:
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        yield {
                            'timestamp': timestamp,
                            'email': email.strip().lower(),
                            'sender': sender.strip(),
                            'status': 'sent'
                        }
                    except ValueError:
                        continue


def sync_campaign(conn, campaign_dir):
    """Sync a single campaign's logs and state to database"""
    campaign = campaign_dir.name
    logs_dir = campaign_dir / 'logs'
    state_file = campaign_dir / 'state.json'

    # Get existing emails
    existing = get_existing_emails(conn, campaign)
    new_sends = []

    # 1. Parse log files
    if logs_dir.exists():
        log_files = list(logs_dir.glob('sent*.log'))
        for log_file in log_files:
            for record in parse_log_file(log_file):
                if record['email'] not in existing:
                    new_sends.append(record)
                    existing.add(record['email'])

    # 2. Parse state.json for emails not in logs
    if state_file.exists():
        import json
        try:
            with open(state_file) as f:
                state = json.load(f)
            sent_emails = state.get('sent', state.get('sent_emails', []))
            last_sent = state.get('last_sent', state.get('last_send', ''))

            # Try to parse last_sent as timestamp
            try:
                if isinstance(last_sent, str) and len(last_sent) >= 10:
                    timestamp = datetime.strptime(last_sent[:19], '%Y-%m-%d %H:%M:%S')
                else:
                    timestamp = datetime.now()
            except:
                timestamp = datetime.now()

            # Get sender from config or state
            sender = state.get('sender', state.get('primary_sender', 'unknown'))

            for email in sent_emails:
                email_clean = email.strip().lower()
                if email_clean and email_clean not in existing:
                    new_sends.append({
                        'timestamp': timestamp,
                        'email': email_clean,
                        'sender': sender,
                        'status': 'sent'
                    })
                    existing.add(email_clean)
        except Exception as e:
            pass  # Skip if state file is invalid

    if not new_sends:
        return 0

    # Insert new sends
    cur = conn.cursor()
    inserted = 0
    for send in new_sends:
        try:
            cur.execute("""
                INSERT INTO send_log (campaign, email, sender, status, sent_at_utc)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (campaign, send['email'], send['sender'], send['status'], send['timestamp']))
            inserted += 1
        except Exception as e:
            print(f"  Error inserting {send['email']}: {e}")

    conn.commit()
    return inserted


def main():
    print("=== Syncing sends to database ===")
    print(f"Campaigns dir: {CAMPAIGNS_DIR}")
    print()

    conn = get_db_connection()

    # Get initial count
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM send_log")
    initial_count = cur.fetchone()[0]
    print(f"Initial DB count: {initial_count}")
    print()

    total_inserted = 0

    # Process each campaign
    for campaign_dir in sorted(CAMPAIGNS_DIR.iterdir()):
        if not campaign_dir.is_dir():
            continue
        if campaign_dir.name.startswith('.'):
            continue

        inserted = sync_campaign(conn, campaign_dir)
        if inserted > 0:
            print(f"  {campaign_dir.name}: +{inserted}")
            total_inserted += inserted

    # Final count
    cur.execute("SELECT COUNT(*) FROM send_log")
    final_count = cur.fetchone()[0]

    print()
    print(f"=== Summary ===")
    print(f"Inserted: {total_inserted}")
    print(f"DB count: {initial_count} -> {final_count}")

    conn.close()


if __name__ == "__main__":
    main()
