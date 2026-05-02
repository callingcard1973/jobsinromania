#!/usr/bin/env python3
"""Feed GERMANY_ULTIMATE_MASTER.csv into email campaigns.
Deduplicates against existing contacts and already-sent emails.
Splits into GERMANY (general employers) and GERMANY_AGENCIES (staffing agencies).

Usage:
    python3 germany_campaign_feeder.py           # Feed new contacts into campaigns
    python3 germany_campaign_feeder.py --status   # Show current campaign status
    python3 germany_campaign_feeder.py --dry-run  # Show what would be added without writing
"""

import csv
import json
import os
import re
import sys
import argparse
from datetime import datetime
from pathlib import Path

MASTER = '/opt/ACTIVE/OPENDATA/DATA/GERMANY_ENRICHED/GERMANY_ULTIMATE_MASTER.csv'
CAMPAIGNS_DIR = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS')

CAMPAIGNS = {
    'GERMANY': CAMPAIGNS_DIR / 'GERMANY',
    'GERMANY_AGENCIES': CAMPAIGNS_DIR / 'GERMANY_AGENCIES',
}

# Keywords that identify staffing/temp agencies
AGENCY_KEYWORDS = [
    'zeitarbeit', 'personal', 'leiharbeit', 'staffing', 'recruiting',
    'arbeitnehmerüberlassung', 'arbeitnehmerueberlassung', 'temporary',
    'manpower', 'randstad', 'adecco', 'hays', 'robert half',
    'personalvermittlung', 'personaldienstleistung', 'personalservice',
    'personalberatung', 'tempton', 'i.k. hofmann', 'piening',
    'orient', 'start people', 'unique', 'avanta', 'bindan',
]

def is_agency(company_name):
    """Check if company is a staffing/temp agency."""
    name_lower = company_name.lower()
    return any(kw in name_lower for kw in AGENCY_KEYWORDS)

def load_existing_emails(campaign_dir):
    """Load all existing + already-sent emails for a campaign."""
    emails = set()

    # From contacts file
    contacts_file = campaign_dir / 'contacts' / 'contacts.csv'
    if contacts_file.exists():
        with open(contacts_file, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get('email', '').strip().lower()
                if email:
                    emails.add(email)

    # From state.json (already sent)
    state_file = campaign_dir / 'state.json'
    if state_file.exists():
        try:
            with open(state_file) as f:
                state = json.load(f)
            for email in state.get('sent', []):
                emails.add(email.lower())
            for email in state.get('bounced', []):
                emails.add(email.lower())
            for email in state.get('blacklisted', []):
                emails.add(email.lower())
        except (json.JSONDecodeError, TypeError):
            pass

    # From all_contacts.csv if exists
    all_contacts = campaign_dir / 'contacts' / 'all_contacts.csv'
    if all_contacts.exists():
        with open(all_contacts, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            for row in reader:
                for col in ['email', 'email_1']:
                    email = row.get(col, '').strip().lower()
                    if email:
                        emails.add(email)

    return emails

def load_master():
    """Load ULTIMATE_MASTER contacts."""
    contacts = []
    with open(MASTER, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = row.get('email', '').strip().lower()
            if email and '@' in email:
                contacts.append(row)
    return contacts

def show_status():
    """Show current campaign status."""
    for name, cdir in CAMPAIGNS.items():
        existing = load_existing_emails(cdir)
        contacts_file = cdir / 'contacts' / 'contacts.csv'
        count = 0
        if contacts_file.exists():
            with open(contacts_file) as f:
                count = sum(1 for _ in f) - 1

        state_file = cdir / 'state.json'
        sent = 0
        if state_file.exists():
            try:
                with open(state_file) as f:
                    state = json.load(f)
                sent = len(state.get('sent', []))
            except:
                pass

        print(f"{name}: {count} contacts, {sent} sent, {len(existing)} total known emails")

def main():
    parser = argparse.ArgumentParser(description='Germany Campaign Feeder')
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if not os.path.exists(MASTER):
        print(f"ERROR: {MASTER} not found. Run germany_consolidate_master.py first.")
        sys.exit(1)

    # Load master contacts
    master_contacts = load_master()
    print(f"ULTIMATE_MASTER: {len(master_contacts)} contacts")

    # Load existing emails from both campaigns
    germany_existing = load_existing_emails(CAMPAIGNS['GERMANY'])
    agencies_existing = load_existing_emails(CAMPAIGNS['GERMANY_AGENCIES'])
    all_existing = germany_existing | agencies_existing
    print(f"Already known: GERMANY={len(germany_existing)}, AGENCIES={len(agencies_existing)}, combined={len(all_existing)}")

    # Split and dedup
    new_germany = []
    new_agencies = []

    for contact in master_contacts:
        email = contact['email'].lower()
        if email in all_existing:
            continue

        company = contact.get('company_name', '')
        row = {
            'denumire': company,
            'anaf_phone': contact.get('phone', ''),
            'email': email,
        }

        if is_agency(company):
            new_agencies.append(row)
        else:
            new_germany.append(row)

    print(f"\nNew contacts to add:")
    print(f"  GERMANY (general): {len(new_germany)}")
    print(f"  GERMANY_AGENCIES (staffing): {len(new_agencies)}")

    if args.dry_run:
        print("\n[DRY RUN] No files written.")
        if new_germany:
            print("\nSample GERMANY:")
            for c in new_germany[:5]:
                print(f"  {c['denumire']} - {c['email']}")
        if new_agencies:
            print("\nSample AGENCIES:")
            for c in new_agencies[:5]:
                print(f"  {c['denumire']} - {c['email']}")
        return

    # Append to campaign contacts
    for camp_name, new_contacts in [('GERMANY', new_germany), ('GERMANY_AGENCIES', new_agencies)]:
        if not new_contacts:
            continue

        contacts_file = CAMPAIGNS[camp_name] / 'contacts' / 'contacts.csv'

        # Backup existing
        if contacts_file.exists():
            backup = contacts_file.parent / f"contacts_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            import shutil
            shutil.copy2(contacts_file, backup)
            print(f"  Backed up {camp_name} contacts to {backup.name}")

        # Read existing
        existing_rows = []
        if contacts_file.exists():
            with open(contacts_file, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)
                existing_rows = list(reader)

        # Append new
        all_rows = existing_rows + new_contacts

        with open(contacts_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['denumire', 'anaf_phone', 'email'])
            writer.writeheader()
            for row in all_rows:
                writer.writerow(row)

        print(f"  {camp_name}: {len(existing_rows)} existing + {len(new_contacts)} new = {len(all_rows)} total")

    print(f"\nDone! Campaigns updated.")
    print(f"Total new contacts added: {len(new_germany) + len(new_agencies)}")

if __name__ == '__main__':
    main()
