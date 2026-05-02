#!/usr/bin/env python3
"""
A2 SMTP Spam Checker - Monitors deliverability using seed emails.

How it works:
1. Sends test email to seed Gmail account
2. Waits for delivery (30-60 sec)
3. Checks Gmail via IMAP - inbox vs spam folder
4. Returns spam status

Usage:
    a2_spam_checker.py --test                    # Send test and check
    a2_spam_checker.py --check-inbox             # Just check inbox status
    a2_spam_checker.py --domain horecaworkers.eu # Test specific domain

Integrate into sender:
    from a2_spam_checker import check_a2_spam, SpamDetected

    # After every 10 sends:
    if send_count % 10 == 0:
        result = check_a2_spam("horecaworkers.eu")
        if result.is_spam:
            raise SpamDetected(result.message)
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import imaplib
import smtplib
import ssl
import email
import time
import argparse
import json
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path

from dotenv import load_dotenv
from skills_common import get_a2_password
from alerting import send_telegram

# Load env
load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

# Configuration
SEED_EMAIL = os.getenv('SPAM_CHECK_EMAIL', 'manpowerdristor@gmail.com')
SEED_PASSWORD = os.getenv('SPAM_CHECK_PASSWORD', os.getenv('GMAIL_APP_PASSWORD', ''))
IMAP_SERVER = 'imap.gmail.com'
STATE_FILE = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/DATA/spam_check_state.json')

# A2 domains to check
A2_DOMAINS = [
    'horecaworkers.eu',
    'horecaworkers2026.eu',
    'horecaworkers2026.com',
    'horecaworkers2026.online',
    'factoryjobs.eu',
    'warehouseworkers.eu',
    'meatworkers.eu',
    'electricjobs.eu',
    'mechanicjobs.eu',
    'farmworkers.eu',
]


@dataclass
class SpamCheckResult:
    domain: str
    is_spam: bool
    location: str  # 'inbox', 'spam', 'not_found', 'error'
    message: str
    checked_at: str


class SpamDetected(Exception):
    """Raised when spam is detected."""
    pass


def load_state() -> dict:
    """Load spam check state."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except:
            pass
    return {'checks': {}, 'last_spam': None}


def save_state(state: dict):
    """Save spam check state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


def send_test_email(domain: str, to_email: str = SEED_EMAIL) -> tuple[bool, str]:
    """Send test email via A2 SMTP."""
    from_email = f"office@{domain}"
    password = get_a2_password(domain)

    if not password:
        return False, f"No password for {domain}"

    # Create unique subject for tracking
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    subject = f"[SPAM-CHECK-{domain}-{timestamp}]"

    msg = MIMEMultipart()
    msg['From'] = f"Spam Check <{from_email}>"
    msg['To'] = to_email
    msg['Subject'] = subject

    body = f"""
This is an automated spam check email.
Domain: {domain}
Time: {datetime.now().isoformat()}
Tracking ID: {timestamp}

If you see this in SPAM folder, the domain has deliverability issues.
"""
    msg.attach(MIMEText(body, 'plain'))

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(f"mail.{domain}", 465, context=ctx, timeout=30) as server:
            server.login(from_email, password)
            server.send_message(msg)
        return True, subject
    except Exception as e:
        return False, str(e)


def check_gmail_for_email(subject: str, check_spam: bool = True, timeout: int = 90) -> tuple[str, Optional[str]]:
    """
    Check Gmail for email with given subject.
    Returns: (location, message_id) where location is 'inbox', 'spam', 'not_found'
    """
    if not SEED_PASSWORD:
        return 'error', 'No Gmail password configured'

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(SEED_EMAIL, SEED_PASSWORD)

        # Search in INBOX first
        mail.select('INBOX')
        _, messages = mail.search(None, f'SUBJECT "{subject}"')
        if messages[0]:
            mail.logout()
            return 'inbox', messages[0].decode().split()[-1]

        # Search in SPAM folder
        if check_spam:
            mail.select('[Gmail]/Spam')
            _, messages = mail.search(None, f'SUBJECT "{subject}"')
            if messages[0]:
                mail.logout()
                return 'spam', messages[0].decode().split()[-1]

        mail.logout()
        return 'not_found', None

    except Exception as e:
        return 'error', str(e)


def check_a2_spam(domain: str, wait_seconds: int = 60) -> SpamCheckResult:
    """
    Full spam check: send test email, wait, check location.
    """
    timestamp = datetime.now().isoformat()

    # Send test email
    success, subject_or_error = send_test_email(domain)
    if not success:
        return SpamCheckResult(
            domain=domain,
            is_spam=False,
            location='error',
            message=f"Send failed: {subject_or_error}",
            checked_at=timestamp
        )

    subject = subject_or_error
    print(f"[{domain}] Test email sent, waiting {wait_seconds}s for delivery...")

    # Wait for delivery
    time.sleep(wait_seconds)

    # Check location
    location, msg_id = check_gmail_for_email(subject)

    is_spam = location == 'spam'

    if is_spam:
        message = f"SPAM DETECTED: {domain} emails landing in spam folder!"
    elif location == 'inbox':
        message = f"OK: {domain} emails landing in inbox"
    elif location == 'not_found':
        message = f"WARNING: Test email not found (may still be in transit)"
    else:
        message = f"ERROR: {msg_id}"

    result = SpamCheckResult(
        domain=domain,
        is_spam=is_spam,
        location=location,
        message=message,
        checked_at=timestamp
    )

    # Update state
    state = load_state()
    state['checks'][domain] = {
        'location': location,
        'is_spam': is_spam,
        'checked_at': timestamp,
        'subject': subject
    }
    if is_spam:
        state['last_spam'] = {'domain': domain, 'at': timestamp}
    save_state(state)

    return result


def quick_inbox_check() -> dict:
    """Quick check of recent emails in inbox vs spam."""
    results = {'inbox': 0, 'spam': 0, 'spam_domains': []}

    if not SEED_PASSWORD:
        return {'error': 'No Gmail password configured'}

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(SEED_EMAIL, SEED_PASSWORD)

        # Count recent in inbox
        mail.select('INBOX')
        since = (datetime.now() - timedelta(hours=24)).strftime('%d-%b-%Y')
        _, messages = mail.search(None, f'SINCE {since}')
        results['inbox'] = len(messages[0].split()) if messages[0] else 0

        # Count and identify spam
        mail.select('[Gmail]/Spam')
        _, messages = mail.search(None, f'SINCE {since}')
        if messages[0]:
            results['spam'] = len(messages[0].split())

            # Get spam senders
            for msg_id in messages[0].split()[-5:]:  # Last 5
                _, msg_data = mail.fetch(msg_id, '(RFC822.HEADER)')
                msg = email.message_from_bytes(msg_data[0][1])
                sender = msg.get('From', '')
                for domain in A2_DOMAINS:
                    if domain in sender:
                        results['spam_domains'].append(domain)
                        break

        mail.logout()

    except Exception as e:
        results['error'] = str(e)

    return results


def integrate_with_sender(domain: str, send_count: int, check_every: int = 10) -> Optional[SpamCheckResult]:
    """
    Call this from sender script after each batch.
    Returns SpamCheckResult if check was performed, None otherwise.
    """
    if send_count % check_every != 0:
        return None

    print(f"\n[SPAM CHECK] Checking {domain} after {send_count} sends...")
    result = check_a2_spam(domain, wait_seconds=45)

    if result.is_spam:
        send_telegram(f"🚨 SPAM ALERT: {domain} emails going to spam! Campaign should STOP.")
        raise SpamDetected(result.message)

    print(f"[SPAM CHECK] {result.message}")
    return result


def show_status():
    """Show spam check status."""
    state = load_state()

    print("=" * 50)
    print("A2 SPAM CHECK STATUS")
    print("=" * 50)
    print(f"Seed email: {SEED_EMAIL}")
    print(f"Password configured: {'Yes' if SEED_PASSWORD else 'NO!'}")
    print()

    # Quick inbox check
    inbox = quick_inbox_check()
    if 'error' not in inbox:
        print(f"Last 24h: {inbox['inbox']} inbox, {inbox['spam']} spam")
        if inbox['spam_domains']:
            print(f"A2 domains in spam: {', '.join(set(inbox['spam_domains']))}")
    print()

    # Domain status
    print("Domain checks:")
    for domain in A2_DOMAINS:
        check = state.get('checks', {}).get(domain, {})
        if check:
            loc = check.get('location', '?')
            icon = '✓' if loc == 'inbox' else '✗' if loc == 'spam' else '?'
            at = check.get('checked_at', '')[:16]
            print(f"  {icon} {domain}: {loc} ({at})")
        else:
            print(f"  ? {domain}: not checked")

    if state.get('last_spam'):
        print(f"\n⚠ Last spam detected: {state['last_spam']['domain']} at {state['last_spam']['at']}")


def main():
    parser = argparse.ArgumentParser(description='A2 SMTP Spam Checker')
    parser.add_argument('--test', '-t', action='store_true', help='Send test and check all domains')
    parser.add_argument('--domain', '-d', help='Test specific domain')
    parser.add_argument('--check-inbox', '-c', action='store_true', help='Quick inbox check')
    parser.add_argument('--status', '-s', action='store_true', help='Show status')
    parser.add_argument('--wait', '-w', type=int, default=60, help='Wait seconds after send (default: 60)')
    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.check_inbox:
        result = quick_inbox_check()
        print(json.dumps(result, indent=2))
    elif args.domain:
        result = check_a2_spam(args.domain, args.wait)
        print(f"\n{result.message}")
        if result.is_spam:
            sys.exit(1)
    elif args.test:
        # Test all LUCIAN_HORECA domains
        domains = ['horecaworkers.eu', 'horecaworkers2026.eu', 'horecaworkers2026.com', 'horecaworkers2026.online']
        for domain in domains:
            result = check_a2_spam(domain, args.wait)
            icon = '✗' if result.is_spam else '✓' if result.location == 'inbox' else '?'
            print(f"{icon} {domain}: {result.location}")
            if result.is_spam:
                print(f"  ALERT: {result.message}")
    else:
        show_status()


if __name__ == '__main__':
    main()
