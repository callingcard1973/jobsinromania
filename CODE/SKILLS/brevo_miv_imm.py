#!/usr/bin/env python3
"""MIV_IMM_CORPORATE Brevo Campaign - with anti-spam protection.
Sends personalized emails to fresh ANOFM jobs (1-5 positions, corporate only).
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import csv
import json
import subprocess
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from skills_common import to_ascii
from brevo_safe_sender import BrevoSafeSender, SpamDetectedError, HighBounceRateError

load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

API_KEY = os.getenv("BREVO_MIVROMANIA_API_KEY")
SENDER_EMAIL = "office@mivromania.info"
SENDER_NAME = "MIV Romania"
DAILY_LIMIT = 290

FRESH_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/ANOFM_FRESH/")
TEMPLATE_FILE = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/MIV_IMM/templates/01_romanian.txt")
STATE_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/brevo_state/MIV_IMM_state.json")
MASTER_CSV = Path("/opt/ACTIVE/OPENDATA/DATA/MIV_IMM_MASTER.csv")
FRESH_SCRAPER = "/opt/ACTIVE/INFRA/SKILLS/anofm_fresh_scraper.py"

from global_sent_tracker import GlobalSentTracker
TRACKER = GlobalSentTracker()


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"sent": [], "seen_job_ids": [], "last_scrape": None, "sent_today": 0, "last_send": None}


def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def log_to_master(contact, sent_time):
    fieldnames = ['sent_time', 'email', 'company', 'job_title', 'occupation',
                  'contact_name', 'city', 'job_id', 'job_url']
    file_exists = MASTER_CSV.exists()
    with open(MASTER_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            'sent_time': sent_time,
            'email': contact['email'],
            'company': contact['company'],
            'job_title': contact['job_title'],
            'occupation': contact.get('occupation', ''),
            'contact_name': contact.get('contact_name', ''),
            'city': contact.get('city', ''),
            'job_id': contact.get('job_id', ''),
            'job_url': contact.get('job_url', '')
        })


def load_template():
    if TEMPLATE_FILE.exists():
        with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        lines = content.strip().split('\n')
        subject = lines[0].replace("Subject:", "").strip()
        body = '\n'.join(lines[2:])
        return subject, body
    return ("{company} - {job_title} - propunere colaborare", "Am vazut ca angajati...")


def run_fresh_scraper():
    print("Running fresh scraper...")
    result = subprocess.run(["/opt/ACTIVE/INFRA/venv/bin/python3", FRESH_SCRAPER], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Scraper error: {result.stderr}")
    else:
        print(result.stdout)


def load_fresh_contacts(state):
    sent_set = set(state.get("sent", []))
    contacts = []
    fresh_files = sorted(FRESH_DIR.glob("fresh_*.csv"), key=lambda x: x.stat().st_mtime, reverse=True)
    for csv_file in fresh_files:
        with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get('email', '').strip().lower()
                if not email or '@' not in email:
                    continue
                if email in sent_set:
                    continue
                can_send, reason = TRACKER.can_send(email, campaign="MIV_IMM")
                if not can_send:
                    continue
                sent_set.add(email)
                contacts.append({
                    "email": email,
                    "company": row.get('company', '')[:100],
                    "job_title": row.get('job_title', '')[:100],
                    "occupation": row.get('occupation', '')[:100],
                    "contact_name": row.get('contact_name', ''),
                    "contact_title": row.get('contact_title', ''),
                    "city": row.get('city', ''),
                    "positions": row.get('positions', ''),
                    "job_id": row.get('job_id', ''),
                    "job_url": row.get('job_url', '')
                })
    return contacts


def personalize_email(contact, subject_tpl, body_tpl):
    greeting = "Buna ziua"
    if contact.get("contact_name"):
        greeting = f"Buna ziua, {contact['contact_name']}"
    subject = to_ascii(subject_tpl.format(
        company=contact["company"],
        job_title=contact["job_title"],
        occupation=contact.get("occupation", ""),
        city=contact.get("city", "")
    ))
    body = to_ascii(body_tpl.format(
        company=contact["company"],
        job_title=contact["job_title"],
        occupation=contact.get("occupation", contact["job_title"]),
        greeting=greeting,
        contact_name=contact.get("contact_name", ""),
        city=contact.get("city", ""),
        job_url=contact.get("job_url", "")
    ))
    return subject, body


def send_batch(skip_scrape=False, dry_run=False):
    print(f"\n=== MIV_IMM_CORPORATE - {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
    if not skip_scrape:
        run_fresh_scraper()
    state = load_state()
    today = datetime.now().strftime("%Y-%m-%d")
    if state.get("last_send") != today:
        state["sent_today"] = 0
    remaining_today = DAILY_LIMIT - state["sent_today"]
    if remaining_today <= 0:
        print(f"Daily limit reached ({DAILY_LIMIT})")
        return
    contacts = load_fresh_contacts(state)
    print(f"Fresh contacts available: {len(contacts)}")
    if not contacts:
        print("No fresh contacts to send")
        return
    batch = contacts[:remaining_today]
    subject_tpl, body_tpl = load_template()

    sender = BrevoSafeSender(API_KEY, SENDER_EMAIL, SENDER_NAME, batch_size=1, wait_minutes=4, dry_run=dry_run)
    def on_sent(contact, success, msg):
        if success:
            state["sent"].append(contact["email"])
            TRACKER.mark_sent(contact["email"], campaign="MIV_IMM", sender="brevo_mivromania")
            log_to_master(contact, datetime.now().isoformat())
    try:
        sent_count = sender.send_batch_safe(batch, subject_tpl, body_tpl, personalize_fn=personalize_email, on_sent=on_sent)
        state["sent_today"] = state.get("sent_today", 0) + sent_count
        state["last_send"] = today
        save_state(state)
        print(f"\nSent: {sent_count}, Total: {len(state['sent'])}, Remaining today: {DAILY_LIMIT - state['sent_today']}")
    except (SpamDetectedError, HighBounceRateError) as e:
        print(f"\n!!! STOPPED: {e}")
        save_state(state)


def show_status():
    state = load_state()
    contacts = load_fresh_contacts(state)
    fresh_files = list(FRESH_DIR.glob("fresh_*.csv"))
    print(f"\n=== MIV_IMM_CORPORATE STATUS ===")
    print(f"Fresh files: {len(fresh_files)}")
    print(f"Available contacts: {len(contacts)}")
    print(f"Total sent: {len(state.get('sent', []))}")
    print(f"Today: {state.get('sent_today', 0)}/{DAILY_LIMIT}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--status', '-s', action='store_true')
    parser.add_argument('--reset', action='store_true')
    parser.add_argument('--send-only', action='store_true', help='Send without scraping')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if args.reset:
        save_state({"sent": [], "seen_job_ids": [], "last_scrape": None, "sent_today": 0, "last_send": None})
        print("State reset")
    elif args.status:
        show_status()
    else:
        send_batch(skip_scrape=args.send_only, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
