#!/usr/bin/env python3
"""WarehouseWorkers.eu Brevo Automation - with anti-spam protection."""
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

# CLAUDE.md compliance: Pre-send validation
SENDER_RULES = SenderRules("WAREHOUSEWORKERS")

# Corporate-only filter
FREE_EMAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'yahoo.fr',
    'yahoo.ro', 'yahoo.de', 'hotmail.fr', 'live.com', 'aol.com',
    'mail.ru', 'yandex.ru', 'wp.pl', 'o2.pl', 'interia.pl',
    'icloud.com', 'ymail.com', 'gmx.com', 'gmx.de', 'web.de'
}

API_KEY = os.getenv("BREVO_WAREHOUSEWORKERS_API_KEY")
SENDER_EMAIL = "office@warehouseworkers.eu"
SENDER_NAME = "WarehouseWorkers EU"
DAILY_LIMIT = 290

MASTER_CSVS = [
    Path("/mnt/hdd/SCRAPER_DATA/csv/SWEDEN/Sweden_MASTER_50.csv"),
    # EURES master_contacts_50.csv removed - file has no emails (empty data)
]

ANOFM_DIR = Path("/mnt/hdd/SCRAPER_DATA/csv/ANOFM")

# ANOFM Domeniul activitate filter (exact match)
ANOFM_SECTORS = ['COMERT', 'Retail', 'Vanzari']

TEMPLATE_EN = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/WAREHOUSE_EU/templates/01_english.txt")
TEMPLATE_RO = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/WAREHOUSE_EU/templates/01_romanian.txt")
STATE_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/brevo_state/WAREHOUSEWORKERS_state.json")
STATE_FILE.parent.mkdir(exist_ok=True)

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
        temp_file.rename(STATE_FILE)
    except Exception:
        if temp_file.exists():
            temp_file.unlink()
        raise


def load_template(is_romania: bool):
    template_file = TEMPLATE_RO if is_romania else TEMPLATE_EN
    if template_file.exists():
        with open(template_file, 'r', encoding='utf-8') as f:
            content = f.read()
        lines = content.strip().split('\n')
        subject = lines[0].replace("Subject:", "").strip()
        body = '\n'.join(lines[2:])
        return subject, body
    return "Warehouse workers available", "Hello, we have workers available."


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
    """CLAUDE.md compliant email validation."""
    if not email or '@' not in email:
        return False, "invalid"
    if email in sent_set or email in seen_emails:
        return False, "duplicate"
    # REQUIRED: SenderRules validation
    allowed, reason = SENDER_RULES.check_send_allowed(email)
    if not allowed:
        return False, reason
    # Corporate-only
    if not is_corporate_email(email):
        return False, "free email"
    # Cooldown check
    can_send, reason = TRACKER.can_send(email, campaign="WAREHOUSEWORKERS")
    if not can_send:
        return False, reason
    return True, "ok"


def load_contacts(state):
    sent_set = set(state["sent"])
    seen_emails = set()
    contacts = []
    skipped = {"free_email": 0, "invalid": 0}

    # EU sources
    for csv_file in MASTER_CSVS:
        if not csv_file.exists():
            continue
        with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get('email_1', row.get('email', '')).strip().lower()
                valid, reason = validate_email(email, sent_set, seen_emails)
                if not valid:
                    if "free" in reason:
                        skipped["free_email"] += 1
                    else:
                        skipped["invalid"] += 1
                    continue
                seen_emails.add(email)
                country = row.get('country_name', row.get('country', ''))
                contacts.append({
                    "email": email,
                    "company": to_ascii(row.get('company_name', row.get('company', '')))[:100],
                    "country": country,
                    "city": to_ascii(row.get('company_city', row.get('city', ''))),
                    "is_romania": 'romania' in country.lower()
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
                    if "free" in reason:
                        skipped["free_email"] += 1
                    else:
                        skipped["invalid"] += 1
                    continue
                seen_emails.add(email)
                contacts.append({
                    "email": email,
                    "company": to_ascii(row.get('company_name', ''))[:100],
                    "country": "Romania",
                    "city": to_ascii(row.get('company_city', '')),
                    "is_romania": True
                })

    return contacts


def personalize_email(contact, subject_tpl, body_tpl):
    return load_template(contact["is_romania"])


def send_batch(dry_run=False):
    print(f"\n=== WAREHOUSEWORKERS.EU - {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
    state = load_state()
    today = datetime.now().strftime("%Y-%m-%d")
    if state.get("last_send") != today:
        state["sent_today"] = 0
    remaining_today = DAILY_LIMIT - state["sent_today"]
    if remaining_today <= 0:
        print(f"Daily limit reached ({DAILY_LIMIT})")
        return
    contacts = load_contacts(state)
    print(f"Master CSV: {len(contacts)} unsent")
    if not contacts:
        print("No contacts remaining")
        return
    batch = contacts[:remaining_today]

    sender = BrevoSafeSender(API_KEY, SENDER_EMAIL, SENDER_NAME, batch_size=1, wait_minutes=4, dry_run=dry_run)
    def on_sent(contact, success, msg):
        if success:
            state["sent"].append(contact["email"])
            TRACKER.mark_sent(contact["email"], campaign="WAREHOUSEWORKERS", sender="brevo_warehouseworkers")
    try:
        sent_count = sender.send_batch_safe(batch, "", "", personalize_fn=personalize_email, on_sent=on_sent)
        state["sent_today"] = state.get("sent_today", 0) + sent_count
        state["last_send"] = today
        save_state(state)
        print(f"\nSent: {sent_count}, Total: {len(state['sent'])}, Remaining: {len(contacts) - sent_count}")
    except (SpamDetectedError, HighBounceRateError) as e:
        print(f"\n!!! STOPPED: {e}")
        save_state(state)


def show_status():
    state = load_state()
    contacts = load_contacts(state)
    print(f"\n=== WAREHOUSEWORKERS.EU STATUS ===")
    print(f"Sources: {len(MASTER_CSVS)} files")
    print(f"Total sent: {len(state['sent'])}")
    print(f"Remaining: {len(contacts)}")
    print(f"Today: {state.get('sent_today', 0)}/{DAILY_LIMIT}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--status', '-s', action='store_true')
    parser.add_argument('--reset', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
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
