#!/usr/bin/env python3
"""
EU Fonduri Campaign Setup - Create campaign from scraped EU fund winners

Usage:
    python3 eu_fonduri_campaign_setup.py --leads /path/to/leads.csv
    python3 eu_fonduri_campaign_setup.py --list                    # List campaigns
    python3 eu_fonduri_campaign_setup.py --run                     # Run main campaign
    python3 eu_fonduri_campaign_setup.py --run-followup          # Run follow-up

Creates:
    - Personalized emails with gender detection (Domnule/Doamna)
    - Brevo for corporate emails
    - Gmail for Yahoo/Gmail addresses
    - Follow-up after 3 days
    - CSV tracking with sent/response columns
"""

import argparse
import csv
import json
import os
import random
import smtplib
import sys
import time
import requests
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from pathlib import Path
from dotenv import load_dotenv

# Configuration
CSV_FILE = '/opt/ACTIVE/SCRAPERS/ROMANIA/SCRAPERS/LISTAFIRME/DATA/output/emails_constructii_personalizate.csv'
TEMPLATE_FILE = '/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/CAMPAIGNS/EU_FONDURI_CONSTRUCTII/template.txt'
FOLLOWUP_TEMPLATE = '/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/CAMPAIGNS/EU_FONDURI_CONSTRUCTII/template_followup.txt'
STATE_FILE = '/opt/ACTIVE/SCRAPERS/ROMANIA/SCRAPERS/LISTAFIRME/DATA/output/eu_fonduri_state.txt'
FOLLOWUP_STATE = '/opt/ACTIVE/SCRAPERS/ROMANIA/SCRAPERS/LISTAFIRME/DATA/output/eu_fonduri_followup_state.txt'

# Senders
BREVO_API_KEY = os.getenv('BREVO_SEICARESCU_API_KEY')
BREVO_EMAIL = 'tudor@seicarescu.com'
BREVO_NAME = 'Tudor Seicarescu'
GMAIL_EMAIL = os.getenv('GMAIL_EXPATS_USER')
GMAIL_PASSWORD = os.getenv('GMAIL_EXPATS_PASSWORD')

DAILY_LIMIT = 50
DELAY_MIN = 400  # 7 minutes
DELAY_MAX = 440
GMAIL_DOMAINS = ['gmail.com', 'yahoo.com', 'ymail.com', 'hotmail.com', 'outlook.com']

# Romanian first names for gender detection
MALE_FIRST = ['ADRIAN', 'ALEXANDRU', 'ANDREI', 'CATALIN', 'CONSTANTIN', 'CRISTIAN',
    'DANIEL', 'DINU', 'EMIL', 'FLORIN', 'GHEORGHE', 'ION', 'IONUT', 'MARIUS',
    'MIRCEA', 'NICOLAE', 'OVIDIU', 'PAUL', 'PETRE', 'RADU', 'RAZVAN', 'ROMULUS',
    'SORIN', 'STEFAN', 'VALENTIN', 'VASILE', 'LIVIU', 'CALIN', 'CIPRIAN', 'COSMIN',
    'DAN', 'DORIN', 'DRAGOS', 'EUGEN', 'FILIP', 'GEORGE', 'IULIAN', 'LAURENTIU',
    'MARIAN', 'MIHAI', 'NICUSOR', 'OCTAVIAN', 'OLEG', 'PAVEL', 'PETRU', 'RALUCA',
    'ROBERT', 'SEBASTIAN', 'SILVIU', 'TEODOR', 'TIBERIU', 'TUDOR', 'VIOREL', 'VLAD']

FEMALE_FIRST = ['ADRIANA', 'ALINA', 'ANA', 'ANDREEA', 'ANCA', 'BIANCA', 'CARMEN',
    'CORINA', 'CRISTINA', 'DANIELA', 'DIANA', 'ELENA', 'FLORICA', 'GEORGETA',
    'IOANA', 'IONELA', 'LAURA', 'LOREDANA', 'LUMINITA', 'MADALINA', 'MARGARETA',
    'MARIA', 'MARINA', 'MELANIA', 'MIHAELA', 'MONICA', 'NATALIA', 'NICOLETA',
    'OANA', 'PETRONELA', 'RAMONA', 'RODICA', 'SANDA', 'SILVIA', 'SIMONA',
    'SORINA', 'STEFANIA', 'VALENTINA', 'VIORICA', 'IULIANA', 'GEORGIANA']


def detect_gender(name):
    """Detect gender from Romanian name (Domnule/Doamna)"""
    if not name:
        return 'Domnule'
    name_upper = name.upper().replace('-', ' ')
    for part in name_upper.split():
        if part in FEMALE_FIRST:
            return 'Doamna'
    return 'Domnule'


def load_template(path):
    """Load email template"""
    with open(path) as f:
        content = f.read()
    lines = content.strip().split('\n')
    subject = lines[0].replace('Subject: ', '')
    body = '\n'.join(lines[2:])
    return subject, body


def get_sender(email):
    """Choose sender based on email domain"""
    domain = email.lower().split('@')[1].split('.')[0]
    return 'gmail' if domain in GMAIL_DOMAINS else 'brevo'


def send_brevo(to_email, subject, body):
    """Send via Brevo API"""
    url = "https://api.brevo.com/v3/smtp/email"
    html = f"<div style='font-family:Arial;font-size:14px'>{body.replace(chr(10), '<br>')}</div>"
    payload = {
        "sender": {"email": BREVO_EMAIL, "name": BREVO_NAME},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html,
        "replyTo": {"email": BREVO_EMAIL}
    }
    r = requests.post(url, json=payload, headers={"api-key": BREVO_API_KEY})
    return r.status_code == 201, r.text


def send_gmail(to_email, subject, body):
    """Send via Gmail SMTP"""
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = GMAIL_EMAIL
    msg['To'] = to_email
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_EMAIL, GMAIL_PASSWORD)
        server.sendmail(GMAIL_EMAIL, [to_email], msg.as_string())
        server.quit()
        return True, "OK"
    except Exception as e:
        return False, str(e)


def run_campaign(dry_run=False):
    """Run main campaign"""
    load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')
    subject_tpl, body_tpl = load_template(TEMPLATE_FILE)
    
    try:
        with open(STATE_FILE) as f:
            start_idx = int(f.read().strip())
    except:
        start_idx = 0
    
    with open(CSV_FILE) as f:
        reader = list(csv.DictReader(f))
    
    total = len(reader)
    sent_today = 0
    
    for i, row in enumerate(reader[start_idx:], start=start_idx):
        if sent_today >= DAILY_LIMIT:
            break
        if row.get('sent') == '1':
            continue
        
        to_email = row['to_email']
        company = row.get('company', '')
        contact = row.get('contact', '')
        salutation = detect_gender(contact)
        first_name = contact.split('-')[0].strip().split()[0] if contact else ''
        
        body = body_tpl.format(
            salutation=salutation,
            contact_name=first_name,
            company=company[:50],
            salutation_ending='a' if salutation == 'Doamna' else '',
            interested_ending='a' if salutation == 'Doamna' else ''
        )
        
        sender = get_sender(to_email)
        if sender == 'gmail':
            ok, resp = send_gmail(to_email, subject_tpl, body)
        else:
            ok, resp = send_brevo(to_email, subject_tpl, body)
        
        if ok:
            row['sent'] = '1'
            row['sent_at'] = datetime.now().isoformat()
            row['salutation'] = salutation
            sent_today += 1
            start_idx = i + 1
        
        time.sleep(random.randint(DELAY_MIN, DELAY_MAX))
    
    with open(STATE_FILE, 'w') as f:
        f.write(str(start_idx))
    
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=reader[0].keys())
        writer.writeheader()
        writer.writerows(reader)
    
    print(f"Done. Sent {sent_today} emails.")


def run_followup(dry_run=False):
    """Run follow-up campaign (3 days after)"""
    load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')
    subject_tpl, body_tpl = load_template(FOLLOWUP_TEMPLATE)
    
    try:
        with open(FOLLOWUP_STATE) as f:
            start_idx = int(f.read().strip())
    except:
        start_idx = 0
    
    with open(CSV_FILE) as f:
        reader = list(csv.DictReader(f))
    
    cutoff = datetime.now() - timedelta(days=3)
    candidates = []
    
    for i, row in enumerate(reader):
        if row.get('sent') != '1':
            continue
        if row.get('response', '').strip():
            continue
        if row.get('followup_sent') == '1':
            continue
        
        sent_at = row.get('sent_at', '')
        if sent_at:
            try:
                sent_date = datetime.fromisoformat(sent_at)
                if sent_date > cutoff:
                    continue
            except:
                pass
        candidates.append((i, row))
    
    total = len(candidates)
    sent_today = 0
    
    for idx, (i, row) in enumerate(candidates[start_idx:], start=start_idx):
        if sent_today >= DAILY_LIMIT:
            break
        
        to_email = row['to_email']
        company = row.get('company', '')
        contact = row.get('contact', '')
        salutation = row.get('salutation', 'Domnule')
        first_name = contact.split('-')[0].strip().split()[0] if contact else ''
        
        body = body_tpl.format(
            salutation=salutation,
            contact_name=first_name,
            company=company[:50]
        )
        
        sender = get_sender(to_email)
        if sender == 'gmail':
            ok, resp = send_gmail(to_email, subject_tpl, body)
        else:
            ok, resp = send_brevo(to_email, subject_tpl, body)
        
        if ok:
            row['followup_sent'] = '1'
            row['followup_sent_at'] = datetime.now().isoformat()
            sent_today += 1
            start_idx = idx + 1
        
        time.sleep(random.randint(DELAY_MIN, DELAY_MAX))
    
    with open(FOLLOWUP_STATE, 'w') as f:
        f.write(str(start_idx))
    
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=reader[0].keys())
        writer.writeheader()
        writer.writerows(reader)
    
    print(f"Done. Sent {sent_today} follow-ups.")


def list_campaigns():
    """List campaign status"""
    import pandas as pd
    df = pd.read_csv(CSV_FILE)
    print(f"\n=== EU Fonduri Constructii Campaign ===")
    print(f"Total: {len(df)}")
    print(f"Sent: {(df['sent'] == '1').sum()}")
    print(f"Follow-up sent: {(df['followup_sent'] == '1').sum()}")
    print(f"With response: {df['response'].notna().sum()}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true', help='Run main campaign')
    parser.add_argument('--run-followup', action='store_true', help='Run follow-up')
    parser.add_argument('--list', action='store_true', help='List status')
    parser.add_argument('--dry', action='store_true', help='Dry run')
    args = parser.parse_args()
    
    if args.list:
        list_campaigns()
    elif args.run:
        run_campaign(args.dry)
    elif args.run_followup:
        run_followup(args.dry)
    else:
        print(__doc__)
