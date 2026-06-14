#!/usr/bin/env python3
"""Auto-organize emails using labels.db intent classification."""

import imaplib
import email
import email.header
import re
import json
import os
import sys
import sqlite3
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

# Load environment
ENV_PATH = Path("/opt/ACTIVE/EMAIL/.env")
load_dotenv(ENV_PATH)

# Import DNC functions from shared module (PostgreSQL)
sys.path.insert(0, '/opt/ACTIVE/EMAIL/CAMPAIGNS/SCRIPTS/SHARED')
try:
    from dnc_utils import add_to_dnc, get_dnc_count
    DNC_AVAILABLE = True
except ImportError:
    DNC_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LABELS_DB = DATA_DIR / "training_data" / "labels.db"
LOG_FILE = DATA_DIR / "training_data" / "auto_organize.log"

A2_CREDENTIALS_FILE = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/a2_smtp_credentials.json")
A2_IMAP_SERVER = "nl1-cl8-ats1.a2hosting.com"
A2_IMAP_PORT = 993

# Gmail credentials - all accounts with passwords in .env
GMAIL_ACCOUNTS = {
    # Primary accounts
    "manpowerdristor@gmail.com": os.environ.get("GMAIL_MANPOWERDRISTOR_APP_PASSWORD", "").replace(" ", ""),
    "manpower.dristor@gmail.com": os.environ.get("GMAIL_MANPOWER_APP_PASSWORD", "").replace(" ", ""),
    "elena.manpower.dristor@gmail.com": os.environ.get("GMAIL_ELENA_PASSWORD", "").replace(" ", ""),

    # Additional accounts
    "fruitnature4@gmail.com": os.environ.get("GMAIL_SEARCH_PASSWORD", "").replace(" ", ""),
    "expatsinromania@gmail.com": os.environ.get("GMAIL_EXPATS_PASSWORD", "").replace(" ", ""),
    "cumparlegume@gmail.com": os.environ.get("GMAIL_CUMPARLEGUME_PASSWORD", "").replace(" ", ""),
    "casafaurbucuresti@gmail.com": os.environ.get("GMAIL_CASAFAUR_PASSWORD", "").replace(" ", ""),
    "vegetablesbucharest@gmail.com": os.environ.get("GMAIL_VEGETABLESBUCHAREST_PASSWORD", "").replace(" ", ""),
    "fructexportromania@gmail.com": os.environ.get("GMAIL_FRUCTEXPORT_PASSWORD", "").replace(" ", ""),
    "icralbucuresti@gmail.com": os.environ.get("GMAIL_ICRALBUCURESTI_PASSWORD", "").replace(" ", ""),

    # Additional from .env
    "pamintstrabun@gmail.com": os.environ.get("GMAIL_PAMINTSTRABUN_PASSWORD", "").replace(" ", ""),
    "solonet.bucuresti@gmail.com": os.environ.get("GMAIL_SOLONET_APP_PASSWORD", "").replace(" ", ""),
}

# Folder mappings
FOLDERS = {
    "application": "APPLICATIONS_RECEIVED",
    "unsubscribe": "UNSUBSCRIBES",
    "bounce": "BOUNCES",
    "auto_reply": "AUTOREPLY",
    "newsletter": "NEWSLETTERS",
    "spam": "SPAM",
    "campaign_reply": "CAMPAIGN_REPLIES",
    "inquiry": "INQUIRIES",
}

# Intents that trigger folder moves
ACTIONABLE_INTENTS = {"application", "unsubscribe", "bounce", "auto_reply", "newsletter", "spam", "campaign_reply", "inquiry"}


def log(msg):
    """Log to file and stdout."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def decode_header(value):
    """Decode email header."""
    if not value:
        return ""
    decoded = email.header.decode_header(value)
    result = []
    for part, charset in decoded:
        if isinstance(part, bytes):
            try:
                result.append(part.decode(charset or "utf-8", errors="replace"))
            except:
                result.append(part.decode("utf-8", errors="replace"))
        else:
            result.append(part)
    return " ".join(result)


def make_dedup_key(subject, from_addr):
    """Create dedup key matching labels.db format."""
    text = f"{subject.lower().strip()}|{from_addr.lower().strip()}"
    return hashlib.md5(text.encode()).hexdigest()


def load_a2_accounts():
    """Load A2 Hosting accounts from credentials JSON."""
    if not A2_CREDENTIALS_FILE.exists():
        log(f"Warning: A2 credentials file not found: {A2_CREDENTIALS_FILE}")
        return {}

    try:
        with open(A2_CREDENTIALS_FILE, "r") as f:
            data = json.load(f)

        accounts = {}
        for domain_key, creds in data.items():
            email_addr = creds.get("email", "")
            password = creds.get("password", "")
            if email_addr and password:
                accounts[email_addr] = password

        return accounts
    except Exception as e:
        log(f"Error loading A2 credentials: {e}")
        return {}


def get_labels_from_db(message_id=None, subject=None, from_addr=None):
    """Look up email intent from labels.db.

    Returns (intent, folder) or (None, None) if not found or not actionable.
    """
    if not LABELS_DB.exists():
        return None, None

    try:
        conn = sqlite3.connect(LABELS_DB)
        cursor = conn.cursor()

        # Try message_id first
        if message_id:
            cursor.execute(
                "SELECT intent FROM labels WHERE message_id = ?",
                (message_id,)
            )
            row = cursor.fetchone()
            if row:
                intent = row[0]
                conn.close()
                if intent in ACTIONABLE_INTENTS:
                    return intent, FOLDERS.get(intent)
                return None, None

        # Try dedup_key (subject + from_addr)
        if subject and from_addr:
            dedup_key = make_dedup_key(subject, from_addr)
            cursor.execute(
                "SELECT intent FROM labels WHERE dedup_key = ?",
                (dedup_key,)
            )
            row = cursor.fetchone()
            if row:
                intent = row[0]
                conn.close()
                if intent in ACTIONABLE_INTENTS:
                    return intent, FOLDERS.get(intent)
                return None, None

        conn.close()
    except Exception as e:
        log(f"DB lookup error: {e}")

    return None, None


def process_imap_account(account, password, imap_server, imap_port, dry_run=False, days=30):
    """Process any IMAP account (Gmail or A2).

    Uses labels.db to determine which emails need organizing.
    """
    is_a2 = "a2hosting" in imap_server.lower()
    account_type = "A2" if is_a2 else "Gmail"
    log(f"Processing {account_type}: {account} (dry_run={dry_run})")

    try:
        imap = imaplib.IMAP4_SSL(imap_server, imap_port)
        imap.login(account, password)
    except Exception as e:
        log(f"Login failed for {account}: {e}")
        return {"error": str(e)}

    # Ensure folders exist (A2 needs INBOX. prefix)
    folder_prefix = "INBOX." if is_a2 else ""
    for folder in FOLDERS.values():
        try:
            imap.create(f"{folder_prefix}{folder}")
        except:
            pass

    imap.select("INBOX")

    # Search recent emails
    since_date = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
    status, data = imap.search(None, f'SINCE "{since_date}"')
    if status != "OK":
        log("Search failed")
        imap.logout()
        return {"error": "Search failed"}

    msg_ids = data[0].split()
    log(f"Found {len(msg_ids)} emails to check")

    stats = {"applications": 0, "unsubscribes": 0, "bounces": 0, "auto_replies": 0, "newsletters": 0, "spam": 0, "campaign_replies": 0, "inquiries": 0, "skipped": 0}

    for msg_id in msg_ids:
        try:
            # Fetch email
            status, fetch_data = imap.fetch(msg_id, "(UID RFC822)")
            if status != "OK":
                continue

            uid = None
            msg = None

            for item in fetch_data:
                if isinstance(item, tuple):
                    meta = item[0].decode() if isinstance(item[0], bytes) else str(item[0])
                    uid_match = re.search(r"UID (\d+)", meta)
                    if uid_match:
                        uid = uid_match.group(1)

                    if len(item) > 1 and isinstance(item[1], bytes):
                        msg = email.message_from_bytes(item[1])

            if not uid or not msg:
                continue

            subject = decode_header(msg.get("Subject", ""))
            from_addr = decode_header(msg.get("From", ""))
            message_id = msg.get("Message-ID", "")

            # Look up intent from labels.db
            intent, dest_folder = get_labels_from_db(message_id, subject, from_addr)

            if intent and dest_folder:
                # A2 needs INBOX. prefix for folders
                actual_folder = f"{folder_prefix}{dest_folder}"
                # Track stats
                if intent == "application":
                    stats["applications"] += 1
                elif intent == "unsubscribe":
                    stats["unsubscribes"] += 1
                    # Add to DNC list
                    try:
                        email_match = re.search(r'<([^>]+)>', from_addr)
                        sender_email = email_match.group(1).lower() if email_match else from_addr.split()[0].lower()
                        if DNC_AVAILABLE and sender_email and "@" in sender_email:
                            add_to_dnc(sender_email, reason="unsubscribe_request", source_email=subject[:100])
                            log(f"    Added to DNC: {sender_email}")
                    except Exception as e:
                        log(f"    DNC add error: {e}")
                elif intent == "bounce":
                    stats["bounces"] += 1
                elif intent == "auto_reply":
                    stats["auto_replies"] += 1
                elif intent == "newsletter":
                    stats["newsletters"] += 1
                elif intent == "spam":
                    stats["spam"] += 1
                elif intent == "campaign_reply":
                    stats["campaign_replies"] += 1
                elif intent == "inquiry":
                    stats["inquiries"] += 1

                log(f"  [{intent}] → {actual_folder}: {from_addr[:30]} | {subject[:40]}")

                if not dry_run:
                    result = imap.uid("COPY", uid, actual_folder)
                    if result[0] == "OK":
                        imap.uid("STORE", uid, "+FLAGS", "\\Deleted")
                    else:
                        log(f"    Failed: {result}")
            else:
                stats["skipped"] += 1

        except Exception as e:
            log(f"  Error: {e}")

    if not dry_run:
        imap.expunge()

    imap.logout()
    log(f"Done: {stats}")
    return stats


def process_gmail(account, password, dry_run=False, days=30):
    """Process Gmail account."""
    return process_imap_account(
        account=account,
        password=password,
        imap_server="imap.gmail.com",
        imap_port=993,
        dry_run=dry_run,
        days=days
    )


def process_a2(account, password, dry_run=False, days=30):
    """Process A2 Hosting account."""
    return process_imap_account(
        account=account,
        password=password,
        imap_server=A2_IMAP_SERVER,
        imap_port=A2_IMAP_PORT,
        dry_run=dry_run,
        days=days
    )


def get_all_accounts():
    """Get all available accounts (Gmail + A2)."""
    accounts = []

    # Gmail accounts with valid passwords
    for email_addr, password in GMAIL_ACCOUNTS.items():
        if password and password not in ("NEEDS_APP_PASSWORD", ""):
            accounts.append({
                "email": email_addr,
                "password": password,
                "type": "gmail"
            })

    # A2 Hosting accounts
    a2_accounts = load_a2_accounts()
    for email_addr, password in a2_accounts.items():
        if password:
            accounts.append({
                "email": email_addr,
                "password": password,
                "type": "a2"
            })

    return accounts


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Auto-organize emails using labels.db")
    parser.add_argument("--account", help="Email account to process")
    parser.add_argument("--all", action="store_true", help="Process all accounts")
    parser.add_argument("--gmail-only", action="store_true", help="Process only Gmail accounts")
    parser.add_argument("--a2-only", action="store_true", help="Process only A2 Hosting accounts")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually move emails")
    parser.add_argument("--days", type=int, default=30, help="Look back N days (default: 30)")
    parser.add_argument("--list", action="store_true", help="List all available accounts")
    args = parser.parse_args()

    if args.list:
        all_accounts = get_all_accounts()
        print(f"\nAvailable accounts ({len(all_accounts)} total):\n")

        gmail_accts = [a for a in all_accounts if a["type"] == "gmail"]
        a2_accts = [a for a in all_accounts if a["type"] == "a2"]

        print(f"=== Gmail ({len(gmail_accts)}) ===")
        for acct in gmail_accts:
            print(f"  {acct['email']}")

        print(f"\n=== A2 Hosting ({len(a2_accts)}) ===")
        for acct in a2_accts:
            print(f"  {acct['email']}")

        return

    if args.account:
        # Single account mode
        # Check Gmail first
        password = GMAIL_ACCOUNTS.get(args.account, "")
        if password and password not in ("NEEDS_APP_PASSWORD", ""):
            process_gmail(args.account, password, args.dry_run, args.days)
            return

        # Check A2 accounts
        a2_accounts = load_a2_accounts()
        password = a2_accounts.get(args.account, "")
        if password:
            process_a2(args.account, password, args.dry_run, args.days)
            return

        print(f"No password found for {args.account}")
        return

    if args.all or args.gmail_only or args.a2_only:
        all_accounts = get_all_accounts()
        total_stats = {
            "accounts_processed": 0,
            "accounts_failed": 0,
            "applications": 0,
            "unsubscribes": 0,
            "bounces": 0,
            "auto_replies": 0,
            "skipped": 0
        }

        for acct in all_accounts:
            # Filter by type if requested
            if args.gmail_only and acct["type"] != "gmail":
                continue
            if args.a2_only and acct["type"] != "a2":
                continue

            if acct["type"] == "gmail":
                result = process_gmail(acct["email"], acct["password"], args.dry_run, args.days)
            else:
                result = process_a2(acct["email"], acct["password"], args.dry_run, args.days)

            if "error" in result:
                total_stats["accounts_failed"] += 1
            else:
                total_stats["accounts_processed"] += 1
                total_stats["applications"] += result.get("applications", 0)
                total_stats["unsubscribes"] += result.get("unsubscribes", 0)
                total_stats["bounces"] += result.get("bounces", 0)
                total_stats["auto_replies"] += result.get("auto_replies", 0)
                total_stats["skipped"] += result.get("skipped", 0)

        print("\n=== TOTAL ===")
        print(f"Accounts processed: {total_stats['accounts_processed']}")
        print(f"Accounts failed: {total_stats['accounts_failed']}")
        print(f"Applications moved: {total_stats['applications']}")
        print(f"Unsubscribes moved: {total_stats['unsubscribes']}")
        print(f"Bounces moved: {total_stats['bounces']}")
        print(f"Auto-replies moved: {total_stats['auto_replies']}")
        print(f"Skipped (not in labels.db or not actionable): {total_stats['skipped']}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
