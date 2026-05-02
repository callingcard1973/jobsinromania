#!/usr/bin/env python3
"""
Inbox Monitor - Track email responses for service inquiries.

Monitors Gmail inbox for responses to sent inquiries and tracks status.

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/inbox_monitor.py --account fruitnature4@gmail.com --subject "praguri" --output /opt/TINICHIGII/raspunsuri.csv
    python3 /opt/ACTIVE/INFRA/SKILLS/inbox_monitor.py --account fruitnature4@gmail.com --since 2026-01-10
    python3 /opt/ACTIVE/INFRA/SKILLS/inbox_monitor.py --status /opt/TINICHIGII/raspunsuri.csv

Author: Claude Code
"""

import os
import sys
import csv
import argparse
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
from typing import List, Dict, Optional

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, clean_text

# Load env
from dotenv import load_dotenv
load_dotenv("/opt/ACTIVE/EMAIL/CAMPAIGNS/.env")


class InboxMonitor:
    """Monitor inbox for email responses."""

    def __init__(self, email_addr: str, password: str = None):
        self.email = email_addr
        self.password = password or os.getenv(f"GMAIL_{email_addr.split('@')[0].upper()}_APP_PASSWORD")
        self.imap = None
        self.results: List[Dict] = []

    def connect(self) -> bool:
        """Connect to Gmail IMAP."""
        try:
            self.imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            self.imap.login(self.email, self.password)
            print(f"Connected to {self.email}")
            return True
        except Exception as e:
            print(f"EROARE conectare: {e}")
            return False

    def disconnect(self):
        """Disconnect from IMAP."""
        if self.imap:
            try:
                self.imap.logout()
            except:
                pass

    def decode_subject(self, msg) -> str:
        """Decode email subject."""
        subject = msg.get("Subject", "")
        if subject:
            decoded = decode_header(subject)
            parts = []
            for data, charset in decoded:
                if isinstance(data, bytes):
                    parts.append(data.decode(charset or 'utf-8', errors='ignore'))
                else:
                    parts.append(str(data))
            return ' '.join(parts)
        return ""

    def decode_from(self, msg) -> tuple:
        """Decode sender email and name."""
        from_header = msg.get("From", "")
        if '<' in from_header:
            name = from_header.split('<')[0].strip().strip('"')
            email_addr = from_header.split('<')[1].rstrip('>')
        else:
            name = ""
            email_addr = from_header
        return to_ascii(name), email_addr.lower()

    def get_body(self, msg) -> str:
        """Extract email body text."""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or 'utf-8'
                        body = payload.decode(charset, errors='ignore')
                        break
                    except:
                        pass
        else:
            try:
                payload = msg.get_payload(decode=True)
                charset = msg.get_content_charset() or 'utf-8'
                body = payload.decode(charset, errors='ignore')
            except:
                pass
        return clean_text(body, 500)

    def search_inbox(self, subject_filter: str = None, since_date: str = None,
                     from_filter: str = None) -> List[Dict]:
        """Search inbox for matching emails."""
        results = []

        if not self.imap:
            print("Nu sunt conectat la IMAP")
            return results

        self.imap.select("INBOX")

        # Build search criteria
        criteria = []
        if since_date:
            criteria.append(f'SINCE {since_date}')
        if subject_filter:
            criteria.append(f'SUBJECT "{subject_filter}"')
        if from_filter:
            criteria.append(f'FROM "{from_filter}"')

        search_str = ' '.join(criteria) if criteria else 'ALL'
        print(f"Cautare: {search_str}")

        status, messages = self.imap.search(None, search_str)
        if status != "OK":
            print(f"Eroare cautare: {status}")
            return results

        msg_ids = messages[0].split()
        print(f"Gasite: {len(msg_ids)} emailuri")

        for msg_id in msg_ids[-50:]:  # Limit to last 50
            try:
                status, msg_data = self.imap.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                name, from_email = self.decode_from(msg)
                subject = self.decode_subject(msg)
                date_str = msg.get("Date", "")
                body = self.get_body(msg)

                # Parse date
                try:
                    date_parsed = email.utils.parsedate_to_datetime(date_str)
                    date_formatted = date_parsed.strftime("%Y-%m-%d %H:%M")
                except:
                    date_formatted = date_str[:20]

                results.append({
                    'data': date_formatted,
                    'de_la': from_email,
                    'nume': name,
                    'subiect': to_ascii(subject)[:100],
                    'continut': body[:300],
                    'status': 'NOU'
                })
            except Exception as e:
                print(f"Eroare procesare email: {e}")

        self.results = results
        return results

    def save_csv(self, output_path: str):
        """Save results to CSV."""
        if not self.results:
            print("Nu sunt rezultate de salvat")
            return

        fieldnames = ['data', 'de_la', 'nume', 'subiect', 'continut', 'status']

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in self.results:
                writer.writerow(r)

        print(f"Salvat: {output_path} ({len(self.results)} randuri)")

    def match_with_sent(self, sent_csv: str) -> Dict[str, str]:
        """Match responses with sent emails."""
        matches = {}

        if not os.path.exists(sent_csv):
            return matches

        # Load sent emails
        sent_emails = set()
        try:
            with open(sent_csv, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    email_col = row.get('Email') or row.get('email') or ''
                    if email_col:
                        sent_emails.add(email_col.lower().strip())
        except Exception as e:
            print(f"Eroare citire sent CSV: {e}")
            return matches

        # Match with responses
        for r in self.results:
            from_email = r.get('de_la', '').lower()
            if from_email in sent_emails:
                matches[from_email] = r.get('status', 'RASPUNS')

        print(f"Potriviri: {len(matches)} din {len(sent_emails)} trimise")
        return matches

    def generate_report(self, sent_csv: str = None) -> str:
        """Generate status report."""
        lines = []
        lines.append(f"# Raport Raspunsuri - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"\nTotal raspunsuri gasite: {len(self.results)}")

        if sent_csv and os.path.exists(sent_csv):
            matches = self.match_with_sent(sent_csv)
            lines.append(f"Potriviri cu emailuri trimise: {len(matches)}")

        lines.append("\n## Raspunsuri Recente\n")
        lines.append("| Data | De la | Subiect |")
        lines.append("|------|-------|---------|")

        for r in self.results[:20]:
            data = r.get('data', '-')[:16]
            de_la = r.get('de_la', '-')[:30]
            subiect = r.get('subiect', '-')[:40]
            lines.append(f"| {data} | {de_la} | {subiect} |")

        return '\n'.join(lines)


def show_status(csv_path: str):
    """Show status of tracked responses."""
    if not os.path.exists(csv_path):
        print(f"Fisier inexistent: {csv_path}")
        return

    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"\n=== Status Raspunsuri: {csv_path} ===\n")
    print(f"Total: {len(rows)} raspunsuri\n")

    for r in rows[:20]:
        data = r.get('data', '-')[:16]
        de_la = r.get('de_la', '-')[:35]
        status = r.get('status', '-')
        print(f"  {data}  {de_la:<35}  [{status}]")

    if len(rows) > 20:
        print(f"\n  ... si inca {len(rows) - 20} raspunsuri")


def main():
    parser = argparse.ArgumentParser(description='Monitor inbox pentru raspunsuri')
    parser.add_argument('--account', help='Email account (ex: fruitnature4@gmail.com)')
    parser.add_argument('--password', help='App password (sau din .env)')
    parser.add_argument('--subject', help='Filtru subiect')
    parser.add_argument('--since', help='De la data (YYYY-MM-DD)')
    parser.add_argument('--from-filter', help='Filtru expeditor')
    parser.add_argument('--output', help='Output CSV path')
    parser.add_argument('--sent-csv', help='CSV cu emailuri trimise (pentru matching)')
    parser.add_argument('--status', help='Arata status fisier CSV existent')

    args = parser.parse_args()

    # Status mode
    if args.status:
        show_status(args.status)
        return

    # Monitor mode
    if not args.account:
        print("EROARE: Specifica --account sau --status")
        parser.print_help()
        sys.exit(1)

    # Get password from env
    password = args.password
    if not password:
        account_key = args.account.split('@')[0].upper().replace('.', '_')
        password = os.getenv(f"GMAIL_{account_key}_APP_PASSWORD")
        if not password:
            password = os.getenv("GMAIL_APP_PASSWORD")

    if not password:
        print(f"EROARE: Nu am gasit parola pentru {args.account}")
        print("Seteaza GMAIL_<ACCOUNT>_APP_PASSWORD in /opt/ACTIVE/EMAIL/CAMPAIGNS/.env")
        sys.exit(1)

    # Default since date (7 days ago)
    since_date = args.since
    if not since_date:
        since_dt = datetime.now() - timedelta(days=7)
        since_date = since_dt.strftime("%d-%b-%Y")
    elif '-' in args.since and len(args.since) == 10:
        # Convert YYYY-MM-DD to DD-Mon-YYYY
        dt = datetime.strptime(args.since, "%Y-%m-%d")
        since_date = dt.strftime("%d-%b-%Y")

    monitor = InboxMonitor(args.account, password)

    if not monitor.connect():
        sys.exit(1)

    try:
        results = monitor.search_inbox(
            subject_filter=args.subject,
            since_date=since_date,
            from_filter=args.from_filter
        )

        if results:
            # Save CSV
            if args.output:
                monitor.save_csv(args.output)

            # Match with sent
            if args.sent_csv:
                monitor.match_with_sent(args.sent_csv)

            # Print report
            print("\n" + monitor.generate_report(args.sent_csv))
        else:
            print("\nNu am gasit emailuri matching.")

    finally:
        monitor.disconnect()


if __name__ == "__main__":
    main()
