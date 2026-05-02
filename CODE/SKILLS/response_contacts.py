#!/usr/bin/env python3
"""
Response Contacts Extractor

Scans all email accounts for responses (not bounces/automated),
extracts contact info, and exports to Google Contacts CSV format.

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/response_contacts.py                    # Scan all, last 30 days
    python3 /opt/ACTIVE/INFRA/SKILLS/response_contacts.py --days 7           # Last 7 days
    python3 /opt/ACTIVE/INFRA/SKILLS/response_contacts.py --output contacts.csv
    python3 /opt/ACTIVE/INFRA/SKILLS/response_contacts.py --account gmail    # Only Gmail accounts
    python3 /opt/ACTIVE/INFRA/SKILLS/response_contacts.py --test             # Show what would be found
"""

import imaplib
import email
from email.header import decode_header
from email.utils import parseaddr
import re
import csv
import argparse
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

# Load env
from dotenv import load_dotenv
load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

# Shared imports
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
try:
    from skills_common import to_ascii, get_a2_password
except ImportError:
    def to_ascii(text):
        if not text:
            return ''
        normalized = unicodedata.normalize('NFKD', str(text))
        return normalized.encode('ascii', 'ignore').decode('ascii').strip()
    def get_a2_password(domain):
        return os.getenv('A2_EMAIL_PASSWORD', '')

# ============= EMAIL ACCOUNTS =============
# Format: (email, password, imap_server, label)
# A2 passwords loaded per-domain from a2_smtp_credentials.json

def _build_accounts():
    """Build accounts list with passwords from credentials file."""
    accounts = []
    # A2 Hosting - all passwords from credentials file
    a2_domains = [
        ("buildjobs.eu", "A2-buildjobs"),
        ("factoryjobs.eu", "A2-factoryjobs"),
        ("warehouseworkers.eu", "A2-warehouse"),
        ("interjob.ro", "A2-interjob"),
        ("mivromania.info", "A2-mivromania"),
        ("mivromania.online", "A2-mivromania-online"),
        ("careworkers.eu", "A2-careworkers"),
        ("cifn.info", "A2-cifn"),
        ("nepalezi.com", "A2-nepalezi"),
        ("expatsinromania.org", "A2-expats"),
        ("horecaworkers.eu", "A2-horeca"),
        ("meatworkers.eu", "A2-meatworkers"),
        ("electricjobs.eu", "A2-electricjobs"),
        ("mechanicjobs.eu", "A2-mechanicjobs"),
        ("farmworkers.eu", "A2-farmworkers"),
    ]
    for domain, label in a2_domains:
        pw = get_a2_password(domain)
        if pw:
            accounts.append((f"office@{domain}", pw, f"mail.{domain}", label))

    # Gmail accounts (app passwords - not in credentials file)
    accounts.append(('manpowerdristor@gmail.com', os.getenv('GMAIL_APP_PASSWORD', 'dmrsuqiudvqtrpzu'), 'imap.gmail.com', 'Gmail-manpowerdristor'))
    accounts.append(('manpower.dristor@gmail.com', os.getenv('GMAIL_MANPOWER_APP_PASSWORD', 'tbdh pycf vbxo eung'), 'imap.gmail.com', 'Gmail-manpower.dristor'))
    accounts.append(('elena.manpower.dristor@gmail.com', os.getenv('GMAIL_ELENA_PASSWORD', 'wmfnpikkcierkmrq'), 'imap.gmail.com', 'Gmail-elena'))
    accounts.append(('expatsinromania@gmail.com', os.getenv('GMAIL_EXPATS_PASSWORD', 'hxdn mukn jloe shkk'), 'imap.gmail.com', 'Gmail-expats'))
    accounts.append(('cumparlegume@gmail.com', os.getenv('GMAIL_CUMPARLEGUME_PASSWORD', 'iggy urti wmze znqo'), 'imap.gmail.com', 'Gmail-cumparlegume'))
    accounts.append(('casafaurbucuresti@gmail.com', os.getenv('GMAIL_CASAFAUR_PASSWORD', 'zlfb mbqf xiki mcbw'), 'imap.gmail.com', 'Gmail-casafaur'))
    # Yahoo accounts
    accounts.append(('secretariatagentieasia@yahoo.com', os.getenv('YAHOO_APP_PASSWORD', 'tjchtpebagichoxz'), 'imap.mail.yahoo.com', 'Yahoo-secretariat'))
    accounts.append(('apaminerala@yahoo.com', os.getenv('YAHOO_APAMINERALA_APP_PASSWORD', 'fmlytelcixsizgeh'), 'imap.mail.yahoo.com', 'Yahoo-apaminerala'))
    return accounts

ACCOUNTS = _build_accounts()

# ============= BOUNCE/AUTO DETECTION =============
BOUNCE_SENDERS = [
    'mailer-daemon', 'postmaster', 'mail delivery', 'delivery notification',
    'noreply', 'no-reply', 'donotreply', 'do-not-reply', 'auto-reply',
    'autoreply', 'automatic reply', 'out of office', 'vacation reply',
    'undeliverable', 'delivery failed', 'mail-daemon', 'bounce',
    'MAILER-DAEMON', 'Mail Delivery Subsystem'
]

BOUNCE_SUBJECTS = [
    'undeliverable', 'delivery', 'returned', 'failure', 'failed',
    'rejected', 'bounce', 'out of office', 'automatic reply',
    'auto-reply', 'vacation', 'away from office', 'abwesend',
    'message not delivered', 'delivery status', 'mail delivery failed'
]

# ============= CONTACT EXTRACTION =============
PHONE_PATTERNS = [
    r'(?:tel|phone|mobile|cell|fax|whatsapp|viber)[\s.:]*([+\d\s\-()]{8,20})',
    r'(?:^|[\s,;])(\+?\d{1,4}[\s\-]?\d{2,4}[\s\-]?\d{3,4}[\s\-]?\d{2,4})(?:$|[\s,;])',
    r'(\+\d{10,15})',
    r'(\d{3}[\s\-]\d{3}[\s\-]\d{4})',  # 123-456-7890
]

def decode_str(s):
    """Decode email header string."""
    if not s:
        return ''
    decoded = []
    for part, encoding in decode_header(s):
        if isinstance(part, bytes):
            try:
                decoded.append(part.decode(encoding or 'utf-8', errors='replace'))
            except:
                decoded.append(part.decode('utf-8', errors='replace'))
        else:
            decoded.append(part)
    return ' '.join(decoded)

def get_email_body(msg):
    """Extract plain text body from email."""
    body = ''
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == 'text/plain':
                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or 'utf-8'
                    body = payload.decode(charset, errors='replace')
                    break
                except:
                    pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or 'utf-8'
            body = payload.decode(charset, errors='replace')
        except:
            body = str(msg.get_payload())
    return body

def is_bounce_or_auto(from_addr, subject):
    """Check if email is a bounce or auto-reply."""
    from_lower = from_addr.lower()
    subject_lower = subject.lower()

    for pattern in BOUNCE_SENDERS:
        if pattern.lower() in from_lower:
            return True

    for pattern in BOUNCE_SUBJECTS:
        if pattern.lower() in subject_lower:
            return True

    return False

def extract_name_from_email(email_addr):
    """Extract name from email address (before @)."""
    if not email_addr:
        return ''
    local = email_addr.split('@')[0]
    # Clean up common patterns
    local = re.sub(r'[._\-]', ' ', local)
    local = re.sub(r'\d+', '', local)
    parts = local.split()
    return ' '.join(p.capitalize() for p in parts if len(p) > 1)

def extract_phone(text):
    """Extract phone number from text."""
    for pattern in PHONE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            phone = re.sub(r'[^\d+]', '', match.group(1))
            if len(phone) >= 8:
                return phone
    return ''

def extract_company(text, email_domain):
    """Extract company name from text or email domain."""
    # Skip generic domains
    generic_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
                       'yahoo.ro', 'yahoo.co.uk', 'googlemail.com', 'icloud.com',
                       'aol.com', 'protonmail.com', 'mail.ru', 'yandex.ru']

    # Fall back to email domain for business emails
    if email_domain and email_domain.lower() not in generic_domains:
        domain_name = email_domain.split('.')[0]
        # Clean up common patterns
        domain_name = re.sub(r'^(office|info|contact|mail|admin|sales|hr|jobs)$', '', domain_name)
        if domain_name and len(domain_name) > 2:
            return domain_name.replace('-', ' ').replace('_', ' ').title()

    return ''

def parse_email_address(from_header):
    """Parse From header into name and email."""
    name, email_addr = parseaddr(from_header)
    name = decode_str(name)
    return to_ascii(name), email_addr.lower() if email_addr else ''

def scan_account(email_addr, password, imap_server, label, days=30, test_mode=False):
    """Scan single email account for responses."""
    contacts = []

    try:
        mail = imaplib.IMAP4_SSL(imap_server, 993)
        mail.login(email_addr, password)
        mail.select('INBOX')

        since_date = (datetime.now() - timedelta(days=days)).strftime('%d-%b-%Y')
        status, messages = mail.search(None, 'SINCE', since_date)

        if status != 'OK':
            return contacts

        msg_ids = messages[0].split()
        print(f"  {label}: {len(msg_ids)} emails to scan")

        for msg_id in msg_ids:
            try:
                status, msg_data = mail.fetch(msg_id, '(RFC822)')
                if status != 'OK':
                    continue

                msg = email.message_from_bytes(msg_data[0][1])
                from_header = msg.get('From', '')
                subject = decode_str(msg.get('Subject', ''))
                date_str = msg.get('Date', '')

                name, sender_email = parse_email_address(from_header)

                # Skip bounces and auto-replies
                if is_bounce_or_auto(from_header, subject):
                    continue

                # Skip if from our own domains
                our_domains = ['interjob.ro', 'buildjobs.eu', 'factoryjobs.eu', 'careworkers.eu',
                              'mivromania.info', 'mivromania.online', 'horecaworkers.eu',
                              'expatsinromania.org', 'nepalezi.com', 'cifn.info']
                if any(d in sender_email for d in our_domains):
                    continue

                # Get body for additional extraction
                body = get_email_body(msg)

                # Extract contact info
                phone = extract_phone(body)
                email_domain = sender_email.split('@')[1] if '@' in sender_email else ''
                company = extract_company(body, email_domain)

                # If no name from header, try to extract from email
                if not name:
                    name = extract_name_from_email(sender_email)

                # Split name into first/last
                name_parts = name.split() if name else []
                given_name = name_parts[0] if name_parts else ''
                family_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

                contact = {
                    'name': to_ascii(name),
                    'given_name': to_ascii(given_name),
                    'family_name': to_ascii(family_name),
                    'email': sender_email,
                    'phone': phone,
                    'company': company,
                    'subject': to_ascii(subject[:100]),
                    'date': date_str,
                    'source_mailbox': label,
                    'body_preview': to_ascii(body[:200].replace('\n', ' ').replace('\r', ''))
                }

                contacts.append(contact)

                if test_mode and len(contacts) >= 5:
                    break

            except Exception as e:
                continue

        mail.close()
        mail.logout()

    except Exception as e:
        print(f"  {label}: ERROR - {str(e)[:50]}")

    return contacts

def export_google_csv(contacts, output_path):
    """Export contacts to Google Contacts CSV format."""
    # Google Contacts CSV headers
    headers = [
        'Name', 'Given Name', 'Family Name',
        'E-mail 1 - Type', 'E-mail 1 - Value',
        'Phone 1 - Type', 'Phone 1 - Value',
        'Organization 1 - Name',
        'Notes'
    ]

    seen_emails = set()
    unique_contacts = []

    for c in contacts:
        if c['email'] and c['email'] not in seen_emails:
            seen_emails.add(c['email'])
            unique_contacts.append(c)

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for c in unique_contacts:
            row = [
                c['name'] or c['email'].split('@')[0],
                c['given_name'],
                c['family_name'],
                'Work',
                c['email'],
                'Work' if c['phone'] else '',
                c['phone'],
                c['company'],
                f"Source: {c['source_mailbox']} | Subject: {c['subject'][:50]}"
            ]
            writer.writerow(row)

    return len(unique_contacts)

def export_detailed_csv(contacts, output_path):
    """Export all contact details (for reference)."""
    headers = ['name', 'email', 'phone', 'company', 'subject', 'date', 'source_mailbox', 'body_preview']

    seen_emails = set()
    unique_contacts = []

    for c in contacts:
        if c['email'] and c['email'] not in seen_emails:
            seen_emails.add(c['email'])
            unique_contacts.append(c)

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(unique_contacts)

    return len(unique_contacts)

def main():
    parser = argparse.ArgumentParser(description='Extract contacts from email responses')
    parser.add_argument('--days', type=int, default=30, help='Days to scan (default: 30)')
    parser.add_argument('--output', '-o', default='/opt/ACTIVE/OPENDATA/DATA/response_contacts.csv', help='Output CSV path')
    parser.add_argument('--account', help='Filter accounts: gmail, yahoo, a2, or specific label')
    parser.add_argument('--test', action='store_true', help='Test mode (5 emails per account)')
    parser.add_argument('--detailed', action='store_true', help='Also export detailed CSV')
    args = parser.parse_args()

    print(f"=== Response Contacts Extractor ===")
    print(f"Scanning last {args.days} days")
    print()

    # Filter accounts if specified
    accounts = ACCOUNTS
    if args.account:
        filter_lower = args.account.lower()
        accounts = [a for a in ACCOUNTS if filter_lower in a[3].lower()]
        if not accounts:
            print(f"No accounts match filter: {args.account}")
            return

    all_contacts = []

    for email_addr, password, imap_server, label in accounts:
        contacts = scan_account(email_addr, password, imap_server, label,
                               days=args.days, test_mode=args.test)
        all_contacts.extend(contacts)
        if contacts:
            print(f"    Found {len(contacts)} responses")

    print()
    print(f"Total responses found: {len(all_contacts)}")

    if all_contacts:
        # Export Google Contacts format
        count = export_google_csv(all_contacts, args.output)
        print(f"Exported {count} unique contacts to: {args.output}")

        if args.detailed:
            detailed_path = args.output.replace('.csv', '_detailed.csv')
            export_detailed_csv(all_contacts, detailed_path)
            print(f"Detailed export: {detailed_path}")

        # Show sample
        print()
        print("=== Sample Contacts ===")
        for c in all_contacts[:5]:
            print(f"  {c['name'] or '(no name)'} <{c['email']}> - {c['company'] or '(no company)'}")
    else:
        print("No responses found.")

if __name__ == '__main__':
    main()
