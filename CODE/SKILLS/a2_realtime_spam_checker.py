#!/usr/bin/env python3
"""
A2 Realtime Spam Checker - Checks after EVERY email.

How it works:
1. Each email is BCC'd to seed Gmail
2. After send, wait 30s, check inbox vs spam
3. If spam → STOP immediately

Usage in sender:
    from a2_realtime_spam_checker import RealtimeSpamChecker

    checker = RealtimeSpamChecker()

    # After each send:
    bcc_email = checker.get_bcc_email()  # Add to BCC
    # ... send email with BCC ...

    result = checker.check_last_email(domain, subject)
    if result.is_spam:
        raise SpamDetected(f"{domain} going to spam!")
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import imaplib
import email
import time
import json
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, Tuple
from pathlib import Path

from dotenv import load_dotenv
from alerting import send_telegram

load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

# Configuration
SEED_EMAIL = os.getenv('GMAIL_EMAIL', 'manpowerdristor@gmail.com')
SEED_PASSWORD = os.getenv('GMAIL_APP_PASSWORD', '')
IMAP_SERVER = 'imap.gmail.com'
CHECK_WAIT_SECONDS = 60  # Wait time before checking (1 minute)
STATE_FILE = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/DATA/realtime_spam_state.json')


@dataclass
class SpamCheckResult:
    is_spam: bool
    location: str  # 'inbox', 'spam', 'not_found', 'error'
    message: str
    domain: str
    checked_at: str


class SpamDetected(Exception):
    """Raised when spam is detected."""
    pass


class RealtimeSpamChecker:
    """Realtime spam checker - checks after each email."""

    def __init__(self, wait_seconds: int = CHECK_WAIT_SECONDS):
        self.wait_seconds = wait_seconds
        self.seed_email = SEED_EMAIL
        self.seed_password = SEED_PASSWORD
        self.mail = None
        self.last_check_time = None
        self.consecutive_spam = 0
        self.consecutive_inbox = 0
        self.total_checked = 0
        self.state = self._load_state()

    def _load_state(self) -> dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except:
                pass
        return {'checks': [], 'spam_count': 0, 'inbox_count': 0}

    def _save_state(self):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(self.state, indent=2, default=str))

    def get_bcc_email(self) -> str:
        """Get BCC email address to add to each send."""
        return self.seed_email

    def _connect_imap(self) -> bool:
        """Connect to Gmail IMAP."""
        if not self.seed_password:
            return False
        try:
            self.mail = imaplib.IMAP4_SSL(IMAP_SERVER)
            self.mail.login(self.seed_email, self.seed_password)
            return True
        except Exception as e:
            print(f"[SPAM] IMAP connect failed: {e}")
            return False

    def _disconnect_imap(self):
        """Disconnect from IMAP."""
        if self.mail:
            try:
                self.mail.logout()
            except:
                pass
            self.mail = None

    def _search_email(self, subject: str, folder: str = 'INBOX') -> Tuple[bool, Optional[str]]:
        """Search for email by subject in folder. Returns (found, msg_id)."""
        try:
            self.mail.select(folder)
            # Search by subject (partial match)
            search_term = subject[:50] if len(subject) > 50 else subject
            _, messages = self.mail.search(None, f'SUBJECT "{search_term}"')
            if messages[0]:
                return True, messages[0].decode().split()[-1]
            return False, None
        except Exception as e:
            return False, str(e)

    def _delete_email(self, msg_id: str, folder: str = 'INBOX') -> bool:
        """Delete email by message ID."""
        try:
            self.mail.select(folder)
            self.mail.store(msg_id, '+FLAGS', '\\Deleted')
            self.mail.expunge()
            print(f"[SPAM-CHECK] Deleted BCC email {msg_id} from {folder}")
            return True
        except Exception as e:
            print(f"[SPAM-CHECK] Delete FAILED for {msg_id} in {folder}: {e}")
            return False

    def verify_inbox_clean(self, max_allowed: int = 5) -> dict:
        """
        Verify seed inbox has minimal campaign emails.

        Args:
            max_allowed: Max emails allowed before warning

        Returns:
            dict with inbox_count, is_clean, seed_email
        """
        if not self._connect_imap():
            return {'error': 'Cannot connect to IMAP'}

        try:
            # Define our campaign domains
            our_domains = ['horecaworkers', 'mivromania', 'factoryjobs', 'buildjobs',
                          'interjob', 'careworkers', 'cifn', 'warehouseworkers',
                          'meatworkers', 'electricjobs', 'mechanicjobs', 'farmworkers']

            self.mail.select('INBOX')
            _, messages = self.mail.search(None, 'ALL')

            total_count = 0
            campaign_count = 0

            if messages[0]:
                msg_ids = messages[0].decode().split()
                total_count = len(msg_ids)

                # Check each email for campaign origin
                for msg_id in msg_ids:
                    try:
                        _, data = self.mail.fetch(msg_id, '(RFC822.HEADER)')
                        header = data[0][1].decode(errors='ignore').lower()
                        if any(d in header for d in our_domains):
                            campaign_count += 1
                    except:
                        pass

            return {
                'seed_email': self.seed_email,
                'total_inbox': total_count,
                'campaign_emails': campaign_count,
                'is_clean': campaign_count <= max_allowed,
                'max_allowed': max_allowed,
                'checked_at': datetime.now().isoformat()
            }
        finally:
            self._disconnect_imap()

    def check_last_email(self, domain: str, subject: str, wait: bool = True) -> SpamCheckResult:
        """
        Check if the last sent email landed in inbox or spam.

        Args:
            domain: Sending domain (for logging)
            subject: Email subject to search for
            wait: Whether to wait before checking (default True)

        Returns:
            SpamCheckResult with location and status
        """
        timestamp = datetime.now().isoformat()

        if wait:
            time.sleep(self.wait_seconds)

        if not self._connect_imap():
            return SpamCheckResult(
                is_spam=False,
                location='error',
                message='IMAP connection failed',
                domain=domain,
                checked_at=timestamp
            )

        try:
            # Check INBOX first
            found_inbox, msg_id = self._search_email(subject, 'INBOX')
            if found_inbox:
                self.consecutive_inbox += 1
                self.consecutive_spam = 0
                self.state['inbox_count'] = self.state.get('inbox_count', 0) + 1
                self._save_state()

                # Delete the verified email from seed inbox (BCC cleanup)
                if msg_id:
                    deleted = self._delete_email(msg_id, 'INBOX')
                    if not deleted:
                        print(f"[SPAM-CHECK] WARNING: Failed to delete BCC from INBOX")

                return SpamCheckResult(
                    is_spam=False,
                    location='inbox',
                    message=f'OK - inbox ({self.consecutive_inbox} consecutive)',
                    domain=domain,
                    checked_at=timestamp
                )

            # Check SPAM folder
            found_spam, msg_id = self._search_email(subject, '[Gmail]/Spam')
            if found_spam:
                self.consecutive_spam += 1
                self.consecutive_inbox = 0
                self.state['spam_count'] = self.state.get('spam_count', 0) + 1
                self._save_state()

                # Alert immediately
                send_telegram(f"🚨 SPAM DETECTED: {domain}\nSubject: {subject[:50]}\nConsecutive spam: {self.consecutive_spam}")

                # Delete from spam folder too (BCC cleanup)
                if msg_id:
                    deleted = self._delete_email(msg_id, '[Gmail]/Spam')
                    if not deleted:
                        print(f"[SPAM-CHECK] WARNING: Failed to delete BCC from SPAM folder")

                return SpamCheckResult(
                    is_spam=True,
                    location='spam',
                    message=f'SPAM! ({self.consecutive_spam} consecutive)',
                    domain=domain,
                    checked_at=timestamp
                )

            # Not found yet (may still be in transit)
            return SpamCheckResult(
                is_spam=False,
                location='not_found',
                message='Email not found yet (may be delayed)',
                domain=domain,
                checked_at=timestamp
            )

        finally:
            self._disconnect_imap()

    def check_without_wait(self, domain: str, subject: str) -> SpamCheckResult:
        """Check immediately without waiting."""
        return self.check_last_email(domain, subject, wait=False)

    def get_stats(self) -> dict:
        """Get spam check statistics."""
        return {
            'total_checked': self.state.get('inbox_count', 0) + self.state.get('spam_count', 0),
            'inbox_count': self.state.get('inbox_count', 0),
            'spam_count': self.state.get('spam_count', 0),
            'consecutive_inbox': self.consecutive_inbox,
            'consecutive_spam': self.consecutive_spam,
            'spam_rate': self.state.get('spam_count', 0) / max(1, self.state.get('inbox_count', 0) + self.state.get('spam_count', 0)) * 100
        }


def check_recent_emails(minutes: int = 30) -> dict:
    """Check recent emails in inbox vs spam."""
    result = {'inbox': [], 'spam': [], 'stats': {}}

    if not SEED_PASSWORD:
        return {'error': 'No password configured'}

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(SEED_EMAIL, SEED_PASSWORD)

        since = (datetime.now() - timedelta(minutes=minutes)).strftime('%d-%b-%Y')

        # Check INBOX
        mail.select('INBOX')
        _, messages = mail.search(None, f'SINCE {since}')
        if messages[0]:
            for msg_id in messages[0].split()[-10:]:  # Last 10
                _, msg_data = mail.fetch(msg_id, '(RFC822.HEADER)')
                msg = email.message_from_bytes(msg_data[0][1])
                result['inbox'].append({
                    'from': msg.get('From', '')[:50],
                    'subject': msg.get('Subject', '')[:50],
                    'date': msg.get('Date', '')[:25]
                })

        # Check SPAM
        mail.select('[Gmail]/Spam')
        _, messages = mail.search(None, f'SINCE {since}')
        if messages[0]:
            for msg_id in messages[0].split()[-10:]:
                _, msg_data = mail.fetch(msg_id, '(RFC822.HEADER)')
                msg = email.message_from_bytes(msg_data[0][1])
                result['spam'].append({
                    'from': msg.get('From', '')[:50],
                    'subject': msg.get('Subject', '')[:50],
                    'date': msg.get('Date', '')[:25]
                })

        mail.logout()

        result['stats'] = {
            'inbox_count': len(result['inbox']),
            'spam_count': len(result['spam']),
            'period_minutes': minutes
        }

    except Exception as e:
        result['error'] = str(e)

    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Realtime Spam Checker')
    parser.add_argument('--recent', '-r', type=int, default=30, help='Check recent N minutes')
    parser.add_argument('--stats', '-s', action='store_true', help='Show stats')
    parser.add_argument('--verify', '-v', action='store_true', help='Verify inbox is clean')
    args = parser.parse_args()

    if args.verify:
        checker = RealtimeSpamChecker()
        result = checker.verify_inbox_clean()
        if 'error' in result:
            print(f"ERROR: {result['error']}")
            sys.exit(1)

        print("=== BCC INBOX VERIFICATION ===")
        print(f"  Seed email: {result['seed_email']}")
        print(f"  Total inbox: {result['total_inbox']}")
        print(f"  Campaign emails: {result['campaign_emails']}")
        status = "OK" if result['is_clean'] else f"WARNING: {result['campaign_emails']} > {result['max_allowed']}"
        print(f"  Status: {status}")
        sys.exit(0 if result['is_clean'] else 1)

    elif args.stats:
        checker = RealtimeSpamChecker()
        stats = checker.get_stats()
        print("Realtime Spam Check Stats:")
        print(f"  Total checked: {stats['total_checked']}")
        print(f"  Inbox: {stats['inbox_count']}")
        print(f"  Spam: {stats['spam_count']}")
        print(f"  Spam rate: {stats['spam_rate']:.1f}%")
    else:
        result = check_recent_emails(args.recent)
        print(f"\nRecent {args.recent} minutes:")
        print(f"  Inbox: {result.get('stats', {}).get('inbox_count', 0)}")
        print(f"  Spam: {result.get('stats', {}).get('spam_count', 0)}")

        if result.get('spam'):
            print("\nSpam emails:")
            for e in result['spam']:
                print(f"  - {e['from']}: {e['subject']}")
