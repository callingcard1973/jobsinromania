#!/usr/bin/env python3
"""
Yahoo Inbox Spam Inspector with LLM Classification

Uses existing spam patterns + local LLM to classify inbox emails.

Usage:
    python3 yahoo_spam_inspector.py                    # Check apaminerala inbox
    python3 yahoo_spam_inspector.py --days 7           # Last 7 days
    python3 yahoo_spam_inspector.py --move-spam        # Move detected spam to Bulk Mail
    python3 yahoo_spam_inspector.py --stats            # Show spam statistics
"""

import imaplib
import email
from email.header import decode_header
import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Tuple, Optional
import requests

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from dotenv import load_dotenv

load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

# Yahoo IMAP config
YAHOO_EMAIL = os.getenv('YAHOO_APAMINERALA_EMAIL', 'apaminerala@yahoo.com')
YAHOO_PASSWORD = os.getenv('YAHOO_APAMINERALA_APP_PASSWORD', '')
IMAP_SERVER = 'imap.mail.yahoo.com'
SPAM_FOLDER = 'Bulk Mail'

# Local LLM
LLM_URL = "http://localhost:1234/v1/chat/completions"
LLM_MODEL = "llama-3.2-3b-instruct"

# Spam patterns from existing code (email_spam_checker.py)
SPAM_SUBJECTS = [
    'unsubscribe', 'promotional', 'discount', 'sale', 'offer',
    'winner', 'congratulations', 'lottery', 'prize', 'free',
    'urgent', 'act now', 'limited time', 'exclusive deal',
    'crypto', 'bitcoin', 'investment opportunity',
    'weight loss', 'diet', 'viagra', 'pills',
    'nigerian', 'prince', 'inheritance', 'million dollars',
    'click here', 'verify your account', 'suspended',
    'your order', 'tracking', 'shipment'  # unless expected
]

SPAM_SENDERS = [
    'noreply', 'no-reply', 'donotreply', 'newsletter', 'promo',
    'marketing', 'offers', 'deals', 'info@', 'support@',
    'mailer-daemon', 'postmaster'
]

# Whitelist - never spam
WHITELIST_DOMAINS = [
    'interjob.ro', 'factoryjobs.eu', 'buildjobs.eu', 'horecaworkers.eu',
    'mivromania.info', 'expatsinromania.org', 'careworkers.eu',
    'bp-p.co.uk', 'bpandp', 'lucian', 'tudor'
]


@dataclass
class EmailInfo:
    uid: str
    subject: str
    sender: str
    date: str
    snippet: str
    spam_score: float = 0.0
    spam_reason: str = ""
    llm_verdict: str = ""


def decode_mime_header(header: str) -> str:
    """Decode MIME encoded header."""
    if not header:
        return ""
    decoded_parts = decode_header(header)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            charset = charset or 'utf-8'
            try:
                result.append(part.decode(charset, errors='replace'))
            except:
                result.append(part.decode('utf-8', errors='replace'))
        else:
            result.append(str(part))
    return ' '.join(result)


def pattern_spam_score(subject: str, sender: str) -> Tuple[float, str]:
    """Score email using pattern matching (0-1 scale)."""
    score = 0.0
    reasons = []

    subject_lower = subject.lower()
    sender_lower = sender.lower()

    # Check whitelist first
    for domain in WHITELIST_DOMAINS:
        if domain in sender_lower:
            return 0.0, "whitelisted"

    # Check spam subjects
    for pattern in SPAM_SUBJECTS:
        if pattern in subject_lower:
            score += 0.15
            reasons.append(f"subject:{pattern}")

    # Check spam senders
    for pattern in SPAM_SENDERS:
        if pattern in sender_lower:
            score += 0.2
            reasons.append(f"sender:{pattern}")

    # Suspicious patterns
    if subject_lower.count('!') > 2:
        score += 0.1
        reasons.append("excessive_exclamation")

    if subject_lower.isupper() and len(subject) > 10:
        score += 0.15
        reasons.append("all_caps")

    if '$' in subject or '€' in subject:
        score += 0.1
        reasons.append("currency_symbol")

    return min(score, 1.0), ", ".join(reasons) if reasons else "clean"


def llm_classify(subject: str, sender: str, snippet: str) -> Tuple[str, float]:
    """Use local LLM to classify email as spam or not."""
    try:
        prompt = f"""Classify this email as SPAM or HAM (not spam).

From: {sender}
Subject: {subject}
Preview: {snippet[:200]}

Reply with ONLY one word: SPAM or HAM"""

        response = requests.post(
            LLM_URL,
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": "You classify emails as SPAM or HAM. Reply with one word only."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 10,
                "temperature": 0.1
            },
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            verdict = result['choices'][0]['message']['content'].strip().upper()
            if 'SPAM' in verdict:
                return 'SPAM', 0.8
            else:
                return 'HAM', 0.0
    except Exception as e:
        return 'ERROR', 0.0

    return 'UNKNOWN', 0.0


def fetch_inbox(days: int = 3, limit: int = 50) -> List[EmailInfo]:
    """Fetch recent emails from Yahoo inbox."""
    if not YAHOO_PASSWORD:
        print("ERROR: No Yahoo password configured")
        return []

    emails = []

    try:
        imap = imaplib.IMAP4_SSL(IMAP_SERVER, 993)
        imap.login(YAHOO_EMAIL, YAHOO_PASSWORD)
        imap.select('INBOX')

        since_date = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
        _, messages = imap.search(None, f'(SINCE {since_date})')

        msg_ids = messages[0].split()[-limit:]  # Last N messages

        for msg_id in msg_ids:
            try:
                _, msg_data = imap.fetch(msg_id, '(RFC822)')

                if not msg_data or not msg_data[0]:
                    continue

                msg = email.message_from_bytes(msg_data[0][1])

                subject = decode_mime_header(msg.get('Subject', ''))
                sender = decode_mime_header(msg.get('From', ''))
                date_str = msg.get('Date', '')[:25]

                # Get snippet from body
                snippet = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == 'text/plain':
                            try:
                                snippet = part.get_payload(decode=True).decode('utf-8', errors='replace')[:300]
                            except:
                                pass
                            break
                else:
                    try:
                        snippet = msg.get_payload(decode=True).decode('utf-8', errors='replace')[:300]
                    except:
                        pass

                emails.append(EmailInfo(
                    uid=msg_id.decode(),
                    subject=subject,
                    sender=sender,
                    date=date_str,
                    snippet=snippet
                ))

            except Exception as e:
                continue

        imap.logout()

    except Exception as e:
        print(f"IMAP Error: {e}")

    return emails


def analyze_emails(emails: List[EmailInfo], use_llm: bool = True) -> List[EmailInfo]:
    """Analyze emails for spam using patterns + LLM."""
    for em in emails:
        # Pattern-based scoring
        score, reason = pattern_spam_score(em.subject, em.sender)
        em.spam_score = score
        em.spam_reason = reason

        # LLM classification for uncertain cases
        if use_llm and 0.2 < score < 0.6:
            verdict, llm_score = llm_classify(em.subject, em.sender, em.snippet)
            em.llm_verdict = verdict
            if verdict == 'SPAM':
                em.spam_score = max(em.spam_score, llm_score)
        elif score >= 0.6:
            em.llm_verdict = "PATTERN_SPAM"
        else:
            em.llm_verdict = "PATTERN_HAM"

    return emails


def move_to_spam(imap, uid: str) -> bool:
    """Move email to Bulk Mail folder."""
    try:
        imap.uid('COPY', uid, SPAM_FOLDER)
        imap.uid('STORE', uid, '+FLAGS', '\\Deleted')
        imap.expunge()
        return True
    except:
        return False


def main():
    parser = argparse.ArgumentParser(description='Yahoo Inbox Spam Inspector')
    parser.add_argument('--days', type=int, default=3, help='Days to look back')
    parser.add_argument('--limit', type=int, default=50, help='Max emails to check')
    parser.add_argument('--move-spam', action='store_true', help='Move detected spam to Bulk Mail')
    parser.add_argument('--stats', action='store_true', help='Show statistics only')
    parser.add_argument('--no-llm', action='store_true', help='Skip LLM classification')
    args = parser.parse_args()

    print(f"=== Yahoo Inbox Inspector: {YAHOO_EMAIL} ===")
    print(f"Checking last {args.days} days, up to {args.limit} emails\n")

    # Fetch emails
    emails = fetch_inbox(days=args.days, limit=args.limit)

    if not emails:
        print("No emails found or connection failed")
        return

    print(f"Found {len(emails)} emails\n")

    # Analyze
    emails = analyze_emails(emails, use_llm=not args.no_llm)

    # Sort by spam score
    emails.sort(key=lambda x: x.spam_score, reverse=True)

    # Stats
    spam_count = sum(1 for e in emails if e.spam_score >= 0.5)
    suspicious = sum(1 for e in emails if 0.3 <= e.spam_score < 0.5)
    clean = sum(1 for e in emails if e.spam_score < 0.3)

    if args.stats:
        print(f"SPAM (>=0.5):      {spam_count}")
        print(f"Suspicious:        {suspicious}")
        print(f"Clean (<0.3):      {clean}")
        return

    # Display results
    print("--- LIKELY SPAM (score >= 0.5) ---")
    for em in emails:
        if em.spam_score >= 0.5:
            print(f"[{em.spam_score:.1f}] {em.subject[:50]}")
            print(f"       From: {em.sender[:40]}")
            print(f"       Reason: {em.spam_reason}")
            print()

    print("\n--- SUSPICIOUS (0.3 - 0.5) ---")
    for em in emails:
        if 0.3 <= em.spam_score < 0.5:
            print(f"[{em.spam_score:.1f}] {em.subject[:50]}")
            print(f"       From: {em.sender[:40]}")
            print(f"       LLM: {em.llm_verdict}")
            print()

    print("\n--- SUMMARY ---")
    print(f"Total: {len(emails)} | Spam: {spam_count} | Suspicious: {suspicious} | Clean: {clean}")

    # Move spam if requested
    if args.move_spam and spam_count > 0:
        print(f"\nMoving {spam_count} spam emails to Bulk Mail...")
        try:
            imap = imaplib.IMAP4_SSL(IMAP_SERVER, 993)
            imap.login(YAHOO_EMAIL, YAHOO_PASSWORD)
            imap.select('INBOX')

            moved = 0
            for em in emails:
                if em.spam_score >= 0.5:
                    if move_to_spam(imap, em.uid):
                        moved += 1
                        print(f"  Moved: {em.subject[:40]}")

            imap.logout()
            print(f"Moved {moved}/{spam_count} emails")
        except Exception as e:
            print(f"Error moving emails: {e}")


if __name__ == '__main__':
    main()
