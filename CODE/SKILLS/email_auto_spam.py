#!/usr/bin/env python3
"""
Unified Email Auto-Spam - Learns from spam folders, applies to inbox.
Supports: Yahoo, Gmail

Usage:
    python3 email_auto_spam.py                    # All accounts
    python3 email_auto_spam.py --account yahoo    # Yahoo only
    python3 email_auto_spam.py --account gmail    # Gmail only
    python3 email_auto_spam.py --dry-run          # Preview only
"""

import imaplib
import email
from email.header import decode_header
import os
import json
from dotenv import load_dotenv

load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

PREFS_FILE = '/opt/ACTIVE/INFRA/SKILLS/data/email_preferences.json'

ACCOUNTS = {
    'yahoo': {
        'email': os.getenv('YAHOO_APAMINERALA_EMAIL'),
        'password': os.getenv('YAHOO_APAMINERALA_APP_PASSWORD'),
        'server': 'imap.mail.yahoo.com',
        'spam_folder': 'Bulk',
    },
    'gmail': {
        'email': os.getenv('GMAIL_EMAIL', 'manpowerdristor@gmail.com'),
        'password': os.getenv('GMAIL_APP_PASSWORD'),
        'server': 'imap.gmail.com',
        'spam_folder': '[Gmail]/Spam',
    },
}


def load_prefs():
    try:
        with open(PREFS_FILE) as f:
            return json.load(f)
    except:
        return {"always_keep": {}, "always_delete": {"senders": [], "domains": [], "keywords_subject": []}}


def save_prefs(prefs):
    os.makedirs(os.path.dirname(PREFS_FILE), exist_ok=True)
    with open(PREFS_FILE, 'w') as f:
        json.dump(prefs, f, indent=2)


def dec(h):
    if not h: return ""
    try:
        parts = decode_header(h)
        return ' '.join(p.decode(c or 'utf-8', errors='replace') if isinstance(p,bytes) else str(p) for p,c in parts)
    except:
        return str(h)


def should_delete(fr, subj, prefs):
    fr = fr.lower()
    subj = subj.lower()

    # Check keep first
    for d in prefs.get('always_keep', {}).get('domains', []):
        if d in fr: return False
    for s in prefs.get('always_keep', {}).get('senders', []):
        if s in fr: return False
    for k in prefs.get('always_keep', {}).get('keywords_subject', []):
        if k in subj: return False

    # Check delete
    for d in prefs.get('always_delete', {}).get('domains', []):
        if d in fr: return True
    for s in prefs.get('always_delete', {}).get('senders', []):
        if s in fr: return True
    for k in prefs.get('always_delete', {}).get('keywords_subject', []):
        if k in subj: return True

    return False


def process_account(name, config, prefs, dry_run=False):
    if not config['password']:
        print(f"  Skip {name}: no password")
        return 0

    print(f"\n=== {name.upper()}: {config['email']} ===")

    try:
        imap = imaplib.IMAP4_SSL(config['server'], 993)
        imap.login(config['email'], config['password'])
    except Exception as e:
        print(f"  Login failed: {e}")
        return 0

    # Learn from spam (last 30)
    print("  Learning from spam...")
    new_patterns = 0
    try:
        imap.select(config['spam_folder'])
        _, msgs = imap.search(None, 'ALL')
        ids = msgs[0].split()[-30:] if msgs[0] else []

        existing_d = set(d.lower() for d in prefs['always_delete'].get('domains', []))
        existing_s = set(s.lower() for s in prefs['always_delete'].get('senders', []))

        for mid in ids:
            try:
                _, d = imap.fetch(mid, '(RFC822.HEADER)')
                m = email.message_from_bytes(d[0][1])
                fr = dec(m.get('From', '')).lower()

                if '@' in fr:
                    domain = fr.split('@')[-1].split('>')[0].strip()
                    if domain and domain not in existing_d and len(domain) > 4:
                        prefs['always_delete'].setdefault('domains', []).append(domain)
                        existing_d.add(domain)
                        new_patterns += 1
            except:
                pass
        print(f"  Learned {new_patterns} new patterns")
    except Exception as e:
        print(f"  Spam folder error: {e}")

    # Apply to inbox
    print("  Applying to inbox...")
    moved = 0
    try:
        imap.select('INBOX')
        _, msgs = imap.search(None, 'ALL')
        ids = msgs[0].split() if msgs[0] else []

        for mid in ids:
            try:
                _, d = imap.fetch(mid, '(RFC822.HEADER)')
                m = email.message_from_bytes(d[0][1])
                fr = dec(m.get('From', ''))
                subj = dec(m.get('Subject', ''))

                if should_delete(fr, subj, prefs):
                    if not dry_run:
                        imap.copy(mid, config['spam_folder'])
                        imap.store(mid, '+FLAGS', '\\Deleted')
                    moved += 1
                    print(f"    {'[DRY]' if dry_run else 'SPAM'}: {fr[:35]}")
            except:
                pass

        if not dry_run and moved:
            imap.expunge()
    except Exception as e:
        print(f"  Inbox error: {e}")

    imap.logout()
    print(f"  Moved {moved} to spam")
    return moved


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--account', choices=['yahoo', 'gmail', 'all'], default='all')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    prefs = load_prefs()
    total = 0

    accounts = [args.account] if args.account != 'all' else ['yahoo', 'gmail']

    for acc in accounts:
        if acc in ACCOUNTS:
            total += process_account(acc, ACCOUNTS[acc], prefs, args.dry_run)

    save_prefs(prefs)
    print(f"\n=== DONE: {total} total emails moved ===")


if __name__ == '__main__':
    main()
