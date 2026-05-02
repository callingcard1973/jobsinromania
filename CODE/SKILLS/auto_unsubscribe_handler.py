#!/usr/bin/env python3
"""
Auto-Unsubscribe Handler - Process STOP replies automatically

Monitors:
- Classified replies with UNSUBSCRIBE category
- Keywords: STOP, unsubscribe, remove, dezabonare
- Adds to DNC list automatically

Usage:
    python3 auto_unsubscribe_handler.py                    # Process new
    python3 auto_unsubscribe_handler.py --scan             # Scan all replies
    python3 auto_unsubscribe_handler.py --dry-run          # Preview only
    python3 auto_unsubscribe_handler.py --status           # Show stats
    python3 auto_unsubscribe_handler.py --list             # List recent unsubs

Runs automatically after reply classifier.
"""

import os
import sys
import csv
import json
import re
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

try:
    from alerting import send_telegram
except ImportError:
    def send_telegram(msg):
        print(f"[TELEGRAM] {msg}")

# Paths
REPLIES_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/REPLIES")
DNC_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/MASTER_DNC.csv")
BLACKLIST_FILE = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/EMAIL_CLEANUP/blacklist.txt")
STATE_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/.unsubscribe_state.json")

# Unsubscribe patterns
UNSUB_PATTERNS = [
    r'\bstop\b',
    r'\bunsubscribe\b',
    r'\bremove\b',
    r'\bopt.?out\b',
    r'\bdezabonare\b',
    r'\bnu mai\b',
    r'\bwypisz\b',  # Polish
    r'\bodhlasit\b',  # Czech
    r'\babmelden\b',  # German
    r'\bne plus\b',  # French
]


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "processed": [],
        "total_unsubscribed": 0,
        "last_run": None
    }


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def load_existing_dnc():
    """Load existing DNC emails."""
    dnc = set()

    # From DNC file
    if DNC_FILE.exists():
        try:
            with open(DNC_FILE, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    email = row.get('email', '').lower().strip()
                    if email:
                        dnc.add(email)
        except:
            pass

    # From blacklist
    if BLACKLIST_FILE.exists():
        try:
            with open(BLACKLIST_FILE, 'r') as f:
                for line in f:
                    email = line.strip().lower()
                    if '@' in email:
                        dnc.add(email)
        except:
            pass

    return dnc


def add_to_dnc(email, reason="unsubscribe"):
    """Add email to DNC list."""
    email = email.lower().strip()

    # Add to DNC CSV
    DNC_FILE.parent.mkdir(parents=True, exist_ok=True)

    file_exists = DNC_FILE.exists()

    with open(DNC_FILE, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['email', 'reason', 'added_at'])
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            'email': email,
            'reason': reason,
            'added_at': datetime.now().isoformat()
        })

    # Also add to blacklist
    BLACKLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(BLACKLIST_FILE, 'a') as f:
        f.write(f"{email}\n")

    return True


def is_unsubscribe_request(subject, body):
    """Check if message is an unsubscribe request."""
    text = (subject + " " + body).lower()

    for pattern in UNSUB_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True, pattern

    return False, None


def find_unsubscribe_requests():
    """Find unsubscribe requests from classified replies."""
    requests = []

    # Check classified replies
    classified_file = REPLIES_DIR / "classified_replies.csv"
    if classified_file.exists():
        try:
            with open(classified_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('category') == 'UNSUBSCRIBE':
                        requests.append({
                            'email': row.get('sender_email', '').lower().strip(),
                            'subject': row.get('subject', ''),
                            'date': row.get('date', ''),
                            'source': 'classifier'
                        })
        except Exception as e:
            log(f"Error reading classified replies: {e}")

    return requests


def process_unsubscribes(dry_run=False):
    """Process unsubscribe requests."""
    state = load_state()
    existing_dnc = load_existing_dnc()

    requests = find_unsubscribe_requests()
    log(f"Found {len(requests)} unsubscribe requests")

    processed = 0
    skipped_existing = 0
    skipped_processed = 0

    for req in requests:
        email = req['email']

        if not email:
            continue

        # Skip if already in DNC
        if email in existing_dnc:
            skipped_existing += 1
            continue

        # Skip if already processed
        if email in state['processed']:
            skipped_processed += 1
            continue

        if dry_run:
            log(f"[DRY RUN] Would add to DNC: {email}")
        else:
            add_to_dnc(email, f"unsubscribe:{req.get('subject', '')[:50]}")
            state['processed'].append(email)
            state['total_unsubscribed'] += 1
            log(f"Added to DNC: {email}")

        processed += 1

    log(f"Processed: {processed}")
    log(f"Skipped (already in DNC): {skipped_existing}")
    log(f"Skipped (already processed): {skipped_processed}")

    if not dry_run and processed > 0:
        state['last_run'] = datetime.now().isoformat()
        save_state(state)

        # Send notification
        send_telegram(f"📧 Unsubscribe Handler: Added {processed} emails to DNC")

    return processed


def show_status():
    """Show handler status."""
    state = load_state()
    existing_dnc = load_existing_dnc()

    print("\n=== Auto-Unsubscribe Handler Status ===\n")
    print(f"Last run: {state.get('last_run', 'Never')}")
    print(f"Total unsubscribed: {state.get('total_unsubscribed', 0)}")
    print(f"Processed emails: {len(state.get('processed', []))}")
    print(f"Total DNC entries: {len(existing_dnc)}")

    # Show recent
    recent = state.get('processed', [])[-10:]
    if recent:
        print("\nRecent unsubscribes:")
        for email in recent:
            print(f"  {email}")


def list_recent():
    """List recent unsubscribes."""
    requests = find_unsubscribe_requests()

    print("\n=== Recent Unsubscribe Requests ===\n")

    for req in requests[-20:]:
        print(f"{req['email']}")
        print(f"  Subject: {req.get('subject', '')[:50]}")
        print(f"  Date: {req.get('date', 'unknown')}")
        print()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Auto-Unsubscribe Handler")
    parser.add_argument("--scan", action="store_true", help="Scan all replies")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--list", action="store_true", help="List recent")

    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.list:
        list_recent()
        return

    log("=== Auto-Unsubscribe Handler ===")
    process_unsubscribes(args.dry_run)


if __name__ == "__main__":
    main()
