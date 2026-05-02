#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
Norway Response Tracker - IMAP scan for replies from .no domains.
Classifies: interested, declined, unsubscribe, auto_reply, bounce.
Cron: every 2 hours.

Usage:
    python3 norway_response_tracker.py           # Scan all inboxes
    python3 norway_response_tracker.py --stats   # Show response stats
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS')

import os
import re
import imaplib
import email
import argparse
import psycopg2
from datetime import datetime, timedelta
from email.header import decode_header
from pathlib import Path
from dotenv import load_dotenv

load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')
load_dotenv('/opt/ACTIVE/EMAIL/.env')

DB_CONFIG = dict(host='localhost', dbname='norway_emails', user='tudor', password='tudor')

try:
    from alerting import send_telegram
except Exception:
    def send_telegram(msg): pass

# Inboxes to scan (match sender accounts used in campaigns)
INBOXES = [
    {'host': 'nl1-cl8-ats1.a2hosting.com', 'port': 993, 'user': 'office@interjob.ro',
     'pass_env': 'IMAP_INTERJOB_PASS'},
    {'host': 'nl1-cl8-ats1.a2hosting.com', 'port': 993, 'user': 'office@nepalezi.com',
     'pass_env': 'IMAP_NEPALEZI_PASS'},
    {'host': 'nl1-cl8-ats1.a2hosting.com', 'port': 993, 'user': 'office@careworkers.eu',
     'pass_env': 'IMAP_CAREWORKERS_PASS'},
    {'host': 'nl1-cl8-ats1.a2hosting.com', 'port': 993, 'user': 'office@factoryjobs.eu',
     'pass_env': 'IMAP_FACTORYJOBS_PASS'},
]

# Classification keywords
DECLINE_WORDS = ['not interested', 'no thank', 'remove', 'stop', 'unsubscribe',
                 'ikke interessert', 'nei takk', 'fjern', 'slutt', 'avmeld']
INTERESTED_WORDS = ['interested', 'tell me more', 'send', 'cv', 'candidates',
                     'interessert', 'fortell mer', 'kandidater', 'ring meg']
BOUNCE_WORDS = ['undeliverable', 'delivery failed', 'bounce', 'rejected',
                'mailer-daemon', 'postmaster']
AUTO_REPLY_WORDS = ['out of office', 'auto-reply', 'automatic reply',
                     'fravarende', 'automatisk svar', 'fravarsmelding']


def classify_response(subject, body):
    """Classify response type."""
    text = f"{subject} {body}".lower()

    if any(w in text for w in BOUNCE_WORDS):
        return 'bounce'
    if any(w in text for w in AUTO_REPLY_WORDS):
        return 'auto_reply'
    if any(w in text for w in ['unsubscribe', 'avmeld', 'remove me', 'fjern meg']):
        return 'unsubscribe'
    if any(w in text for w in DECLINE_WORDS):
        return 'declined'
    if any(w in text for w in INTERESTED_WORDS):
        return 'interested'
    return 'unknown'


def decode_subject(msg):
    raw = msg.get('Subject', '')
    decoded_parts = decode_header(raw)
    parts = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            parts.append(part.decode(charset or 'utf-8', errors='replace'))
        else:
            parts.append(part)
    return ' '.join(parts)


def get_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode('utf-8', errors='replace')[:2000]
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode('utf-8', errors='replace')[:2000]
    return ''


def scan_inbox(inbox_cfg, conn, since_date):
    """Scan one IMAP inbox for Norwegian replies."""
    password = os.environ.get(inbox_cfg['pass_env'], '')
    if not password:
        return 0

    try:
        imap = imaplib.IMAP4_SSL(inbox_cfg['host'], inbox_cfg['port'])
        imap.login(inbox_cfg['user'], password)
        imap.select('INBOX')
    except Exception as e:
        print(f"  IMAP error {inbox_cfg['user']}: {e}")
        return 0

    # Search for recent emails
    search_date = since_date.strftime('%d-%b-%Y')
    status, msg_ids = imap.search(None, f'SINCE {search_date}')
    if status != 'OK':
        imap.logout()
        return 0

    ids = msg_ids[0].split()
    new_responses = 0
    cur = conn.cursor()

    for msg_id in ids[-200:]:  # Last 200 messages
        try:
            status, data = imap.fetch(msg_id, '(RFC822)')
            if status != 'OK':
                continue
            msg = email.message_from_bytes(data[0][1])

            from_addr = email.utils.parseaddr(msg.get('From', ''))[1].lower()
            if not from_addr.endswith('.no'):
                continue

            subject = decode_subject(msg)
            body = get_body(msg)
            response_type = classify_response(subject, body)

            # Check if already tracked
            cur.execute("SELECT id FROM norway_responses WHERE email = %s AND raw_subject = %s",
                        (from_addr, subject[:200]))
            if cur.fetchone():
                continue

            # Look up company
            cur.execute("SELECT name, org_number FROM norway_emails WHERE LOWER(email) = %s LIMIT 1",
                        (from_addr,))
            company_row = cur.fetchone()
            company_name = company_row[0] if company_row else ''
            org_number = company_row[1] if company_row else ''

            # Insert response
            cur.execute("""
                INSERT INTO norway_responses (email, company_name, org_number, campaign, response_type, raw_subject)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (from_addr, company_name, org_number, inbox_cfg['user'], response_type, subject[:200]))

            # Update main table
            cur.execute(
                "UPDATE norway_emails SET campaign_status = 'responded', response_type = %s WHERE LOWER(email) = %s",
                (response_type, from_addr)
            )

            # Auto-add unsubscribes to DNC
            if response_type == 'unsubscribe':
                cur.execute(
                    "INSERT INTO norway_dnc (email, reason) VALUES (%s, %s) ON CONFLICT (email) DO NOTHING",
                    (from_addr, 'unsubscribe_reply')
                )

            new_responses += 1
            print(f"    {response_type}: {from_addr} - {subject[:50]}")

        except Exception as e:
            continue

    conn.commit()
    imap.logout()
    return new_responses


def show_stats():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT response_type, COUNT(*) FROM norway_responses GROUP BY response_type ORDER BY COUNT(*) DESC")
    rows = cur.fetchall()
    cur.execute("SELECT COUNT(*) FROM norway_responses")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM norway_dnc")
    dnc_count = cur.fetchone()[0]
    conn.close()

    print(f"\nNorway Response Stats")
    print(f"{'=' * 35}")
    print(f"Total responses: {total}")
    for rtype, count in rows:
        print(f"  {rtype}: {count}")
    print(f"DNC list: {dnc_count}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stats', action='store_true')
    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    print(f"Norway Response Tracker - {datetime.now():%Y-%m-%d %H:%M}")
    since = datetime.now() - timedelta(days=7)
    conn = psycopg2.connect(**DB_CONFIG)
    total_new = 0

    for inbox in INBOXES:
        print(f"  Scanning {inbox['user']}...")
        count = scan_inbox(inbox, conn, since)
        total_new += count

    conn.close()
    print(f"\nNew responses: {total_new}")

    if total_new > 0:
        try:
            send_telegram(f"Norway responses: {total_new} new replies detected")
        except Exception:
            pass


if __name__ == '__main__':
    main()
