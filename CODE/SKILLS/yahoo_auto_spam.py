#!/usr/bin/env python3
"""
Yahoo Auto-Spam Learner - Learns from your Spam folder, applies instantly.

Behavior:
1. Scans your Bulk Mail (spam) folder
2. Extracts all sender patterns
3. Adds them to delete rules
4. Scans inbox and moves matching emails to spam
5. Runs continuously

Usage:
    python3 yahoo_auto_spam.py              # Run once
    python3 yahoo_auto_spam.py --watch      # Run continuously (every 5 min)
    python3 yahoo_auto_spam.py --learn-only # Just learn from spam folder
"""

import imaplib
import email
from email.header import decode_header
import os
import sys
import json
import time
import argparse
from datetime import datetime
from dotenv import load_dotenv

load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

YAHOO_EMAIL = os.getenv('YAHOO_APAMINERALA_EMAIL', 'apaminerala@yahoo.com')
YAHOO_PASSWORD = os.getenv('YAHOO_APAMINERALA_APP_PASSWORD', '')
PREFS_FILE = '/opt/ACTIVE/INFRA/SKILLS/data/email_preferences.json'
SPAM_FOLDER = 'Bulk'


def load_prefs():
    try:
        with open(PREFS_FILE) as f:
            return json.load(f)
    except:
        return {"always_keep": {}, "always_delete": {"senders": [], "domains": [], "keywords_subject": []}}


def save_prefs(prefs):
    prefs['updated'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    os.makedirs(os.path.dirname(PREFS_FILE), exist_ok=True)
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


def extract_sender_pattern(from_addr):
    """Extract spam pattern from sender."""
    from_lower = from_addr.lower()

    # Extract email domain
    if '<' in from_lower and '>' in from_lower:
        email_part = from_lower.split('<')[1].split('>')[0]
        if '@' in email_part:
            domain = email_part.split('@')[1]
            return ('domain', domain)

    # Extract sender name
    name_part = from_lower.split('<')[0].strip().strip('"').strip()
    if name_part and len(name_part) > 2:
        # Get first 2-3 words
        words = name_part.split()[:2]
        pattern = ' '.join(words)
        if len(pattern) > 3:
            return ('sender', pattern)

    return None


def learn_from_spam_folder(imap, limit=100):
    """Scan spam folder and extract patterns."""
    patterns = {'senders': set(), 'domains': set()}

    try:
        imap.select(SPAM_FOLDER)
        _, messages = imap.search(None, 'ALL')

        if not messages[0]:
            return patterns

        msg_ids = messages[0].split()[-limit:]

        for msg_id in msg_ids:
            try:
                _, data = imap.fetch(msg_id, '(RFC822.HEADER)')
                msg = email.message_from_bytes(data[0][1])
                from_addr = decode_hdr(msg.get('From', ''))

                result = extract_sender_pattern(from_addr)
                if result:
                    ptype, pattern = result
                    if ptype == 'domain':
                        patterns['domains'].add(pattern)
                    else:
                        patterns['senders'].add(pattern)
            except:
                continue

    except Exception as e:
        print(f"Error reading spam folder: {e}")

    return patterns


def update_rules_from_spam(patterns, prefs):
    """Add learned patterns to delete rules."""
    added = []

    existing_domains = set(d.lower() for d in prefs['always_delete'].get('domains', []))
    existing_senders = set(s.lower() for s in prefs['always_delete'].get('senders', []))

    # Don't add whitelisted
    keep_domains = set(d.lower() for d in prefs['always_keep'].get('domains', []))
    keep_senders = set(s.lower() for s in prefs['always_keep'].get('senders', []))

    for domain in patterns['domains']:
        if domain not in existing_domains and domain not in keep_domains:
            prefs['always_delete'].setdefault('domains', []).append(domain)
            added.append(f"domain:{domain}")

    for sender in patterns['senders']:
        if sender not in existing_senders and sender not in keep_senders:
            prefs['always_delete'].setdefault('senders', []).append(sender)
            added.append(f"sender:{sender}")

    return added


def should_delete(from_addr, subject, prefs):
    """Check if email matches delete rules."""
    from_lower = from_addr.lower()
    subj_lower = subject.lower()

    # Check keep rules first
    for domain in prefs['always_keep'].get('domains', []):
        if domain in from_lower:
            return False, "keep:domain"

    for sender in prefs['always_keep'].get('senders', []):
        if sender in from_lower:
            return False, "keep:sender"

    for kw in prefs['always_keep'].get('keywords_subject', []):
        if kw in subj_lower:
            return False, "keep:keyword"

    # Check delete rules
    for domain in prefs['always_delete'].get('domains', []):
        if domain in from_lower:
            return True, f"domain:{domain}"

    for sender in prefs['always_delete'].get('senders', []):
        if sender in from_lower:
            return True, f"sender:{sender}"

    for kw in prefs['always_delete'].get('keywords_subject', []):
        if kw in subj_lower:
            return True, f"keyword:{kw}"

    return False, None


def apply_to_inbox(imap, prefs, dry_run=False):
    """Scan inbox and move spam to Bulk Mail."""
    moved = []

    try:
        imap.select('INBOX')
        _, messages = imap.search(None, 'ALL')

        if not messages[0]:
            return moved

        msg_ids = messages[0].split()

        for msg_id in msg_ids:
            try:
                _, data = imap.fetch(msg_id, '(RFC822.HEADER)')
                msg = email.message_from_bytes(data[0][1])

                from_addr = decode_hdr(msg.get('From', ''))
                subject = decode_hdr(msg.get('Subject', ''))

                delete, reason = should_delete(from_addr, subject, prefs)

                if delete:
                    if not dry_run:
                        imap.copy(msg_id, SPAM_FOLDER)
                        imap.store(msg_id, '+FLAGS', '\\Deleted')
                    moved.append({
                        'from': from_addr[:40],
                        'subject': subject[:40],
                        'reason': reason
                    })
            except:
                continue

        if not dry_run and moved:
            imap.expunge()

    except Exception as e:
        print(f"Error processing inbox: {e}")

    return moved


def run_once(learn_only=False, dry_run=False):
    """Run one cycle: learn from spam, apply to inbox."""
    if not YAHOO_PASSWORD:
        print("ERROR: No Yahoo password")
        return

    prefs = load_prefs()

    try:
        imap = imaplib.IMAP4_SSL('imap.mail.yahoo.com', 993)
        imap.login(YAHOO_EMAIL, YAHOO_PASSWORD)

        # Learn from spam folder
        print("Learning from spam folder...")
        patterns = learn_from_spam_folder(imap, limit=200)
        added = update_rules_from_spam(patterns, prefs)

        if added:
            print(f"Learned {len(added)} new patterns:")
            for p in added[:10]:
                print(f"  + {p}")
            if len(added) > 10:
                print(f"  ... and {len(added)-10} more")
            save_prefs(prefs)
        else:
            print("No new patterns")

        if learn_only:
            imap.logout()
            return

        # Apply to inbox
        print("\nApplying rules to inbox...")
        moved = apply_to_inbox(imap, prefs, dry_run=dry_run)

        if moved:
            print(f"{'Would move' if dry_run else 'Moved'} {len(moved)} emails to spam:")
            for m in moved[:10]:
                print(f"  - {m['subject'][:35]} [{m['reason']}]")
            if len(moved) > 10:
                print(f"  ... and {len(moved)-10} more")
        else:
            print("Inbox clean")

        imap.logout()

    except Exception as e:
        print(f"Error: {e}")


def watch_mode(interval=300):
    """Run continuously."""
    print(f"=== Yahoo Auto-Spam Learner ===")
    print(f"Account: {YAHOO_EMAIL}")
    print(f"Interval: {interval}s")
    print("Press Ctrl+C to stop\n")

    while True:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Running...")
        run_once()
        print(f"Sleeping {interval}s...\n")
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description='Yahoo Auto-Spam Learner')
    parser.add_argument('--watch', action='store_true', help='Run continuously')
    parser.add_argument('--interval', type=int, default=300, help='Watch interval (seconds)')
    parser.add_argument('--learn-only', action='store_true', help='Only learn, dont apply')
    parser.add_argument('--dry-run', action='store_true', help='Dont actually move emails')
    args = parser.parse_args()

    if args.watch:
        watch_mode(args.interval)
    else:
        run_once(learn_only=args.learn_only, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
