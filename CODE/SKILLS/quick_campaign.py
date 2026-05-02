#!/usr/bin/env python3
"""
Quick Campaign - Simple CSV-to-Email sender without AI.

Usage:
    # List available senders
    quick_campaign.py --list-senders

    # Send campaign
    quick_campaign.py --csv /path/contacts.csv --sender factoryjobs.eu --template /path/template.txt
    quick_campaign.py --csv /path/contacts.csv --sender factoryjobs.eu --template /path/template.txt --limit 50
    quick_campaign.py --csv /path/contacts.csv --sender factoryjobs.eu --template /path/template.txt --dry-run

    # Check status of running campaign
    quick_campaign.py --status my_campaign

    # Resume paused campaign
    quick_campaign.py --resume my_campaign

Template format:
    Subject: Your subject line here

    Body text here.
    Use {company} and {name} for personalization.

    --
    Signature
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import csv
import json
import time
import random

# --- DB tracking (added by patch) ---
def log_send_to_db(email, campaign, sender, method="a2_smtp"):
    """Log send to anofm.send_log + email_sender.global_sends"""
    try:
        import psycopg2
        from datetime import date
        # anofm send_log
        conn = psycopg2.connect(dbname="anofm", user="tudor", host="localhost", password="tudor")
        cur = conn.cursor()
        cur.execute("INSERT INTO send_log(email, campaign, sector, sender, method, status) VALUES(%s,%s,%s,%s,%s,'sent')",
            (email, campaign, method, sender, method))
        conn.commit(); conn.close()
        # global_sends
        conn2 = psycopg2.connect(dbname="email_sender", user="tudor", host="localhost", password="tudor")
        cur2 = conn2.cursor()
        cur2.execute("INSERT INTO global_sends(email, campaign, sender, sent_date) VALUES(%s,%s,%s,%s)",
            (email, campaign, sender, date.today()))
        conn2.commit(); conn2.close()
    except:
        pass  # don't break sending if DB fails
# --- end DB tracking ---

import hashlib
import argparse
import smtplib
import ssl
import requests
from pathlib import Path
from datetime import datetime, date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

# Paths
A2_CREDS_FILE = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/a2_smtp_credentials.json")
STATE_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/QUICK_CAMPAIGNS")
STATE_DIR.mkdir(parents=True, exist_ok=True)

# SMTP settings
A2_SMTP_SERVER = "nl1-cl8-ats1.a2hosting.com"
A2_SMTP_PORT = 465
BREVO_API = "https://api.brevo.com/v3/smtp/email"

# Defaults
DEFAULT_DELAY = 180  # 3 minutes between emails
DEFAULT_LIMIT = 290  # daily limit

# Import shared modules
try:
    from skills_common import to_ascii
except ImportError:
    def to_ascii(t):
        return t.encode('ascii', 'ignore').decode('ascii') if t else ''

try:
    from email_sender_rules import check_send_allowed
    HAS_RULES = True
except ImportError:
    HAS_RULES = False
    def check_send_allowed(email, company):
        return True, "OK"


def load_a2_credentials():
    """Load A2 SMTP credentials."""
    if not A2_CREDS_FILE.exists():
        return {}
    with open(A2_CREDS_FILE) as f:
        return json.load(f)


def get_brevo_senders():
    """Get Brevo senders from .env."""
    senders = {}
    env_file = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/.env")
    if not env_file.exists():
        return senders

    with open(env_file) as f:
        for line in f:
            if line.startswith("BREVO_") and "_API_KEY=" in line:
                # BREVO_FACTORYJOBS_API_KEY -> factoryjobs.eu
                name = line.split("=")[0].replace("BREVO_", "").replace("_API_KEY", "").lower()
                key = line.split("=")[1].strip()
                if key:
                    # Map common names to domains
                    domain_map = {
                        "buildjobs": "buildjobs.eu",
                        "factoryjobs": "factoryjobs.eu",
                        "careworkers": "careworkers.eu",
                        "warehouseworkers": "warehouseworkers.eu",
                        "electricjobs": "electricjobs.eu",
                        "mivromania": "mivromania.info",
                        "mivromania_online": "mivromania.online",
                        "cifn": "cifn.info",
                        "nepalezi": "nepalezi.com",
                        "expatsinromania": "expatsinromania.org",
                        "interjob": "interjob.ro",
                    }
                    domain = domain_map.get(name, f"{name}.eu")
                    senders[f"brevo_{name}"] = {
                        "type": "brevo",
                        "domain": domain,
                        "email": f"office@{domain}",
                        "api_key_env": f"BREVO_{name.upper()}_API_KEY",
                        "limit": 290
                    }
    return senders


def list_senders():
    """List all available senders."""
    print("\n=== A2 SMTP SENDERS (500/day each) ===\n")
    a2_creds = load_a2_credentials()

    # Filter main domains only
    main_domains = [d for d in a2_creds.keys() if not "_at_" in d and "." in d]
    for domain in sorted(main_domains)[:15]:
        creds = a2_creds[domain]
        print(f"  {domain:<25} {creds.get('email', f'office@{domain}')}")

    print("\n=== BREVO API SENDERS (290/day each) ===\n")
    brevo = get_brevo_senders()
    for name, config in sorted(brevo.items())[:12]:
        print(f"  {name:<25} {config['email']}")

    print(f"\nTotal: {len(main_domains)} A2 + {len(brevo)} Brevo senders")
    print("\nUsage: quick_campaign.py --csv file.csv --sender factoryjobs.eu --template tmpl.txt")


def load_template(template_path):
    """Load and parse email template."""
    with open(template_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    lines = content.strip().split('\n')
    subject = ""
    body_start = 0

    for i, line in enumerate(lines):
        if line.lower().startswith('subject:'):
            subject = line[8:].strip()
            body_start = i + 1
            # Skip empty line after subject
            if body_start < len(lines) and not lines[body_start].strip():
                body_start += 1
            break

    body = '\n'.join(lines[body_start:])
    return to_ascii(subject), to_ascii(body)


def load_contacts(csv_path):
    """Load contacts from CSV."""
    contacts = []
    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Find email column
            email = None
            for col in ['email', 'Email', 'EMAIL', 'email_1', 'e-mail', 'mail']:
                if col in row and row[col] and '@' in str(row[col]):
                    email = row[col].strip().lower()
                    break

            if not email:
                continue

            # Find company column
            company = ""
            for col in ['company', 'Company', 'company_name', 'employer', 'nume_firma', 'name']:
                if col in row and row[col]:
                    company = to_ascii(str(row[col]).strip())[:100]
                    break

            # Find name column
            name = ""
            for col in ['contact_name', 'contact', 'name', 'Name', 'first_name']:
                if col in row and row[col] and col != 'company_name':
                    name = to_ascii(str(row[col]).strip())[:50]
                    break

            contacts.append({
                'email': email,
                'company': company,
                'name': name
            })

    return contacts


def personalize(text, contact):
    """Replace placeholders in text."""
    result = text
    result = result.replace('{company}', contact.get('company', ''))
    result = result.replace('{name}', contact.get('name', ''))
    result = result.replace('{email}', contact.get('email', ''))
    return result


def send_a2(sender_domain, to_email, subject, body, creds):
    """Send via A2 SMTP."""
    email_addr = creds.get('email', f'office@{sender_domain}')
    password = creds.get('password')

    if not password:
        return False, "No password"

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = email_addr
    msg['To'] = to_email

    # Plain text and HTML versions
    text_part = MIMEText(body, 'plain', 'utf-8')
    html_body = f"<div style='font-family:Arial,sans-serif;font-size:14px;line-height:1.6'>{body.replace(chr(10), '<br>')}</div>"
    html_part = MIMEText(html_body, 'html', 'utf-8')

    msg.attach(text_part)
    msg.attach(html_part)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(A2_SMTP_SERVER, A2_SMTP_PORT, context=context, timeout=30) as server:
            server.login(email_addr, password)
            server.send_message(msg)
        return True, "OK"
    except Exception as e:
        return False, str(e)


def send_brevo(sender_config, to_email, subject, body):
    """Send via Brevo API."""
    api_key = os.getenv(sender_config['api_key_env'])
    if not api_key:
        return False, f"No API key: {sender_config['api_key_env']}"

    html_body = f"<div style='font-family:Arial,sans-serif;font-size:14px;line-height:1.6'>{body.replace(chr(10), '<br>')}</div>"

    payload = {
        "sender": {"email": sender_config['email'], "name": sender_config['domain'].split('.')[0].title()},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_body,
        "replyTo": {"email": sender_config['email']}
    }

    try:
        resp = requests.post(
            BREVO_API,
            headers={"api-key": api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        if resp.status_code in (200, 201):
            return True, "OK"
        else:
            return False, f"HTTP {resp.status_code}: {resp.text[:100]}"
    except Exception as e:
        return False, str(e)


def get_campaign_id(csv_path, sender):
    """Generate unique campaign ID."""
    name = Path(csv_path).stem[:20]
    h = hashlib.md5(f"{csv_path}{sender}".encode()).hexdigest()[:6]
    return f"{name}_{sender.split('.')[0]}_{h}"


def load_state(campaign_id):
    """Load campaign state."""
    state_file = STATE_DIR / f"{campaign_id}.json"
    if state_file.exists():
        with open(state_file) as f:
            return json.load(f)
    return {
        "campaign_id": campaign_id,
        "created": datetime.now().isoformat(),
        "sent_emails": [],
        "last_index": 0,
        "total_sent": 0,
        "daily_sent": {},
        "errors": []
    }


def save_state(campaign_id, state):
    """Save campaign state."""
    state_file = STATE_DIR / f"{campaign_id}.json"
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)


def run_campaign(args):
    """Run the campaign."""
    # Load sender config
    sender = args.sender
    a2_creds = load_a2_credentials()
    brevo_senders = get_brevo_senders()

    sender_type = None
    sender_config = None

    if sender in a2_creds:
        sender_type = "a2"
        sender_config = a2_creds[sender]
    elif sender.startswith("brevo_") and sender in brevo_senders:
        sender_type = "brevo"
        sender_config = brevo_senders[sender]
    elif f"brevo_{sender.replace('.', '_').replace('-', '_').split('.')[0]}" in brevo_senders:
        key = f"brevo_{sender.replace('.', '_').replace('-', '_').split('.')[0]}"
        sender_type = "brevo"
        sender_config = brevo_senders[key]
    else:
        print(f"❌ Unknown sender: {sender}")
        print("Use --list-senders to see available options")
        return 1

    # Load contacts
    contacts = load_contacts(args.csv)
    if not contacts:
        print(f"❌ No valid contacts found in {args.csv}")
        return 1

    print(f"📧 Loaded {len(contacts)} contacts from {args.csv}")

    # Load template
    subject, body = load_template(args.template)
    if not subject:
        print(f"❌ No subject found in template (use 'Subject: ...' on first line)")
        return 1

    print(f"📝 Template: {subject[:50]}...")

    # Campaign state
    campaign_id = get_campaign_id(args.csv, sender)
    state = load_state(campaign_id)

    # Check daily limit
    today = date.today().isoformat()
    daily_sent = state["daily_sent"].get(today, 0)
    limit = args.limit or DEFAULT_LIMIT

    if daily_sent >= limit:
        print(f"⚠️ Daily limit reached ({daily_sent}/{limit})")
        return 0

    remaining_limit = limit - daily_sent

    # Filter already sent
    sent_set = set(state["sent_emails"])
    to_send = [c for c in contacts if c['email'] not in sent_set]

    if not to_send:
        print("✅ All contacts already sent")
        return 0

    print(f"📤 Sending to {min(len(to_send), remaining_limit)} of {len(to_send)} remaining contacts")
    print(f"🔧 Sender: {sender} ({sender_type.upper()})")
    print(f"⏱️ Delay: {args.delay}s between emails")

    if args.dry_run:
        print("\n🔍 DRY RUN - No emails will be sent\n")
        for i, contact in enumerate(to_send[:5]):
            print(f"  {i+1}. {contact['email']} ({contact['company'][:30]})")
        if len(to_send) > 5:
            print(f"  ... and {len(to_send)-5} more")
        return 0

    # Send loop
    print(f"\n{'='*50}")
    print(f"Starting campaign: {campaign_id}")
    print(f"{'='*50}\n")

    sent_count = 0
    error_count = 0

    for i, contact in enumerate(to_send):
        if sent_count >= remaining_limit:
            print(f"\n⚠️ Daily limit reached ({limit})")
            break

        email = contact['email']

        # Check send rules
        if HAS_RULES:
            allowed, reason = check_send_allowed(email, contact.get('company', ''))
            if not allowed:
                print(f"⏭️ Skip {email}: {reason}")
                continue

        # Personalize
        p_subject = personalize(subject, contact)
        p_body = personalize(body, contact)

        # Send
        if sender_type == "a2":
            success, msg = send_a2(sender, email, p_subject, p_body, sender_config)
        else:
            success, msg = send_brevo(sender_config, email, p_subject, p_body)

        if success:
            sent_count += 1
            state["sent_emails"].append(email)
            log_send_to_db(email, campaign_id, args.sender, "a2_smtp" if "@" not in args.sender else "brevo")
            state["total_sent"] += 1
            state["daily_sent"][today] = state["daily_sent"].get(today, 0) + 1
            print(f"✅ [{sent_count}/{remaining_limit}] {email}")
        else:
            error_count += 1
            state["errors"].append({"email": email, "error": msg, "time": datetime.now().isoformat()})
            print(f"❌ {email}: {msg}")

            # Stop on repeated errors
            if error_count >= 5:
                print("\n🛑 Too many errors, stopping")
                break

        # Save state periodically
        if sent_count % 10 == 0:
            save_state(campaign_id, state)

        # Delay (with some randomness)
        if i < len(to_send) - 1 and sent_count < remaining_limit:
            delay = args.delay + random.randint(-10, 10)
            delay = max(30, delay)  # minimum 30s
            print(f"   ⏱️ Waiting {delay}s...")
            time.sleep(delay)

    # Final save
    state["last_run"] = datetime.now().isoformat()
    save_state(campaign_id, state)

    print(f"\n{'='*50}")
    print(f"Campaign complete: {sent_count} sent, {error_count} errors")
    print(f"State saved: {STATE_DIR}/{campaign_id}.json")
    print(f"{'='*50}")

    return 0


def show_status(campaign_id=None):
    """Show campaign status."""
    if campaign_id:
        state_file = STATE_DIR / f"{campaign_id}.json"
        if not state_file.exists():
            print(f"❌ Campaign not found: {campaign_id}")
            return 1
        with open(state_file) as f:
            state = json.load(f)
        print(f"\nCampaign: {campaign_id}")
        print(f"Created: {state.get('created', '?')}")
        print(f"Total sent: {state.get('total_sent', 0)}")
        print(f"Last run: {state.get('last_run', 'never')}")
        today = date.today().isoformat()
        print(f"Sent today: {state.get('daily_sent', {}).get(today, 0)}")
        if state.get('errors'):
            print(f"Recent errors: {len(state['errors'][-5:])}")
        return 0

    # List all campaigns
    print("\n=== QUICK CAMPAIGNS ===\n")
    for sf in sorted(STATE_DIR.glob("*.json")):
        with open(sf) as f:
            state = json.load(f)
        today = date.today().isoformat()
        daily = state.get('daily_sent', {}).get(today, 0)
        total = state.get('total_sent', 0)
        print(f"  {sf.stem:<40} sent:{total:>5}  today:{daily:>3}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Quick Campaign - CSV to Email sender")
    parser.add_argument("--list-senders", action="store_true", help="List available senders")
    parser.add_argument("--csv", help="Path to contacts CSV")
    parser.add_argument("--sender", help="Sender domain (e.g., factoryjobs.eu)")
    parser.add_argument("--template", help="Path to email template")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help=f"Daily limit (default: {DEFAULT_LIMIT})")
    parser.add_argument("--delay", type=int, default=DEFAULT_DELAY, help=f"Delay between emails in seconds (default: {DEFAULT_DELAY})")
    parser.add_argument("--dry-run", action="store_true", help="Preview without sending")
    parser.add_argument("--status", nargs="?", const="", help="Show campaign status")
    parser.add_argument("--resume", help="Resume paused campaign")

    args = parser.parse_args()

    if args.list_senders:
        list_senders()
        return 0

    if args.status is not None:
        return show_status(args.status if args.status else None)

    if args.resume:
        state_file = STATE_DIR / f"{args.resume}.json"
        if not state_file.exists():
            print(f"❌ Campaign not found: {args.resume}")
            return 1
        with open(state_file) as f:
            state = json.load(f)
        # Extract original args from campaign_id
        print(f"Resume not yet implemented. Use original command with same CSV/sender.")
        return 1

    if not args.csv or not args.sender or not args.template:
        parser.print_help()
        print("\nExample:")
        print("  quick_campaign.py --csv contacts.csv --sender factoryjobs.eu --template template.txt --limit 50")
        return 1

    if not Path(args.csv).exists():
        print(f"❌ CSV not found: {args.csv}")
        return 1

    if not Path(args.template).exists():
        print(f"❌ Template not found: {args.template}")
        return 1

    return run_campaign(args)


if __name__ == "__main__":
    sys.exit(main())
