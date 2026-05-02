#!/usr/bin/env python3
"""
ANOFM Instant Send Skill

Scrapes ANOFM jobs and sends targeted emails to employers with:
- New jobs (posted today)
- Expiring jobs (within N days)

Filters:
- 1-20 positions (small to medium employers)
- Corporate email only (NO yahoo, gmail OK)
- Target sectors

RASPI RULES:
- 4-minute wait between emails
- Spam check after each send via Brevo API
- On spam detection: skip sender for today, continue with others
- Uses BrevoSafeSender for proper spam verification

Usage:
    python3 anofm_instant_send.py --dry-run
    python3 anofm_instant_send.py --new-today --limit 100
    python3 anofm_instant_send.py --expiring 7 --limit 100
    python3 anofm_instant_send.py --new-today --expiring 7 --limit 200
    python3 anofm_instant_send.py --status
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

# Unbuffered stdout for real-time logging
sys.stdout.reconfigure(line_buffering=True)

import os
import csv
import json
import time
import argparse
import requests
import threading
from queue import Queue
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

from skills_common import to_ascii
from brevo_safe_sender import BrevoSafeSender, SpamDetectedError, HighBounceRateError
from email_sender_rules import SenderRules
from smtp_fallback import SmtpFallback, SmtpConfig

# Paths
CAMPAIGN_NAME = "ANOFM_INSTANT"
CAMPAIGN_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_INSTANT")
ANOFM_DATA_DIR = Path("/mnt/hdd/SCRAPER_DATA/csv/ANOFM")
TEMPLATE_FILE = CAMPAIGN_DIR / "templates/01_intro.txt"
STATE_FILE = CAMPAIGN_DIR / "state.json"
LOG_DIR = CAMPAIGN_DIR / "logs"

LOG_DIR.mkdir(parents=True, exist_ok=True)

# Free email domains to exclude - NO YAHOO, GMAIL OK
# Yahoo has high spam filtering, causes delivery issues
FREE_DOMAINS = {
    'yahoo.com', 'yahoo.ro', 'yahoo.fr', 'yahoo.de', 'yahoo.co.uk',
    'ymail.com', 'rocketmail.com',  # Yahoo family
    'hotmail.com', 'outlook.com', 'live.com', 'live.ro', 'msn.com',  # Microsoft
    'icloud.com', 'me.com', 'mac.com',  # Apple
    'aol.com', 'mail.com', 'protonmail.com',
    'gmx.com', 'gmx.de', 'web.de', 'mail.ru', 'libero.it', 'wp.pl'
}
# NOTE: gmail.com is ALLOWED - good deliverability

# Target sectors (Romanian names from ANOFM)
TARGET_SECTORS = {
    'Agricultura / Zootehnie',
    'Turism / Alimentatie',
    'RESTAURANTE',
    'Productie / Logistica',
    'Constructii / Instalatii',
    'FABRICAREA ARTICOLELOR DE IMBRACAMINTE',
    'PRODUCTIE MOBILA',
    'SERVICE AUTO',
    'Au pair / Babysitter / Curatenie',
    'Altele'
}

# Sender mapping by sector
SECTOR_SENDER_MAP = {
    'Agricultura / Zootehnie': 'brevo_cifn',
    'Turism / Alimentatie': 'brevo_mivromania',
    'RESTAURANTE': 'brevo_mivromania',
    'Productie / Logistica': 'brevo_buildjobs',
    'FABRICAREA ARTICOLELOR DE IMBRACAMINTE': 'brevo_buildjobs',
    'PRODUCTIE MOBILA': 'brevo_buildjobs',
    'Constructii / Instalatii': 'brevo_factoryjobs',
    'SERVICE AUTO': 'brevo_factoryjobs',
    'Au pair / Babysitter / Curatenie': 'brevo_careworkers',
    'ASISTENTA SOCIALA': 'brevo_careworkers',
    'Medicina / Sanatate /Psihoterapie': 'brevo_careworkers',
}
DEFAULT_SENDER = 'brevo_interjob'

# Brevo sender configurations
BREVO_CONFIGS = {
    'brevo_interjob': {
        'api_key_env': 'BREVO_API_KEY',
        'email': 'office@interjob.ro',
        'name': 'INTERJOB Solutions'
    },
    'brevo_cifn': {
        'api_key_env': 'BREVO_CIFN_API_KEY',
        'email': 'office@cifn.info',
        'name': 'CIFN Romania'
    },
    'brevo_mivromania': {
        'api_key_env': 'BREVO_MIVROMANIA_API_KEY',
        'email': 'office@mivromania.info',
        'name': 'MIV Romania'
    },
    'brevo_buildjobs': {
        'api_key_env': 'BREVO_BUILDJOBS_API_KEY',
        'email': 'office@buildjobs.eu',
        'name': 'Build Jobs EU'
    },
    'brevo_factoryjobs': {
        'api_key_env': 'BREVO_FACTORYJOBS_API_KEY',
        'email': 'office@factoryjobs.eu',
        'name': 'Factory Jobs EU'
    },
    'brevo_careworkers': {
        'api_key_env': 'BREVO_CAREWORKERS_API_KEY',
        'email': 'office@careworkers.eu',
        'name': 'Care Workers EU'
    },
}

# Gmail sender configuration
GMAIL_CONFIG = {
    'gmail_elena': {
        'user_env': 'GMAIL_ELENA_USER',
        'password_env': 'GMAIL_ELENA_PASSWORD',
        'email': 'elena.manpower.dristor@gmail.com',
        'name': 'Elena - Manpower Dristor',
        'smtp_host': 'smtp.gmail.com',
        'smtp_port': 587,
        'daily_limit': 50,
        'wait_minutes': 5  # 5-minute wait for Gmail
    }
}

# RASPI Rules
DAILY_LIMIT_PER_SENDER = 290  # Brevo limit
GMAIL_DAILY_LIMIT = 50  # Gmail limit
WAIT_MINUTES = 4  # 4-minute wait between Brevo emails
GMAIL_WAIT_MINUTES = 5  # 5-minute wait between Gmail emails
DELAY_SECONDS = WAIT_MINUTES * 60  # 240 seconds for Brevo
GMAIL_DELAY_SECONDS = GMAIL_WAIT_MINUTES * 60  # 300 seconds for Gmail
COOLDOWN_DAYS = 14
SPAM_CHECK_ENABLED = True  # Check Brevo API for spam after each send

# Thread-safe state lock
_state_lock = threading.Lock()


def load_state():
    """Load state from file."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "sent_job_ids": [],
        "sent_emails": {},  # email -> last_sent_date
        "last_run": None,
        "daily_counts": {},  # date -> {sender -> count}
        "blocked_senders": {},  # date -> [blocked senders] (spam/bounce detected)
        "spam_stopped": None  # timestamp if ALL senders blocked
    }


def save_state(state):
    """Save state to file."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def get_latest_csv():
    """Find the most recent ANOFM CSV file by filename date."""
    files = sorted(ANOFM_DATA_DIR.glob("anofm_*.csv"), key=lambda x: x.name, reverse=True)
    return files[0] if files else None


def is_valid_email(email):
    """Check if email is valid for sending (corporate, no yahoo)."""
    if not email or '@' not in email:
        return False
    domain = email.split('@')[1].lower()
    # Reject free domains (yahoo, hotmail, etc.)
    if domain in FREE_DOMAINS:
        return False
    return True


def load_template(sender_name=None):
    """Load email template for specific sender."""
    # Try sender-specific template first
    if sender_name:
        sender_template = CAMPAIGN_DIR / f"templates/{sender_name}.txt"
        if sender_template.exists():
            template_file = sender_template
        else:
            template_file = TEMPLATE_FILE
    else:
        template_file = TEMPLATE_FILE

    with open(template_file) as f:
        content = f.read()
    lines = content.split('\n')
    subject = lines[0].replace('Subject: ', '').strip()
    body = '\n'.join(lines[2:]).strip()
    return subject, body


# Cache templates per sender
_template_cache = {}


def get_sender_for_sector(sector):
    """Get appropriate sender for sector."""
    return SECTOR_SENDER_MAP.get(sector, DEFAULT_SENDER)


def get_daily_count(state, sender):
    """Get today's send count for sender."""
    today = datetime.now().strftime('%Y-%m-%d')
    if today not in state.get("daily_counts", {}):
        state["daily_counts"] = {today: {}}
    return state["daily_counts"].get(today, {}).get(sender, 0)


def increment_daily_count(state, sender):
    """Increment daily send count for sender."""
    today = datetime.now().strftime('%Y-%m-%d')
    if today not in state.get("daily_counts", {}):
        state["daily_counts"] = {today: {}}
    state["daily_counts"][today][sender] = state["daily_counts"][today].get(sender, 0) + 1


def is_in_cooldown(state, email):
    """Check if email is in cooldown period."""
    email = email.lower()
    last_sent = state.get("sent_emails", {}).get(email)
    if not last_sent:
        return False
    try:
        last_date = datetime.fromisoformat(last_sent)
        return (datetime.now() - last_date).days < COOLDOWN_DAYS
    except (ValueError, TypeError):
        return False


def is_sender_blocked(state, sender):
    """Check if sender is blocked for today due to spam/bounce."""
    today = datetime.now().strftime('%Y-%m-%d')
    blocked = state.get("blocked_senders", {}).get(today, [])
    return sender in blocked


def block_sender(state, sender, reason="spam"):
    """Block sender for today due to spam/bounce detection."""
    today = datetime.now().strftime('%Y-%m-%d')
    if "blocked_senders" not in state:
        state["blocked_senders"] = {}
    if today not in state["blocked_senders"]:
        state["blocked_senders"][today] = []
    if sender not in state["blocked_senders"][today]:
        state["blocked_senders"][today].append(sender)
        print(f"\n*** SENDER {sender} BLOCKED for today ({reason}) ***")


def get_available_senders(state, include_gmail=True):
    """Get list of senders not blocked for today."""
    today = datetime.now().strftime('%Y-%m-%d')
    blocked = set(state.get("blocked_senders", {}).get(today, []))
    all_senders = set(BREVO_CONFIGS.keys())
    if include_gmail:
        all_senders.update(GMAIL_CONFIG.keys())
    return all_senders - blocked


def get_gmail_daily_count(state, sender='gmail_elena'):
    """Get today's send count for Gmail sender."""
    today = datetime.now().strftime('%Y-%m-%d')
    return state.get("daily_counts", {}).get(today, {}).get(sender, 0)


def is_gmail_available(state):
    """Check if Gmail sender is available (not blocked, under limit)."""
    if is_sender_blocked(state, 'gmail_elena'):
        return False
    count = get_gmail_daily_count(state)
    return count < GMAIL_DAILY_LIMIT


def check_brevo_spam(api_key, last_minutes=10):
    """
    Check Brevo API for spam complaints in the last N minutes.
    Returns (has_spam, complaint_count, details)
    """
    try:
        headers = {"api-key": api_key, "Content-Type": "application/json"}
        start_date = (datetime.now() - timedelta(minutes=last_minutes)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")

        resp = requests.get(
            "https://api.brevo.com/v3/smtp/statistics/events",
            headers=headers,
            params={
                "event": "complaint",
                "limit": 100,
                "startDate": start_date,
                "endDate": end_date
            },
            timeout=30
        )

        if resp.status_code == 200:
            data = resp.json()
            events = data.get("events", [])
            return len(events) > 0, len(events), events
        return False, 0, []
    except Exception as e:
        print(f"  WARNING: Spam check failed: {e}")
        return False, 0, []


def get_gmail_sender():
    """
    Get Gmail sender using shared SmtpFallback module.
    Returns SmtpFallback instance configured for gmail_elena only.
    """
    config = GMAIL_CONFIG.get('gmail_elena')
    gmail_password = os.getenv(config['password_env'])

    gmail_chain = [
        SmtpConfig(
            name='gmail_elena',
            host=config['smtp_host'],
            port=config['smtp_port'],
            user=config['email'],
            password=gmail_password,
            from_email=config['email'],
            from_name=config['name']
        )
    ]
    return SmtpFallback(smtp_chain=gmail_chain)


def send_gmail(to_email, subject, body, sender_name='gmail_elena'):
    """
    Send email via Gmail SMTP using shared SmtpFallback module.
    Returns (success, error_message)
    """
    sender = get_gmail_sender()
    success, via, msg = sender.send(to_email, subject, body)
    return success, msg if not success else None


def filter_jobs(csv_file, state, new_today=False, expiring_days=None):
    """
    Filter jobs from CSV based on criteria.

    Args:
        csv_file: Path to ANOFM CSV
        state: Current state dict
        new_today: Include jobs scraped today
        expiring_days: Include jobs expiring within N days

    Returns:
        List of filtered job dicts (deduplicated by email)
    """
    today = datetime.now().date()
    sent_job_ids = set(state.get("sent_job_ids", []))
    seen_emails = set()  # For deduplication within this batch

    filtered = []

    with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            job_id = row.get('job_id', '').strip()
            if not job_id:
                continue

            # Skip already sent
            if job_id in sent_job_ids:
                continue

            # Filter: 1-20 positions (small to medium employers)
            try:
                positions = int(row.get('positions_available', '0').strip() or '0')
            except ValueError:
                positions = 0
            if positions < 1 or positions > 20:
                continue

            # Filter: valid email (corporate, no yahoo)
            email = (row.get('email_1') or row.get('email', '')).strip().lower()
            if not is_valid_email(email):
                continue

            # Filter: dedupe within batch (one email per company)
            if email in seen_emails:
                continue
            seen_emails.add(email)

            # Filter: cooldown
            if is_in_cooldown(state, email):
                continue

            # Filter: target sectors (optional - include all if sector not in map)
            sector = row.get('sector', '').strip()

            # Filter by date criteria
            include = False

            if new_today:
                scrape_date = row.get('scrape_date', '')
                try:
                    scrape = datetime.strptime(scrape_date, '%Y-%m-%d').date()
                    if scrape == today:
                        include = True
                except (ValueError, TypeError):
                    pass

            if expiring_days:
                expiry_date = row.get('expiry_date') or row.get('application_deadline', '')
                try:
                    expiry = datetime.strptime(expiry_date, '%Y-%m-%d').date()
                    days_until = (expiry - today).days
                    if 0 <= days_until <= expiring_days:
                        include = True
                except (ValueError, TypeError):
                    pass

            if not include:
                continue

            # Build job dict
            job = {
                'job_id': job_id,
                'email': email,
                'company': to_ascii(row.get('company_name', ''))[:100],
                'job_title': to_ascii(row.get('job_title', ''))[:100],
                'sector': sector,
                'city': to_ascii(row.get('location') or row.get('company_city', ''))[:50],
                'positions': positions,
                'phone': row.get('phone_1', ''),
                'expiry_date': row.get('expiry_date') or row.get('application_deadline', ''),
                'scrape_date': row.get('scrape_date', ''),
                'sender': get_sender_for_sector(sector)
            }
            filtered.append(job)

    return filtered


def log_send(email, status, msg, sender=None):
    """Log send attempt."""
    log_file = LOG_DIR / f"sent_{datetime.now().strftime('%Y%m%d')}.log"
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sender_str = f" [{sender}]" if sender else ""
    with open(log_file, 'a') as f:
        f.write(f"{timestamp}{sender_str} | {status} | {email} | {msg}\n")


def sender_worker(sender_name, jobs_queue, state, results, rules, is_gmail=False):
    """
    Worker thread for a single sender.
    Processes jobs from queue with independent delay timer.

    Args:
        sender_name: Name of the sender (e.g. 'brevo_interjob', 'gmail_elena')
        jobs_queue: Queue of jobs to process
        state: Shared state dict (use _state_lock for thread-safe access)
        results: Shared results dict to track sent/failed counts
        rules: SenderRules instance for validation
        is_gmail: True if this is a Gmail sender
    """
    delay_seconds = GMAIL_DELAY_SECONDS if is_gmail else DELAY_SECONDS
    wait_minutes = GMAIL_WAIT_MINUTES if is_gmail else WAIT_MINUTES

    # Initialize sender
    sender = None

    if is_gmail:
        sender = get_gmail_sender()
    else:
        config = BREVO_CONFIGS.get(sender_name)
        if not config:
            print(f"[{sender_name}] ERROR: Unknown sender")
            return

        api_key = os.getenv(config['api_key_env'])
        if not api_key:
            print(f"[{sender_name}] ERROR: Missing API key")
            return

        sender = BrevoSafeSender(
            api_key=api_key,
            sender_email=config['email'],
            sender_name=config['name'],
            campaign_name=CAMPAIGN_NAME,
            batch_size=1,
            wait_minutes=wait_minutes,
            dry_run=False
        )

    # Load template for this sender
    subject_template, body_template = load_template(sender_name)

    sent_count = 0
    processed = 0

    while not jobs_queue.empty():
        try:
            job = jobs_queue.get_nowait()
        except:
            break

        email = job['email']
        processed += 1

        # Check if sender is blocked (thread-safe)
        with _state_lock:
            if is_sender_blocked(state, sender_name):
                print(f"[{sender_name}] BLOCKED - skipping {email}")
                jobs_queue.task_done()
                continue

            # Check daily limit
            current_count = get_daily_count(state, sender_name)
            limit = GMAIL_DAILY_LIMIT if is_gmail else DAILY_LIMIT_PER_SENDER
            if current_count >= limit:
                print(f"[{sender_name}] AT LIMIT ({current_count}/{limit}) - skipping {email}")
                jobs_queue.task_done()
                continue

        # Pre-send validation
        can_send, reason = rules.check_send_allowed(email)
        if not can_send:
            print(f"[{sender_name}] {email} - SKIP: {reason}")
            log_send(email, "SKIP", reason, sender_name)
            jobs_queue.task_done()
            continue

        # Personalize template
        subject = subject_template
        body = body_template.replace('{job_title}', job['job_title'] or 'pozitia dumneavoastra')
        body = body.replace('{city}', job['city'] or 'Romania')
        body = body.replace('{company}', job['company'] or '')

        print(f"[{sender_name}] Sending to {email}...", end=" ", flush=True)

        try:
            if is_gmail:
                success, via, msg = sender.send(email, subject, body)
                success = success  # Already boolean
                error = msg if not success else None
            else:
                success, msg = sender.send_one(email, subject, body)
                error = msg if not success else None

            if success:
                print("OK")
                with _state_lock:
                    state["sent_job_ids"].append(job['job_id'])
                    state["sent_emails"][email] = datetime.now().isoformat()
                    increment_daily_count(state, sender_name)
                    state["last_run"] = datetime.now().isoformat()
                sent_count += 1
                log_send(email, "OK", f"sent via {sender_name}", sender_name)
            else:
                print(f"FAIL: {error}")
                log_send(email, "FAIL", error or "send failed", sender_name)

        except SpamDetectedError as e:
            print(f"\n*** [{sender_name}] SPAM DETECTED ***")
            with _state_lock:
                block_sender(state, sender_name, reason="spam")
            log_send(email, "SPAM_BLOCK", str(e), sender_name)
            jobs_queue.task_done()
            break  # Stop this worker

        except HighBounceRateError as e:
            print(f"\n*** [{sender_name}] HIGH BOUNCE RATE ***")
            with _state_lock:
                block_sender(state, sender_name, reason="bounce")
            log_send(email, "BOUNCE_BLOCK", str(e), sender_name)
            jobs_queue.task_done()
            break  # Stop this worker

        except Exception as e:
            print(f"ERROR: {e}")
            log_send(email, "ERROR", str(e), sender_name)

        jobs_queue.task_done()

        # Save state periodically (thread-safe)
        with _state_lock:
            save_state(state)

        # Wait before next send (independent per sender)
        if not jobs_queue.empty():
            print(f"[{sender_name}] Waiting {wait_minutes} minutes...")
            time.sleep(delay_seconds)

    # Update results
    with _state_lock:
        results[sender_name] = {
            'sent': sent_count,
            'processed': processed
        }

    print(f"[{sender_name}] DONE: {sent_count} sent")


def show_status():
    """Show current status."""
    state = load_state()
    csv_file = get_latest_csv()
    today = datetime.now().strftime('%Y-%m-%d')

    print("=" * 60)
    print("ANOFM INSTANT SEND STATUS")
    print("=" * 60)
    print(f"CSV: {csv_file}")
    print(f"Last run: {state.get('last_run', 'Never')}")
    print(f"Sent job IDs: {len(state.get('sent_job_ids', []))}")
    print(f"Tracked emails: {len(state.get('sent_emails', {}))}")

    # Spam stop status
    if state.get("spam_stopped"):
        print(f"\n*** ALL SENDERS BLOCKED at {state['spam_stopped']} ***")

    # Today's blocked senders
    blocked = state.get("blocked_senders", {}).get(today, [])
    if blocked:
        print(f"\nBlocked senders today:")
        for sender in blocked:
            print(f"  - {sender}")

    # Today's counts
    daily = state.get("daily_counts", {}).get(today, {})
    if daily:
        print(f"\nToday's sends ({today}):")
        for sender, count in sorted(daily.items()):
            print(f"  {sender}: {count}/{DAILY_LIMIT_PER_SENDER}")
    else:
        print(f"\nNo sends today ({today})")

    # Count remaining capacity
    total_remaining = sum(DAILY_LIMIT_PER_SENDER - daily.get(s, 0)
                          for s in set(SECTOR_SENDER_MAP.values()))
    print(f"\nTotal remaining capacity: ~{total_remaining}")

    # Check latest CSV
    if csv_file:
        with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
            total_rows = sum(1 for _ in csv.DictReader(f))
        print(f"\nLatest CSV rows: {total_rows}")

    # Gmail status
    gmail_count = get_gmail_daily_count(state)
    gmail_available = is_gmail_available(state)
    print(f"\nGmail (fallback):")
    print(f"  gmail_elena: {gmail_count}/{GMAIL_DAILY_LIMIT} ({'available' if gmail_available else 'blocked/full'})")

    print(f"\nRASPI Rules:")
    print(f"  Brevo wait: {WAIT_MINUTES} minutes")
    print(f"  Gmail wait: {GMAIL_WAIT_MINUTES} minutes")
    print(f"  Spam check: {'ENABLED' if SPAM_CHECK_ENABLED else 'DISABLED'}")
    print(f"  Yahoo emails: BLOCKED")
    print(f"  Gmail recipients: ALLOWED")


def run_campaign(args):
    """Main campaign runner with PARALLEL senders."""
    print(f"\n{'=' * 60}")
    print(f"ANOFM INSTANT SEND - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'=' * 60}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE (PARALLEL)'}")
    print(f"New today: {args.new_today}")
    print(f"Expiring days: {args.expiring}")
    print(f"Limit: {args.limit}")
    print(f"Wait between sends: {WAIT_MINUTES} minutes (per sender)")
    print(f"Spam check: {'ENABLED' if SPAM_CHECK_ENABLED else 'DISABLED'}")

    csv_file = get_latest_csv()
    if not csv_file:
        print("ERROR: No ANOFM CSV found!")
        return

    print(f"CSV: {csv_file.name}")

    state = load_state()

    # Check if stopped due to spam
    if state.get("spam_stopped"):
        print(f"\n*** CAMPAIGN STOPPED DUE TO SPAM at {state['spam_stopped']} ***")
        print("Run with --reset to clear this and resume.")
        return

    # Filter jobs
    jobs = filter_jobs(csv_file, state,
                       new_today=args.new_today,
                       expiring_days=args.expiring)

    print(f"Matched jobs: {len(jobs)}")

    if not jobs:
        print("No jobs to send!")
        return

    # Group by sender
    jobs_by_sender = {}
    for job in jobs:
        sender = job['sender']
        if sender not in jobs_by_sender:
            jobs_by_sender[sender] = []
        jobs_by_sender[sender].append(job)

    print(f"\nJobs by sender:")
    for sender, sender_jobs in sorted(jobs_by_sender.items()):
        remaining = DAILY_LIMIT_PER_SENDER - get_daily_count(state, sender)
        print(f"  {sender}: {len(sender_jobs)} jobs (limit: {remaining} remaining)")

    # Show Gmail fallback capacity
    gmail_remaining = GMAIL_DAILY_LIMIT - get_gmail_daily_count(state)
    print(f"\nGmail fallback: {gmail_remaining}/{GMAIL_DAILY_LIMIT} remaining")

    if args.dry_run:
        print(f"\n=== DRY RUN - Would send ===")
        for job in jobs[:10]:
            print(f"  [{job['sender']}] {job['email']} - {job['company'][:30]} - {job['job_title'][:25]}")
        if len(jobs) > 10:
            print(f"  ... and {len(jobs) - 10} more")
        return

    # Apply limit and distribute to sender queues
    jobs_limited = jobs[:args.limit]
    sender_queues = {}
    jobs_per_sender = {}

    for job in jobs_limited:
        sender = job['sender']

        # Check if sender is blocked
        if is_sender_blocked(state, sender):
            # Try Gmail fallback
            if is_gmail_available(state) and get_gmail_daily_count(state) < GMAIL_DAILY_LIMIT:
                sender = 'gmail_elena'
            else:
                continue  # Skip this job

        # Check if sender at daily limit
        current_count = get_daily_count(state, sender)
        limit = GMAIL_DAILY_LIMIT if sender == 'gmail_elena' else DAILY_LIMIT_PER_SENDER
        queued = jobs_per_sender.get(sender, 0)

        if current_count + queued >= limit:
            # Try Gmail fallback
            if sender != 'gmail_elena' and is_gmail_available(state):
                gmail_count = get_daily_count(state, 'gmail_elena')
                gmail_queued = jobs_per_sender.get('gmail_elena', 0)
                if gmail_count + gmail_queued < GMAIL_DAILY_LIMIT:
                    sender = 'gmail_elena'
                else:
                    continue
            else:
                continue

        if sender not in sender_queues:
            sender_queues[sender] = Queue()
            jobs_per_sender[sender] = 0

        sender_queues[sender].put(job)
        jobs_per_sender[sender] += 1

    # Print queue distribution
    total_queued = sum(jobs_per_sender.values())
    print(f"\n=== PARALLEL SEND MODE ===")
    print(f"Total queued: {total_queued}")
    print(f"Active senders: {len(sender_queues)}")
    for sender, count in sorted(jobs_per_sender.items()):
        print(f"  {sender}: {count} emails queued")

    if total_queued == 0:
        print("No emails to send (all senders at limit or blocked)")
        return

    # Calculate expected time
    max_queue = max(jobs_per_sender.values()) if jobs_per_sender else 0
    expected_minutes = max_queue * WAIT_MINUTES
    print(f"\nExpected completion: ~{expected_minutes} minutes ({expected_minutes/60:.1f} hours)")
    print(f"Throughput: ~{total_queued / (expected_minutes/60) if expected_minutes > 0 else 0:.0f} emails/hour")

    # Initialize shared resources
    rules = SenderRules(CAMPAIGN_NAME)
    results = {}  # Thread-safe results dict

    # Launch worker threads with 1 minute stagger between each
    threads = []
    STAGGER_SECONDS = 60  # 1 minute between launching each sender
    print(f"\nLaunching {len(sender_queues)} parallel sender threads (1-min stagger)...")

    for i, (sender_name, queue) in enumerate(sender_queues.items()):
        is_gmail = sender_name.startswith('gmail_')
        t = threading.Thread(
            target=sender_worker,
            args=(sender_name, queue, state, results, rules, is_gmail),
            name=f"sender-{sender_name}"
        )
        t.start()
        threads.append(t)
        print(f"  Started: {sender_name} ({queue.qsize()} emails)")

        # Stagger next thread launch (except for last one)
        if i < len(sender_queues) - 1:
            print(f"  Waiting 1 minute before next sender...")
            time.sleep(STAGGER_SECONDS)

    # Wait for all threads to complete
    print(f"\nWaiting for all senders to complete...")
    for t in threads:
        t.join()

    # Summarize results
    total_sent = sum(r.get('sent', 0) for r in results.values())
    total_processed = sum(r.get('processed', 0) for r in results.values())

    print(f"\n{'=' * 60}")
    print(f"COMPLETE: {total_sent}/{total_queued} sent")
    print(f"\nResults by sender:")
    for sender, r in sorted(results.items()):
        print(f"  {sender}: {r.get('sent', 0)} sent / {r.get('processed', 0)} processed")

    # Final state save
    with _state_lock:
        state["last_run"] = datetime.now().isoformat()
        save_state(state)

    print(f"\nTotal sent job IDs: {len(state['sent_job_ids'])}")


def main():
    parser = argparse.ArgumentParser(description="ANOFM Instant Send Skill (RASPI Safe)")
    parser.add_argument('--status', '-s', action='store_true', help='Show status')
    parser.add_argument('--dry-run', '-d', '--test', action='store_true', dest='dry_run', help='Dry run mode')
    parser.add_argument('--new-today', '-n', action='store_true', help='Include jobs scraped today')
    parser.add_argument('--expiring', '-e', type=int, help='Include jobs expiring within N days')
    parser.add_argument('--limit', '-l', type=int, default=100, help='Max emails to send')
    parser.add_argument('--reset', action='store_true', help='Reset state (clears spam stop)')

    args = parser.parse_args()

    if args.reset:
        save_state({
            "sent_job_ids": [],
            "sent_emails": {},
            "last_run": None,
            "daily_counts": {},
            "blocked_senders": {},
            "spam_stopped": None
        })
        print("State reset (including blocked senders).")
        return

    if args.status:
        show_status()
        return

    if not args.new_today and not args.expiring:
        if args.dry_run:
            # Auto-set expiring 7 for test mode
            args.expiring = 7
        else:
            print("ERROR: Specify --new-today and/or --expiring N")
            parser.print_help()
            return

    run_campaign(args)


if __name__ == "__main__":
    main()
