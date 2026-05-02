#!/usr/bin/env python3
"""
Check bounced emails from IMAP inbox and optionally retry sending.

Usage:
    python3 check_bounces.py                    # List all bounces
    python3 check_bounces.py --domain anofm.ro  # Filter by domain
    python3 check_bounces.py --retry            # Retry all soft bounces (421)
    python3 check_bounces.py --retry --domain anofm.ro  # Retry specific domain
    python3 check_bounces.py --delete           # Delete bounce notifications after processing
"""

import imaplib
import email
import re
import smtplib
import argparse
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from collections import defaultdict
from datetime import datetime

# IMAP config - tudor@seicarescu.com
IMAP_HOST = "mail.seicarescu.com"
IMAP_USER = "tudor@seicarescu.com"
IMAP_PASS = "Romania1973"

# A2 SMTP for retries
A2_SMTP_HOST = "nl1-cl8-ats1.a2hosting.com"
A2_SMTP_PORT = 465
A2_SMTP_USER = "office@horecaworkers.eu"
A2_SMTP_PASS = "z5b3VcHeskXckckl"


def get_bounces(domain_filter=None):
    """Fetch all bounce emails from IMAP."""
    mail = imaplib.IMAP4_SSL(IMAP_HOST)
    mail.login(IMAP_USER, IMAP_PASS)
    mail.select("INBOX")

    status, messages = mail.search(None, '(OR FROM "mailer-daemon" FROM "mailchannels" FROM "postmaster")')
    msg_ids = messages[0].split() if messages[0] else []

    bounces = []

    for msg_id in msg_ids:
        status, msg_data = mail.fetch(msg_id, "(RFC822)")
        if status != "OK":
            continue

        msg = email.message_from_bytes(msg_data[0][1])
        date_str = msg.get("Date", "")
        subject = msg.get("Subject", "")

        # Get body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                ct = part.get_content_type()
                if ct == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode('utf-8', errors='ignore')
                        break
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode('utf-8', errors='ignore')

        # Extract failed email
        failed_emails = re.findall(r'<([^>]+@[^>]+)>', body)

        # Extract error code
        error_match = re.search(r'(4\d{2}|5\d{2})[^\n]{0,100}', body)
        error_code = error_match.group()[:100] if error_match else "Unknown"

        # Determine bounce type
        if error_code.startswith('4'):
            bounce_type = 'soft'  # Temporary
        elif error_code.startswith('5'):
            bounce_type = 'hard'  # Permanent
        else:
            bounce_type = 'unknown'

        # Extract original message if available
        original_subject = ""
        orig_match = re.search(r'Subject:\s*(.+)', body)
        if orig_match:
            original_subject = orig_match.group(1).strip()[:80]

        for failed_email in failed_emails:
            if domain_filter and domain_filter.lower() not in failed_email.lower():
                continue

            bounces.append({
                'msg_id': msg_id,
                'date': date_str[:25] if date_str else 'Unknown',
                'email': failed_email,
                'error': error_code,
                'type': bounce_type,
                'original_subject': original_subject
            })

    mail.logout()
    return bounces


def delete_bounce_notifications(msg_ids):
    """Delete processed bounce notifications from inbox."""
    if not msg_ids:
        return 0

    mail = imaplib.IMAP4_SSL(IMAP_HOST)
    mail.login(IMAP_USER, IMAP_PASS)
    mail.select("INBOX")

    deleted = 0
    for msg_id in set(msg_ids):
        try:
            mail.store(msg_id, '+FLAGS', '\\Deleted')
            deleted += 1
        except:
            pass

    mail.expunge()
    mail.logout()
    return deleted


def retry_send(email_addr, subject, body):
    """Retry sending email via A2 SMTP."""
    msg = MIMEMultipart()
    msg['From'] = f"Tudor Seicarescu <{A2_SMTP_USER}>"
    msg['To'] = email_addr
    msg['Subject'] = subject
    msg['Reply-To'] = IMAP_USER
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    try:
        with smtplib.SMTP_SSL(A2_SMTP_HOST, A2_SMTP_PORT, timeout=30) as server:
            server.login(A2_SMTP_USER, A2_SMTP_PASS)
            server.sendmail(A2_SMTP_USER, email_addr, msg.as_string())
        return True, None
    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(description='Check and retry bounced emails')
    parser.add_argument('--domain', help='Filter by email domain (e.g., anofm.ro)')
    parser.add_argument('--retry', action='store_true', help='Retry soft bounces (421)')
    parser.add_argument('--delete', action='store_true', help='Delete bounce notifications after processing')
    parser.add_argument('--subject', default='Re: Cerere informatii', help='Subject for retry')
    parser.add_argument('--body-file', help='File containing email body for retry')
    parser.add_argument('--limit', type=int, default=0, help='Limit retries (0=all)')
    parser.add_argument('--delay', type=int, default=2, help='Delay between sends in seconds (default: 2)')
    args = parser.parse_args()

    print(f"Checking bounces from {IMAP_USER}...")
    bounces = get_bounces(args.domain)

    if not bounces:
        print("No bounces found.")
        return

    # Group by type
    by_type = defaultdict(list)
    for b in bounces:
        by_type[b['type']].append(b)

    print(f"\n{'='*60}")
    print(f"BOUNCE SUMMARY")
    print(f"{'='*60}")
    print(f"Soft (4xx - temporary): {len(by_type['soft'])}")
    print(f"Hard (5xx - permanent): {len(by_type['hard'])}")
    print(f"Unknown: {len(by_type['unknown'])}")
    print(f"Total: {len(bounces)}")

    if args.domain:
        print(f"Filtered by: {args.domain}")

    # List bounces
    print(f"\n{'='*60}")
    print(f"BOUNCED EMAILS")
    print(f"{'='*60}")

    seen_emails = set()
    unique_bounces = []
    for b in bounces:
        if b['email'] not in seen_emails:
            seen_emails.add(b['email'])
            unique_bounces.append(b)
            status = "SOFT" if b['type'] == 'soft' else "HARD" if b['type'] == 'hard' else "????"
            print(f"[{status}] {b['email']}")
            print(f"        {b['error'][:60]}")

    print(f"\nUnique emails: {len(unique_bounces)}")

    # Retry soft bounces
    if args.retry:
        soft_bounces = [b for b in unique_bounces if b['type'] == 'soft']

        if not soft_bounces:
            print("\nNo soft bounces to retry.")
            return

        # Load body
        if args.body_file:
            with open(args.body_file, 'r') as f:
                body = f.read()
        else:
            body = """Stimate domnule/Stimata doamna,

Revin cu rugamintea de a raspunde la cererea de informatii de interes public transmisa anterior, in temeiul Legii nr. 544/2001.

Va multumesc anticipat pentru raspuns.

Cu stima,
Tudor Seicarescu
Tel: 0722789938
"""

        print(f"\n{'='*60}")
        print(f"RETRYING {len(soft_bounces)} SOFT BOUNCES")
        print(f"{'='*60}")

        success = 0
        failed = 0
        limit = args.limit if args.limit > 0 else len(soft_bounces)

        for i, b in enumerate(soft_bounces[:limit]):
            print(f"[{i+1}/{limit}] Sending to {b['email']}...", end=' ')
            ok, err = retry_send(b['email'], args.subject, body)
            if ok:
                print("OK")
                success += 1
            else:
                print(f"FAILED: {err}")
                failed += 1
            if i < limit - 1:  # Don't sleep after last email
                print(f"    Waiting {args.delay}s...")
                time.sleep(args.delay)

        print(f"\nRetry complete: {success} sent, {failed} failed")

    # Delete notifications
    if args.delete:
        msg_ids = [b['msg_id'] for b in bounces]
        deleted = delete_bounce_notifications(msg_ids)
        print(f"\nDeleted {deleted} bounce notifications from inbox")


if __name__ == '__main__':
    main()
