#!/usr/bin/env python3
"""
CV Processor - Full Pipeline

1. Fetches CVs from all email inboxes
2. Saves to /opt/ACTIVE/OPENDATA/DATA/CV_INBOX/
3. Extracts info (name, phone, email, country)
4. Moves processed emails to "Processed" folder (or deletes)
5. Creates master CSV for later use

Usage:
    python3 cv_processor.py                    # Full pipeline
    python3 cv_processor.py --fetch-only       # Just fetch, don't process
    python3 cv_processor.py --extract-only     # Just extract from saved CVs
    python3 cv_processor.py --stats            # Show statistics
    python3 cv_processor.py --export           # Export master CSV
    python3 cv_processor.py --cleanup          # Delete processed from inbox
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

try:
    import sys as _sys, os as _os
    for _p in ["/opt/ACTIVE/INFRA", r"D:\MEMORY\CODE\POSTHOG"]:
        if _os.path.exists(_p) and _p not in _sys.path:
            _sys.path.insert(0, _p)
    from posthog_track import track_applicant, track_solonet_order, track_cv_generated, ph_shutdown as _ph_shutdown
    _PH = True
except Exception:
    _PH = False
    def track_applicant(*a, **kw): pass
    def track_solonet_order(*a, **kw): pass
    def track_cv_generated(*a, **kw): pass
    def _ph_shutdown(): pass

import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
import os
import json
import re
import argparse
import csv
import hashlib
from pathlib import Path

from skills_common import to_ascii, get_a2_password

# ============== CONFIGURATION ==============

# A2 passwords loaded per-domain from a2_smtp_credentials.json
# DO NOT hardcode passwords - use get_a2_password(domain)

def _build_accounts():
    """Build accounts list with passwords from credentials file."""
    accounts = []
    # A2 Hosting - all passwords from credentials file
    a2_domains = [
        ("buildjobs.eu", "BUILDJOBS"),
        ("factoryjobs.eu", "FACTORYJOBS"),
        ("warehouseworkers.eu", "WAREHOUSE"),
        ("interjob.ro", "INTERJOB"),
        ("mivromania.info", "HORECA"),
        ("mivromania.online", "MIV_ONLINE"),
        ("careworkers.eu", "CAREWORKERS"),
        ("cifn.info", "CIFN"),
        ("nepalezi.com", "NEPALEZI"),
        ("expatsinromania.org", "EXPATS"),
    ]
    for domain, label in a2_domains:
        pw = get_a2_password(domain)
        if pw:
            accounts.append((f"office@{domain}", pw, f"mail.{domain}", label))

    # Gmail (app passwords - not in credentials file)
    accounts.append(("manpower.dristor@gmail.com", "tbdh pycf vbxo eung", "imap.gmail.com", "GMAIL1"))
    accounts.append(("manpowerdristor@gmail.com", "dmrsuqiudvqtrpzu", "imap.gmail.com", "GMAIL2"))
    # Yahoo
    accounts.append(("apaminerala@yahoo.com", "fmlytelcixsizgeh", "imap.mail.yahoo.com", "YAHOO"))
    return accounts

ACCOUNTS = _build_accounts()

CV_INBOX = Path("/opt/ACTIVE/OPENDATA/DATA/CV_INBOX")
MASTER_CSV = CV_INBOX / "master_applicants.csv"
PROCESSED_DB = CV_INBOX / ".processed_ids.json"

# Keywords for job applications
APPLICATION_KEYWORDS = [
    "cv", "resume", "candidatura", "aplicare", "application", "job",
    "angajare", "work", "employment", "worker", "muncitor", "apply",
    "looking for work", "caut lucru", "factory", "warehouse", "construction",
    "butcher", "meat", "driver", "nurse", "caregiver", "cleaner"
]

# Phone patterns
PHONE_PATTERNS = [
    r'\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
    r'\b\d{10,14}\b',
]

# Email pattern
EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'


def decode_str(s: str) -> str:
    """Decode email header."""
    if not s:
        return ""
    try:
        decoded = decode_header(s)
    except:
        return str(s)
    result = ""
    for part, enc in decoded:
        if isinstance(part, bytes):
            try:
                enc = enc if enc and enc.lower() not in ['unknown-8bit', 'unknown'] else 'utf-8'
                result += part.decode(enc, errors="ignore")
            except:
                result += part.decode("utf-8", errors="ignore")
        else:
            result += str(part)
    return result


def get_email_body(msg) -> str:
    """Extract email body text."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    charset = part.get_content_charset() or "utf-8"
                    payload = part.get_payload(decode=True)
                    if payload:
                        body += payload.decode(charset, errors="ignore")
                except:
                    pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode("utf-8", errors="ignore")
        except:
            pass
    return body


def is_application(subject: str, body: str, has_cv_attachment: bool, sender: str = "") -> bool:
    """Check if email is a job application. STRICT: must have CV attachment."""
    # MUST have CV/resume attachment to be considered
    if not has_cv_attachment:
        return False

    # Combine subject and sender for checking
    check_text = f"{subject} {sender}".lower()

    # Exclude newsletters, invoices, automated emails
    exclude_patterns = [
        # English
        'newsletter', 'unsubscribe', 'weekly digest', 'daily digest',
        'your order', 'invoice', 'receipt', 'confirmation', 'verify',
        'password', 'security', 'notification', 'alert', 'update your',
        'billing', 'payment', 'subscription', 'account statement',
        # Romanian - invoices/bills
        'factura', 'plata', 'extras', 'bancar', 'intretinere', 'nota de plata',
        'chitanta', 'bon fiscal', 'debit', 'sold', 'cont bancar',
        # Known invoice senders
        'engie', 'enel', 'electrica', 'e-on', 'digi', 'telekom', 'vodafone',
        'orange', 'rcs-rds', 'rer sud', 'e-bloc', 'noreply', 'no-reply',
        'donotreply', 'factura@', 'billing@', 'info@engie', 'info@enel'
    ]
    if any(p in check_text for p in exclude_patterns):
        return False

    return True


def extract_phone(text: str) -> str:
    """Extract phone number from text."""
    for pattern in PHONE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            phone = re.sub(r'[^\d+]', '', match.group())
            if len(phone) >= 9:
                return phone
    return ""


def extract_email(text: str) -> str:
    """Extract email from text."""
    match = re.search(EMAIL_PATTERN, text)
    return match.group() if match else ""


def extract_name_from_sender(sender: str) -> str:
    """Extract name from email sender field."""
    # "John Doe <john@email.com>" -> "John Doe"
    if '<' in sender:
        name = sender.split('<')[0].strip().strip('"').strip("'")
        if name:
            return to_ascii(name)
    # john.doe@email.com -> John Doe
    email_part = sender.split('<')[-1].replace('>', '').strip()
    local = email_part.split('@')[0]
    name = local.replace('.', ' ').replace('_', ' ').replace('-', ' ')
    return to_ascii(name.title())


def get_message_id(msg) -> str:
    """Get unique message ID for dedup."""
    msg_id = msg.get("Message-ID", "")
    if msg_id:
        return hashlib.md5(msg_id.encode()).hexdigest()[:16]
    # Fallback: hash of date+from+subject
    combo = f"{msg.get('Date', '')}{msg.get('From', '')}{msg.get('Subject', '')}"
    return hashlib.md5(combo.encode()).hexdigest()[:16]


def load_processed_ids() -> set:
    """Load already processed message IDs."""
    if PROCESSED_DB.exists():
        with open(PROCESSED_DB) as f:
            return set(json.load(f))
    return set()


def save_processed_ids(ids: set):
    """Save processed message IDs."""
    CV_INBOX.mkdir(parents=True, exist_ok=True)
    with open(PROCESSED_DB, 'w') as f:
        json.dump(list(ids), f)


def save_cv(msg, sender: str, subject: str, body: str, campaign: str, msg_id: str) -> dict:
    """Save CV and extract info. Returns applicant dict."""

    # Create folder
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_sender = to_ascii(re.sub(r'[^\w]', '_', sender.split('@')[0])[:20])
    safe_subject = to_ascii(re.sub(r'[^\w]', '_', subject)[:25])
    folder_name = f"{date_str}_{safe_sender}_{safe_subject}"
    folder_path = CV_INBOX / campaign / folder_name

    if folder_path.exists():
        return None  # Already saved

    folder_path.mkdir(parents=True, exist_ok=True)

    # Extract info
    full_text = f"{sender}\n{subject}\n{body}"
    applicant = {
        "id": msg_id,
        "name": extract_name_from_sender(sender),
        "email": extract_email(sender) or extract_email(body),
        "phone": extract_phone(body) or extract_phone(subject),
        "sender": sender,
        "subject": subject,
        "campaign": campaign,
        "date": msg.get("Date", ""),
        "saved_at": datetime.now().isoformat(),
        "folder": str(folder_path),
        "cv_files": []
    }

    # Save attachments
    if msg.is_multipart():
        for part in msg.walk():
            filename = part.get_filename()
            if filename:
                safe_filename = to_ascii(re.sub(r'[^\w\.]', '_', decode_str(filename)))
                # Only save CV-like files
                if safe_filename.lower().endswith(('.pdf', '.doc', '.docx', '.rtf')):
                    data = part.get_payload(decode=True)
                    if data:
                        filepath = folder_path / safe_filename
                        with open(filepath, "wb") as f:
                            f.write(data)
                        applicant["cv_files"].append(safe_filename)

    # Save metadata
    with open(folder_path / "metadata.json", "w") as f:
        json.dump(applicant, f, indent=2, ensure_ascii=False)

    # Save body
    with open(folder_path / "body.txt", "w") as f:
        f.write(body)

    return applicant


def fetch_and_process(account: tuple, days: int, cleanup: bool, processed_ids: set) -> list:
    """Fetch and process CVs from one account."""
    email_addr, password, server, campaign = account
    applicants = []

    try:
        mail = imaplib.IMAP4_SSL(server)
        mail.login(email_addr, password)
        mail.select("INBOX")
    except Exception as e:
        print(f"  [ERROR] {email_addr}: {str(e)[:40]}")
        return []

    since_date = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
    _, data = mail.search(None, f'(SINCE "{since_date}")')
    email_ids = data[0].split()

    new_count = 0
    for email_id in email_ids:
        try:
            _, msg_data = mail.fetch(email_id, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            msg_id = get_message_id(msg)
            if msg_id in processed_ids:
                continue

            sender = decode_str(msg.get("From", ""))
            subject = decode_str(msg.get("Subject", ""))
            body = get_email_body(msg)

            # Check for CV attachments
            has_cv = False
            if msg.is_multipart():
                for part in msg.walk():
                    filename = (part.get_filename() or "").lower()
                    if any(x in filename for x in ['cv', 'resume', 'lebenslauf']) or \
                       filename.endswith(('.pdf', '.doc', '.docx')):
                        has_cv = True
                        break

            if is_application(subject, body, has_cv_attachment=has_cv, sender=sender):
                applicant = save_cv(msg, sender, subject, body, campaign, msg_id)
                if applicant:
                    applicants.append(applicant)
                    processed_ids.add(msg_id)
                    new_count += 1
                    print(f"    [+] {applicant['name'][:20]} - {applicant.get('phone', 'no phone')}")
                    track_cv_generated(sector=campaign.lower() if campaign else "unknown")

                    # Mark as seen and optionally delete
                    if cleanup:
                        mail.store(email_id, '+FLAGS', '\\Seen')
                        mail.store(email_id, '+FLAGS', '\\Deleted')
        except Exception as e:
            pass

    if cleanup:
        mail.expunge()  # Actually delete flagged messages

    mail.logout()

    if new_count > 0:
        print(f"  {campaign}: {new_count} new CVs")

    return applicants


def update_master_csv(applicants: list):
    """Update master CSV with new applicants."""
    CV_INBOX.mkdir(parents=True, exist_ok=True)

    # Load existing
    existing = {}
    if MASTER_CSV.exists():
        with open(MASTER_CSV, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing[row.get('id', '')] = row

    # Add new
    for app in applicants:
        existing[app['id']] = {
            'id': app['id'],
            'name': app['name'],
            'email': app['email'],
            'phone': app['phone'],
            'campaign': app['campaign'],
            'date': app['date'],
            'cv_files': ','.join(app.get('cv_files', [])),
            'folder': app['folder'],
            'saved_at': app['saved_at']
        }

    # Write back
    if existing:
        fieldnames = ['id', 'name', 'email', 'phone', 'campaign', 'date', 'cv_files', 'folder', 'saved_at']
        with open(MASTER_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in sorted(existing.values(), key=lambda x: x.get('saved_at', ''), reverse=True):
                writer.writerow(row)


def show_stats():
    """Show CV statistics."""
    print("=" * 60)
    print("CV PROCESSOR STATISTICS")
    print("=" * 60)

    total = 0
    if CV_INBOX.exists():
        for campaign in sorted(CV_INBOX.iterdir()):
            if campaign.is_dir() and not campaign.name.startswith('.'):
                count = len([d for d in campaign.iterdir() if d.is_dir()])
                if count > 0:
                    print(f"  {campaign.name}: {count}")
                    total += count

    print(f"\nTotal CVs: {total}")
    print(f"Inbox: {CV_INBOX}")

    if MASTER_CSV.exists():
        with open(MASTER_CSV) as f:
            lines = len(f.readlines()) - 1
        print(f"Master CSV: {lines} applicants")
        print(f"  {MASTER_CSV}")

    processed = load_processed_ids()
    print(f"Processed IDs: {len(processed)}")


def main():
    parser = argparse.ArgumentParser(description="CV Processor - fetch, save, extract, cleanup")
    parser.add_argument("--days", type=int, default=7, help="Days to look back (default: 7)")
    parser.add_argument("--fetch-only", action="store_true", help="Just fetch, no extraction")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--export", action="store_true", help="Export master CSV path")
    parser.add_argument("--cleanup", action="store_true", help="Delete processed emails from inbox")
    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    if args.export:
        print(f"Master CSV: {MASTER_CSV}")
        return

    print(f"CV Processor - Fetching last {args.days} days")
    print("=" * 60)
    if args.cleanup:
        print("⚠️  CLEANUP MODE: Will delete processed emails from inbox!")
    print()

    processed_ids = load_processed_ids()
    all_applicants = []

    for account in ACCOUNTS:
        applicants = fetch_and_process(account, args.days, args.cleanup, processed_ids)
        all_applicants.extend(applicants)

    # Save processed IDs
    save_processed_ids(processed_ids)

    # Update master CSV
    if all_applicants:
        update_master_csv(all_applicants)
        print()
        print(f"New CVs saved: {len(all_applicants)}")
        print(f"Master CSV updated: {MASTER_CSV}")
    else:
        print("\nNo new CVs found.")

    print()
    show_stats()
    _ph_shutdown()


if __name__ == "__main__":
    main()
