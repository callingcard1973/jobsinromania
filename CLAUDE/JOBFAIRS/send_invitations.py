#!/usr/bin/env python3
"""
Job Fair Employer Invitation Sender — Brevo email campaign.

Sends invitation emails to employers for a specific job fair event.
Reuses CampaignSender and SenderRules from shared infrastructure.

Usage:
    python send_invitations.py --event arges_2025-04-15 --source ejd_companies.csv --lang en --test
    python send_invitations.py --event arges_2025-04-15 --source ejd_companies.csv --lang en --limit 290
    python send_invitations.py --event arges_2025-04-15 --status
"""
import sys
import os

SHARED_PATHS = ['/opt/SCRAPERS/SCRIPTS/SHARED', '/shared',
                '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED']
for p in SHARED_PATHS:
    if os.path.exists(p):
        sys.path.insert(0, p)
        break

import csv
import random
import time
import json
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

for env_path in ['/opt/EMAIL/.env', '/app/.env']:
    if os.path.exists(env_path):
        load_dotenv(env_path)
        break

from campaign_sender import CampaignSender
from email_sender_rules import SenderRules

SCRIPT_DIR = Path(__file__).parent
EVENTS_DIR = SCRIPT_DIR / "events"
TEMPLATES_DIR = SCRIPT_DIR / "templates"
CAMPAIGN_NAME = "jobfair_invitations"
SENDER = "brevo_interjob"  # office@interjob.ro
DELAY_MIN = 180
DELAY_MAX = 300
DAILY_LIMIT = 290


def load_event(event_slug):
    """Load event info from events/<slug>/event_info.json."""
    event_dir = EVENTS_DIR / event_slug
    info_file = event_dir / "event_info.json"
    if not info_file.exists():
        print(f"ERROR: Event not found: {info_file}")
        print(f"Available events:")
        if EVENTS_DIR.exists():
            for d in sorted(EVENTS_DIR.iterdir()):
                if d.is_dir():
                    print(f"  {d.name}")
        sys.exit(1)
    return json.loads(info_file.read_text(encoding='utf-8')), event_dir


def load_template(lang):
    """Load email template for given language."""
    template_file = TEMPLATES_DIR / f"email_employer_{lang}.html"
    if not template_file.exists():
        print(f"ERROR: Template not found: {template_file}")
        print(f"Available: {', '.join(f.stem for f in TEMPLATES_DIR.glob('email_employer_*.html'))}")
        sys.exit(1)
    return template_file.read_text(encoding='utf-8')


def render_template(template, event_info, contact):
    """Replace template variables with actual values."""
    html = template
    html = html.replace('{company}', contact.get('company', contact.get('name', 'Your Company')))
    html = html.replace('{contact_person}', contact.get('contact_person', contact.get('name', '')))
    html = html.replace('{county}', event_info['county'])
    html = html.replace('{date}', event_info['date'])
    html = html.replace('{venue}', event_info['venue'])
    html = html.replace('{registration_url}', event_info.get('registration_url', 'https://interjob.ro/jobfair/employer.html'))
    return html


def get_subject(lang, event_info):
    """Get email subject line for given language."""
    county = event_info['county']
    date = event_info['date']
    subjects = {
        'en': f"You're invited: Romania International Job Fair — {county}, {date}",
        'ro': f"Invitatie: Targ International de Locuri de Munca — {county}, {date}",
        'de': f"Einladung: Internationale Jobmesse Rumanien — {county}, {date}",
    }
    return subjects.get(lang, subjects['en'])


def load_state(event_dir):
    """Load campaign state for this event."""
    state_file = event_dir / "invitation_state.json"
    if state_file.exists():
        with open(state_file) as f:
            return json.load(f)
    return {"sent": [], "failed": [], "permanent_failures": [],
            "last_send": None, "daily_sent": 0, "last_date": None}


def save_state(state, event_dir):
    """Save campaign state."""
    state_file = event_dir / "invitation_state.json"
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)


def get_daily_sent(state):
    """Get/reset daily sent counter."""
    today = datetime.now().strftime('%Y-%m-%d')
    if state.get("last_date") != today:
        state["daily_sent"] = 0
        state["last_date"] = today
    return state.get("daily_sent", 0)


def log_send(event_dir, email, status, msg):
    """Log send attempt."""
    log_dir = event_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"sent_{datetime.now().strftime('%Y%m%d')}.log"
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(log_file, 'a') as f:
        f.write(f"{timestamp} | {status} | {email} | {msg}\n")


def is_valid_email(email):
    """Basic email format validation."""
    if not email or '@' not in email:
        return False, "Missing @"
    try:
        email.encode('ascii')
    except UnicodeEncodeError:
        return False, "Non-ASCII characters"
    local, domain = email.rsplit('@', 1)
    if local.startswith('.') or local.endswith('.'):
        return False, "Invalid local part"
    if '.' not in domain or len(domain) < 4:
        return False, "Invalid domain"
    return True, ""


def show_status(event_slug):
    """Show campaign status for an event."""
    event_info, event_dir = load_event(event_slug)
    state = load_state(event_dir)

    print(f"\nEvent: {event_info['county']} — {event_info['date']}")
    print(f"Venue: {event_info['venue']}")
    print(f"Status: {event_info.get('status', 'unknown')}")
    print(f"\n--- Campaign State ---")
    print(f"  Sent: {len(state.get('sent', []))}")
    print(f"  Failed: {len(state.get('failed', []))}")
    print(f"  Permanent failures: {len(state.get('permanent_failures', []))}")
    print(f"  Daily sent: {get_daily_sent(state)}/{DAILY_LIMIT}")
    print(f"  Last send: {state.get('last_send', 'Never')}")


def main():
    parser = argparse.ArgumentParser(description='Send job fair invitation emails')
    parser.add_argument('--event', required=True, help='Event slug (e.g., arges_2025-04-15)')
    parser.add_argument('--source', help='CSV file with employer contacts')
    parser.add_argument('--lang', default='en', choices=['en', 'ro', 'de'], help='Email language')
    parser.add_argument('--test', action='store_true', help='Dry run — show what would be sent')
    parser.add_argument('--limit', type=int, default=10, help='Max emails to send')
    parser.add_argument('--status', action='store_true', help='Show campaign status')
    parser.add_argument('--reply-to', default='office@interjob.ro', help='Reply-to email')
    args = parser.parse_args()

    if args.status:
        show_status(args.event)
        return

    event_info, event_dir = load_event(args.event)

    print(f"JOB FAIR INVITATION CAMPAIGN — {datetime.now()}")
    print(f"Event: {event_info['county']} — {event_info['date']}")
    print(f"Sender: {SENDER}")
    print(f"Language: {args.lang}")
    print(f"Mode: {'TEST' if args.test else 'LIVE'}")
    print(f"Limit: {args.limit}")
    print("-" * 50)

    # Load template
    template = load_template(args.lang)
    subject = get_subject(args.lang, event_info)

    # Load state
    state = load_state(event_dir)
    sent_emails = set(state.get("sent", []))
    failed_emails = set(state.get("failed", []))
    perm_failures = set(state.get("permanent_failures", []))
    skip_emails = sent_emails | failed_emails | perm_failures
    daily_sent = get_daily_sent(state)
    remaining_today = DAILY_LIMIT - daily_sent

    print(f"Previously sent: {len(sent_emails)}")
    print(f"Failed/skipped: {len(failed_emails | perm_failures)}")
    print(f"Sent today: {daily_sent}/{DAILY_LIMIT}")

    if remaining_today <= 0 and not args.test:
        print("Daily limit reached!")
        return

    # Load contacts
    if not args.source:
        print("ERROR: --source CSV file required (e.g., --source ejd_companies.csv)")
        return

    source_path = Path(args.source)
    if not source_path.exists():
        # Try relative to script dir
        source_path = SCRIPT_DIR / args.source
    if not source_path.exists():
        print(f"ERROR: Source file not found: {args.source}")
        return

    with open(source_path, encoding='utf-8') as f:
        contacts = list(csv.DictReader(f))

    # Filter contacts
    to_send = []
    for c in contacts:
        email = c.get('email', c.get('Email', '')).strip().lower()
        if not email or email in skip_emails:
            continue
        valid, reason = is_valid_email(email)
        if not valid:
            if email not in failed_emails:
                state["failed"].append(email)
                failed_emails.add(email)
            continue
        c['_email'] = email
        to_send.append(c)

    print(f"Contacts to send: {len(to_send)}")

    if not to_send:
        print("No contacts to send!")
        save_state(state, event_dir)
        return

    to_send = to_send[:min(args.limit, remaining_today)]
    print(f"Will send: {len(to_send)}")

    # Test mode
    if args.test:
        print(f"\n=== TEST MODE ===")
        print(f"Subject: {subject}")
        print()
        for c in to_send[:10]:
            company = c.get('company', c.get('Company', c.get('name', '')))
            print(f"  {c['_email']:45s} | {company}")
        if len(to_send) > 10:
            print(f"  ... and {len(to_send) - 10} more")

        # Render one sample
        if to_send:
            print(f"\n--- Sample email (first contact) ---")
            sample = render_template(template, event_info, to_send[0])
            # Show first 500 chars of rendered HTML
            print(sample[:500] + "...")
        return

    # Live send
    sender = CampaignSender(campaign=CAMPAIGN_NAME, senders=[SENDER])
    rules = SenderRules(CAMPAIGN_NAME)

    sent_count = 0
    for i, contact in enumerate(to_send):
        email = contact['_email']
        company = contact.get('company', contact.get('Company', contact.get('name', '')))

        body = render_template(template, event_info, contact)
        print(f"\n[{i+1}/{len(to_send)}] {email} ({company})...")

        can_send, reason = rules.check_send_allowed(email)
        if not can_send:
            print(f"  SKIP: {reason}")
            log_send(event_dir, email, "SKIP", reason)
            continue

        try:
            success, msg = sender.send(
                sender_name=SENDER,
                to_email=email,
                subject=subject,
                body=body,
                display_name="InterJob Solutions - Job Fair",
                reply_to=args.reply_to
            )

            if success:
                print(f"  OK: {msg}")
                state["sent"].append(email)
                state["daily_sent"] = state.get("daily_sent", 0) + 1
                state["last_send"] = datetime.now().isoformat()
                sent_count += 1
                log_send(event_dir, email, "OK", msg)
            else:
                print(f"  FAIL: {msg}")
                bounce_type = rules.handle_send_result(email, False, msg)
                if bounce_type:
                    print(f"  BOUNCE: {bounce_type}")
                    state["permanent_failures"].append(email)
                else:
                    state["failed"].append(email)
                log_send(event_dir, email, "FAIL", msg)

        except Exception as e:
            print(f"  ERROR: {e}")
            log_send(event_dir, email, "ERROR", str(e))

        save_state(state, event_dir)

        if i < len(to_send) - 1:
            delay = random.randint(DELAY_MIN, DELAY_MAX)
            print(f"  Waiting {delay}s...")
            time.sleep(delay)

    print(f"\n{'=' * 50}")
    print(f"COMPLETE: {sent_count}/{len(to_send)}")
    print(f"Total sent: {len(state['sent'])}")


if __name__ == "__main__":
    main()
