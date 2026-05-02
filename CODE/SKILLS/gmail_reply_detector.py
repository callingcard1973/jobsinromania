#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
Gmail Reply Detector - Monitors all Gmail sender inboxes for campaign replies.

Connects to each Gmail IMAP inbox, finds UNSEEN non-bounce messages,
extracts lead info, saves to leads.json, and marks as SEEN.

Usage:
    python3 gmail_reply_detector.py              # Check all accounts
    python3 gmail_reply_detector.py --status     # Show lead count + per-account stats
    python3 gmail_reply_detector.py --recent     # Show last 10 leads

Deploy to: /opt/ACTIVE/INFRA/SKILLS/gmail_reply_detector.py
Leads:     /opt/ACTIVE/EMAIL/CAMPAIGNS/leads.json
Logs:      /opt/ACTIVE/INFRA/LOGS/gmail_reply_detector.log

[AI: Claude Code]
"""

import os
import sys
import json
import imaplib
import email
import email.header
import email.utils
import argparse
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

LEADS_FILE = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/leads.json')
LOG_FILE = Path('/opt/ACTIVE/INFRA/LOGS/gmail_reply_detector.log')

# Ensure directories exist
LEADS_FILE.parent.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger('gmail_reply_detector')

# All Gmail sender accounts with their .env password keys
GMAIL_ACCOUNTS = [
    {
        'email': 'manpowerdristor@gmail.com',
        'password_env': 'GMAIL_APP_PASSWORD',
    },
    {
        'email': 'elena.manpower.dristor@gmail.com',
        'password_env': 'GMAIL_ELENA_PASSWORD',
    },
    {
        'email': 'expatsinromania@gmail.com',
        'password_env': 'GMAIL_EXPATS_PASSWORD',
    },
    {
        'email': 'pamintstrabun@gmail.com',
        'password_env': 'GMAIL_PAMINTSTRABUN_PASSWORD',
    },
    {
        'email': 'casafaurbucuresti@gmail.com',
        'password_env': 'GMAIL_CASAFAUR_PASSWORD',
    },
    {
        'email': 'fructexportromania@gmail.com',
        'password_env': 'GMAIL_FRUCTEXPORT_PASSWORD',
    },
    {
        'email': 'manpowersearchromania@gmail.com',
        'password_env': 'GMAIL_MANPOWERSEARCH_PASSWORD',
    },
]

IMAP_HOST = 'imap.gmail.com'
IMAP_PORT = 993
IMAP_TIMEOUT = 30


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def decode_header_value(raw):
    """Decode an RFC 2047 encoded email header into a plain string."""
    if not raw:
        return ''
    parts = email.header.decode_header(raw)
    decoded = []
    for data, charset in parts:
        if isinstance(data, bytes):
            decoded.append(data.decode(charset or 'utf-8', errors='replace'))
        else:
            decoded.append(data)
    return ' '.join(decoded).strip()


def extract_body_preview(msg, max_chars=200):
    """Extract first max_chars of the plain-text body from an email.Message."""
    body = ''
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            disp = str(part.get('Content-Disposition', ''))
            if ct == 'text/plain' and 'attachment' not in disp:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or 'utf-8'
                    body = payload.decode(charset, errors='replace')
                    break
        # Fallback: try text/html if no plain text
        if not body:
            for part in msg.walk():
                ct = part.get_content_type()
                disp = str(part.get('Content-Disposition', ''))
                if ct == 'text/html' and 'attachment' not in disp:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        body = payload.decode(charset, errors='replace')
                        # Crude HTML strip
                        import re
                        body = re.sub(r'<[^>]+>', ' ', body)
                        body = re.sub(r'\s+', ' ', body)
                        break
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or 'utf-8'
            body = payload.decode(charset, errors='replace')
            if msg.get_content_type() == 'text/html':
                import re
                body = re.sub(r'<[^>]+>', ' ', body)
                body = re.sub(r'\s+', ' ', body)

    return body.strip()[:max_chars] if body else ''


def load_leads():
    """Load existing leads from JSON file."""
    if LEADS_FILE.exists() and LEADS_FILE.stat().st_size > 0:
        try:
            with open(LEADS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            log.warning('Could not parse leads.json, starting fresh')
    return []


def save_leads(leads):
    """Save leads list to JSON file."""
    with open(LEADS_FILE, 'w', encoding='utf-8') as f:
        json.dump(leads, f, indent=2, ensure_ascii=False, default=str)


def make_dedup_key(from_email, date_str):
    """Create deduplication key from sender email + date."""
    return f"{from_email.lower().strip()}|{date_str.strip()}"


def build_dedup_set(leads):
    """Build set of existing dedup keys from leads list."""
    keys = set()
    for lead in leads:
        key = make_dedup_key(lead.get('from_email', ''), lead.get('date', ''))
        keys.add(key)
    return keys


# ---------------------------------------------------------------------------
# IMAP scanning
# ---------------------------------------------------------------------------

def check_account(account):
    """
    Connect to one Gmail IMAP account, find UNSEEN non-bounce messages,
    extract lead data, mark as SEEN.

    Returns list of new lead dicts found.
    """
    addr = account['email']
    password = os.getenv(account['password_env'], '')

    if not password:
        log.warning(f'[{addr}] No password in env var {account["password_env"]}, skipping')
        return []

    new_leads = []
    conn = None

    try:
        log.info(f'[{addr}] Connecting to IMAP...')
        conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, timeout=IMAP_TIMEOUT)
        conn.login(addr, password)
        conn.select('INBOX')

        # Search for UNSEEN messages NOT from mailer-daemon
        # Gmail IMAP supports NOT FROM "mailer-daemon" in search
        status, data = conn.search(None, '(UNSEEN)')
        if status != 'OK' or not data[0]:
            log.info(f'[{addr}] No unseen messages')
            conn.close()
            conn.logout()
            return []

        msg_ids = data[0].split()
        log.info(f'[{addr}] Found {len(msg_ids)} unseen message(s)')

        for mid in msg_ids:
            try:
                # Fetch full message
                status, msg_data = conn.fetch(mid, '(RFC822)')
                if status != 'OK' or not msg_data[0]:
                    continue

                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)

                # Extract From
                from_raw = decode_header_value(msg.get('From', ''))
                # Parse out just the email address
                from_name, from_addr = email.utils.parseaddr(from_raw)
                from_addr = from_addr.lower().strip()

                # Skip bounces / mailer-daemon
                if not from_addr:
                    continue
                if 'mailer-daemon' in from_addr or 'postmaster' in from_addr:
                    log.debug(f'[{addr}] Skipping bounce from {from_addr}')
                    # Still mark as seen so we don't re-process
                    conn.store(mid, '+FLAGS', '\\Seen')
                    continue

                # Skip messages from our own sender accounts (auto-notifications, etc.)
                our_addresses = {a['email'].lower() for a in GMAIL_ACCOUNTS}
                if from_addr in our_addresses:
                    conn.store(mid, '+FLAGS', '\\Seen')
                    continue

                # Skip automated / no-reply senders
                skip_prefixes = ('no-reply@', 'noreply@', 'do-not-reply@', 'donotreply@')
                skip_domains = ('mailtrack.io', 'accounts.google.com', 'google.com',
                                'facebookmail.com', 'linkedin.com', 'newsletter.',
                                'notifications.', 'marketing.', 'promo.')
                if any(from_addr.startswith(p) for p in skip_prefixes):
                    conn.store(mid, '+FLAGS', '\\Seen')
                    continue
                from_domain = from_addr.split('@')[-1] if '@' in from_addr else ''
                if any(from_domain == d or from_domain.endswith('.' + d) for d in skip_domains):
                    conn.store(mid, '+FLAGS', '\\Seen')
                    continue

                # Extract fields
                subject = decode_header_value(msg.get('Subject', ''))
                date_raw = msg.get('Date', '')
                date_parsed = email.utils.parsedate_to_datetime(date_raw) if date_raw else None
                date_str = date_parsed.isoformat() if date_parsed else date_raw
                body_preview = extract_body_preview(msg, max_chars=200)

                lead = {
                    'from_email': from_addr,
                    'from_name': from_name or from_addr.split('@')[0],
                    'subject': subject,
                    'date': date_str,
                    'body_preview': body_preview,
                    'detected_by': addr,
                    'detected_at': datetime.now().isoformat(),
                }

                new_leads.append(lead)
                log.info(f'[{addr}] Reply from {from_addr}: {subject[:60]}')

                # Mark as SEEN so we don't re-detect
                conn.store(mid, '+FLAGS', '\\Seen')

            except Exception as e:
                log.error(f'[{addr}] Error processing message {mid}: {e}')
                continue

        conn.close()
        conn.logout()

    except imaplib.IMAP4.error as e:
        log.error(f'[{addr}] IMAP error: {e}')
        if conn:
            try:
                conn.logout()
            except Exception:
                pass
    except Exception as e:
        log.error(f'[{addr}] Connection error: {e}')
        if conn:
            try:
                conn.logout()
            except Exception:
                pass

    return new_leads


# ---------------------------------------------------------------------------
# Main actions
# ---------------------------------------------------------------------------

def check_all_accounts():
    """Check all Gmail accounts and save new leads."""
    log.info('=== Gmail Reply Detector - checking all accounts ===')

    leads = load_leads()
    dedup_keys = build_dedup_set(leads)
    total_new = 0

    for account in GMAIL_ACCOUNTS:
        try:
            new_leads = check_account(account)
            added = 0
            for lead in new_leads:
                key = make_dedup_key(lead['from_email'], lead['date'])
                if key not in dedup_keys:
                    leads.append(lead)
                    dedup_keys.add(key)
                    added += 1
                else:
                    log.debug(f'Duplicate skipped: {lead["from_email"]}')
            total_new += added
            if added:
                log.info(f'[{account["email"]}] Added {added} new lead(s)')
        except Exception as e:
            log.error(f'[{account["email"]}] Failed: {e}')
            continue

    if total_new > 0:
        save_leads(leads)
        log.info(f'Saved {total_new} new lead(s). Total leads: {len(leads)}')
    else:
        log.info(f'No new leads found. Total leads: {len(leads)}')

    return total_new


def show_status():
    """Print lead count and per-account breakdown."""
    leads = load_leads()
    total = len(leads)

    print(f'\n  Total leads: {total}')
    print(f'  Leads file:  {LEADS_FILE}')

    if not leads:
        print('  (no leads yet)\n')
        return

    # Per-account breakdown
    by_account = {}
    for lead in leads:
        acct = lead.get('detected_by', 'unknown')
        by_account[acct] = by_account.get(acct, 0) + 1

    print(f'\n  Per account:')
    for acct in sorted(by_account, key=by_account.get, reverse=True):
        print(f'    {acct:<45} {by_account[acct]:>4} leads')

    # Date range
    dates = [lead.get('date', '') for lead in leads if lead.get('date')]
    if dates:
        dates_sorted = sorted(dates)
        print(f'\n  First lead:  {dates_sorted[0][:19]}')
        print(f'  Latest lead: {dates_sorted[-1][:19]}')

    print()


def show_recent(count=10):
    """Print the last N leads."""
    leads = load_leads()

    if not leads:
        print('\n  No leads yet.\n')
        return

    # Sort by date descending
    leads_sorted = sorted(leads, key=lambda x: x.get('date', ''), reverse=True)
    showing = leads_sorted[:count]

    print(f'\n  Last {min(count, len(showing))} leads (of {len(leads)} total):\n')
    print(f'  {"Date":<20} {"From":<35} {"Subject":<50} {"Via"}')
    print(f'  {"-"*20} {"-"*35} {"-"*50} {"-"*30}')

    for lead in showing:
        date_short = lead.get('date', '')[:19]
        from_email = lead.get('from_email', '')[:34]
        subject = lead.get('subject', '')[:49]
        via = lead.get('detected_by', '')
        # Shorten the via field
        via_short = via.split('@')[0] if '@' in via else via
        print(f'  {date_short:<20} {from_email:<35} {subject:<50} {via_short}')

    if len(showing) > 0:
        print()
        latest = showing[0]
        print(f'  Latest body preview:')
        print(f'  {latest.get("body_preview", "(empty)")[:200]}')

    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Gmail Reply Detector - monitor campaign inboxes for replies'
    )
    parser.add_argument('--status', action='store_true',
                        help='Show lead count and per-account stats')
    parser.add_argument('--recent', action='store_true',
                        help='Show last 10 leads')
    parser.add_argument('--recent-count', type=int, default=10,
                        help='Number of recent leads to show (default: 10)')
    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.recent:
        show_recent(args.recent_count)
    else:
        check_all_accounts()


if __name__ == '__main__':
    main()
