#!/usr/bin/env python3
"""
Email Spam/Bounce Checker - No tokens, local only

Checks for spam complaints and bounces:
- Brevo: API check (free)
- A2 SMTP: IMAP inbox check for bounces

Usage:
    from email_spam_checker import check_sender, SpamAlert

    alert = check_sender("a2_horecaworkers")
    if alert:
        print(f"PROBLEM: {alert.message}")
        print(f"Suggestion: {alert.suggestion}")
"""
import os
import sys
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, Tuple, List
from dotenv import load_dotenv

load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

@dataclass
class SpamAlert:
    """Alert when spam/bounce detected."""
    sender: str
    alert_type: str  # 'spam', 'bounce', 'block'
    count: int
    message: str
    suggestion: str


# A2 SMTP credentials (from .env)
A2_DOMAINS = {
    'horecaworkers.eu': {'user': 'office@horecaworkers.eu', 'env_pass': 'A2_HORECAWORKERS_PASS'},
    'meatworkers.eu': {'user': 'office@meatworkers.eu', 'env_pass': 'A2_MEATWORKERS_PASS'},
    'electricjobs.eu': {'user': 'office@electricjobs.eu', 'env_pass': 'A2_ELECTRICJOBS_PASS'},
    'mechanicjobs.eu': {'user': 'office@mechanicjobs.eu', 'env_pass': 'A2_MECHANICJOBS_PASS'},
    'farmworkers.eu': {'user': 'office@farmworkers.eu', 'env_pass': 'A2_FARMWORKERS_PASS'},
    'factoryjobs.eu': {'user': 'office@factoryjobs.eu', 'env_pass': 'A2_FACTORYJOBS_PASS'},
    'warehouseworkers.eu': {'user': 'office@warehouseworkers.eu', 'env_pass': 'A2_WAREHOUSEWORKERS_PASS'},
}

A2_IMAP_SERVER = "mail.a2hosting.com"

# Bounce/spam keywords to detect
BOUNCE_SUBJECTS = [
    'undeliverable', 'delivery failed', 'mail delivery failed',
    'returned mail', 'delivery status notification', 'failure notice',
    'undelivered mail', 'could not be delivered', 'message blocked',
    'rejected', 'spam', 'complaint', 'abuse'
]

BOUNCE_SENDERS = [
    'mailer-daemon', 'postmaster', 'mail-daemon', 'noreply',
    'bounce', 'returned', 'failed'
]


def check_a2_imap(domain: str, hours: int = 1) -> Tuple[int, int, List[str]]:
    """
    Check A2 IMAP inbox for bounces in last N hours.

    Returns:
        (bounce_count, spam_count, affected_emails)
    """
    if domain not in A2_DOMAINS:
        return 0, 0, []

    config = A2_DOMAINS[domain]
    password = os.getenv(config['env_pass'])

    if not password:
        print(f"  Warning: No password for {domain}")
        return 0, 0, []

    bounces = 0
    spam_reports = 0
    affected = []

    try:
        # Connect to IMAP
        imap = imaplib.IMAP4_SSL(A2_IMAP_SERVER, 993)
        imap.login(config['user'], password)
        imap.select('INBOX')

        # Search for recent emails
        since_date = (datetime.now() - timedelta(hours=hours)).strftime("%d-%b-%Y")
        _, messages = imap.search(None, f'(SINCE {since_date})')

        for msg_id in messages[0].split():
            _, msg_data = imap.fetch(msg_id, '(RFC822.HEADER)')

            if not msg_data or not msg_data[0]:
                continue

            header_data = msg_data[0][1]
            msg = email.message_from_bytes(header_data)

            # Get subject
            subject = msg.get('Subject', '')
            if subject:
                decoded = decode_header(subject)
                subject = ''.join(
                    part.decode(enc or 'utf-8') if isinstance(part, bytes) else part
                    for part, enc in decoded
                ).lower()

            # Get from
            from_addr = msg.get('From', '').lower()

            # Check for bounce
            is_bounce = any(kw in subject for kw in BOUNCE_SUBJECTS)
            is_bounce = is_bounce or any(s in from_addr for s in BOUNCE_SENDERS)

            # Check for spam report
            is_spam = 'spam' in subject or 'complaint' in subject or 'abuse' in subject

            if is_bounce:
                bounces += 1
                # Try to extract original recipient
                affected.append(subject[:50])

            if is_spam:
                spam_reports += 1
                affected.append(f"SPAM: {subject[:50]}")

        imap.logout()

    except imaplib.IMAP4.error as e:
        print(f"  IMAP error for {domain}: {e}")
    except Exception as e:
        print(f"  Error checking {domain}: {e}")

    return bounces, spam_reports, affected


def check_brevo_api(api_key: str, hours: int = 1) -> Tuple[int, int, float]:
    """
    Check Brevo API for spam/bounces.

    Returns:
        (spam_count, bounce_count, bounce_rate)
    """
    import requests

    headers = {"api-key": api_key}

    spam_count = 0
    bounce_count = 0
    bounce_rate = 0.0

    try:
        # Check complaints
        start_date = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")

        resp = requests.get(
            "https://api.brevo.com/v3/smtp/statistics/events",
            headers=headers,
            params={"event": "complaint", "limit": 100, "startDate": start_date, "endDate": end_date},
            timeout=10
        )

        if resp.status_code == 200:
            events = resp.json().get("events", [])
            # Filter to last hour
            hour_ago = datetime.now() - timedelta(hours=hours)
            for event in events:
                try:
                    event_time = datetime.fromisoformat(event.get("date", "").replace("Z", "+00:00"))
                    if event_time.replace(tzinfo=None) > hour_ago:
                        spam_count += 1
                except:
                    pass

        # Check bounce rate
        resp = requests.get(
            "https://api.brevo.com/v3/smtp/statistics/aggregatedReport",
            headers=headers,
            params={"days": 1},
            timeout=10
        )

        if resp.status_code == 200:
            data = resp.json()
            total = data.get("requests", 0)
            if total > 0:
                hard = data.get("hardBounces", 0)
                soft = data.get("softBounces", 0)
                bounce_count = hard + soft
                bounce_rate = (bounce_count / total) * 100

    except Exception as e:
        print(f"  Brevo API error: {e}")

    return spam_count, bounce_count, bounce_rate


def check_sender(sender_id: str, hours: int = 1) -> Optional[SpamAlert]:
    """
    Check a sender for spam/bounce issues.

    Args:
        sender_id: e.g. 'a2_horecaworkers' or 'brevo_buildjobs'
        hours: How many hours back to check

    Returns:
        SpamAlert if problem detected, None if OK
    """
    print(f"Checking {sender_id}...")

    if sender_id.startswith('a2_'):
        # A2 SMTP - check IMAP
        domain = sender_id.replace('a2_', '') + '.eu'
        bounces, spam, affected = check_a2_imap(domain, hours)

        if spam > 0:
            return SpamAlert(
                sender=sender_id,
                alert_type='spam',
                count=spam,
                message=f"{spam} spam complaints in last {hours}h",
                suggestion="STOP sending. Check inbox for abuse reports. May need to pause domain 24-48h."
            )

        if bounces > 3:
            return SpamAlert(
                sender=sender_id,
                alert_type='bounce',
                count=bounces,
                message=f"{bounces} bounces in last {hours}h",
                suggestion="Clean contact list. Run bounce sync. Check for invalid domains."
            )

        print(f"  OK: {bounces} bounces, {spam} spam")
        return None

    elif sender_id.startswith('brevo_'):
        # Brevo - check API
        domain = sender_id.replace('brevo_', '').upper()
        api_key = os.getenv(f'BREVO_{domain}_API_KEY')

        if not api_key:
            # Try alternate naming
            alt_names = {
                'mivromania': 'MIVROMANIA',
                'mivromania_online': 'MIVROMANIA_ONLINE',
                'buildjobs': 'BUILDJOBS',
                'factoryjobs': 'FACTORYJOBS',
                'careworkers': 'CAREWORKERS',
                'cifn': 'CIFN',
                'interjob': 'INTERJOB',
                'nepalezi': 'NEPALEZI',
                'warehouse': 'WAREHOUSE'
            }
            name = sender_id.replace('brevo_', '')
            if name in alt_names:
                api_key = os.getenv(f'BREVO_{alt_names[name]}_API_KEY')

        if not api_key:
            print(f"  Warning: No API key for {sender_id}")
            return None

        spam, bounces, bounce_rate = check_brevo_api(api_key, hours)

        if spam > 0:
            return SpamAlert(
                sender=sender_id,
                alert_type='spam',
                count=spam,
                message=f"{spam} spam complaints in last {hours}h",
                suggestion="STOP immediately. Brevo will suspend account. Wait 24h, clean list, change template."
            )

        if bounce_rate > 15.0:  # Was 5.0, raised: aggregatedReport is account-wide not per-campaign
            return SpamAlert(
                sender=sender_id,
                alert_type='bounce',
                count=bounces,
                message=f"Bounce rate {bounce_rate:.1f}% (>15% threshold)",
                suggestion="Pause campaign. Run bounce sync. Clean invalid emails from contacts."
            )

        print(f"  OK: {spam} spam, {bounce_rate:.1f}% bounce rate")
        return None

    else:
        print(f"  Unknown sender type: {sender_id}")
        return None


def check_all_senders() -> List[SpamAlert]:
    """Check all configured senders."""
    alerts = []

    # A2 senders
    for domain in A2_DOMAINS:
        sender_id = f"a2_{domain.replace('.eu', '')}"
        alert = check_sender(sender_id)
        if alert:
            alerts.append(alert)

    # Brevo senders
    brevo_senders = ['brevo_mivromania', 'brevo_mivromania_online', 'brevo_buildjobs',
                     'brevo_factoryjobs', 'brevo_careworkers', 'brevo_cifn',
                     'brevo_interjob', 'brevo_nepalezi']

    for sender_id in brevo_senders:
        alert = check_sender(sender_id)
        if alert:
            alerts.append(alert)

    return alerts


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Check senders for spam/bounce issues")
    parser.add_argument('sender', nargs='?', help='Sender ID (e.g. a2_horecaworkers)')
    parser.add_argument('--all', '-a', action='store_true', help='Check all senders')
    parser.add_argument('--hours', '-H', type=int, default=1, help='Hours to check (default: 1)')
    args = parser.parse_args()

    if args.all:
        print("=== Checking all senders ===\n")
        alerts = check_all_senders()

        if alerts:
            print("\n=== ALERTS ===")
            for alert in alerts:
                print(f"\n{alert.sender}: {alert.alert_type.upper()}")
                print(f"  {alert.message}")
                print(f"  Suggestion: {alert.suggestion}")
        else:
            print("\nAll senders OK")

    elif args.sender:
        alert = check_sender(args.sender, args.hours)

        if alert:
            print(f"\n!!! ALERT: {alert.alert_type.upper()} !!!")
            print(f"Message: {alert.message}")
            print(f"Suggestion: {alert.suggestion}")
            sys.exit(1)
        else:
            print("OK - No issues detected")

    else:
        parser.print_help()
