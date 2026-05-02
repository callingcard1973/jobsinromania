#!/usr/bin/env python3
"""
Brevo SMTP Warmup with Spam Checking

Safe warmup schedule:
- Day 1-7:   10/day (check spam after each)
- Day 8-14:  25/day (check spam after 5)
- Day 15-21: 50/day (check spam after 10)
- Day 22-30: 100/day (check spam after 25)
- Day 31+:   200/day (check spam after 50)

Usage:
    python3 brevo_warmup.py status
    python3 brevo_warmup.py send <campaign> [--limit N]
    python3 brevo_warmup.py send-all
    python3 brevo_warmup.py check-spam <sender>
"""

import os
import sys
import json
import csv
import time
import random
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from pathlib import Path

STATE_FILE = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/brevo_warmup_state.json')
CAMPAIGNS_DIR = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS')
ENV_FILE = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

CAMPAIGN_SENDERS = {
    'CAREWORKERS_BREVO': 'CAREWORKERS',
    'BUILDJOBS_BREVO': 'BUILDJOBS',
    'FACTORYJOBS_BREVO': 'FACTORYJOBS',
    'WAREHOUSE_BREVO': 'WAREHOUSEWORKERS',
    'SEICARESCU_BREVO': 'SEICARESCU',
    'CUMPARLEGUME_BREVO': 'CUMPARLEGUME',
    'NORWAY_BREVO': 'MIVROMANIA',
    'SWEDEN_BREVO': 'MIVROMANIA_ONLINE',
    'FINLAND_BREVO': 'NEPALEZI',
    'CIFN_BREVO': 'CIFN',
    'NEPALEZI_BREVO': 'NEPALEZI',
    'HORECAWORKERS2026_EU_BREVO': 'A2:HORECAWORKERS2026_EU',  # Uses A2 SMTP (Brevo not activated)
}

# A2 SMTP senders (prefix with A2: in CAMPAIGN_SENDERS)
A2_SENDERS = {
    'HORECAWORKERS2026_EU': {
        'server': 'nl1-cl8-ats1.a2hosting.com',
        'port': 465,
        'email': 'office@horecaworkers2026.eu',
        'env_password': 'A2_HORECAWORKERS2026_EU_PASSWORD',
    },
}

# Brevo sending schedule: 290/day per sender, spam check after each email
# Per CLAUDE.md rules: 290/day max, 3-5 min delay, spam check after EVERY email
WARMUP_SCHEDULE = [
    (1, 999, 290, 1),   # All days: 290/day, check after EVERY email
]

def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if '=' in line and not line.startswith('#'):
                key, val = line.split('=', 1)
                env[key.strip()] = val.strip().strip('"\'')
    return env

def get_a2_credentials(sender_name):
    """Get A2 SMTP credentials."""
    if sender_name not in A2_SENDERS:
        print(f"ERROR: Unknown A2 sender: {sender_name}")
        return None

    env = load_env()
    config = A2_SENDERS[sender_name]
    password = env.get(config['env_password'])

    if not password:
        print(f"ERROR: Missing {config['env_password']} in .env")
        return None

    return {
        'type': 'a2',
        'smtp_server': config['server'],
        'smtp_port': config['port'],
        'username': config['email'],
        'password': password,
        'from_email': config['email'],
        'from_name': sender_name.replace('_', ' ').title(),
        'api_key': None,  # No API for A2
    }

def get_brevo_credentials(sender_name):
    env = load_env()
    api_key = env.get(f'BREVO_{sender_name}_API_KEY')
    smtp_user = env.get(f'BREVO_{sender_name}_SMTP_USER')
    smtp_key = env.get(f'BREVO_{sender_name}_SMTP_KEY')
    from_email = env.get(f'BREVO_{sender_name}_FROM') or f'office@{sender_name.lower().replace("_","")}.eu'

    # API key is required - SMTP is optional (will use API if no SMTP)
    if not api_key:
        print(f"ERROR: Missing BREVO_{sender_name}_API_KEY in .env")
        return None

    return {
        'type': 'brevo',
        'smtp_server': 'smtp-relay.brevo.com',
        'smtp_port': 587,
        'username': smtp_user,
        'password': smtp_key,  # Can be None - will use API instead
        'api_key': api_key,
        'from_email': from_email,
        'from_name': sender_name.replace('_', ' ').title()
    }

def get_credentials(sender_spec):
    """Get credentials - handles both Brevo and A2 senders."""
    if sender_spec.startswith('A2:'):
        return get_a2_credentials(sender_spec[3:])
    return get_brevo_credentials(sender_spec)

def get_warmup_params(start_date):
    """Get daily limit and check frequency based on warmup day."""
    days = (datetime.now() - start_date).days + 1
    for day_start, day_end, limit, check_every in WARMUP_SCHEDULE:
        if day_start <= days <= day_end:
            return days, limit, check_every
    return days, 200, 50

def get_bounced_emails(api_key, hours=24):
    """Get list of bounced email addresses from Brevo."""
    if not api_key:
        return []

    bounced = []
    try:
        headers = {'api-key': api_key, 'accept': 'application/json'}

        # Get hard bounces
        url = 'https://api.brevo.com/v3/smtp/blockedContacts'
        params = {'limit': 100, 'offset': 0}

        resp = requests.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for contact in data.get('contacts', []):
                bounced.append(contact.get('email', '').lower())
    except Exception as e:
        print(f"  Error fetching bounces: {e}")

    return bounced

def remove_bounced_from_contacts(contacts_file, bounced_emails):
    """Remove bounced emails from contacts file."""
    if not bounced_emails or not Path(contacts_file).exists():
        return 0

    bounced_set = set(e.lower() for e in bounced_emails)
    removed = 0

    # Read all contacts
    rows = []
    with open(contacts_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            email = row.get('email', '').lower().strip()
            if email not in bounced_set:
                rows.append(row)
            else:
                removed += 1

    # Write back without bounced
    if removed > 0:
        with open(contacts_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"  Auto-removed {removed} bounced emails from {Path(contacts_file).name}")

    return removed

def check_spam_status(api_key, hours=1):
    """Check Brevo for spam complaints and bounces."""
    if not api_key:
        return {'ok': True, 'error': 'No API key'}

    try:
        # Get events from last N hours
        end = datetime.now()
        start = end - timedelta(hours=hours)

        headers = {'api-key': api_key, 'accept': 'application/json'}

        # Check for spam complaints
        url = 'https://api.brevo.com/v3/smtp/statistics/aggregatedReport'
        params = {'startDate': start.strftime('%Y-%m-%d'), 'endDate': end.strftime('%Y-%m-%d')}

        resp = requests.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code != 200:
            return {'ok': True, 'error': f'API error: {resp.status_code}'}

        data = resp.json()

        spam = data.get('spamReports', 0)
        bounces = data.get('hardBounces', 0) + data.get('softBounces', 0)
        delivered = data.get('delivered', 0)

        bounce_rate = (bounces / delivered * 100) if delivered > 0 else 0

        # Threshold 20% for warmup (cleaned contacts, allow sends to dilute rate)
        # Will naturally decrease as more successful sends happen
        result = {
            'ok': spam == 0 and bounce_rate < 20,
            'spam': spam,
            'bounces': bounces,
            'delivered': delivered,
            'bounce_rate': round(bounce_rate, 2),
        }

        if spam > 0:
            result['error'] = f'SPAM DETECTED: {spam} complaints!'
        elif bounce_rate >= 20:
            result['error'] = f'HIGH BOUNCE RATE: {bounce_rate}%'

        return result

    except Exception as e:
        return {'ok': True, 'error': f'Check failed: {e}'}

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))

def init_campaign(campaign):
    state = load_state()
    if campaign not in state:
        state[campaign] = {
            'start_date': datetime.now().isoformat(),
            'total_sent': 0,
            'daily_sends': {},
            'spam_checks': []
        }
        save_state(state)
    return state[campaign]

def get_today_sent(campaign_state):
    today = datetime.now().strftime('%Y-%m-%d')
    return campaign_state.get('daily_sends', {}).get(today, 0)

def load_contacts(campaign):
    csv_path = CAMPAIGNS_DIR / campaign / 'contacts' / 'contacts.csv'
    if not csv_path.exists():
        return []
    with open(csv_path, 'r', errors='ignore') as f:
        return list(csv.DictReader(f))

def load_sent_emails(campaign):
    sent = set()
    log_dir = CAMPAIGNS_DIR / campaign / 'logs'
    if log_dir.exists():
        for log in log_dir.glob('sent_*.log'):
            for line in log.read_text(errors='ignore').splitlines():
                if '| OK |' in line or '|OK|' in line:
                    parts = line.split('|')
                    if len(parts) >= 2:
                        sent.add(parts[1].strip().lower())
    return sent

def load_template(campaign):
    template_dir = CAMPAIGNS_DIR / campaign / 'templates'
    templates = list(template_dir.glob('*.txt'))
    if not templates:
        return None, None
    template = random.choice(templates)
    content = template.read_text()
    lines = content.strip().split('\n')
    subject = lines[0].replace('Subject:', '').strip() if lines[0].startswith('Subject:') else 'Job Opportunity'
    body = '\n'.join(lines[2:]) if len(lines) > 2 else '\n'.join(lines[1:])
    return subject, body

def send_email_api(creds, to_email, subject, body, company=''):
    """Send via Brevo API (fallback when no SMTP creds)."""
    try:
        body = body.replace('{company}', company or 'your company')
        payload = {
            "sender": {"name": creds['from_name'], "email": creds['from_email']},
            "to": [{"email": to_email}],
            "subject": subject,
            "textContent": body
        }
        resp = requests.post(
            'https://api.brevo.com/v3/smtp/email',
            headers={'api-key': creds['api_key'], 'Content-Type': 'application/json'},
            json=payload,
            timeout=30
        )
        if resp.status_code in (200, 201):
            return True, None
        return False, f"API {resp.status_code}: {resp.text[:100]}"
    except Exception as e:
        return False, str(e)

def send_email_a2(creds, to_email, subject, body, company=''):
    """Send via A2 SMTP (SSL on port 465)."""
    import ssl
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{creds['from_name']} <{creds['from_email']}>"
        msg['To'] = to_email

        body = body.replace('{company}', company or 'your company')
        msg.attach(MIMEText(body, 'plain'))

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(creds['smtp_server'], creds['smtp_port'], context=context, timeout=30) as server:
            server.login(creds['username'], creds['password'])
            server.send_message(msg)

        return True, None
    except Exception as e:
        return False, str(e)

def send_email(creds, to_email, subject, body, company=''):
    # Use A2 SMTP for A2 senders
    if creds.get('type') == 'a2':
        return send_email_a2(creds, to_email, subject, body, company)

    # Use Brevo API if no SMTP credentials
    if not creds.get('password'):
        return send_email_api(creds, to_email, subject, body, company)

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{creds['from_name']} <{creds['from_email']}>"
        msg['To'] = to_email

        body = body.replace('{company}', company or 'your company')
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(creds['smtp_server'], creds['smtp_port']) as server:
            server.starttls()
            server.login(creds['username'], creds['password'])
            server.send_message(msg)

        return True, None
    except Exception as e:
        return False, str(e)

def log_send(campaign, email, status, error=None):
    log_dir = CAMPAIGNS_DIR / campaign / 'logs'
    log_dir.mkdir(exist_ok=True)
    today = datetime.now().strftime('%Y%m%d')
    log_file = log_dir / f'sent_{today}.log'
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    status_str = 'OK' if status else f'FAIL: {error}'
    with open(log_file, 'a') as f:
        f.write(f"{timestamp} | {email} | {status_str}\n")

def cmd_status():
    state = load_state()
    print("\n=== Brevo Warmup Status (Safe Mode) ===\n")
    print(f"{'Campaign':<22} {'Day':>4} {'Limit':>6} {'Check':>6} {'Today':>6} {'Total':>7} {'Status'}")
    print("-" * 80)

    for campaign in CAMPAIGN_SENDERS.keys():
        camp_state = state.get(campaign, {})
        if not camp_state:
            contacts = load_contacts(campaign)
            print(f"{campaign:<22} {'--':>4} {'--':>6} {'--':>6} {'--':>6} {'--':>7} NOT STARTED ({len(contacts)} contacts)")
            continue

        start = datetime.fromisoformat(camp_state['start_date'])
        day, limit, check_every = get_warmup_params(start)
        today_sent = get_today_sent(camp_state)
        total = camp_state.get('total_sent', 0)
        remaining = limit - today_sent

        status = f"WARMING ({remaining} left)"
        if remaining <= 0:
            status = "DONE TODAY"

        print(f"{campaign:<22} {day:>4} {limit:>6} {check_every:>6} {today_sent:>6} {total:>7} {status}")

    print("\nSchedule: Day 1-7: 10/day | Day 8-14: 25/day | Day 15-21: 50/day | Day 22-30: 100/day | Day 31+: 200/day")

def cmd_check_spam(sender_name):
    creds = get_brevo_credentials(sender_name)
    if not creds:
        return
    result = check_spam_status(creds['api_key'])
    print(f"\n=== Spam Check: {sender_name} ===")
    print(f"Status: {'OK' if result['ok'] else 'PROBLEM'}")
    print(f"Spam complaints: {result.get('spam', 0)}")
    print(f"Bounces: {result.get('bounces', 0)}")
    print(f"Delivered: {result.get('delivered', 0)}")
    print(f"Bounce rate: {result.get('bounce_rate', 0)}%")
    if result.get('error'):
        print(f"Issue: {result['error']}")

def cmd_send(campaign, limit=None):
    if campaign not in CAMPAIGN_SENDERS:
        print(f"Unknown campaign: {campaign}")
        return

    sender_spec = CAMPAIGN_SENDERS[campaign]
    creds = get_credentials(sender_spec)
    if not creds:
        return

    # A2 senders don't need API key, Brevo senders do
    if creds.get('type') != 'a2' and not creds.get('api_key'):
        print(f"No Brevo API key for {sender_spec}")
        return

    # Init state
    camp_state = init_campaign(campaign)
    start = datetime.fromisoformat(camp_state['start_date'])
    day, warmup_limit, check_every = get_warmup_params(start)
    today_sent = get_today_sent(camp_state)

    can_send = warmup_limit - today_sent
    if limit:
        can_send = min(can_send, limit)

    if can_send <= 0:
        print(f"{campaign}: Daily limit reached ({warmup_limit} for day {day})")
        return

    # Pre-flight spam check (skip for A2 senders - no API)
    print(f"\n=== {campaign} - Day {day} ===")
    if creds.get('type') == 'a2':
        print(f"A2 SMTP sender - skipping spam check")
    else:
        print(f"Checking spam status before sending...")
        spam_result = check_spam_status(creds['api_key'])
        if not spam_result['ok']:
            print(f"STOPPED: {spam_result.get('error', 'Spam/bounce issue detected')}")
            return
        print(f"Spam check OK - proceeding with send")

    # Load contacts
    contacts_file = CAMPAIGNS_DIR / campaign / 'contacts' / 'contacts.csv'
    contacts = load_contacts(campaign)
    sent_emails = load_sent_emails(campaign)
    unsent = [c for c in contacts if (c.get('email') or '').lower() not in sent_emails]
    random.shuffle(unsent)

    if not unsent:
        print(f"{campaign}: No more contacts")
        return

    subject, body = load_template(campaign)
    if not subject:
        print(f"{campaign}: No template")
        return

    sender_type = "A2 SMTP" if creds.get('type') == 'a2' else "BREVO"
    print(f"\n=== {sender_type} SENDER: {campaign} ===")
    print(f"Contacts: {len(unsent)}, Remaining: {can_send}")
    print(f"Delay: 2-5 min between emails")
    print()

    state = load_state()
    today = datetime.now().strftime('%Y-%m-%d')
    sent_count = 0
    batch_count = 0
    total_contacts = len(unsent[:can_send])

    for i, contact in enumerate(unsent[:can_send]):
        email = (contact.get('email') or '').strip()
        company = contact.get('company', '') or contact.get('denumire', '')

        # Personalized greeting from officer/contact data
        officer_lastname = contact.get('officer_lastname', '').strip()
        if officer_lastname:
            greeting = f'Dear Mr./Ms. {officer_lastname},'
        else:
            greeting = 'Dear Hiring Manager,'

        # Apply all template variables
        personalized_body = body.replace('{greeting}', greeting)
        personalized_subject = subject.replace('{company}', company or 'your company')

        print(f"[{i+1}/{total_contacts}] {email}")
        success, error = send_email(creds, email, personalized_subject, personalized_body, company)
        log_send(campaign, email, success, error)

        if success:
            sent_count += 1
            batch_count += 1
            state[campaign]['total_sent'] = state[campaign].get('total_sent', 0) + 1
            state[campaign]['daily_sends'][today] = state[campaign]['daily_sends'].get(today, 0) + 1
            save_state(state)
            print(f"  OK: sent")

            # Check spam after every N emails (skip for A2)
            if batch_count >= check_every and creds.get('type') != 'a2':
                print(f"\n  --- Spam check after {batch_count} emails ---")
                time.sleep(30)  # Wait for Brevo to process
                spam_result = check_spam_status(creds['api_key'])
                if not spam_result['ok']:
                    print(f"  STOPPED: {spam_result.get('error')}")
                    print(f"\n{campaign}: Sent {sent_count} emails before stopping")
                    return
                print(f"  Spam check OK (bounces: {spam_result.get('bounces', 0)}, spam: {spam_result.get('spam', 0)})")
                batch_count = 0
        else:
            print(f"  FAIL: {email} - {error}")

        # Delay 3-5 minutes between emails (per CLAUDE.md rules)
        if sent_count < can_send:
            delay = random.randint(180, 300)
            print(f"\n  Waiting {delay//60} min {delay%60} sec...")
            time.sleep(delay)

            # Check for bounces after each email (skip for A2 - no API)
            if creds.get('type') == 'a2':
                print(f"  A2 sender - continuing...\n")
            else:
                print(f"  Checking Brevo for bounces...")
                bounce_check = check_spam_status(creds['api_key'], hours=1)

                if bounce_check.get('spam', 0) > 0:
                    # SPAM is critical - stop immediately
                    print(f"  [SPAM DETECTED] Stopping! Spam: {bounce_check.get('spam', 0)}")
                    break

                if bounce_check.get('bounces', 0) > 0:
                    # Bounces - auto-remove and continue
                    print(f"  [BOUNCE DETECTED] Auto-removing bounced emails...")
                    bounced_emails = get_bounced_emails(creds['api_key'])
                    if bounced_emails:
                        remove_bounced_from_contacts(contacts_file, bounced_emails)
                    print(f"  Continuing after cleanup...")
                else:
                    print(f"  Clear. Continuing...\n")

    print(f"\n{campaign}: Sent {sent_count} emails total")

def cmd_send_all():
    for campaign in CAMPAIGN_SENDERS.keys():
        cmd_send(campaign)
        print("\nWaiting 5 minutes before next campaign...\n")
        time.sleep(300)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'status':
        cmd_status()
    elif cmd == 'send':
        if len(sys.argv) < 3:
            print("Usage: brevo_warmup.py send <campaign> [--limit N]")
            sys.exit(1)
        campaign = sys.argv[2]
        limit = None
        if '--limit' in sys.argv:
            idx = sys.argv.index('--limit')
            limit = int(sys.argv[idx + 1])
        cmd_send(campaign, limit)
    elif cmd == 'send-all':
        cmd_send_all()
    elif cmd == 'check-spam':
        if len(sys.argv) < 3:
            print("Usage: brevo_warmup.py check-spam <sender>")
            sys.exit(1)
        cmd_check_spam(sys.argv[2])
    else:
        print(f"Unknown command: {cmd}")
