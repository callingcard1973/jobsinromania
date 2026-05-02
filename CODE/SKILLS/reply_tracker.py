#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
Reply Tracker — check IMAP accounts for campaign replies, log to PostgreSQL.

Usage:
    python3 reply_tracker.py              # Check all accounts, log replies
    python3 reply_tracker.py --stats      # Show reply stats
    python3 reply_tracker.py --recent 7   # Replies in last N days

Cron: 0 */4 * * * /opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/INFRA/SKILLS/reply_tracker.py >> /opt/ACTIVE/INFRA/LOGS/campaigns/reply_tracker.log 2>&1
"""
import imaplib
import email
import os
import sys
import argparse
import re
from datetime import datetime, timedelta
from email.header import decode_header
from dotenv import load_dotenv

import psycopg2

load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

DB = {'host': 'localhost', 'dbname': 'email_sender', 'user': 'tudor', 'password': 'tudor'}

# Reply-to accounts to check
ACCOUNTS = [
    {
        'email': 'fruitnature4@gmail.com',
        'password_env': 'GMAIL_SEARCH_PASSWORD',
        'server': 'imap.gmail.com',
        'campaigns': ['NORWAY', 'DENMARK', 'ROMANIA'],
    },
    {
        'email': 'lucian.bpandp@gmail.com',
        'password_env': 'GMAIL_LUCIAN_APP_PASSWORD',
        'server': 'imap.gmail.com',
        'campaigns': ['LUCIAN_HORECA'],
    },
    {
        'email': 'apaminerala@yahoo.com',
        'password_env': 'YAHOO_APAMINERALA_APP_PASSWORD',
        'server': 'imap.mail.yahoo.com',
        'campaigns': ['LICHIDATORI'],
    },
    {
        'email': 'expatsinromania@gmail.com',
        'password_env': 'GMAIL_EXPATS_PASSWORD',
        'server': 'imap.gmail.com',
        'campaigns': ['NECALIFICATI'],
    },
]


def create_table():
    conn = psycopg2.connect(**DB)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS campaign_replies (
            id SERIAL PRIMARY KEY,
            from_email VARCHAR(255) NOT NULL,
            to_account VARCHAR(255),
            subject TEXT,
            reply_date TIMESTAMP,
            campaign VARCHAR(100),
            message_id VARCHAR(500),
            snippet TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_replies_from ON campaign_replies (LOWER(from_email));
        CREATE INDEX IF NOT EXISTS idx_replies_date ON campaign_replies (reply_date);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_replies_msgid ON campaign_replies (message_id);
    """)
    conn.close()


def decode_str(s):
    if not s:
        return ''
    parts = decode_header(s)
    result = []
    for data, charset in parts:
        if isinstance(data, bytes):
            result.append(data.decode(charset or 'utf-8', errors='replace'))
        else:
            result.append(data)
    return ' '.join(result)


# Domains/patterns that are newsletters or automated, not real replies
NOISE_DOMAINS = {
    'facebookmail.com', 'mail.adobe.com', 'airbnb.com', 'eg.expedia.com',
    'mail.apollo.io', 'mail.replit.com', 'timeleft.com', 'mail.airtable.com',
    'earnapp.com', 'emergentagent.com', 'aioseo.com', 'base44.com',
    '10web.io', 'motorola-mail.com', 'hello.docsbot.ai', 'mail.perplexity.ai',
    'makeuseof.com', 'howtogeek.com',
}
NOISE_PREFIXES = [
    'noreply', 'no-reply', 'mailer-daemon', 'postmaster',
    'newsletter@', 'notifications@', 'updates@', 'security@',
    'friendsuggestion@', 'friendupdates@', 'friends@',
]


def is_noise(from_addr):
    """Return True if this sender is newsletter/automated noise."""
    domain = from_addr.split('@')[-1] if '@' in from_addr else ''
    if domain in NOISE_DOMAINS:
        return True
    for prefix in NOISE_PREFIXES:
        if from_addr.startswith(prefix):
            return True
    return False


def extract_email_addr(s):
    if not s:
        return ''
    m = re.search(r'[\w.+-]+@[\w.-]+', s)
    return m.group(0).lower() if m else s.lower()


def get_body_snippet(msg, max_len=200):
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == 'text/plain':
                try:
                    body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                    return body[:max_len].strip()
                except Exception:
                    pass
        return ''
    try:
        body = msg.get_payload(decode=True).decode('utf-8', errors='replace')
        return body[:max_len].strip()
    except Exception:
        return ''


def check_account(acct, conn, days=7):
    pw = os.environ.get(acct['password_env'], '').strip().strip('"').replace(' ', '')
    if not pw or pw == 'NEEDS_APP_PASSWORD':
        print(f"  SKIP {acct['email']}: no password")
        return 0

    try:
        imap = imaplib.IMAP4_SSL(acct['server'], timeout=30)
        imap.login(acct['email'], pw)
        imap.select('INBOX', readonly=True)
    except Exception as e:
        print(f"  ERROR {acct['email']}: {str(e)[:60]}")
        return 0

    since = (datetime.now() - timedelta(days=days)).strftime('%d-%b-%Y')
    _, data = imap.search(None, f'(SINCE {since})')
    msg_ids = data[0].split()

    cur = conn.cursor()
    new_replies = 0

    for mid in msg_ids:
        _, msg_data = imap.fetch(mid, '(RFC822.HEADER BODY.PEEK[1]<0.500>)')
        if not msg_data or not msg_data[0]:
            continue

        # Parse header
        raw = msg_data[0][1] if isinstance(msg_data[0], tuple) else b''
        try:
            msg = email.message_from_bytes(raw)
        except Exception:
            continue

        from_addr = extract_email_addr(msg.get('From', ''))
        subject = decode_str(msg.get('Subject', ''))
        message_id = msg.get('Message-ID', '')
        date_str = msg.get('Date', '')

        # Skip our own sent messages
        if from_addr in {a['email'].lower() for a in ACCOUNTS}:
            continue
        # Skip automated and newsletter noise
        if is_noise(from_addr):
            continue

        # Parse date
        try:
            from email.utils import parsedate_to_datetime
            reply_date = parsedate_to_datetime(date_str)
        except Exception:
            reply_date = datetime.now()

        # Guess campaign from subject or account
        campaign = acct['campaigns'][0] if acct['campaigns'] else 'UNKNOWN'

        # Get body snippet
        snippet = ''
        if len(msg_data) > 2 and isinstance(msg_data[2], tuple):
            try:
                snippet = msg_data[2][1].decode('utf-8', errors='replace')[:200]
            except Exception:
                pass

        try:
            cur.execute("""
                INSERT INTO campaign_replies (from_email, to_account, subject, reply_date, campaign, message_id, snippet)
                VALUES (LOWER(%s), %s, %s, %s, %s, %s, %s)
                ON CONFLICT (message_id) DO NOTHING
            """, (from_addr, acct['email'], subject, reply_date, campaign, message_id or f'{from_addr}_{reply_date}', snippet))
            if cur.rowcount > 0:
                new_replies += 1
        except Exception:
            conn.rollback()

    conn.commit()
    imap.logout()
    return new_replies


def show_stats(days=30):
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    cur.execute("SELECT COUNT(*) FROM campaign_replies WHERE reply_date >= %s", (cutoff,))
    total = cur.fetchone()[0]

    cur.execute("""
        SELECT campaign, COUNT(*), COUNT(DISTINCT from_email)
        FROM campaign_replies WHERE reply_date >= %s
        GROUP BY campaign ORDER BY count DESC
    """, (cutoff,))
    by_campaign = cur.fetchall()

    cur.execute("""
        SELECT DATE(reply_date), COUNT(*)
        FROM campaign_replies WHERE reply_date >= %s
        GROUP BY DATE(reply_date) ORDER BY date DESC LIMIT 14
    """, (cutoff,))
    by_day = cur.fetchall()

    print(f"\nReply Stats (last {days} days): {total} total replies")
    print("\nBy campaign:")
    for c, n, u in by_campaign:
        print(f"  {c}: {n} replies ({u} unique)")
    print("\nBy day (last 14):")
    for d, n in by_day:
        print(f"  {d}: {n}")

    # Cross-reference with global_sends to get reply rate
    cur.execute("""
        SELECT gs.campaign, COUNT(DISTINCT gs.email) as sent, COUNT(DISTINCT cr.from_email) as replied
        FROM global_sends gs
        LEFT JOIN campaign_replies cr ON LOWER(cr.from_email) = LOWER(gs.email) AND cr.campaign = gs.campaign
        WHERE gs.sent_date >= %s
        GROUP BY gs.campaign ORDER BY sent DESC
    """, (cutoff,))
    rates = cur.fetchall()
    if rates:
        print("\nReply rates:")
        for c, s, r in rates:
            pct = (r / s * 100) if s > 0 else 0
            print(f"  {c}: {r}/{s} ({pct:.1f}%)")

    conn.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--stats', action='store_true')
    p.add_argument('--recent', type=int, default=7)
    args = p.parse_args()

    create_table()

    if args.stats:
        show_stats(days=args.recent)
        return

    print(f"[{datetime.now():%Y-%m-%d %H:%M}] Checking replies...")
    conn = psycopg2.connect(**DB)
    total = 0
    for acct in ACCOUNTS:
        n = check_account(acct, conn, days=args.recent)
        print(f"  {acct['email']}: {n} new replies")
        total += n
    conn.close()
    print(f"Total new replies: {total}")


if __name__ == '__main__':
    main()
