#!/usr/bin/env python3
"""
Verify BCC emails are being deleted after spam check.
Run periodically or on-demand to ensure:
1. manpowerdristor@gmail.com (seed) inbox stays clean
2. lucian.bpandp@gmail.com (reply-to) is NOT receiving BCCs

Usage:
    python3 verify_bcc_cleanup.py           # Quick check
    python3 verify_bcc_cleanup.py --verbose # Show details
    python3 verify_bcc_cleanup.py --json    # JSON output for automation
"""

import sys
import os
import json
import imaplib
from datetime import datetime
from typing import Dict, Optional

from dotenv import load_dotenv

load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

# Account configs
ACCOUNTS = {
    'manpowerdristor': {
        'email': os.getenv('GMAIL_EMAIL', 'manpowerdristor@gmail.com'),
        'password': os.getenv('GMAIL_APP_PASSWORD', ''),
        'role': 'SEED (should receive BCCs, then delete)',
        'max_campaign_emails': 5  # Warning threshold
    },
    'lucian': {
        'email': os.getenv('GMAIL_LUCIAN_EMAIL', 'lucian.bpandp@gmail.com'),
        'password': os.getenv('GMAIL_LUCIAN_APP_PASSWORD', '').replace('"', '').strip(),
        'role': 'REPLY-TO ONLY (should NOT receive BCCs)',
        'max_campaign_emails': 0  # Should never have campaign emails
    }
}

# Our campaign sender domains
OUR_DOMAINS = [
    'horecaworkers', 'horecaworkers2026',
    'mivromania', 'factoryjobs', 'buildjobs', 'interjob',
    'careworkers', 'cifn', 'warehouseworkers',
    'meatworkers', 'electricjobs', 'mechanicjobs', 'farmworkers'
]


def check_inbox(name: str, email: str, password: str, verbose: bool = False) -> Dict:
    """
    Count campaign emails in inbox.

    Returns:
        dict with campaign_count, total_count, details, error
    """
    result = {
        'account': name,
        'email': email,
        'campaign_count': 0,
        'total_count': 0,
        'details': [],
        'error': None
    }

    if not password:
        result['error'] = 'No password configured'
        return result

    try:
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(email, password)
        mail.select('INBOX')

        # Get all messages
        _, messages = mail.search(None, 'ALL')
        if messages[0]:
            msg_ids = messages[0].decode().split()
            result['total_count'] = len(msg_ids)

            # Check each for campaign origin
            for msg_id in msg_ids:
                try:
                    _, data = mail.fetch(msg_id, '(RFC822.HEADER)')
                    header = data[0][1].decode(errors='ignore')
                    header_lower = header.lower()

                    # Check if from our domains
                    is_campaign = any(d in header_lower for d in OUR_DOMAINS)
                    if is_campaign:
                        result['campaign_count'] += 1

                        # Extract subject for details
                        if verbose:
                            for line in header.split('\n'):
                                if line.lower().startswith('subject:'):
                                    subject = line[8:].strip()[:50]
                                    result['details'].append(subject)
                                    break
                except Exception as e:
                    if verbose:
                        print(f"  Warning: Error reading message {msg_id}: {e}")

        mail.logout()

    except Exception as e:
        result['error'] = str(e)

    return result


def verify(verbose: bool = False, json_output: bool = False) -> bool:
    """
    Verify all accounts.

    Returns:
        True if all accounts are clean, False otherwise
    """
    results = {}
    all_clean = True

    for name, config in ACCOUNTS.items():
        result = check_inbox(
            name,
            config['email'],
            config['password'],
            verbose
        )
        result['role'] = config['role']
        result['max_allowed'] = config['max_campaign_emails']
        result['is_clean'] = (
            result['error'] is None and
            result['campaign_count'] <= config['max_campaign_emails']
        )

        if not result['is_clean']:
            all_clean = False

        results[name] = result

    # Output
    if json_output:
        output = {
            'checked_at': datetime.now().isoformat(),
            'all_clean': all_clean,
            'accounts': results
        }
        print(json.dumps(output, indent=2))
    else:
        print("=== BCC CLEANUP VERIFICATION ===")
        print(f"Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        for name, data in results.items():
            if data['error']:
                status = f"ERROR: {data['error']}"
                symbol = "X"
            elif data['is_clean']:
                status = "OK"
                symbol = "OK"
            else:
                status = f"WARNING: {data['campaign_count']} campaign emails (max: {data['max_allowed']})"
                symbol = "!!"

            print(f"  [{symbol}] {name} ({data['email']})")
            print(f"      Role: {data['role']}")
            print(f"      Total inbox: {data['total_count']}, Campaign emails: {data['campaign_count']}")
            print(f"      Status: {status}")

            if verbose and data['details']:
                print(f"      Recent subjects:")
                for subj in data['details'][:5]:
                    print(f"        - {subj}")
            print()

        print("=" * 35)
        if all_clean:
            print("RESULT: All accounts clean")
        else:
            print("RESULT: Issues detected - check above")

    return all_clean


def cleanup_campaign_emails(account: str, dry_run: bool = True) -> Dict:
    """
    Delete campaign emails from specified account.

    Args:
        account: Account name ('manpowerdristor' or 'lucian')
        dry_run: If True, only count, don't delete

    Returns:
        dict with deleted_count, error
    """
    if account not in ACCOUNTS:
        return {'error': f'Unknown account: {account}'}

    config = ACCOUNTS[account]
    email = config['email']
    password = config['password']

    result = {
        'account': account,
        'email': email,
        'found_count': 0,
        'deleted_count': 0,
        'dry_run': dry_run,
        'error': None
    }

    if not password:
        result['error'] = 'No password configured'
        return result

    try:
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(email, password)
        mail.select('INBOX')

        _, messages = mail.search(None, 'ALL')
        if messages[0]:
            msg_ids = messages[0].decode().split()

            for msg_id in msg_ids:
                try:
                    _, data = mail.fetch(msg_id, '(RFC822.HEADER)')
                    header = data[0][1].decode(errors='ignore').lower()

                    if any(d in header for d in OUR_DOMAINS):
                        result['found_count'] += 1
                        if not dry_run:
                            mail.store(msg_id, '+FLAGS', '\\Deleted')
                            result['deleted_count'] += 1
                except Exception as e:
                    print(f"  Warning: Error processing {msg_id}: {e}")

            if not dry_run and result['deleted_count'] > 0:
                mail.expunge()
                print(f"[CLEANUP] Deleted {result['deleted_count']} campaign emails from {email}")

        mail.logout()

    except Exception as e:
        result['error'] = str(e)

    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Verify BCC cleanup is working correctly'
    )
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed information')
    parser.add_argument('--json', '-j', action='store_true',
                       help='Output as JSON')
    parser.add_argument('--cleanup', '-c', metavar='ACCOUNT',
                       help='Clean campaign emails from account (manpowerdristor/lucian)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Dry run for cleanup (count only, no delete)')
    args = parser.parse_args()

    if args.cleanup:
        result = cleanup_campaign_emails(args.cleanup, dry_run=args.dry_run)
        if result.get('error'):
            print(f"ERROR: {result['error']}")
            sys.exit(1)

        if args.dry_run:
            print(f"DRY RUN: Would delete {result['found_count']} campaign emails from {result['email']}")
        else:
            print(f"CLEANUP: Deleted {result['deleted_count']} campaign emails from {result['email']}")
        sys.exit(0)

    success = verify(verbose=args.verbose, json_output=args.json)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
