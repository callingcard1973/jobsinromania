#!/usr/bin/env python3
"""
BuildJobs.eu Brevo Automation
Feeds continuously from master CSV, sends 290/day via Brevo.

Uses BrevoSafeSender for anti-spam protection:
- Sends 1 email at a time
- Waits 4 minutes, checks for spam
- Checks Brevo API for spam complaints
- Stops if spam detected

Usage:
    brevo_buildjobs.py              # Send daily batch (290)
    brevo_buildjobs.py --status     # Show status
    brevo_buildjobs.py --reset      # Reset sent list
    brevo_buildjobs.py --dry-run    # Test without sending
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import csv
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from skills_common import to_ascii
from brevo_safe_sender import BrevoSafeSender, SpamDetectedError, HighBounceRateError
from email_sender_rules import SenderRules

load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

# Initialize sender rules for pre-send validation
SENDER_RULES = SenderRules("BUILDJOBS")

# Free email domains to filter out (corporate only)
FREE_EMAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'yahoo.fr',
    'yahoo.ro', 'yahoo.de', 'hotmail.fr', 'live.com', 'aol.com',
    'mail.ru', 'yandex.ru', 'wp.pl', 'o2.pl', 'interia.pl',
    'icloud.com', 'ymail.com', 'gmx.com', 'gmx.de', 'web.de',
    'protonmail.com', 'zoho.com', 'mail.com'
}

# Config
API_KEY = os.getenv("BREVO_BUILDJOBS_API_KEY")
SENDER_EMAIL = "office@buildjobs.eu"
SENDER_NAME = "BuildJobs EU"
DAILY_LIMIT = 290

# Source
MASTER_CSV = Path("/opt/ACTIVE/OPENDATA/DATA/CONSTRUCTION_ALL_COMBINED.csv")

ANOFM_DIR = Path("/mnt/hdd/SCRAPER_DATA/csv/ANOFM")

# ANOFM Domeniul activitate filter (exact match)
ANOFM_SECTORS = ['Constructii / Instalatii']

# Templates
TEMPLATE_EN = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/CONSTRUCT2026/templates/01_english.txt")
TEMPLATE_RO = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/CONSTRUCT2026/templates/brevo_buildjobs.txt")

# State
STATE_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/brevo_state/BUILDJOBS_state.json")
STATE_FILE.parent.mkdir(exist_ok=True)

# Cross-campaign tracking (7-day cooldown)
from global_sent_tracker import GlobalSentTracker
TRACKER = GlobalSentTracker()


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"sent": [], "last_send": None, "sent_today": 0}


def save_state(state):
    """Save state with atomic write to prevent corruption."""
    import fcntl
    temp_file = STATE_FILE.with_suffix('.tmp')
    try:
        with open(temp_file, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            json.dump(state, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        temp_file.rename(STATE_FILE)  # Atomic rename
    except Exception as e:
        if temp_file.exists():
            temp_file.unlink()
        raise


def load_template(is_romania: bool):
    template_file = TEMPLATE_RO if is_romania else TEMPLATE_EN
    with open(template_file, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.strip().split('\n')
    subject = lines[0].replace("Subject:", "").strip()
    body = '\n'.join(lines[2:])
    return subject, body


def is_target_sector(row):
    """Filter ANOFM by Domeniul activitate (exact match)."""
    sector = (row.get('sector', '') or '').strip()
    return sector in ANOFM_SECTORS


def get_latest_anofm():
    """Get latest ANOFM CSV."""
    files = list(ANOFM_DIR.glob("anofm_*.csv"))
    return max(files, key=lambda f: f.name) if files else None


def is_corporate_email(email):
    """Check if email is corporate (not free email provider)."""
    if '@' not in email:
        return False
    domain = email.split('@')[-1].lower()
    return domain not in FREE_EMAIL_DOMAINS


def validate_email(email, sent_set, seen_emails):
    """
    Validate email using CLAUDE.md rules.
    Returns (is_valid, reason).
    """
    if not email or '@' not in email:
        return False, "invalid format"
    if email in sent_set:
        return False, "already sent"
    if email in seen_emails:
        return False, "duplicate"

    # REQUIRED: Pre-send validation (CLAUDE.md Rule 1)
    allowed, reason = SENDER_RULES.check_send_allowed(email)
    if not allowed:
        return False, reason

    # Corporate-only filter (reduce bounces from free email)
    if not is_corporate_email(email):
        return False, "free email domain"

    # Cross-campaign cooldown
    can_send, reason = TRACKER.can_send(email, campaign="BUILDJOBS")
    if not can_send:
        return False, reason

    return True, "ok"


def load_contacts(state):
    sent_set = set(state["sent"])
    seen_emails = set()
    contacts = []
    skipped = {"free_email": 0, "validation": 0, "cooldown": 0, "duplicate": 0}

    # Master CSV
    if MASTER_CSV.exists():
        with open(MASTER_CSV, 'r', encoding='utf-8', errors='ignore') as f:
            for row in csv.DictReader(f):
                email = row.get('email', '').strip().lower()

                valid, reason = validate_email(email, sent_set, seen_emails)
                if not valid:
                    if "free email" in reason:
                        skipped["free_email"] += 1
                    elif "cooldown" in reason or "sent" in reason:
                        skipped["cooldown"] += 1
                    elif "duplicate" in reason:
                        skipped["duplicate"] += 1
                    else:
                        skipped["validation"] += 1
                    continue

                seen_emails.add(email)
                country = row.get('country', '').strip()
                contacts.append({
                    "email": email,
                    "company": to_ascii(row.get('company', ''))[:100],
                    "country": country,
                    "city": to_ascii(row.get('city', '')),
                    "phone": row.get('phone', ''),
                    "is_romania": country.lower() == 'romania'
                })

    # ANOFM Romania (filtered by Domeniul activitate)
    anofm_file = get_latest_anofm()
    if anofm_file:
        with open(anofm_file, 'r', encoding='utf-8', errors='ignore') as f:
            for row in csv.DictReader(f):
                if not is_target_sector(row):
                    continue
                email = (row.get('email_1', '') or '').strip().lower()

                valid, reason = validate_email(email, sent_set, seen_emails)
                if not valid:
                    if "free email" in reason:
                        skipped["free_email"] += 1
                    elif "cooldown" in reason or "sent" in reason:
                        skipped["cooldown"] += 1
                    elif "duplicate" in reason:
                        skipped["duplicate"] += 1
                    else:
                        skipped["validation"] += 1
                    continue

                seen_emails.add(email)
                contacts.append({
                    "email": email,
                    "company": to_ascii(row.get('company_name', ''))[:100],
                    "country": "Romania",
                    "city": to_ascii(row.get('company_city', '')),
                    "phone": row.get('phone_1', ''),
                    "is_romania": True
                })

    # Log skip stats
    if any(skipped.values()):
        print(f"Skipped: {skipped['free_email']} free email, {skipped['validation']} invalid, {skipped['cooldown']} cooldown")

    return contacts


def personalize_email(contact, subject_tpl, body_tpl):
    """Personalize email based on contact's country."""
    subject, body = load_template(contact["is_romania"])
    return subject, body


def send_batch(dry_run=False):
    print(f"\n=== BUILDJOBS.EU - {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")

    state = load_state()

    # Reset daily counter if new day
    today = datetime.now().strftime("%Y-%m-%d")
    if state.get("last_send") != today:
        state["sent_today"] = 0

    remaining_today = DAILY_LIMIT - state["sent_today"]
    if remaining_today <= 0:
        print(f"Daily limit reached ({DAILY_LIMIT})")
        return

    # Load contacts
    contacts = load_contacts(state)
    print(f"Master CSV: {len(contacts)} unsent")

    if not contacts:
        print("No contacts remaining")
        return

    # Get batch
    batch = contacts[:remaining_today]
    print(f"Sending: {len(batch)}")

    # Initialize safe sender
    sender = BrevoSafeSender(
        api_key=API_KEY,
        sender_email=SENDER_EMAIL,
        sender_name=SENDER_NAME,
        batch_size=1,
        wait_minutes=4,
        dry_run=dry_run
    )

    # Callback for each sent email
    def on_sent(contact, success, msg):
        if success:
            state["sent"].append(contact["email"])
            TRACKER.mark_sent(contact["email"], campaign="BUILDJOBS", sender="brevo_buildjobs")

    try:
        sent_count = sender.send_batch_safe(
            batch,
            subject_template="",  # Not used - personalize_fn handles it
            body_template="",
            personalize_fn=personalize_email,
            on_sent=on_sent
        )

        # Update state
        state["sent_today"] = state.get("sent_today", 0) + sent_count
        state["last_send"] = today
        save_state(state)

        remaining = len(contacts) - sent_count
        print(f"\nSent: {sent_count}")
        print(f"Total sent: {len(state['sent'])}")
        print(f"Remaining: {remaining}")
        print(f"Days left: {remaining // DAILY_LIMIT + 1}")

    except SpamDetectedError as e:
        print(f"\n!!! SPAM DETECTED - STOPPING !!!")
        print(f"Error: {e}")
        save_state(state)

    except HighBounceRateError as e:
        print(f"\n!!! HIGH BOUNCE RATE - STOPPING !!!")
        print(f"Error: {e}")
        save_state(state)


def show_status():
    state = load_state()
    contacts = load_contacts(state)

    print(f"\n=== BUILDJOBS.EU STATUS ===")
    print(f"Master: {MASTER_CSV}")
    print(f"Total sent: {len(state['sent'])}")
    print(f"Remaining: {len(contacts)}")
    print(f"Last send: {state.get('last_send', 'Never')}")
    print(f"Today: {state.get('sent_today', 0)}/{DAILY_LIMIT}")
    print(f"Days left: {len(contacts) // DAILY_LIMIT + 1}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--status', '-s', action='store_true')
    parser.add_argument('--reset', action='store_true')
    parser.add_argument('--dry-run', action='store_true', help='Test without sending')
    args = parser.parse_args()

    if args.reset:
        save_state({"sent": [], "last_send": None, "sent_today": 0})
        print("State reset")
    elif args.status:
        show_status()
    else:
        send_batch(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
