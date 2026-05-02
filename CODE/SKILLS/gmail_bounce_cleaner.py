#!/usr/bin/env python3
"""
Bounce Cleaner Skill (Gmail + Brevo)
[AI: Claude Code]

Automatically cleans bounced emails from Gmail and Brevo:
- Scans Gmail INBOX for mailer-daemon bounce notifications
- Fetches hard bounces from Brevo API
- Extracts failed email addresses
- Adds them to DNC list
- Marks contacts as bounced in campaign database
- Deletes Gmail bounce notifications to reset counter

Usage:
    python3 gmail_bounce_cleaner.py                    # Clean all accounts
    python3 gmail_bounce_cleaner.py --gmail            # Clean only Gmail
    python3 gmail_bounce_cleaner.py --brevo            # Clean only Brevo
    python3 gmail_bounce_cleaner.py --account lucian   # Clean specific Gmail
    python3 gmail_bounce_cleaner.py --dry-run          # Show what would be done
    python3 gmail_bounce_cleaner.py --stats            # Show bounce statistics

Cron: 0 * * * * /usr/bin/python3 /opt/ACTIVE/INFRA/SKILLS/gmail_bounce_cleaner.py
"""

import sys
import os
import re
import imaplib
import email
import argparse
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

try:
    from dotenv import load_dotenv
    load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')
except:
    pass

try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Gmail accounts - correct env vars
GMAIL_ACCOUNTS = [
    {'email': 'lucian.bpandp@gmail.com', 'env_pass': 'GMAIL_LUCIAN_APP_PASSWORD', 'name': 'lucian'},
    {'email': 'manpowerdristor@gmail.com', 'env_pass': 'GMAIL_MANPOWERDRISTOR_APP_PASSWORD', 'name': 'manpowerdristor'},
    {'email': 'elena.manpower.dristor@gmail.com', 'env_pass': 'GMAIL_ELENA_PASSWORD', 'name': 'elena'},
    {'email': 'fruitnature4@gmail.com', 'env_pass': 'GMAIL_FRUITNATURE4_APP_PASSWORD', 'name': 'fruitnature'},
    {'email': 'cumparlegume@gmail.com', 'env_pass': 'GMAIL_CUMPARLEGUME_PASSWORD', 'name': 'cumparlegume'},
    {'email': 'casafaurbucuresti@gmail.com', 'env_pass': 'GMAIL_CASAFAUR_PASSWORD', 'name': 'casafaur'},
    {'email': 'vegetablesbucharest@gmail.com', 'env_pass': 'GMAIL_VEGETABLESBUCHAREST_PASSWORD', 'name': 'vegetables'},
    {'email': 'fructexportromania@gmail.com', 'env_pass': 'GMAIL_FRUCTEXPORT_PASSWORD', 'name': 'fructexport'},
    {'email': 'icralbucuresti@gmail.com', 'env_pass': 'GMAIL_ICRALBUCURESTI_PASSWORD', 'name': 'icral'},
    {'email': 'pamintstrabun@gmail.com', 'env_pass': 'GMAIL_PAMINTSTRABUN_PASSWORD', 'name': 'pamint'},
]

# Brevo accounts
BREVO_ACCOUNTS = [
    {'name': 'buildjobs', 'env_key': 'BREVO_BUILDJOBS_API_KEY'},
    {'name': 'factoryjobs', 'env_key': 'BREVO_FACTORYJOBS_API_KEY'},
    {'name': 'warehouseworkers', 'env_key': 'BREVO_WAREHOUSEWORKERS_API_KEY'},
    {'name': 'careworkers', 'env_key': 'BREVO_CAREWORKERS_API_KEY'},
    {'name': 'mivromania', 'env_key': 'BREVO_MIVROMANIA_API_KEY'},
    {'name': 'mivromania_online', 'env_key': 'BREVO_MIVROMANIA_ONLINE_API_KEY'},
    {'name': 'cifn', 'env_key': 'BREVO_CIFN_API_KEY'},
    {'name': 'interjob', 'env_key': 'BREVO_INTERJOB_API_KEY'},
    {'name': 'nepalezi', 'env_key': 'BREVO_NEPALEZI_API_KEY'},
    {'name': 'bppltd', 'env_key': 'BREVO_BPPLTD_API_KEY'},
]

# Patterns to extract bounced email from notification
BOUNCE_PATTERNS = [
    r"The email account that you tried to reach does not exist.*?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
    r"couldn't be delivered to ([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
    r"Delivery to the following recipient failed.*?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
    r"was rejected by the recipient.*?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
    r"Your message wasn't delivered to ([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
    r"<([a-zA-Z0-9._%+-]+@(?:yahoo|hotmail|outlook|aol)[a-zA-Z0-9.-]+)>",
]


def add_to_dnc(emails: list, reason: str = 'bounce_auto') -> int:
    """Add emails to DNC and mark contacts as bounced."""
    if not HAS_PSYCOPG2 or not emails:
        return 0

    added = 0

    # Try email_sender database first
    db_configs = [
        {'host': 'localhost', 'dbname': 'email_sender', 'user': 'tudor', 'password': 'tudor123'},
        {'host': 'localhost', 'dbname': 'interjob_master', 'user': 'tudor', 'password': 'scraper123'},
    ]

    for db_config in db_configs:
        try:
            conn = psycopg2.connect(**db_config)
            with conn.cursor() as cur:
                # Check if dnc_list table exists
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'dnc_list'
                    )
                """)
                has_dnc_list = cur.fetchone()[0]

                if has_dnc_list:
                    for email_addr in emails:
                        email_addr = email_addr.lower().strip()
                        cur.execute("""
                            INSERT INTO dnc_list (email, reason, added_at)
                            VALUES (%s, %s, NOW())
                            ON CONFLICT (email) DO NOTHING
                        """, (email_addr, reason))
                        if cur.rowcount > 0:
                            added += 1
                            logger.info(f"  Added to DNC: {email_addr}")

                    conn.commit()
                    conn.close()
                    logger.info(f"Added {added} emails to DNC ({db_config['dbname']})")
                    return added
                else:
                    conn.close()
        except Exception as e:
            logger.debug(f"DB {db_config['dbname']}: {e}")
            continue

    # Fallback: write to file-based DNC
    dnc_file = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/dnc_bounces.txt')
    try:
        with open(dnc_file, 'a') as f:
            for email_addr in emails:
                f.write(f"{email_addr.lower().strip()},{reason},{datetime.now().isoformat()}\n")
                added += 1
        logger.info(f"Added {added} emails to file DNC: {dnc_file}")
    except Exception as e:
        logger.error(f"File DNC error: {e}")

    return added


def extract_bounced_email(body: str) -> str:
    """Extract the bounced email address from bounce notification body."""
    for pattern in BOUNCE_PATTERNS:
        match = re.search(pattern, body, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).lower().strip()
    return None


def scan_gmail_bounces(account: dict, dry_run: bool = False) -> dict:
    """Scan Gmail account for bounce notifications."""
    email_addr = account['email']
    password = os.environ.get(account['env_pass'])

    if not password:
        return {'account': email_addr, 'error': f"no_password ({account['env_pass']})", 'bounces': []}

    result = {'account': email_addr, 'bounces': [], 'deleted': 0, 'added_to_dnc': 0}

    try:
        m = imaplib.IMAP4_SSL('imap.gmail.com', timeout=15)
        m.login(email_addr, password)
        m.select('INBOX')

        date_str = datetime.now().strftime('%d-%b-%Y')
        typ, nums = m.search(None, 'FROM', '"mailer-daemon"', 'SINCE', date_str)

        if not nums[0]:
            m.logout()
            return result

        msg_ids = nums[0].split()
        logger.info(f"{email_addr}: Found {len(msg_ids)} bounce notifications")

        bounced_emails = []
        for mid in msg_ids:
            typ, data = m.fetch(mid, '(BODY.PEEK[])')
            if data and data[0]:
                raw = data[0][1]
                msg = email.message_from_bytes(raw)

                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        ctype = part.get_content_type()
                        if ctype in ('text/plain', 'message/delivery-status'):
                            try:
                                body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            except:
                                pass
                else:
                    try:
                        body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except:
                        body = str(msg.get_payload())

                bounced = extract_bounced_email(body)
                if bounced:
                    bounced_emails.append(bounced)
                    logger.info(f"  BOUNCED: {bounced}")

        result['bounces'] = bounced_emails

        if not dry_run and bounced_emails:
            result['added_to_dnc'] = add_to_dnc(bounced_emails, 'bounce_gmail_auto')

            for mid in msg_ids:
                m.store(mid, '+FLAGS', '\\Deleted')
            m.expunge()
            result['deleted'] = len(msg_ids)
            logger.info(f"  Deleted {len(msg_ids)} notifications, added {result['added_to_dnc']} to DNC")

        m.logout()

    except Exception as e:
        result['error'] = str(e)[:100]
        logger.error(f"{email_addr}: {e}")

    return result


def scan_brevo_bounces(account: dict, dry_run: bool = False) -> dict:
    """Fetch hard bounces from Brevo API."""
    api_key = os.environ.get(account['env_key'])

    if not api_key:
        return {'account': account['name'], 'error': f"no_key ({account['env_key']})", 'bounces': []}

    result = {'account': account['name'], 'bounces': [], 'added_to_dnc': 0}

    try:
        # Get hard bounces from last 24 hours
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        url = f"https://api.brevo.com/v3/smtp/statistics/reports"
        params = {
            'limit': 100,
            'offset': 0,
            'startDate': start_date,
            'endDate': end_date,
            'event': 'hardBounces'
        }
        headers = {'api-key': api_key, 'accept': 'application/json'}

        resp = requests.get(url, headers=headers, params=params, timeout=15)

        if resp.status_code == 200:
            data = resp.json()
            reports = data.get('reports', [])

            bounced_emails = []
            for report in reports:
                email_addr = report.get('email', '').lower().strip()
                if email_addr and '@' in email_addr:
                    bounced_emails.append(email_addr)

            result['bounces'] = bounced_emails

            if bounced_emails:
                logger.info(f"Brevo {account['name']}: {len(bounced_emails)} hard bounces")
                for e in bounced_emails[:10]:
                    logger.info(f"  BOUNCED: {e}")

                if not dry_run:
                    result['added_to_dnc'] = add_to_dnc(bounced_emails, f"bounce_brevo_{account['name']}")
        else:
            # Try events endpoint
            url2 = "https://api.brevo.com/v3/smtp/statistics/events"
            params2 = {
                'limit': 100,
                'startDate': start_date,
                'endDate': end_date,
                'event': 'hardBounces'
            }
            resp2 = requests.get(url2, headers=headers, params=params2, timeout=15)

            if resp2.status_code == 200:
                events = resp2.json().get('events', [])
                bounced_emails = []
                for ev in events:
                    email_addr = ev.get('email', '').lower().strip()
                    if email_addr and '@' in email_addr:
                        bounced_emails.append(email_addr)

                result['bounces'] = list(set(bounced_emails))

                if result['bounces']:
                    logger.info(f"Brevo {account['name']}: {len(result['bounces'])} hard bounces")
                    if not dry_run:
                        result['added_to_dnc'] = add_to_dnc(result['bounces'], f"bounce_brevo_{account['name']}")
            else:
                result['error'] = f"API {resp2.status_code}"

    except Exception as e:
        result['error'] = str(e)[:100]
        logger.error(f"Brevo {account['name']}: {e}")

    return result


def get_stats() -> dict:
    """Get bounce statistics from database."""
    if not HAS_PSYCOPG2:
        return {'error': 'psycopg2 not installed'}

    # Try different databases
    db_configs = [
        {'host': 'localhost', 'dbname': 'email_sender', 'user': 'tudor', 'password': 'tudor123'},
        {'host': 'localhost', 'dbname': 'interjob_master', 'user': 'tudor', 'password': 'scraper123'},
    ]

    for db_config in db_configs:
        try:
            conn = psycopg2.connect(**db_config)
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DATE(added_at), COUNT(*)
                    FROM dnc_list WHERE reason LIKE '%bounce%' AND added_at >= NOW() - INTERVAL '7 days'
                    GROUP BY DATE(added_at) ORDER BY 1 DESC
                """)
                daily = cur.fetchall()

                cur.execute("SELECT COUNT(*) FROM dnc_list")
                total_dnc = cur.fetchone()[0]

                cur.execute("""
                    SELECT reason, COUNT(*) FROM dnc_list
                    WHERE reason LIKE '%bounce%' GROUP BY reason ORDER BY 2 DESC LIMIT 10
                """)
                by_reason = cur.fetchall()

            conn.close()
            return {'daily_bounces': daily, 'total_dnc': total_dnc, 'by_reason': by_reason, 'db': db_config['dbname']}
        except Exception as e:
            continue

    # Check file-based DNC
    dnc_file = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/dnc_bounces.txt')
    if dnc_file.exists():
        with open(dnc_file) as f:
            lines = f.readlines()
        return {'total_dnc': len(lines), 'source': 'file', 'file': str(dnc_file)}

    return {'error': 'No DNC database found'}


def main():
    parser = argparse.ArgumentParser(description='Bounce Cleaner (Gmail + Brevo)')
    parser.add_argument('--account', help='Clean specific Gmail account')
    parser.add_argument('--gmail', action='store_true', help='Clean only Gmail')
    parser.add_argument('--brevo', action='store_true', help='Clean only Brevo')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    parser.add_argument('--stats', action='store_true', help='Show bounce statistics')

    args = parser.parse_args()

    if args.stats:
        stats = get_stats()
        print("=== BOUNCE STATISTICS ===")
        print(f"Total DNC entries: {stats.get('total_dnc', 0)}")
        print("\nDaily bounces (last 7 days):")
        for date, count in stats.get('daily_bounces', []):
            print(f"  {date}: {count}")
        print("\nBy reason:")
        for reason, count in stats.get('by_reason', []):
            print(f"  {reason}: {count}")
        return

    if args.dry_run:
        print("=== DRY RUN (no changes) ===\n")

    total_bounces = 0
    total_added = 0

    # Gmail
    if not args.brevo:
        print("=== GMAIL ACCOUNTS ===")
        accounts = GMAIL_ACCOUNTS
        if args.account:
            accounts = [a for a in GMAIL_ACCOUNTS if a['name'] == args.account]

        for account in accounts:
            result = scan_gmail_bounces(account, dry_run=args.dry_run)
            if result.get('error'):
                print(f"  {account['name']}: ERROR - {result['error']}")
            elif result['bounces']:
                print(f"  {account['name']}: {len(result['bounces'])} bounces, {result.get('added_to_dnc', 0)} added to DNC")
                total_bounces += len(result['bounces'])
                total_added += result.get('added_to_dnc', 0)
            else:
                print(f"  {account['name']}: clean")

    # Brevo
    if not args.gmail:
        print("\n=== BREVO ACCOUNTS ===")
        for account in BREVO_ACCOUNTS:
            result = scan_brevo_bounces(account, dry_run=args.dry_run)
            if result.get('error'):
                print(f"  {account['name']}: ERROR - {result['error']}")
            elif result['bounces']:
                print(f"  {account['name']}: {len(result['bounces'])} bounces, {result.get('added_to_dnc', 0)} added to DNC")
                total_bounces += len(result['bounces'])
                total_added += result.get('added_to_dnc', 0)
            else:
                print(f"  {account['name']}: clean")

    print(f"\n=== TOTAL: {total_bounces} bounces, {total_added} added to DNC ===")


if __name__ == '__main__':
    main()
