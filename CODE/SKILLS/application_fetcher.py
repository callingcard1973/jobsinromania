#!/usr/bin/env python3
"""
Application Fetcher Skill

Fetches job applications from all configured email inboxes:
- A2 Hosting domains (10 accounts)
- Gmail (2 accounts)
- Yahoo (2 accounts)

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/application_fetcher.py                    # Fetch from all
    python3 /opt/ACTIVE/INFRA/SKILLS/application_fetcher.py --days 7           # Last 7 days
    python3 /opt/ACTIVE/INFRA/SKILLS/application_fetcher.py --account BUILDJOBS # Single account
    python3 /opt/ACTIVE/INFRA/SKILLS/application_fetcher.py --stats            # Show stats only

Output: /opt/ACTIVE/OPENDATA/DATA/APPLICATIONS/<CAMPAIGN>/
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
import os
import json
import re
import argparse

from skills_common import to_ascii, get_a2_password

# Configuration
# A2 passwords loaded per-domain from a2_smtp_credentials.json
# DO NOT hardcode passwords - use get_a2_password(domain)

A2_ACCOUNTS = [
    ("office@buildjobs.eu", "mail.buildjobs.eu", "BUILDJOBS"),
    ("office@factoryjobs.eu", "mail.factoryjobs.eu", "FACTORYJOBS"),
    ("office@warehouseworkers.eu", "mail.warehouseworkers.eu", "WAREHOUSE"),
    ("office@interjob.ro", "mail.interjob.ro", "INTERJOB"),
    ("office@mivromania.info", "mail.mivromania.info", "HORECA"),
    ("office@mivromania.online", "mail.mivromania.online", "MIV_ONLINE"),
    ("office@careworkers.eu", "mail.careworkers.eu", "CAREWORKERS"),
    ("office@cifn.info", "mail.cifn.info", "CIFN"),
    ("office@nepalezi.com", "mail.nepalezi.com", "NEPALEZI"),
    ("office@expatsinromania.org", "mail.expatsinromania.org", "EXPATS"),
]

GMAIL_ACCOUNTS = [
    ("manpower.dristor@gmail.com", "tbdh pycf vbxo eung", "GMAIL_MANPOWER"),
    ("manpowerdristor@gmail.com", "dmrsuqiudvqtrpzu", "GMAIL_MANPOWER2"),
]

YAHOO_ACCOUNTS = [
    ("secretariatagentieasia@yahoo.com", "tjchtpebagichoxz", "YAHOO_SECRETARIAT"),
    ("apaminerala@yahoo.com", "fmlytelcixsizgeh", "YAHOO_APAMINERALA"),
]

APPS_BASE = "/opt/ACTIVE/OPENDATA/DATA/APPLICATIONS"

APPLICATION_KEYWORDS = [
    "cv", "resume", "candidatura", "aplicare", "application", "job", "pozitie",
    "angajare", "loc de munca", "work", "employment", "interview", "experienta",
    "available", "disponibil", "worker", "muncitor", "apply", "attached cv",
    "looking for work", "caut lucru", "factory", "warehouse", "construction"
]


def decode_str(s: str) -> str:
    """Decode email header with robust encoding handling."""
    if not s:
        return ""
    try:
        decoded = decode_header(s)
    except Exception:
        return str(s)
    result = ""
    for part, enc in decoded:
        if isinstance(part, bytes):
            try:
                if enc and enc.lower() not in ['unknown-8bit', 'unknown']:
                    result += part.decode(enc, errors="ignore")
                else:
                    result += part.decode("utf-8", errors="ignore")
            except (LookupError, UnicodeDecodeError):
                result += part.decode("utf-8", errors="ignore")
        else:
            result += str(part)
    return result


def is_application(subject: str, body: str, attachments: list) -> bool:
    """Check if email is a job application."""
    text = f"{subject} {body}".lower()

    # Has CV/resume attachment
    for att in attachments:
        name = att.get("filename", "").lower()
        if any(x in name for x in ["cv", "resume", "lebenslauf", "curriculum"]):
            return True
        if name.endswith((".pdf", ".doc", ".docx")):
            return True

    # Has application keywords (need 2+)
    keyword_count = sum(1 for kw in APPLICATION_KEYWORDS if kw in text)
    if keyword_count >= 2:
        return True

    return False


def get_email_body(msg) -> str:
    """Extract email body text."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                try:
                    charset = part.get_content_charset() or "utf-8"
                    if charset.lower() in ['unknown-8bit', 'unknown']:
                        charset = 'utf-8'
                    payload = part.get_payload(decode=True)
                    if payload:
                        body += payload.decode(charset, errors="ignore")
                except (LookupError, UnicodeDecodeError):
                    payload = part.get_payload(decode=True)
                    if payload:
                        body += payload.decode("utf-8", errors="ignore")
    else:
        try:
            charset = msg.get_content_charset() or "utf-8"
            if charset.lower() in ['unknown-8bit', 'unknown']:
                charset = 'utf-8'
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode(charset, errors="ignore")
        except (LookupError, UnicodeDecodeError):
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode("utf-8", errors="ignore")
    return body


def get_attachments(msg) -> list:
    """Extract attachment metadata."""
    attachments = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            filename = part.get_filename()
            if filename:
                attachments.append({
                    "filename": decode_str(filename),
                    "content_type": part.get_content_type(),
                    "size": len(part.get_payload(decode=True) or b"")
                })
    return attachments


def save_application(msg, sender: str, subject: str, body: str, attachments: list,
                     apps_dir: str, campaign: str) -> bool:
    """Save application to disk."""
    os.makedirs(apps_dir, exist_ok=True)

    # Create folder name (ASCII safe)
    safe_sender = to_ascii(re.sub(r'[^\w]', '_', sender.split('@')[0])[:20])
    safe_subject = to_ascii(re.sub(r'[^\w]', '_', subject)[:30])
    date_str = datetime.now().strftime("%Y-%m-%d")
    folder_name = f"{date_str}_{safe_sender}_{safe_subject}"
    folder_path = os.path.join(apps_dir, folder_name)

    # Skip if already exists
    if os.path.exists(folder_path):
        return False

    os.makedirs(folder_path, exist_ok=True)

    # Save metadata
    metadata = {
        "sender": sender,
        "subject": subject,
        "date": msg.get("Date", ""),
        "campaign": campaign,
        "attachments": [a["filename"] for a in attachments],
        "saved_at": datetime.now().isoformat()
    }
    with open(os.path.join(folder_path, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # Save body
    with open(os.path.join(folder_path, "body.txt"), "w") as f:
        f.write(body)

    # Save attachments
    if msg.is_multipart():
        for part in msg.walk():
            filename = part.get_filename()
            if filename:
                safe_filename = to_ascii(re.sub(r'[^\w\.]', '_', decode_str(filename)))
                data = part.get_payload(decode=True)
                if data:
                    with open(os.path.join(folder_path, safe_filename), "wb") as f:
                        f.write(data)

    return True


def fetch_inbox(email_addr: str, password: str, server: str, campaign: str,
                days: int = 30) -> tuple:
    """Fetch applications from a single inbox."""
    apps_dir = os.path.join(APPS_BASE, campaign)

    try:
        mail = imaplib.IMAP4_SSL(server)
        mail.login(email_addr, password)
        mail.select("INBOX")
    except Exception as e:
        print(f"  [ERROR] {str(e)[:50]}")
        return 0, 0, 0

    since_date = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
    _, data = mail.search(None, f'(SINCE "{since_date}")')

    email_ids = data[0].split()
    total_emails = len(email_ids)

    apps_saved = 0
    errors = 0

    for email_id in email_ids:
        try:
            _, msg_data = mail.fetch(email_id, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            sender = decode_str(msg.get("From", ""))
            subject = decode_str(msg.get("Subject", ""))
            body = get_email_body(msg)
            attachments = get_attachments(msg)

            if is_application(subject, body, attachments):
                saved = save_application(msg, sender, subject, body, attachments,
                                        apps_dir, campaign)
                if saved:
                    apps_saved += 1
                    print(f"  [+] {sender.split('<')[0][:25]}: {subject[:35]}")
        except Exception as e:
            errors += 1

    mail.logout()
    return apps_saved, errors, total_emails


def get_all_accounts():
    """Return all configured accounts."""
    accounts = []
    for email_addr, server, campaign in A2_ACCOUNTS:
        # Get password per-domain from credentials file
        domain = email_addr.split('@')[1] if '@' in email_addr else server.replace('mail.', '')
        password = get_a2_password(domain)
        if password:
            accounts.append((email_addr, password, server, campaign, "a2"))
        else:
            print(f"[SKIP] No password for {domain} in a2_smtp_credentials.json")
    for email_addr, password, campaign in GMAIL_ACCOUNTS:
        accounts.append((email_addr, password, "imap.gmail.com", campaign, "gmail"))
    for email_addr, password, campaign in YAHOO_ACCOUNTS:
        accounts.append((email_addr, password, "imap.mail.yahoo.com", campaign, "yahoo"))
    return accounts


def show_stats():
    """Show application statistics."""
    print("=" * 60)
    print("APPLICATION STATISTICS")
    print("=" * 60)

    total = 0
    if os.path.exists(APPS_BASE):
        for campaign in sorted(os.listdir(APPS_BASE)):
            campaign_path = os.path.join(APPS_BASE, campaign)
            if os.path.isdir(campaign_path):
                count = len([d for d in os.listdir(campaign_path)
                           if os.path.isdir(os.path.join(campaign_path, d))])
                if count > 0:
                    print(f"  {campaign}: {count}")
                    total += count

    print(f"\nTotal: {total} applications")
    print(f"Path: {APPS_BASE}/")


def main():
    parser = argparse.ArgumentParser(description="Fetch job applications from email inboxes")
    parser.add_argument("--days", type=int, default=30, help="Days to look back (default: 30)")
    parser.add_argument("--account", type=str, help="Fetch from specific account only")
    parser.add_argument("--stats", action="store_true", help="Show stats only")
    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    print("=" * 60)
    print("APPLICATION FETCHER")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Days: {args.days}")
    print("=" * 60)

    accounts = get_all_accounts()
    results = []

    for email_addr, password, server, campaign, provider in accounts:
        if args.account and args.account.upper() != campaign:
            continue

        print(f"\n[{campaign}] {email_addr}...")
        saved, errors, total = fetch_inbox(email_addr, password, server, campaign, args.days)
        results.append((campaign, saved, errors, total))
        print(f"  Emails: {total}, Applications: {saved}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    total_saved = 0
    for campaign, saved, errors, total in results:
        if saved > 0:
            print(f"  {campaign}: {saved} applications")
            total_saved += saved

    print(f"\nTotal: {total_saved} applications saved")
    print(f"Path: {APPS_BASE}/")


if __name__ == "__main__":
    main()
