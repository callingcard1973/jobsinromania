#!/usr/bin/env python3
"""
Gmail Applicant Sorter

Automatically moves job applicant emails to APPLICANTS folder in Gmail.
Keeps inbox clean while preserving all applications.

Usage:
    python3 gmail_applicant_sorter.py                 # Process once
    python3 gmail_applicant_sorter.py --daemon        # Run continuously (every 5 min)
    python3 gmail_applicant_sorter.py --dry-run       # Show what would be moved
    python3 gmail_applicant_sorter.py --stats         # Show folder stats
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import imaplib
import email
from email.header import decode_header
import time
import argparse
from datetime import datetime

# Gmail credentials for manpowerdristor
GMAIL_EMAIL = "manpowerdristor@gmail.com"
GMAIL_PASSWORD = "dmrsuqiudvqtrpzu"  # App password
IMAP_SERVER = "imap.gmail.com"

# Target folder (Gmail label)
APPLICANTS_FOLDER = "APPLICANTS"

# Keywords that identify job applications (subject line only - more precise)
SUBJECT_KEYWORDS = [
    # Form submissions (primary indicator)
    "new submission", "form submission", "contact form", "formspree",
    "new application", "job application", "cv attached", "resume attached",
    # Direct application phrases
    "candidatura", "aplicare pentru", "looking for job", "caut lucru",
    "looking for work in", "i am looking for", "seeking employment",
]

# Keywords for body check (only if subject didn't match)
BODY_KEYWORDS = [
    # Strong indicators of job application
    "attached my cv", "attached cv", "my resume", "job seeker",
    "available for work", "available immediately", "willing to relocate",
    "years of experience", "work permit", "looking for job",
]

# Senders that are always applicants (job portal forms)
APPLICANT_SENDERS = [
    "noreply@formspree.io",
    "formspree",
    "@buildjobs.eu",
    "@careworkers.eu",
    "@electricjobs.eu",
    "@factoryjobs.eu",
    "@farmworkers.eu",
    "@horecaworkers.eu",
    "@meatworkers.eu",
    "@mechanicjobs.eu",
    "@warehouseworkers.eu",
    "@cifn.info",
    "@mivromania.info",
    "@mivromania.online",
    "@nepalezi.com",
    "@interjob.ro",
    "@expatsinromania.org",
]


def decode_str(s):
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


def is_applicant_email(msg):
    """Check if email is a job application."""
    # Check sender FIRST - most reliable
    from_addr = decode_str(msg.get("From", "")).lower()
    for sender in APPLICANT_SENDERS:
        if sender.lower() in from_addr:
            return True, f"sender: {sender}"

    # Check subject for specific application keywords
    subject = decode_str(msg.get("Subject", "")).lower()
    for keyword in SUBJECT_KEYWORDS:
        if keyword.lower() in subject:
            return True, f"subject: '{keyword}'"

    # Check body only for strong indicators (not general keywords)
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode(errors="ignore")[:2000]
                    break
                except:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode(errors="ignore")[:2000]
        except:
            pass

    body_lower = body.lower()
    for keyword in BODY_KEYWORDS:
        if keyword.lower() in body_lower:
            return True, f"body: '{keyword}'"

    return False, "no match"


def ensure_folder_exists(mail, folder_name):
    """Create folder/label if it doesn't exist."""
    # List all folders
    status, folders = mail.list()
    if status != "OK":
        return False

    folder_exists = False
    for folder in folders:
        # Parse folder name from response
        try:
            name = folder.decode().split('"/"')[-1].strip().strip('"')
            if name.upper() == folder_name.upper():
                folder_exists = True
                break
        except:
            continue

    if not folder_exists:
        # Create the folder
        status, _ = mail.create(folder_name)
        if status == "OK":
            print(f"Created folder: {folder_name}")
            return True
        else:
            print(f"Failed to create folder: {folder_name}")
            return False

    return True


def process_inbox(dry_run=False):
    """Process inbox and move applicants to APPLICANTS folder."""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(GMAIL_EMAIL, GMAIL_PASSWORD)
    except Exception as e:
        print(f"Login failed: {e}")
        return 0, 0

    # Ensure APPLICANTS folder exists
    if not dry_run:
        ensure_folder_exists(mail, APPLICANTS_FOLDER)

    # Select inbox
    mail.select("INBOX")

    # Search for all emails
    status, messages = mail.search(None, "ALL")
    if status != "OK":
        print("Failed to search inbox")
        mail.logout()
        return 0, 0

    email_ids = messages[0].split()
    total = len(email_ids)
    moved = 0

    print(f"Processing {total} emails in INBOX...")

    for email_id in email_ids:
        # Fetch email
        try:
            status, data = mail.fetch(email_id, "(RFC822)")
            if status != "OK" or not data or not data[0]:
                continue
            msg = email.message_from_bytes(data[0][1])
        except Exception as e:
            continue
        subject = decode_str(msg.get("Subject", ""))[:50]
        from_addr = decode_str(msg.get("From", ""))[:40]

        is_app, reason = is_applicant_email(msg)

        if is_app:
            if dry_run:
                print(f"  [WOULD MOVE] {subject} - {reason}")
            else:
                # Copy to APPLICANTS folder
                status, _ = mail.copy(email_id, APPLICANTS_FOLDER)
                if status == "OK":
                    # Mark for deletion from inbox
                    mail.store(email_id, "+FLAGS", "\\Deleted")
                    print(f"  [MOVED] {subject}")
                    moved += 1
                else:
                    print(f"  [FAILED] {subject}")

    if not dry_run:
        # Expunge deleted messages
        mail.expunge()

    mail.logout()

    print(f"\nDone: {moved}/{total} emails moved to {APPLICANTS_FOLDER}")
    return moved, total


def show_stats():
    """Show folder statistics."""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(GMAIL_EMAIL, GMAIL_PASSWORD)
    except Exception as e:
        print(f"Login failed: {e}")
        return

    print(f"\n=== Gmail Stats for {GMAIL_EMAIL} ===\n")

    # Check INBOX
    mail.select("INBOX")
    status, messages = mail.search(None, "ALL")
    inbox_count = len(messages[0].split()) if status == "OK" and messages[0] else 0
    print(f"INBOX: {inbox_count} emails")

    # Check APPLICANTS folder
    try:
        mail.select(APPLICANTS_FOLDER)
        status, messages = mail.search(None, "ALL")
        app_count = len(messages[0].split()) if status == "OK" and messages[0] else 0
        print(f"APPLICANTS: {app_count} emails")
    except:
        print(f"APPLICANTS: folder does not exist")

    # List all folders
    mail.select("INBOX")
    status, folders = mail.list()
    if status == "OK":
        print(f"\nAll folders:")
        for folder in folders[:20]:
            try:
                name = folder.decode().split('"/"')[-1].strip().strip('"')
                print(f"  - {name}")
            except:
                continue

    mail.logout()


def daemon_mode():
    """Run continuously, processing every 5 minutes."""
    print(f"Starting daemon mode - processing every 5 minutes")
    print(f"Account: {GMAIL_EMAIL}")
    print(f"Press Ctrl+C to stop\n")

    while True:
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{timestamp}] Processing...")
            moved, total = process_inbox(dry_run=False)
            print(f"[{timestamp}] Moved {moved} applicant emails")
        except Exception as e:
            print(f"Error: {e}")

        # Wait 5 minutes
        time.sleep(300)


def main():
    parser = argparse.ArgumentParser(description="Gmail Applicant Sorter")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be moved")
    parser.add_argument("--daemon", action="store_true", help="Run continuously")
    parser.add_argument("--stats", action="store_true", help="Show folder stats")
    args = parser.parse_args()

    if args.stats:
        show_stats()
    elif args.daemon:
        daemon_mode()
    else:
        process_inbox(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
