#!/usr/bin/env python3
"""
Yahoo Spam Filter - Learned from User Preferences

Applies user's keep/delete preferences automatically.

Usage:
    python3 yahoo_spam_learned.py                # Preview actions
    python3 yahoo_spam_learned.py --apply        # Apply deletions
    python3 yahoo_spam_learned.py --learn        # Interactive learning mode
"""

import imaplib
import email
from email.header import decode_header
import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

YAHOO_EMAIL = os.getenv('YAHOO_APAMINERALA_EMAIL', 'apaminerala@yahoo.com')
YAHOO_PASSWORD = os.getenv('YAHOO_APAMINERALA_APP_PASSWORD', '')
PREFS_FILE = '/opt/ACTIVE/INFRA/SKILLS/data/email_preferences.json'


def load_preferences():
    """Load learned preferences."""
    try:
        with open(PREFS_FILE) as f:
            return json.load(f)
    except:
        return {"always_keep": {}, "always_delete": {}}


def save_preferences(prefs):
    """Save updated preferences."""
    prefs['updated'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    with open(PREFS_FILE, 'w') as f:
        json.dump(prefs, f, indent=2)


def decode_hdr(h):
    if not h: return ""
    parts = decode_header(h)
    r = []
    for p, c in parts:
        if isinstance(p, bytes):
            r.append(p.decode(c or 'utf-8', errors='replace'))
        else:
            r.append(str(p))
    return ' '.join(r)


def classify_email(sender: str, subject: str, prefs: dict) -> tuple:
    """
    Classify email based on learned preferences.
    Returns: (action, reason) where action is 'keep', 'delete', or 'unknown'
    """
    sender_lower = sender.lower()
    subject_lower = subject.lower()

    keep_rules = prefs.get('always_keep', {})
    delete_rules = prefs.get('always_delete', {})

    # Check KEEP rules first (government, police, etc)
    for domain in keep_rules.get('domains', []):
        if domain in sender_lower:
            return 'keep', f'domain:{domain}'

    for kw in keep_rules.get('senders', []):
        if kw in sender_lower:
            return 'keep', f'sender:{kw}'

    for kw in keep_rules.get('keywords_subject', []):
        if kw in subject_lower:
            return 'keep', f'subject:{kw}'

    # Check DELETE rules
    for domain in delete_rules.get('domains', []):
        if domain in sender_lower:
            return 'delete', f'domain:{domain}'

    for kw in delete_rules.get('senders', []):
        if kw in sender_lower:
            return 'delete', f'sender:{kw}'

    for kw in delete_rules.get('keywords_subject', []):
        if kw in subject_lower:
            return 'delete', f'subject:{kw}'

    return 'unknown', 'no_match'


def fetch_and_classify(days: int = 7, limit: int = 50):
    """Fetch emails and classify them."""
    if not YAHOO_PASSWORD:
        print("ERROR: No Yahoo password")
        return []

    prefs = load_preferences()
    results = []

    try:
        imap = imaplib.IMAP4_SSL('imap.mail.yahoo.com', 993)
        imap.login(YAHOO_EMAIL, YAHOO_PASSWORD)
        imap.select('INBOX')

        since = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
        _, messages = imap.search(None, f'(SINCE {since})')
        msg_ids = messages[0].split()[-limit:]

        for msg_id in msg_ids:
            _, data = imap.fetch(msg_id, '(RFC822.HEADER)')
            msg = email.message_from_bytes(data[0][1])

            sender = decode_hdr(msg.get('From', ''))
            subject = decode_hdr(msg.get('Subject', ''))

            action, reason = classify_email(sender, subject, prefs)

            results.append({
                'uid': msg_id,
                'sender': sender,
                'subject': subject,
                'action': action,
                'reason': reason
            })

        imap.logout()
    except Exception as e:
        print(f"Error: {e}")

    return results


def apply_deletions(results):
    """Delete emails marked for deletion."""
    to_delete = [r for r in results if r['action'] == 'delete']

    if not to_delete:
        print("Nothing to delete")
        return

    try:
        imap = imaplib.IMAP4_SSL('imap.mail.yahoo.com', 993)
        imap.login(YAHOO_EMAIL, YAHOO_PASSWORD)
        imap.select('INBOX')

        deleted = 0
        for r in to_delete:
            try:
                imap.copy(r['uid'], 'Trash')
                imap.store(r['uid'], '+FLAGS', '\\Deleted')
                deleted += 1
                print(f"DEL: {r['subject'][:40]}")
            except:
                pass

        imap.expunge()
        imap.logout()
        print(f"\nDeleted {deleted}/{len(to_delete)}")
    except Exception as e:
        print(f"Error: {e}")


def interactive_learn():
    """Interactive learning mode."""
    prefs = load_preferences()
    results = fetch_and_classify(days=14, limit=30)

    unknown = [r for r in results if r['action'] == 'unknown']

    if not unknown:
        print("No unknown emails to learn from")
        return

    print(f"\n{len(unknown)} emails need classification:\n")

    for i, r in enumerate(unknown, 1):
        sender_short = r['sender'].split('<')[0].strip()[:30]
        subj_short = r['subject'][:40]
        print(f"{i}. {sender_short}")
        print(f"   {subj_short}")

        choice = input("   [k]eep / [d]elete / [s]kip? ").lower()

        if choice == 'k':
            # Add sender to keep list
            sender_kw = sender_short.lower().split()[0] if sender_short else ""
            if sender_kw and sender_kw not in prefs['always_keep'].get('senders', []):
                prefs['always_keep'].setdefault('senders', []).append(sender_kw)
                print(f"   Added '{sender_kw}' to keep list")
        elif choice == 'd':
            # Add sender to delete list
            sender_kw = sender_short.lower().split()[0] if sender_short else ""
            if sender_kw and sender_kw not in prefs['always_delete'].get('senders', []):
                prefs['always_delete'].setdefault('senders', []).append(sender_kw)
                print(f"   Added '{sender_kw}' to delete list")
        print()

    save_preferences(prefs)
    print("Preferences saved!")


def main():
    parser = argparse.ArgumentParser(description='Yahoo Spam Filter (Learned)')
    parser.add_argument('--apply', action='store_true', help='Apply deletions')
    parser.add_argument('--learn', action='store_true', help='Interactive learning')
    parser.add_argument('--days', type=int, default=7, help='Days to check')
    args = parser.parse_args()

    if args.learn:
        interactive_learn()
        return

    print(f"=== Yahoo Spam Filter: {YAHOO_EMAIL} ===\n")

    results = fetch_and_classify(days=args.days)

    keep = [r for r in results if r['action'] == 'keep']
    delete = [r for r in results if r['action'] == 'delete']
    unknown = [r for r in results if r['action'] == 'unknown']

    print(f"KEEP ({len(keep)}):")
    for r in keep[:10]:
        print(f"  + {r['subject'][:45]} [{r['reason']}]")

    print(f"\nDELETE ({len(delete)}):")
    for r in delete[:10]:
        print(f"  - {r['subject'][:45]} [{r['reason']}]")

    print(f"\nUNKNOWN ({len(unknown)}):")
    for r in unknown[:10]:
        print(f"  ? {r['subject'][:45]}")

    print(f"\nSummary: {len(keep)} keep, {len(delete)} delete, {len(unknown)} unknown")

    if args.apply:
        apply_deletions(results)


if __name__ == '__main__':
    main()
