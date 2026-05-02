#!/usr/bin/env python3
"""Zoho SMTP Campaign Sender"""
import sys, os, csv, json, time, ssl, smtplib, argparse
from pathlib import Path
from datetime import datetime, date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

STATE_DIR = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/QUICK_CAMPAIGNS')
STATE_DIR.mkdir(parents=True, exist_ok=True)

def get_zoho_config():
    """Get Zoho credentials from .env"""
    return {
        'host': os.getenv('ZOHO_SMTP_HOST', 'smtp.zoho.com'),
        'port': int(os.getenv('ZOHO_SMTP_PORT', '587')),
        'user': os.getenv('ZOHO_SMTP_USER', ''),
        'password': os.getenv('ZOHO_SMTP_PASSWORD', ''),
        'from_name': os.getenv('ZOHO_FROM_NAME', 'InterJob'),
    }

def load_template(path):
    """Load template"""
    with open(path, encoding='utf-8', errors='ignore') as f:
        lines = f.read().strip().split('\n')
    subject = next((l[8:].strip() for l in lines if l.lower().startswith('subject:')), '')
    body_start = next((i+2 for i, l in enumerate(lines) if l.lower().startswith('subject:')), 0)
    return subject, '\n'.join(lines[body_start:])

def load_csv(path):
    """Load contacts"""
    contacts = []
    with open(path, encoding='utf-8', errors='ignore') as f:
        for row in csv.DictReader(f):
            email = row.get('email', '').strip().lower()
            name = row.get('name', '').strip()[:100]
            if '@' in email:
                contacts.append({'email': email, 'name': name, 'company': row.get('name', name)})
    return contacts

def send_zoho(config, to_email, subject, body):
    """Send via Zoho SMTP"""
    try:
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = f"{config['from_name']} <{config['user']}>"
        msg['To'] = to_email
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        ctx = ssl.create_default_context()
        with smtplib.SMTP(config['host'], config['port'], timeout=10) as srv:
            srv.starttls(context=ctx)
            srv.login(config['user'], config['password'])
            srv.send_message(msg)
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', required=True)
    parser.add_argument('--template', required=True)
    parser.add_argument('--limit', type=int, default=25)
    parser.add_argument('--delay', type=int, default=900)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    
    config = get_zoho_config()
    if not config['user'] or not config['password']:
        print('❌ Zoho credentials not in .env')
        return 1
    
    subject, body = load_template(args.template)
    contacts = load_csv(args.csv)
    
    print(f"📧 Loaded {len(contacts)} contacts")
    print(f"📝 Subject: {subject[:60]}")
    print(f"🔧 Sender: {config['user']}")
    print(f"📤 Limit: {args.limit}/day | Delay: {args.delay}s")
    
    if args.dry_run:
        print("\n🔍 DRY RUN\n")
        for c in contacts[:5]:
            print(f"  {c['email']} ({c['company'][:30]})")
        print(f"  ... and {len(contacts)-5} more" if len(contacts) > 5 else "")
        return 0
    
    sent = 0
    for i, c in enumerate(contacts):
        if sent >= args.limit:
            break
        if send_zoho(config, c['email'], subject, body):
            sent += 1
            print(f"✅ {sent}/{args.limit} {c['email']}")
            time.sleep(args.delay)
        else:
            print(f"❌ {c['email']}")
    
    print(f"\n✓ Sent {sent} emails")

if __name__ == '__main__':
    sys.exit(main() or 0)
