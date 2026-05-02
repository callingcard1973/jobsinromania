#!/usr/bin/env python3
"""MIVRomania.info Brevo Automation - with anti-spam protection."""
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
SENDER_RULES = SenderRules("MIVROMANIA")

# Corporate-only filter
FREE_EMAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'yahoo.fr',
    'yahoo.ro', 'yahoo.de', 'hotmail.fr', 'live.com', 'aol.com',
    'mail.ru', 'yandex.ru', 'wp.pl', 'o2.pl', 'interia.pl',
    'icloud.com', 'ymail.com', 'gmx.com', 'gmx.de', 'web.de'
}


API_KEY = os.getenv("BREVO_MIVROMANIA_API_KEY")
SENDER_EMAIL = "office@mivromania.info"
SENDER_NAME = "MIV Romania"
DAILY_LIMIT = 290

ANOFM_DIR = Path("/mnt/hdd/SCRAPER_DATA/csv/ANOFM")

# ANOFM Domeniul activitate filter (exact match) - remaining sectors
ANOFM_SECTORS = [
    'SERVICE AUTO',
    'Au pair / Babysitter / Curatenie',
    'Servicii infrumusetare',
    'Altele',
    'Administrativ / Secretariat',
    'Contabilitate / Financiar',
    'Sport / Arta / Divertisment',
    'Specialisti / Tehnicieni',
    'Educatie / Training / Coaching',
    'Call center / Suport clienti',
    'Management',
    'Marketing',
    'Resurse umane',
    'Legislativ / Juridic / Functii Publice'
]

TEMPLATE_RO = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/MIVROMANIA/templates/01_romanian.txt")
STATE_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/brevo_state/MIVROMANIA_state.json")
STATE_FILE.parent.mkdir(exist_ok=True)

from global_sent_tracker import GlobalSentTracker
TRACKER = GlobalSentTracker()

DEFAULT_SUBJECT = "Muncitori calificati disponibili pentru 2026"
DEFAULT_BODY = """Buna ziua,

Avem disponibili muncitori calificati din Romania, Republica Moldova, Nepal, Sri Lanka, Uganda si Kenya.

Personal cu experienta, documente in regula, disponibili pentru contracte pe termen lung.

Daca aveti nevoie de muncitori, va rog sa raspundeti si va trimit lista cu candidatii disponibili.

Cu stima,
Tudor Seicarescu
office@mivromania.info
"""


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


def load_template():
    if TEMPLATE_RO.exists():
        with open(TEMPLATE_RO, 'r', encoding='utf-8') as f:
            content = f.read()
        lines = content.strip().split('\n')
        subject = lines[0].replace("Subject:", "").strip()
        body = '\n'.join(lines[2:])
        return subject, body
    return DEFAULT_SUBJECT, DEFAULT_BODY


def is_target_sector(row):
    """Filter ANOFM by Domeniul activitate (exact match)."""
    sector = (row.get('sector', '') or '').strip()
    return sector in ANOFM_SECTORS


def get_latest_anofm():
    """Get latest ANOFM CSV."""
    files = list(ANOFM_DIR.glob("anofm_*.csv"))
    return max(files, key=lambda f: f.name) if files else None


def load_contacts(state):
    sent_set = set(state["sent"])
    seen_emails = set()
    contacts = []

    # ANOFM Romania (filtered by Domeniul activitate)
    anofm_file = get_latest_anofm()
    if anofm_file:
        with open(anofm_file, 'r', encoding='utf-8', errors='ignore') as f:
            for row in csv.DictReader(f):
                if not is_target_sector(row):
                    continue
                email = (row.get('email_1', '') or '').strip().lower()
                if not email or '@' not in email or email in sent_set or email in seen_emails:
                    continue
                # CLAUDE.md: Pre-send validation
                allowed, _ = SENDER_RULES.check_send_allowed(email)
                if not allowed:
                    continue
                # Corporate-only
                domain = email.split('@')[-1].lower()
                if domain in FREE_EMAIL_DOMAINS:
                    continue
                can_send, _ = TRACKER.can_send(email, campaign="MIVROMANIA")
                if not can_send:
                    continue
                seen_emails.add(email)
                contacts.append({
                    "email": email,
                    "company": to_ascii(row.get('company_name', ''))[:100],
                    "country": "Romania",
                    "city": to_ascii(row.get('company_city', '')),
                    "phone": row.get('phone_1', '')
                })

    return contacts


def send_batch(dry_run=False):
    print(f"\n=== MIVROMANIA.INFO - {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
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
    subject, body = load_template()

    sender = BrevoSafeSender(API_KEY, SENDER_EMAIL, SENDER_NAME, batch_size=1, wait_minutes=4, dry_run=dry_run)
    def on_sent(contact, success, msg):
        if success:
            state["sent"].append(contact["email"])
            TRACKER.mark_sent(contact["email"], campaign="MIVROMANIA", sender="brevo_mivromania")
    try:
        sent_count = sender.send_batch_safe(batch, subject, body, on_sent=on_sent)
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
    print(f"\n=== MIVROMANIA.INFO STATUS ===")
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
