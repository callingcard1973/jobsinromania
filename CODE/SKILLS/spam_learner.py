#!/usr/bin/env python3
"""
Smart Spam Learning System for Gmail

LEARNING LOGIC:
1. Scan Spam folder -> remember senders
2. Scan Inbox -> if sender is in spam list, move to Spam
3. If user moves email back to Inbox -> remove sender from spam list (user correction)

This learns from YOUR decisions without reading email content.

Usage:
    python3 spam_learner.py                    # Run for default account
    python3 spam_learner.py --account EMAIL    # Run for specific account
    python3 spam_learner.py --stats            # Show learning statistics
    python3 spam_learner.py --list-spammers    # List known spam senders
"""

import imaplib
import email
import os
import sys
import sqlite3
import argparse
from datetime import datetime
import logging

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

# LLM spam scoring (optional)
try:
    sys.path.insert(0, '/opt/ACTIVE/LLM/MEMORY/llm_tasks')
    from telegram.llm_spam_bridge import is_spam_llm
    HAS_LLM = True
except ImportError:
    HAS_LLM = False


# Setup logging
log_dir = '/opt/ACTIVE/INFRA/SKILLS/logs'
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'{log_dir}/spam_learner.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Database for learning
DB_PATH = '/opt/ACTIVE/INFRA/SKILLS/data/spam_learning.db'

# Supported accounts
ACCOUNTS = {
    'fruitnature4@gmail.com': {
        'password_env': 'GMAIL_FRUITNATURE4_APP_PASSWORD',
        'imap_server': 'imap.gmail.com',
        'spam_folder': '[Gmail]/Spam',
        'provider': 'gmail'
    },
    'manpowerdristor@gmail.com': {
        'password_env': 'GMAIL_APP_PASSWORD',
        'imap_server': 'imap.gmail.com',
        'spam_folder': '[Gmail]/Spam',
        'provider': 'gmail'
    },
    'manpower.dristor@gmail.com': {
        'password_env': 'GMAIL_MANPOWER_APP_PASSWORD',
        'imap_server': 'imap.gmail.com',
        'spam_folder': '[Gmail]/Spam',
        'provider': 'gmail'
    },
    'secretariatagentieasia@yahoo.com': {
        'password_env': 'YAHOO_APP_PASSWORD',
        'imap_server': 'imap.mail.yahoo.com',
        'spam_folder': 'Bulk Mail',
        'provider': 'yahoo'
    },
    'apaminerala@yahoo.com': {
        'password_env': 'YAHOO_APAMINERALA_APP_PASSWORD',
        'imap_server': 'imap.mail.yahoo.com',
        'spam_folder': 'Bulk Mail',
        'provider': 'yahoo'
    }
}

DEFAULT_ACCOUNT = 'fruitnature4@gmail.com'

# Whitelist - never mark these domains as spam
WHITELIST_DOMAINS = [
    'interjob.ro',
    'factoryjobs.eu',
    'buildjobs.eu',
    'careworkers.eu',
    'warehouseworkers.eu',
    'mivromania.info',
    'mivromania.online',
    'nepalezi.com',
    'cifn.info',
    'expatsinromania.org',
    'gmail.com',  # Don't spam our own gmail accounts
]

# Verified emails cache (loaded from DB)
VERIFIED_EMAILS = set()

def load_verified_emails():
    """Load verified emails from PostgreSQL - these are campaign contacts who replied"""
    global VERIFIED_EMAILS
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost",
            database="email_sender",
            user="tudor",
            password="tudor123"
        )
        cursor = conn.cursor()

        # Get emails that have replied to our campaigns (campaign_replies table)
        cursor.execute("""
            SELECT DISTINCT LOWER(email) FROM campaign_replies WHERE email IS NOT NULL
        """)
        for row in cursor.fetchall():
            if row[0] and '@' in row[0]:
                VERIFIED_EMAILS.add(row[0].strip().lower())

        conn.close()
        logger.info(f"Loaded {len(VERIFIED_EMAILS)} verified emails from database")
    except Exception as e:
        logger.warning(f"Could not load verified emails: {e}")

def is_verified_email(email_addr):
    """Check if email is verified (replied to our campaigns)"""
    if not email_addr:
        return False
    return email_addr.lower().strip() in VERIFIED_EMAILS


class SpamLearner:
    def __init__(self, email_address):
        self.email_address = email_address

        if email_address not in ACCOUNTS:
            raise ValueError(f"Unknown account: {email_address}")

        self.config = ACCOUNTS[email_address]
        self.password = os.getenv(self.config['password_env'], '')

        if not self.password or self.password in ('NEEDS_APP_PASSWORD', 'EXPIRED_NEEDS_NEW_PASSWORD'):
            raise ValueError(f"No valid password for {email_address}. Set {self.config['password_env']} in /opt/ACTIVE/EMAIL/CAMPAIGNS/.env")

        self.mail = None
        self._resolved_spam_folder = None  # Discovered during folder selection
        self.stats = {
            'learned_from_spam': 0,
            'moved_to_spam': 0,
            'unlearned_from_inbox': 0,
            'llm_flagged': 0,
        }

        self._init_database()

    def _init_database(self):
        """Initialize SQLite database for spam learning"""
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS spam_senders (
                sender_email TEXT PRIMARY KEY,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                times_seen INTEGER DEFAULT 1,
                account TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                action TEXT,
                sender_email TEXT,
                subject TEXT,
                account TEXT
            )
        ''')

        conn.commit()
        conn.close()

    def connect(self):
        """Connect to IMAP server"""
        try:
            logger.info(f"Connecting to {self.config['imap_server']} for {self.email_address}")
            self.mail = imaplib.IMAP4_SSL(self.config['imap_server'], 993)
            self.mail.login(self.email_address, self.password)
            logger.info(f"Connected to {self.email_address}")
            return True
        except Exception as e:
            logger.error(f"Connection failed for {self.email_address}: {e}")
            return False

    def disconnect(self):
        """Disconnect from IMAP"""
        try:
            if self.mail:
                self.mail.close()
                self.mail.logout()
        except:
            pass

    def extract_email_address(self, from_header):
        """Extract clean email address from From header"""
        if not from_header:
            return None

        if isinstance(from_header, bytes):
            from_header = from_header.decode('utf-8', errors='ignore')

        import re
        match = re.search(r'<([^>]+)>', from_header)
        if match:
            return match.group(1).lower().strip()

        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', from_header)
        if email_match:
            return email_match.group(0).lower().strip()

        return None

    def learn_from_spam_folder(self):
        """Learn spam senders from Spam folder"""
        try:
            spam_folder = self.config['spam_folder']
            logger.info(f"Learning from spam folder: {spam_folder}")

            # Try different folder name formats
            folder_attempts = [spam_folder, f'"{spam_folder}"', 'Bulk', '"Bulk"', 'Spam', '"Spam"']
            status = 'NO'
            for folder in folder_attempts:
                try:
                    status, _ = self.mail.select(folder)
                    if status == 'OK':
                        self._resolved_spam_folder = folder
                        logger.info(f"Selected folder: {folder}")
                        break
                except:
                    continue

            if status != 'OK':
                logger.warning(f"Could not select spam folder. Tried: {folder_attempts}")
                return

            status, messages = self.mail.search(None, 'ALL')
            if status != 'OK':
                logger.warning("No messages found in Spam folder")
                return

            message_ids = messages[0].split()
            logger.info(f"Found {len(message_ids)} emails in Spam folder")

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            for msg_id in message_ids[-100:]:  # Process last 100 to avoid long runs
                try:
                    status, msg_data = self.mail.fetch(msg_id, '(BODY[HEADER.FIELDS (FROM SUBJECT)])')
                    if status != 'OK':
                        continue

                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    from_header = msg.get('From', '')
                    subject = msg.get('Subject', '')[:100]

                    sender_email = self.extract_email_address(from_header)
                    if not sender_email:
                        continue

                    # Skip whitelisted domains
                    domain = sender_email.split('@')[-1].lower()
                    if domain in WHITELIST_DOMAINS:
                        continue

                    cursor.execute('''
                        INSERT INTO spam_senders (sender_email, account, times_seen)
                        VALUES (?, ?, 1)
                        ON CONFLICT(sender_email) DO UPDATE SET
                            last_seen = CURRENT_TIMESTAMP,
                            times_seen = times_seen + 1
                    ''', (sender_email, self.email_address))

                    cursor.execute('''
                        INSERT INTO learning_log (action, sender_email, subject, account)
                        VALUES (?, ?, ?, ?)
                    ''', ('LEARNED', sender_email, subject, self.email_address))

                    self.stats['learned_from_spam'] += 1

                except Exception as e:
                    continue

            conn.commit()
            conn.close()

            logger.info(f"Learned {self.stats['learned_from_spam']} spam senders")

        except Exception as e:
            logger.error(f"Error learning from spam folder: {e}")

    def is_spam_sender(self, sender_email):
        """Check if sender is in spam list (respects whitelist and verified emails)"""
        # Check whitelist first
        if sender_email:
            domain = sender_email.split('@')[-1].lower()
            if domain in WHITELIST_DOMAINS:
                return False

        # Check if this is a verified email (replied to our campaigns)
        if is_verified_email(sender_email):
            logger.debug(f"Skipping verified email: {sender_email}")
            return False

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM spam_senders WHERE sender_email = ?', (sender_email,))
        result = cursor.fetchone()
        conn.close()
        return result is not None

    def remove_from_spam_list(self, sender_email, subject):
        """Remove sender from spam list (user correction)"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM spam_senders WHERE sender_email = ?', (sender_email,))

        cursor.execute('''
            INSERT INTO learning_log (action, sender_email, subject, account)
            VALUES (?, ?, ?, ?)
        ''', ('UNLEARNED', sender_email, subject, self.email_address))

        conn.commit()
        conn.close()

        self.stats['unlearned_from_inbox'] += 1
        logger.info(f"Unlearned (user correction): {sender_email}")

    def process_inbox(self):
        """Process inbox - move spam senders to Spam"""
        try:
            self.mail.select('INBOX')

            status, messages = self.mail.search(None, 'ALL')
            if status != 'OK':
                logger.warning("No messages found in INBOX")
                return

            message_ids = messages[0].split()
            logger.info(f"Scanning {len(message_ids)} emails in INBOX")

            spam_folder = self.config['spam_folder']

            for msg_id in message_ids:
                try:
                    status, msg_data = self.mail.fetch(msg_id, '(BODY[HEADER.FIELDS (FROM SUBJECT)])')
                    if status != 'OK':
                        continue

                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    from_header = msg.get('From', '')
                    subject = msg.get('Subject', '')

                    sender_email = self.extract_email_address(from_header)
                    if not sender_email:
                        continue

                    if self.is_spam_sender(sender_email):
                        # Use resolved folder name from learning step
                        target = self._resolved_spam_folder or f'"{spam_folder}"'
                        try:
                            self.mail.copy(msg_id, target)
                            self.mail.store(msg_id, '+FLAGS', '\\Deleted')
                            self.stats['moved_to_spam'] += 1
                            logger.info(f"Moved to spam: {sender_email}")
                        except Exception as copy_err:
                            logger.warning(f"Failed to move {sender_email}: {copy_err}")

                except Exception as e:
                    continue

            self.mail.expunge()
            logger.info(f"Moved {self.stats['moved_to_spam']} emails to spam")

        except Exception as e:
            logger.error(f"Error processing inbox: {e}")

    def check_for_user_corrections(self):
        """Check if user moved emails back to inbox (user correction)"""
        try:
            self.mail.select('INBOX')

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('SELECT sender_email FROM spam_senders WHERE account = ?', (self.email_address,))
            spam_senders = [row[0] for row in cursor.fetchall()]
            conn.close()

            if not spam_senders:
                return

            logger.info(f"Checking for user corrections among {len(spam_senders)} known spam senders")

            status, messages = self.mail.search(None, 'ALL')
            if status != 'OK':
                return

            message_ids = messages[0].split()

            for msg_id in message_ids:
                try:
                    status, msg_data = self.mail.fetch(msg_id, '(BODY[HEADER.FIELDS (FROM SUBJECT)])')
                    if status != 'OK':
                        continue

                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    from_header = msg.get('From', '')
                    subject = msg.get('Subject', '')

                    sender_email = self.extract_email_address(from_header)
                    if not sender_email:
                        continue

                    if sender_email in spam_senders:
                        logger.info(f"User correction detected: {sender_email}")
                        self.remove_from_spam_list(sender_email, subject)

                except Exception as e:
                    continue

        except Exception as e:
            logger.error(f"Error checking user corrections: {e}")


    def llm_score_inbox(self, limit=30):
        """Use LLM to score unknown inbox emails for spam (step 4).
        Separates IMAP fetch from LLM scoring to avoid IMAP timeout."""
        if not HAS_LLM:
            logger.info("LLM not available, skipping AI spam scoring")
            return

        # Phase 1: Collect email headers from IMAP (fast)
        candidates = []
        try:
            self.mail.select('INBOX')
            status, messages = self.mail.search(None, 'ALL')
            if status != 'OK':
                return

            message_ids = messages[0].split()
            recent_ids = message_ids[-limit:] if len(message_ids) > limit else message_ids

            for msg_id in recent_ids:
                try:
                    status, msg_data = self.mail.fetch(msg_id, '(BODY[HEADER.FIELDS (FROM SUBJECT)])')
                    if status != 'OK':
                        continue

                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    from_header = msg.get('From', '')
                    subject = msg.get('Subject', '')[:100]

                    sender_email = self.extract_email_address(from_header)
                    if not sender_email:
                        continue

                    domain = sender_email.split('@')[-1].lower()
                    if domain in WHITELIST_DOMAINS:
                        continue
                    if self.is_spam_sender(sender_email):
                        continue
                    if is_verified_email(sender_email):
                        continue

                    text = f"From: {from_header}\nSubject: {subject}"
                    if len(text) < 20:
                        continue

                    candidates.append((sender_email, from_header, subject, text))
                except Exception:
                    continue

            logger.info(f"LLM: {len(candidates)} emails to score")
        except Exception as e:
            logger.error(f"LLM fetch error: {e}")
            return

        if not candidates:
            logger.info("LLM: no emails to score")
            return

        # Phase 2: Score with LLM (slow, no IMAP needed)
        spam_senders = set()
        checked = 0
        for sender_email, from_header, subject, text in candidates:
            try:
                result = is_spam_llm(text, sender_email, self.email_address, threshold=8, task='email_spam_scorer')
                checked += 1
                if result and result['is_spam']:
                    logger.info(f"LLM spam (score {result['score']}): {sender_email} - {subject[:50]}")
                    spam_senders.add(sender_email)

                    # Learn sender in DB immediately
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute(
                        'INSERT OR IGNORE INTO spam_senders (sender_email, account) VALUES (?, ?)',
                        (sender_email, self.email_address)
                    )
                    cursor.execute(
                        'INSERT INTO learning_log (action, sender_email, subject, account) VALUES (?, ?, ?, ?)',
                        ('LLM_LEARNED', sender_email, subject, self.email_address)
                    )
                    conn.commit()
                    conn.close()
                elif result:
                    logger.debug(f"LLM ok (score {result['score']}): {sender_email}")
            except Exception as e:
                logger.warning(f"LLM score failed for {sender_email}: {e}")
                continue

        logger.info(f"LLM scored {checked} emails, {len(spam_senders)} senders flagged")

        # Phase 3: Reconnect to IMAP and move flagged emails
        if spam_senders:
            try:
                self.mail.logout()
            except Exception:
                pass
            if not self.connect():
                logger.error("Failed to reconnect for LLM spam moves")
                self.stats['llm_flagged'] = len(spam_senders)
                return

            spam_folder = self._resolved_spam_folder or f'"{self.config["spam_folder"]}"'
            try:
                self.mail.select('INBOX')
                status, messages = self.mail.search(None, 'ALL')
                if status != 'OK':
                    return

                all_ids = messages[0].split()
                for msg_id in all_ids:
                    try:
                        status, msg_data = self.mail.fetch(msg_id, '(BODY[HEADER.FIELDS (FROM)])')
                        if status != 'OK':
                            continue
                        raw = msg_data[0][1]
                        m = email.message_from_bytes(raw)
                        sender = self.extract_email_address(m.get('From', ''))
                        if sender in spam_senders:
                            try:
                                self.mail.copy(msg_id, spam_folder)
                                self.mail.store(msg_id, '+FLAGS', '\\Deleted')
                                self.stats['llm_flagged'] += 1
                                logger.info(f"LLM moved to spam: {sender}")
                            except Exception as ce:
                                logger.warning(f"Failed to move LLM spam {sender}: {ce}")
                    except Exception:
                        continue

                self.mail.expunge()
            except Exception as e:
                logger.error(f"LLM move error: {e}")

        logger.info(f"LLM checked {checked} emails, flagged {self.stats['llm_flagged']}")

    def run(self):
        """Run the spam learning process"""
        if not self.connect():
            return False

        try:
            logger.info("=" * 60)
            logger.info(f"SPAM LEARNING - {self.email_address}")
            logger.info("=" * 60)

            logger.info("\n[1/4] Checking for user corrections...")
            self.check_for_user_corrections()

            logger.info("\n[2/4] Learning spam senders...")
            self.learn_from_spam_folder()

            logger.info("\n[3/4] Processing inbox...")
            self.process_inbox()

            logger.info("\n[4/4] LLM spam scoring...")
            self.llm_score_inbox()

            logger.info("\n" + "=" * 60)
            logger.info("SUMMARY")
            logger.info(f"  Learned:      {self.stats['learned_from_spam']} senders")
            logger.info(f"  Moved:        {self.stats['moved_to_spam']} emails")
            logger.info(f"  LLM flagged:  {self.stats['llm_flagged']} emails")
            logger.info(f"  Corrections:  {self.stats['unlearned_from_inbox']} senders")
            logger.info("=" * 60)

            return True

        finally:
            self.disconnect()


def show_stats():
    """Show learning statistics"""
    if not os.path.exists(DB_PATH):
        print("No learning database found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("\n=== SPAM LEARNER STATISTICS ===\n")

    cursor.execute('SELECT COUNT(*) FROM spam_senders')
    total = cursor.fetchone()[0]
    print(f"Total known spam senders: {total}")

    cursor.execute('''
        SELECT account, COUNT(*) as cnt
        FROM spam_senders
        GROUP BY account
        ORDER BY cnt DESC
    ''')
    print("\nBy account:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} senders")

    cursor.execute('''
        SELECT action, COUNT(*) as cnt
        FROM learning_log
        GROUP BY action
    ''')
    print("\nLearning actions:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")

    cursor.execute('''
        SELECT date(timestamp) as day, action, COUNT(*) as cnt
        FROM learning_log
        WHERE timestamp > datetime('now', '-7 days')
        GROUP BY day, action
        ORDER BY day DESC
    ''')
    results = cursor.fetchall()
    if results:
        print("\nLast 7 days:")
        for row in results:
            print(f"  {row[0]} {row[1]}: {row[2]}")

    conn.close()


def list_spammers(limit=50):
    """List known spam senders"""
    if not os.path.exists(DB_PATH):
        print("No learning database found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT sender_email, times_seen, last_seen, account
        FROM spam_senders
        ORDER BY times_seen DESC
        LIMIT ?
    ''', (limit,))

    print(f"\n=== TOP {limit} SPAM SENDERS ===\n")
    print(f"{'Sender':<40} {'Count':<6} {'Last Seen':<12} {'Account':<30}")
    print("-" * 90)

    for row in cursor.fetchall():
        sender = row[0][:38] if len(row[0]) > 38 else row[0]
        last_seen = row[2][:10] if row[2] else 'N/A'
        account = row[3][:28] if row[3] and len(row[3]) > 28 else (row[3] or 'N/A')
        print(f"{sender:<40} {row[1]:<6} {last_seen:<12} {account:<30}")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description='Smart Spam Learner for Gmail/Yahoo')
    parser.add_argument('--account', '-a', default=DEFAULT_ACCOUNT,
                       help=f'Email account to process (default: {DEFAULT_ACCOUNT})')
    parser.add_argument('--stats', action='store_true',
                       help='Show learning statistics')
    parser.add_argument('--list-spammers', action='store_true',
                       help='List known spam senders')
    parser.add_argument('--limit', type=int, default=50,
                       help='Limit for list-spammers (default: 50)')

    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    if args.list_spammers:
        list_spammers(args.limit)
        return

    # Load verified emails from database (campaign respondents - never mark as spam)
    load_verified_emails()

    # Run spam learner
    try:
        learner = SpamLearner(args.account)
        learner.run()
    except ValueError as e:
        logger.error(str(e))
        print(f"\nAvailable accounts:")
        for acc in ACCOUNTS:
            pwd_env = ACCOUNTS[acc]['password_env']
            pwd = os.getenv(pwd_env, '')
            status = 'OK' if pwd and pwd not in ('NEEDS_APP_PASSWORD', 'EXPIRED_NEEDS_NEW_PASSWORD') else 'NEEDS PASSWORD'
            print(f"  {acc}: {status}")


if __name__ == '__main__':
    main()
