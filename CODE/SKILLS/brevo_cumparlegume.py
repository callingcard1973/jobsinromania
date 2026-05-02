#!/usr/bin/env python3
"""
CumparLegume.com Brevo Automation - Romania Agriculture & Food Jobs.

Sources: ANOFM fresh scrape + ANOFM master + MASTER_ALL
Targets: Agriculture, food factories, food distributors (Romania only)
Schema: 50-column standard
Schedule: Daily 09:20 via Node-RED
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import csv
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from skills_common import to_ascii, sanitize, FIELD_LIMITS
from brevo_safe_sender import BrevoSafeSender, SpamDetectedError, HighBounceRateError
from global_sent_tracker import GlobalSentTracker

from email_sender_rules import SenderRules

load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

# CLAUDE.md compliance: Pre-send validation
SENDER_RULES = SenderRules("CUMPARLEGUME")

# Corporate-only filter
FREE_EMAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'yahoo.fr',
    'yahoo.ro', 'yahoo.de', 'hotmail.fr', 'live.com', 'aol.com',
    'mail.ru', 'yandex.ru', 'wp.pl', 'o2.pl', 'interia.pl',
    'icloud.com', 'ymail.com', 'gmx.com', 'gmx.de', 'web.de'
}


# Campaign config
CAMPAIGN_NAME = "CUMPARLEGUME"
API_KEY = os.getenv("BREVO_CUMPARLEGUME_API_KEY")
SENDER_EMAIL = "office@cumparlegume.com"
SENDER_NAME = "cumparlegume sender"
DAILY_LIMIT = 290

# Paths
CAMPAIGN_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/CUMPARLEGUME")
CONTACTS_DIR = CAMPAIGN_DIR / "contacts"
TEMPLATE_DIR = CAMPAIGN_DIR / "templates"
LOG_DIR = CAMPAIGN_DIR / "logs"
STATE_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/brevo_state/CUMPARLEGUME_state.json")

# Data sources
ANOFM_DIR = Path("/mnt/hdd/SCRAPER_DATA/csv/ANOFM")
ANOFM_MASTER = Path("/opt/ACTIVE/OPENDATA/DATA/ROMANIA/ANOFM/anofm_master.csv")
MASTER_ALL = Path("/opt/ACTIVE/OPENDATA/DATA/ROMANIA/MASTER_ALL.csv")

# Ensure directories exist
for d in [CONTACTS_DIR, TEMPLATE_DIR, LOG_DIR, STATE_FILE.parent]:
    d.mkdir(parents=True, exist_ok=True)

TRACKER = GlobalSentTracker()

# 50-column schema
SCHEMA = [
    'company', 'country', 'county', 'city', 'address', 'postal_code', 'category', 'subcategory', 'type', 'registration_id',
    'email', 'email2', 'email3', 'phone', 'phone2', 'phone3', 'website', 'contact_person', 'contact_dept', 'contact_title',
    'products', 'services', 'activity', 'employees', 'revenue', 'founded', 'vat_id', 'cui', 'status', 'notes',
    'anofm_email', 'anofm_phone', 'anofm_address', 'web_email', 'web_phone', 'web_website', 'best_email', 'best_phone', 'best_address', 'verified',
    'source_file', 'source_system', 'scrape_date', 'update_date', 'export_date', 'priority', 'score', 'tags', 'campaign_id', 'notes2'
]

# ANOFM Domeniul activitate filter (exact match)
# Expanded to include food-related production and retail
ANOFM_SECTORS = [
    'Agricultura / Zootehnie',
    'Turism / Alimentatie',
    'RESTAURANTE',
    'Productie / Logistica',  # Food factories
    'COMERT',                 # Grocery/food retail
]


def truncate(text, max_len=200):
    """Truncate text to max length."""
    if not text:
        return ''
    text = str(text).strip()
    return text[:max_len] if len(text) > max_len else text


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
    template_file = TEMPLATE_DIR / "01_romanian.txt"
    if template_file.exists():
        with open(template_file, 'r', encoding='utf-8') as f:
            content = f.read()
        lines = content.strip().split('\n')
        subject = lines[0].replace("Subject:", "").strip()
        body = '\n'.join(lines[2:])
        return subject, body
    return (
        "Muncitori calificati pentru agricultura - sezon 2026",
        "Buna ziua,\n\nAvem disponibili muncitori calificati...\n\nCu stima,\noffice@cumparlegume.com"
    )


def get_latest_csv(directory, pattern="*.csv"):
    """Get the most recent CSV file from a directory by filename."""
    files = list(directory.glob(pattern))
    if not files:
        return None
    return max(files, key=lambda f: f.name)


def is_target_sector(row):
    """Filter ANOFM by Domeniul activitate (exact match)."""
    sector = (row.get('sector', '') or '').strip()
    return sector in ANOFM_SECTORS


def anofm_to_50col(row, source_file):
    """Convert ANOFM row to 50-column schema."""
    output = {col: '' for col in SCHEMA}

    output['company'] = truncate(to_ascii(row.get('company_name', '') or row.get('employer', '')))
    output['country'] = 'Romania'
    output['county'] = truncate(to_ascii(row.get('company_county', '') or row.get('county', '')))
    output['city'] = truncate(to_ascii(row.get('company_city', '') or row.get('city', '')))
    output['address'] = truncate(to_ascii(row.get('company_address', '') or row.get('address', '')))
    output['category'] = truncate(to_ascii(row.get('sector', '')))
    output['subcategory'] = truncate(to_ascii(row.get('occupation', '')))

    output['email'] = (row.get('email_1', '') or row.get('email1', '') or '').strip().lower()
    output['email2'] = (row.get('email_2', '') or row.get('email2', '') or '').strip().lower()
    output['phone'] = truncate(row.get('phone_1', '') or row.get('phone1', '') or row.get('phone', ''))
    output['phone2'] = truncate(row.get('phone_2', '') or row.get('phone2', ''))
    output['website'] = truncate(row.get('website', ''))
    output['contact_person'] = truncate(to_ascii(row.get('contact_name', '')))

    output['activity'] = truncate(to_ascii(row.get('job_title', '')))
    output['employees'] = truncate(row.get('positions', ''))
    output['notes'] = truncate(to_ascii(row.get('job_description', '')))

    output['anofm_email'] = output['email']
    output['anofm_phone'] = output['phone']
    output['anofm_address'] = output['address']
    output['best_email'] = output['email']
    output['best_phone'] = output['phone']

    output['source_file'] = Path(source_file).name if source_file else ''
    output['source_system'] = 'ANOFM'
    output['scrape_date'] = datetime.now().strftime('%Y-%m-%d')
    output['campaign_id'] = CAMPAIGN_NAME
    output['tags'] = 'agriculture,food,romania'

    return output


def master_all_to_50col(row, source_file):
    """Convert MASTER_ALL row to 50-column schema."""
    output = {col: '' for col in SCHEMA}

    output['company'] = truncate(to_ascii(row.get('employer', '') or row.get('company', '')))
    output['country'] = 'Romania'
    output['county'] = truncate(to_ascii(row.get('county', '')))
    output['city'] = truncate(to_ascii(row.get('city', '')))
    output['address'] = truncate(to_ascii(row.get('address', '')))
    output['category'] = truncate(to_ascii(row.get('sector', '') or row.get('category', '')))
    output['subcategory'] = truncate(to_ascii(row.get('occupation', '') or row.get('subcategory', '')))

    output['email'] = (row.get('email1', '') or row.get('email', '') or '').strip().lower()
    output['email2'] = (row.get('email2', '') or '').strip().lower()
    output['phone'] = truncate(row.get('phone1', '') or row.get('phone', ''))
    output['phone2'] = truncate(row.get('phone2', ''))
    output['website'] = truncate(row.get('website', ''))
    output['contact_person'] = truncate(to_ascii(row.get('contact_name', '')))

    output['activity'] = truncate(to_ascii(row.get('job_title', '') or row.get('activity', '')))
    output['employees'] = truncate(row.get('positions', '') or row.get('employees', ''))
    output['notes'] = truncate(to_ascii(row.get('job_description', '') or row.get('notes', '')))

    output['best_email'] = output['email']
    output['best_phone'] = output['phone']

    output['source_file'] = Path(source_file).name if source_file else ''
    output['source_system'] = 'MASTER_ALL'
    output['scrape_date'] = datetime.now().strftime('%Y-%m-%d')
    output['campaign_id'] = CAMPAIGN_NAME
    output['tags'] = 'agriculture,food,romania'

    return output


def load_and_convert_contacts(state):
    """Load agriculture contacts from all sources, convert to 50-column schema."""
    sent_set = set(state["sent"])
    seen_emails = set()
    contacts = []

    def add_contact(row_50col):
        email = row_50col.get('email', '').strip().lower()
        if not email or '@' not in email:
            return
        if email in sent_set or email in seen_emails:
            return
        # CLAUDE.md: Pre-send validation
        allowed, _ = SENDER_RULES.check_send_allowed(email)
        if not allowed:
            return
        # Corporate-only filter
        domain = email.split('@')[-1].lower()
        if domain in FREE_EMAIL_DOMAINS:
            return
        can_send, reason = TRACKER.can_send(email, campaign=CAMPAIGN_NAME)
        if not can_send:
            return
        seen_emails.add(email)
        contacts.append(row_50col)

    # 1. Latest ANOFM scrape
    anofm_file = get_latest_csv(ANOFM_DIR, "anofm_*.csv")
    if anofm_file:
        print(f"Loading fresh ANOFM: {anofm_file.name}")
        with open(anofm_file, 'r', encoding='utf-8', errors='ignore') as f:
            for row in csv.DictReader(f):
                if not is_target_sector(row):
                    continue
                row_50col = anofm_to_50col(row, str(anofm_file))
                add_contact(row_50col)

    # 2. ANOFM master (historical)
    if ANOFM_MASTER.exists():
        print(f"Loading ANOFM master: {ANOFM_MASTER.name}")
        with open(ANOFM_MASTER, 'r', encoding='utf-8', errors='ignore') as f:
            for row in csv.DictReader(f):
                if not is_target_sector(row):
                    continue
                row_50col = anofm_to_50col(row, str(ANOFM_MASTER))
                add_contact(row_50col)

    # 3. MASTER_ALL (Romania agriculture)
    if MASTER_ALL.exists():
        print(f"Loading MASTER_ALL: {MASTER_ALL.name}")
        with open(MASTER_ALL, 'r', encoding='utf-8', errors='ignore') as f:
            for row in csv.DictReader(f):
                country = (row.get('country', '') or '').lower()
                if 'romania' not in country and 'ro' != country:
                    continue
                if not is_target_sector(row):
                    continue
                row_50col = master_all_to_50col(row, str(MASTER_ALL))
                add_contact(row_50col)

    return contacts


def save_contacts_csv(contacts):
    """Save contacts to 50-column CSV."""
    output_file = CONTACTS_DIR / "contacts.csv"
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=SCHEMA)
        writer.writeheader()
        writer.writerows(contacts)
    print(f"Saved {len(contacts)} contacts to {output_file}")
    return output_file


def log_sent(contact, sent_time):
    """Log sent email to campaign log."""
    log_file = LOG_DIR / f"sent_{datetime.now().strftime('%Y-%m-%d')}.csv"
    fieldnames = ['sent_time', 'email', 'company', 'city', 'category']
    file_exists = log_file.exists()
    with open(log_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            'sent_time': sent_time,
            'email': contact.get('email', ''),
            'company': contact.get('company', ''),
            'city': contact.get('city', ''),
            'category': contact.get('category', '')
        })


def send_batch(dry_run=False):
    print(f"\n=== {CAMPAIGN_NAME} - {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")

    if not API_KEY:
        print("ERROR: BREVO_CUMPARLEGUME_API_KEY not set in /opt/ACTIVE/EMAIL/CAMPAIGNS/.env")
        return

    state = load_state()
    today = datetime.now().strftime("%Y-%m-%d")

    if state.get("last_send") != today:
        state["sent_today"] = 0

    remaining_today = DAILY_LIMIT - state["sent_today"]
    if remaining_today <= 0:
        print(f"Daily limit reached ({DAILY_LIMIT})")
        return

    contacts = load_and_convert_contacts(state)
    print(f"Agriculture/food contacts (50-col): {len(contacts)} unsent")

    if not contacts:
        print("No contacts remaining")
        return

    # Save contacts CSV
    save_contacts_csv(contacts)

    batch = contacts[:remaining_today]
    subject, body = load_template()

    sender = BrevoSafeSender(
        API_KEY, SENDER_EMAIL, SENDER_NAME,
        campaign_name=CAMPAIGN_NAME,
        batch_size=1,
        wait_minutes=4,
        dry_run=dry_run
    )

    def on_sent(contact, success, msg):
        if success:
            email = contact.get('email', '')
            state["sent"].append(email)
            TRACKER.mark_sent(email, campaign=CAMPAIGN_NAME, sender="brevo_cumparlegume")
            log_sent(contact, datetime.now().isoformat())

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
    contacts = load_and_convert_contacts(state)

    print(f"\n=== {CAMPAIGN_NAME} STATUS ===")
    print(f"Schema: 50-column standard")
    print(f"Total sent: {len(state['sent'])}")
    print(f"Remaining: {len(contacts)} (ANOFM Romania)")
    print(f"Today: {state.get('sent_today', 0)}/{DAILY_LIMIT}")
    print(f"API Key: {'SET' if API_KEY else 'NOT SET'}")
    print(f"Contacts CSV: {CONTACTS_DIR / 'contacts.csv'}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--status', '-s', action='store_true')
    parser.add_argument('--reset', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--export-only', action='store_true', help='Only export contacts CSV, no sending')
    args = parser.parse_args()

    if args.reset:
        save_state({"sent": [], "last_send": None, "sent_today": 0})
        print("State reset")
    elif args.status:
        show_status()
    elif args.export_only:
        state = load_state()
        contacts = load_and_convert_contacts(state)
        save_contacts_csv(contacts)
    else:
        send_batch(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
