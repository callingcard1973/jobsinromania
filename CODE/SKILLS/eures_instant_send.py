#!/usr/bin/env python3
"""
EURES Instant Send - Send emails to EU employers via A2 SMTP

Uses enriched EURES data from Nordic countries and sends via A2 SMTP domains.
Respects warmup limits and uses sector-based sender matching.

Usage:
    python3 eures_instant_send.py --dry-run
    python3 eures_instant_send.py --limit 100
    python3 eures_instant_send.py --country SE --limit 50
    python3 eures_instant_send.py --status
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

# Unbuffered stdout for real-time logging
sys.stdout.reconfigure(line_buffering=True)

import os
import csv
import json
import time
import random
import smtplib
import argparse
import threading
from pathlib import Path
from datetime import datetime, date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

# Paths
CAMPAIGN_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/EURES_INSTANT")
STATE_FILE = CAMPAIGN_DIR / "state.json"
LOG_DIR = CAMPAIGN_DIR / "logs"
TEMPLATE_DIR = CAMPAIGN_DIR / "templates"
ENRICHED_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/ENRICHED")

# A2 SMTP domains and their sectors (all 7 domains)
A2_SENDERS = {
    "horecaworkers.eu": {
        "email": "office@horecaworkers.eu",
        "sectors": ["horeca", "hotel", "restaurant", "catering", "tourism", "hospitality"],
        "smtp_host": "nl1-cl8-ats1.a2hosting.com",
        "smtp_port": 465,
    },
    "meatworkers.eu": {
        "email": "office@meatworkers.eu",
        "sectors": ["meat", "food", "slaughter", "butcher", "processing"],
        "smtp_host": "nl1-cl8-ats1.a2hosting.com",
        "smtp_port": 465,
    },
    "electricjobs.eu": {
        "email": "office@electricjobs.eu",
        "sectors": ["electric", "electrical", "construction", "building", "installation"],
        "smtp_host": "nl1-cl8-ats1.a2hosting.com",
        "smtp_port": 465,
    },
    "mechanicjobs.eu": {
        "email": "office@mechanicjobs.eu",
        "sectors": ["mechanic", "automotive", "vehicle", "repair", "maintenance"],
        "smtp_host": "nl1-cl8-ats1.a2hosting.com",
        "smtp_port": 465,
    },
    "farmworkers.eu": {
        "email": "office@farmworkers.eu",
        "sectors": ["farm", "agriculture", "agri", "harvest", "greenhouse", "animal"],
        "smtp_host": "nl1-cl8-ats1.a2hosting.com",
        "smtp_port": 465,
    },
    "factoryjobs.eu": {
        "email": "office@factoryjobs.eu",
        "sectors": ["factory", "manufacturing", "production", "assembly", "industrial"],
        "smtp_host": "nl1-cl8-ats1.a2hosting.com",
        "smtp_port": 465,
    },
    "warehouseworkers.eu": {
        "email": "office@warehouseworkers.eu",
        "sectors": ["warehouse", "logistics", "transport", "driver", "storage", "forklift"],
        "smtp_host": "nl1-cl8-ats1.a2hosting.com",
        "smtp_port": 465,
    },
}

# Country to enriched file mapping
COUNTRY_FILES = {
    "SE": ENRICHED_DIR / "SE_ENRICHED.csv",
    "DK": ENRICHED_DIR / "DK_ENRICHED.csv",
    "NO": ENRICHED_DIR / "NO_ENRICHED.csv",
    "FI": ENRICHED_DIR / "FI_ENRICHED.csv",
}

# Warmup schedule (day -> limit per domain)
WARMUP_SCHEDULE = {
    (1, 3): 20,
    (4, 7): 50,
    (8, 14): 100,
    (15, 21): 200,
    (22, 28): 350,
    (29, 999): 500,
}

WARMUP_START_DATE = date(2026, 1, 14)  # Day 1 of A2 warmup
DELAY_SECONDS = 240  # 4 minutes between emails
STAGGER_SECONDS = 60  # 1 minute between sender launches

# Thread lock for state
_state_lock = threading.Lock()


def get_warmup_day():
    """Get current warmup day."""
    delta = (date.today() - WARMUP_START_DATE).days + 1
    return max(1, delta)


def get_daily_limit():
    """Get daily limit per domain based on warmup day."""
    day = get_warmup_day()
    for (start, end), limit in WARMUP_SCHEDULE.items():
        if start <= day <= end:
            return limit
    return 500


def load_state():
    """Load campaign state."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "sent_emails": [],
        "sent_job_ids": [],
        "daily_counts": {},
        "last_run": None,
        "permanent_failures": [],
    }


def save_state(state):
    """Save campaign state thread-safely."""
    with _state_lock:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2, default=str)


def load_blacklist():
    """Load DNC/bounce blacklist."""
    blacklist = set()
    bl_file = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/EMAIL_CLEANUP/blacklist.txt")
    if bl_file.exists():
        with open(bl_file) as f:
            for line in f:
                line = line.strip().lower()
                if line and not line.startswith('#'):
                    blacklist.add(line)
    return blacklist


def get_smtp_password(domain):
    """Get SMTP password for A2 domain."""
    # Format: A2_FACTORYJOBS_EU_PASSWORD for factoryjobs.eu
    key = f"A2_{domain.replace('.', '_').upper()}_PASSWORD"
    return os.getenv(key, os.getenv("A2_SMTP_PASS", ""))


# Round-robin counter for distributing contacts
_rr_counter = 0
_rr_lock = threading.Lock()

def match_sector_to_sender(sector, job_title="", occupation=""):
    """Match job sector/title to best A2 sender. Round-robin for unmatched."""
    global _rr_counter
    text = f"{sector} {job_title} {occupation}".lower()

    # Try sector matching first
    for domain, config in A2_SENDERS.items():
        for keyword in config["sectors"]:
            if keyword in text:
                return domain

    # Round-robin for unmatched sectors (distribute evenly across all senders)
    with _rr_lock:
        domains = list(A2_SENDERS.keys())
        domain = domains[_rr_counter % len(domains)]
        _rr_counter += 1
        return domain


def load_contacts(countries=None, limit=None):
    """Load enriched contacts from specified countries."""
    contacts = []
    blacklist = load_blacklist()
    state = load_state()
    sent_emails = set(e.lower() for e in state.get("sent_emails", []))

    files = COUNTRY_FILES
    if countries:
        files = {k: v for k, v in COUNTRY_FILES.items() if k in countries}

    for country, filepath in files.items():
        if not filepath.exists():
            print(f"  {country}: file not found")
            continue

        with open(filepath) as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = (row.get('email') or row.get('email_1') or '').strip().lower()
                if not email or '@' not in email:
                    continue
                if email in blacklist or email in sent_emails:
                    continue

                # Skip personal emails
                personal_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
                                   'live.com', 'icloud.com', 'protonmail.com']
                if any(email.endswith(d) for d in personal_domains):
                    continue

                contacts.append({
                    "email": email,
                    "company": row.get('company_name') or row.get('company') or '',
                    "city": row.get('city') or row.get('company_city') or '',
                    "country": country,
                    "job_title": row.get('job_title') or '',
                    "sector": row.get('sector') or row.get('occupation') or '',
                    "sender": match_sector_to_sender(
                        row.get('sector', ''),
                        row.get('job_title', ''),
                        row.get('occupation', '')
                    ),
                })

    random.shuffle(contacts)
    if limit:
        contacts = contacts[:limit]

    return contacts


def load_template(sender_domain):
    """Load email template for sender."""
    template_file = TEMPLATE_DIR / f"{sender_domain.replace('.', '_')}.txt"
    if not template_file.exists():
        template_file = TEMPLATE_DIR / "01_intro.txt"

    if not template_file.exists():
        return "Subject: Workers available for your position\n\nHello,\n\nWe have qualified workers available.\n\nBest regards"

    with open(template_file) as f:
        return f.read()


def parse_template(template):
    """Parse template into subject and body."""
    lines = template.strip().split('\n')
    subject = "Workers available"
    body_start = 0

    for i, line in enumerate(lines):
        if line.lower().startswith('subject:'):
            subject = line[8:].strip()
            body_start = i + 1
            break

    body = '\n'.join(lines[body_start:]).strip()
    return subject, body


def personalize(text, contact):
    """Personalize template with contact data."""
    replacements = {
        '{company}': contact.get('company', ''),
        '{city}': contact.get('city', ''),
        '{job_title}': contact.get('job_title', ''),
        '{country}': contact.get('country', ''),
    }
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text


def send_email_a2(to_email, subject, body, sender_domain, dry_run=False):
    """Send email via A2 SMTP."""
    config = A2_SENDERS[sender_domain]
    from_email = config["email"]
    password = get_smtp_password(sender_domain)

    if dry_run:
        return True, "DRY RUN"

    if not password:
        return False, f"No password for {sender_domain}"

    try:
        msg = MIMEMultipart()
        msg['From'] = f"Job Recruitment <{from_email}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        with smtplib.SMTP_SSL(config["smtp_host"], config["smtp_port"], timeout=30) as server:
            server.login(from_email, password)
            server.send_message(msg)

        return True, "OK"
    except Exception as e:
        return False, str(e)


def log_send(sender, email, status, message=""):
    """Log send attempt."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"sent_{date.today().strftime('%Y%m%d')}.log"
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(log_file, 'a') as f:
        f.write(f"{timestamp} [{sender}] | {status} | {email} | {message}\n")


def sender_worker(sender_domain, contacts, state, dry_run=False):
    """Worker thread for a single sender."""
    today = date.today().isoformat()
    daily_limit = get_daily_limit()
    template = load_template(sender_domain)
    subject_tpl, body_tpl = parse_template(template)

    sent_count = 0

    for contact in contacts:
        # Check daily limit
        with _state_lock:
            sender_counts = state["daily_counts"].get(today, {})
            current = sender_counts.get(sender_domain, 0)
            if current >= daily_limit:
                print(f"[{sender_domain}] Daily limit reached ({daily_limit})")
                break

        email = contact["email"]
        subject = personalize(subject_tpl, contact)
        body = personalize(body_tpl, contact)

        print(f"[{sender_domain}] Sending to {email}...", end=" ", flush=True)
        success, msg = send_email_a2(email, subject, body, sender_domain, dry_run)

        if success:
            print("OK")
            log_send(sender_domain, email, "OK", f"sent via {sender_domain}")
            sent_count += 1

            with _state_lock:
                state["sent_emails"].append(email)
                if today not in state["daily_counts"]:
                    state["daily_counts"][today] = {}
                state["daily_counts"][today][sender_domain] = state["daily_counts"][today].get(sender_domain, 0) + 1
                save_state(state)
        else:
            print(f"FAIL: {msg}")
            log_send(sender_domain, email, "FAIL", msg)
            if "550" in msg or "rejected" in msg.lower():
                with _state_lock:
                    state["permanent_failures"].append(email)
                    save_state(state)

        # Wait before next email
        if not dry_run and sent_count < len(contacts):
            print(f"[{sender_domain}] Waiting {DELAY_SECONDS//60} minutes...")
            time.sleep(DELAY_SECONDS)

    print(f"[{sender_domain}] DONE: {sent_count} sent")
    return sent_count


def run_campaign(countries=None, limit=None, dry_run=False):
    """Run the campaign with parallel senders."""
    print(f"\n=== EURES Instant Send ===")
    print(f"Warmup Day: {get_warmup_day()}")
    print(f"Daily Limit: {get_daily_limit()}/domain")
    print(f"Dry Run: {dry_run}")
    print()

    # Load contacts
    contacts = load_contacts(countries, limit)
    if not contacts:
        print("No contacts to send!")
        return 0

    print(f"Loaded {len(contacts)} contacts")

    # Group contacts by sender
    sender_queues = {}
    for contact in contacts:
        sender = contact["sender"]
        if sender not in sender_queues:
            sender_queues[sender] = []
        sender_queues[sender].append(contact)

    print(f"\nSender distribution:")
    for sender, queue in sender_queues.items():
        print(f"  {sender}: {len(queue)} contacts")
    print()

    # Load state
    state = load_state()
    state["last_run"] = datetime.now().isoformat()
    save_state(state)

    # Launch sender threads with stagger
    threads = []
    for i, (sender_domain, queue) in enumerate(sender_queues.items()):
        t = threading.Thread(
            target=sender_worker,
            args=(sender_domain, queue, state, dry_run),
            name=sender_domain
        )
        threads.append(t)
        t.start()
        print(f"  Started {sender_domain} ({len(queue)} contacts)")

        # Stagger next sender launch
        if i < len(sender_queues) - 1:
            print(f"  Waiting 1 minute before next sender...")
            time.sleep(STAGGER_SECONDS)

    # Wait for all threads
    for t in threads:
        t.join()

    # Final state
    state["last_run"] = datetime.now().isoformat()
    save_state(state)

    today = date.today().isoformat()
    total_sent = sum(state["daily_counts"].get(today, {}).values())
    print(f"\n=== Campaign Complete ===")
    print(f"Total sent today: {total_sent}")

    return total_sent


def show_status():
    """Show campaign status."""
    state = load_state()
    today = date.today().isoformat()
    daily_limit = get_daily_limit()

    print(f"\n=== EURES Instant Send Status ===")
    print(f"Warmup Day: {get_warmup_day()}")
    print(f"Daily Limit: {daily_limit}/domain")
    print(f"Last Run: {state.get('last_run', 'Never')}")
    print(f"Total Sent: {len(state.get('sent_emails', []))}")
    print(f"Permanent Failures: {len(state.get('permanent_failures', []))}")
    print()

    print(f"Today's sends:")
    today_counts = state.get("daily_counts", {}).get(today, {})
    for sender in A2_SENDERS:
        count = today_counts.get(sender, 0)
        print(f"  {sender}: {count}/{daily_limit}")

    print()
    print("Available contacts:")
    for country, filepath in COUNTRY_FILES.items():
        if filepath.exists():
            with open(filepath) as f:
                total = sum(1 for _ in f) - 1
            print(f"  {country}: {total}")


def main():
    parser = argparse.ArgumentParser(description="EURES Instant Send via A2 SMTP")
    parser.add_argument("--dry-run", action="store_true", help="Simulate sending")
    parser.add_argument("--limit", type=int, help="Max emails to send")
    parser.add_argument("--country", help="Specific country (SE, DK, NO, FI)")
    parser.add_argument("--status", action="store_true", help="Show status")

    args = parser.parse_args()

    if args.status:
        show_status()
        return

    countries = [args.country.upper()] if args.country else None
    run_campaign(countries=countries, limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
