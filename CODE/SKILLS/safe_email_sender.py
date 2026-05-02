#!/usr/bin/env python3
"""
Safe Email Sender - 1 email every 3 minutes with spam verification

Supports both A2 SMTP and Brevo API with:
- 3-minute wait between emails
- IMAP/API spam checking after each send
- 28-day warmup schedule
- Automatic stop on spam detection

Usage:
    # Check status for a campaign
    python3 safe_email_sender.py --campaign HORECA2026 --status

    # Send via A2 only
    python3 safe_email_sender.py --campaign HORECA2026 --a2-only --limit 60

    # Send via Brevo only
    python3 safe_email_sender.py --campaign HORECA2026 --brevo-only --limit 100

    # Send via specific domain/sender
    python3 safe_email_sender.py --domain horecaworkers.eu --limit 50
    python3 safe_email_sender.py --brevo mivromania --limit 100

    # Test mode (dry run)
    python3 safe_email_sender.py --campaign HORECA2026 --test --limit 5

Campaigns supported:
    - HORECA2026 (3 A2 domains + 4 Brevo senders)
    - HORECAWORKERS_A2 (horecaworkers.eu A2 only)
    - Any campaign with contacts/contacts.csv
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import csv
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from itertools import cycle

load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

# Import safe senders
from a2_safe_sender import A2SafeSender, SpamDetectedError as A2SpamError, HighBounceRateError as A2BounceError
from brevo_safe_sender import BrevoSafeSender, SpamDetectedError as BrevoSpamError, HighBounceRateError as BrevoBounceError
from email_sender_rules import SenderRules
from skills_common import to_ascii

# Configuration
WAIT_MINUTES = 3  # Wait 3 minutes between sends
MAX_RETRIES = 3
RETRY_DELAY = 30

# 28-day warmup schedule
WARMUP_SCHEDULE = [
    (1, 3, 20),
    (4, 7, 50),
    (8, 14, 100),
    (15, 21, 200),
    (22, 28, 290),
    (29, 999, 290),
]

# A2 domains available
A2_DOMAINS = {
    'horecaworkers.eu': 'A2_HORECAWORKERS_EU_PASSWORD',
    'meatworkers.eu': 'A2_MEATWORKERS_EU_PASSWORD',
    'electricjobs.eu': 'A2_ELECTRICJOBS_EU_PASSWORD',
    'mechanicjobs.eu': 'A2_MECHANICJOBS_EU_PASSWORD',
    'farmworkers.eu': 'A2_FARMWORKERS_EU_PASSWORD',
    'factoryjobs.eu': 'A2_FACTORYJOBS_EU_PASSWORD',
    'warehouseworkers.eu': 'A2_WAREHOUSEWORKERS_EU_PASSWORD',
    'horecaworkers2026.eu': 'A2_HORECAWORKERS2026_EU_PASSWORD',
    'horecaworkers2026.com': 'A2_HORECAWORKERS2026_COM_PASSWORD',
    'horecaworkers2026.online': 'A2_HORECAWORKERS2026_ONLINE_PASSWORD',
}

# Brevo senders available
BREVO_SENDERS = {
    'cifn': ('BREVO_CIFN_API_KEY', 'office@cifn.info'),
    'interjob': ('BREVO_INTERJOB_API_KEY', 'noreply@interjob.ro'),
    'nepalezi': ('BREVO_NEPALEZI_API_KEY', 'office@nepalezi.com'),
    'expatsinromania': ('BREVO_EXPATSINROMANIA_API_KEY', 'office@expatsinromania.org'),
    'mivromania': ('BREVO_MIVROMANIA_API_KEY', 'office@mivromania.info'),
    'mivromania_online': ('BREVO_MIVROMANIA_ONLINE_API_KEY', 'office@mivromania.online'),
    'buildjobs': ('BREVO_BUILDJOBS_API_KEY', 'office@buildjobs.eu'),
    'factoryjobs': ('BREVO_FACTORYJOBS_API_KEY', 'office@factoryjobs.eu'),
    'careworkers': ('BREVO_CAREWORKERS_API_KEY', 'office@careworkers.eu'),
}

# Campaign configurations
CAMPAIGNS = {
    'HORECA2026': {
        'contacts': '/opt/ACTIVE/EMAIL/CAMPAIGNS/HORECA2026/contacts/contacts_sorted.csv',
        'templates': '/opt/ACTIVE/EMAIL/CAMPAIGNS/HORECA2026/templates',
        'state': '/opt/ACTIVE/EMAIL/CAMPAIGNS/HORECA2026/state_safe.json',
        'logs': '/opt/ACTIVE/EMAIL/CAMPAIGNS/HORECA2026/logs',
        'sender_name': 'Tudor Seicarescu',
        'a2_domains': ['horecaworkers2026.eu', 'horecaworkers2026.com', 'horecaworkers2026.online'],
        'brevo_senders': ['cifn', 'interjob', 'nepalezi', 'expatsinromania'],
    },
    'HORECAWORKERS_A2': {
        'contacts': '/opt/ACTIVE/EMAIL/CAMPAIGNS/HORECAWORKERS_A2/contacts/contacts.csv',
        'templates': '/opt/ACTIVE/EMAIL/CAMPAIGNS/HORECAWORKERS_A2/templates',
        'state': '/opt/ACTIVE/EMAIL/CAMPAIGNS/HORECAWORKERS_A2/state_safe.json',
        'logs': '/opt/ACTIVE/EMAIL/CAMPAIGNS/HORECAWORKERS_A2/logs',
        'sender_name': 'Tudor Seicarescu',
        'a2_domains': ['horecaworkers.eu'],
        'brevo_senders': [],
    },
}

CAMPAIGNS_DIR = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS')


def get_warmup_day(state: dict) -> int:
    first_send = state.get("first_send_date")
    if not first_send:
        return 1
    try:
        first_date = datetime.fromisoformat(first_send).date()
        today = datetime.now().date()
        return (today - first_date).days + 1
    except:
        return 1


def get_daily_limit(warmup_day: int) -> int:
    for start, end, limit in WARMUP_SCHEDULE:
        if start <= warmup_day <= end:
            return limit
    return 290


def load_template(template_dir: Path):
    templates = list(Path(template_dir).glob("*.txt"))
    if not templates:
        raise FileNotFoundError(f"No templates found in {template_dir}")

    with open(templates[0]) as f:
        content = f.read()

    lines = content.split('\n')
    subject = lines[0].replace('Subject: ', '').strip()
    body = '\n'.join(lines[2:]).strip()
    return subject, body


def load_state(state_file: str) -> dict:
    if os.path.exists(state_file):
        with open(state_file) as f:
            return json.load(f)
    return {
        "sent": [],
        "failed": [],
        "permanent_failures": [],
        "sender_counts": {},
        "last_send": None,
        "first_send_date": None,
        "last_date": None,
        "spam_detected": False,
    }


def save_state(state: dict, state_file: str):
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)


def reset_daily_counts(state: dict) -> dict:
    today = datetime.now().strftime('%Y-%m-%d')
    if state.get("last_date") != today:
        state["sender_counts"] = {}
        state["last_date"] = today
    return state


def log_send(log_dir: Path, email: str, sender: str, status: str, msg: str):
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"safe_send_{datetime.now().strftime('%Y%m%d')}.log"
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(log_file, 'a') as f:
        f.write(f"{timestamp} | {status} | {sender} | {email} | {msg}\n")


def send_campaign(config: dict, args):
    """Send emails for a campaign."""
    state_file = config['state']
    log_dir = Path(config['logs'])

    state = load_state(state_file)

    if args.reset_spam:
        state["spam_detected"] = False
        save_state(state, state_file)
        print("Spam flag reset.")
        return

    if state.get("spam_detected"):
        print("!" * 60)
        print("CAMPAIGN STOPPED: Spam detected!")
        print("Run with --reset-spam to resume.")
        print("!" * 60)
        return

    state = reset_daily_counts(state)
    warmup_day = get_warmup_day(state)
    daily_limit = get_daily_limit(warmup_day)

    print(f"Campaign: {args.campaign}")
    print(f"Warmup day: {warmup_day}")
    print(f"Daily limit per sender: {daily_limit}")
    print(f"Wait: {WAIT_MINUTES} minutes between sends")
    print(f"Mode: {'TEST' if args.test else 'LIVE'}")
    print("-" * 60)

    # Load template
    subject, body = load_template(config['templates'])
    print(f"Subject: {subject}")

    # Load contacts
    sent_emails = set(state.get("sent", []))
    failed_emails = set(state.get("permanent_failures", []))

    with open(config['contacts']) as f:
        contacts = list(csv.DictReader(f))

    to_send = []
    for c in contacts:
        email = c.get('email', '').strip().lower()
        if email and '@' in email and email not in sent_emails and email not in failed_emails:
            to_send.append(c)

    print(f"Previously sent: {len(sent_emails)}")
    print(f"Contacts to send: {len(to_send)}")

    if not to_send:
        print("No contacts to send!")
        return

    to_send = to_send[:args.limit]
    print(f"Will send: {len(to_send)}")

    # Build senders
    senders = []
    sender_name = config.get('sender_name', 'Office')

    if not args.brevo_only:
        for domain in config.get('a2_domains', []):
            if domain in A2_DOMAINS:
                try:
                    sender = A2SafeSender(
                        domain=domain,
                        sender_name=sender_name,
                        wait_minutes=0,
                        dry_run=args.test
                    )
                    senders.append({
                        "type": "a2",
                        "name": f"a2_{domain}",
                        "sender": sender,
                        "email": f"office@{domain}"
                    })
                    print(f"Initialized A2: {domain}")
                except Exception as e:
                    print(f"ERROR A2 {domain}: {e}")

    if not args.a2_only:
        for name in config.get('brevo_senders', []):
            if name in BREVO_SENDERS:
                api_env, email = BREVO_SENDERS[name]
                api_key = os.getenv(api_env)
                if api_key:
                    try:
                        sender = BrevoSafeSender(
                            api_key=api_key,
                            sender_email=email,
                            sender_name=sender_name,
                            batch_size=1,
                            wait_minutes=0,
                            dry_run=args.test
                        )
                        senders.append({
                            "type": "brevo",
                            "name": f"brevo_{name}",
                            "sender": sender,
                            "email": email
                        })
                        print(f"Initialized Brevo: {name}")
                    except Exception as e:
                        print(f"ERROR Brevo {name}: {e}")

    if not senders:
        print("No senders available!")
        return

    print(f"Total senders: {len(senders)}")

    if args.test:
        print("\n=== TEST MODE ===")
        sender_cycle = cycle(senders)
        for i, c in enumerate(to_send[:min(9, len(to_send))]):
            s = next(sender_cycle)
            print(f"  [{i+1}] {c['email']} -> {s['email']} ({s['type']})")
        return

    # Set first send date
    if not state.get("first_send_date"):
        state["first_send_date"] = datetime.now().isoformat()

    rules = SenderRules(args.campaign.lower())
    sender_cycle = cycle(senders)

    sent_count = 0
    for i, contact in enumerate(to_send):
        email = contact['email'].strip().lower()
        company = to_ascii(contact.get('company_name', contact.get('company', '')))

        # Get available sender
        sender_info = None
        checked = 0
        while checked < len(senders):
            candidate = next(sender_cycle)
            if state["sender_counts"].get(candidate["name"], 0) < daily_limit:
                sender_info = candidate
                break
            checked += 1

        if not sender_info:
            print(f"\nAll senders reached daily limit!")
            break

        sender = sender_info["sender"]
        sender_key = sender_info["name"]
        sender_email = sender_info["email"]

        personalized_body = body.replace('{company}', company)

        print(f"\n[{i+1}/{len(to_send)}] {email} -> {sender_email}")

        # Pre-send validation
        can_send, reason = rules.check_send_allowed(email)
        if not can_send:
            print(f"  SKIP: {reason}")
            log_send(log_dir, email, sender_key, "SKIP", reason)
            continue

        # Send with retry
        success = False
        last_error = ""
        for attempt in range(MAX_RETRIES):
            try:
                success, msg = sender.send_one(
                    to_email=email,
                    subject=subject,
                    body=personalized_body
                )

                if success:
                    print(f"  OK: Sent")
                    state["sent"].append(email)
                    state["sender_counts"][sender_key] = state["sender_counts"].get(sender_key, 0) + 1
                    state["last_send"] = datetime.now().isoformat()
                    sent_count += 1
                    log_send(log_dir, email, sender_key, "OK", "sent")
                    break
                else:
                    last_error = msg
                    print(f"  FAIL ({attempt+1}): {msg}")

                    bounce_type = rules.handle_send_result(email, False, msg)
                    if bounce_type:
                        state["permanent_failures"].append(email)
                        log_send(log_dir, email, sender_key, "BOUNCE", bounce_type)
                        break

                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY)

            except (A2SpamError, BrevoSpamError) as e:
                print(f"\n{'!' * 60}")
                print(f"SPAM DETECTED: {e.message}")
                print(f"{'!' * 60}")
                state["spam_detected"] = True
                save_state(state, state_file)
                log_send(log_dir, email, sender_key, "SPAM", str(e.message))
                return

            except (A2BounceError, BrevoBounceError) as e:
                print(f"  HIGH BOUNCE: {e.message}")
                log_send(log_dir, email, sender_key, "HIGH_BOUNCE", str(e.message))
                break

            except Exception as e:
                last_error = str(e)
                print(f"  ERROR ({attempt+1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)

        if not success and last_error:
            state["failed"].append(email)
            log_send(log_dir, email, sender_key, "FAIL", last_error)

        save_state(state, state_file)

        # Wait before next
        if i < len(to_send) - 1 and success:
            print(f"  Waiting {WAIT_MINUTES} minutes...")
            time.sleep(WAIT_MINUTES * 60)

    print(f"\n{'=' * 60}")
    print(f"COMPLETE: {sent_count}/{len(to_send)}")
    print(f"Total sent: {len(state['sent'])}")


def show_status(config: dict, campaign_name: str):
    """Show campaign status."""
    state = load_state(config['state'])

    with open(config['contacts']) as f:
        contacts = list(csv.DictReader(f))

    with_email = [c for c in contacts if c.get('email')]
    sent = set(state.get("sent", []))
    remaining = len([c for c in with_email if c['email'].strip().lower() not in sent])

    warmup_day = get_warmup_day(state)
    daily_limit = get_daily_limit(warmup_day)

    print("=" * 60)
    print(f"SAFE EMAIL SENDER - {campaign_name}")
    print("=" * 60)
    print(f"Warmup day: {warmup_day}")
    print(f"Daily limit per sender: {daily_limit}")
    print(f"Wait between sends: {WAIT_MINUTES} minutes")
    print()
    print(f"Contacts: {len(with_email)}")
    print(f"Sent: {len(sent)}")
    print(f"Remaining: {remaining}")
    print(f"Spam detected: {state.get('spam_detected', False)}")
    print(f"Last send: {state.get('last_send', 'Never')}")
    print()
    print("A2 domains:", ', '.join(config.get('a2_domains', [])) or 'None')
    print("Brevo senders:", ', '.join(config.get('brevo_senders', [])) or 'None')


def main():
    parser = argparse.ArgumentParser(description="Safe Email Sender with spam checking")
    parser.add_argument('--campaign', '-c', help='Campaign name (e.g., HORECA2026)')
    parser.add_argument('--domain', '-d', help='Single A2 domain to use')
    parser.add_argument('--brevo', '-b', help='Single Brevo sender to use')
    parser.add_argument('--limit', '-l', type=int, default=20, help='Max emails to send')
    parser.add_argument('--status', '-s', action='store_true', help='Show status')
    parser.add_argument('--test', '-t', action='store_true', help='Test mode (dry run)')
    parser.add_argument('--a2-only', action='store_true', help='Use A2 senders only')
    parser.add_argument('--brevo-only', action='store_true', help='Use Brevo senders only')
    parser.add_argument('--reset-spam', action='store_true', help='Reset spam flag')
    parser.add_argument('--list', action='store_true', help='List available campaigns')
    args = parser.parse_args()

    if args.list:
        print("Available campaigns:")
        for name in CAMPAIGNS:
            print(f"  - {name}")
        print("\nA2 domains:")
        for domain in A2_DOMAINS:
            print(f"  - {domain}")
        print("\nBrevo senders:")
        for name in BREVO_SENDERS:
            print(f"  - {name}")
        return

    if not args.campaign and not args.domain and not args.brevo:
        parser.print_help()
        return

    # Get campaign config
    if args.campaign:
        if args.campaign.upper() not in CAMPAIGNS:
            print(f"Unknown campaign: {args.campaign}")
            print(f"Available: {', '.join(CAMPAIGNS.keys())}")
            return
        config = CAMPAIGNS[args.campaign.upper()]
    else:
        # Build config from domain/brevo args
        config = {
            'contacts': None,
            'templates': None,
            'state': f'/tmp/safe_sender_{args.domain or args.brevo}.json',
            'logs': Path('/opt/ACTIVE/INFRA/LOGS/safe_sender'),
            'sender_name': 'Office',
            'a2_domains': [args.domain] if args.domain else [],
            'brevo_senders': [args.brevo] if args.brevo else [],
        }
        print("Note: Using single sender mode. Specify --campaign for full campaign.")
        return

    if args.status:
        show_status(config, args.campaign.upper())
    else:
        send_campaign(config, args)


if __name__ == "__main__":
    main()
