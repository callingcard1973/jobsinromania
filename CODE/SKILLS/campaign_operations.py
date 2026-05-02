#!/usr/bin/env python3
"""
Campaign Operations - Feed, Create, Clean

Usage:
    python3 campaign_operations.py --create-nordic
    python3 campaign_operations.py --feed-low
    python3 campaign_operations.py --bounce-cleanup
    python3 campaign_operations.py --all
"""

import os
import sys
import csv
import random
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
try:
    from skills_common import to_ascii
except:
    def to_ascii(t): return t.encode('ascii', 'ignore').decode('ascii') if t else ''

CAMPAIGNS_DIR = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS')

# Data sources with actual emails
DATA_SOURCES = {
    'NORWAY': '/opt/ACTIVE/EMAIL/CAMPAIGNS/NORWAY/segment_corporate.csv',
    'NORWAY_CARE': '/opt/ACTIVE/EMAIL/CAMPAIGNS/NORWAY_CARE_2026/contacts/contacts.csv',
    'TOURISM': '/opt/ACTIVE/EMAIL/CAMPAIGNS/TOURISM_RO/segments/segment_accommodation.csv',
    'POLAND': '/opt/ACTIVE/EMAIL/CAMPAIGNS/POLAND_AGENCIES/contacts/contacts.csv',
    'HORECA': '/opt/ACTIVE/EMAIL/CAMPAIGNS/HORECA2026/contacts/contacts.csv',
    'ANOFM': '/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM/contacts/contacts.csv',
    'CONSTRUCT': '/opt/ACTIVE/EMAIL/CAMPAIGNS/CONSTRUCT2026/contacts/contacts.csv',
    'DSVSA': '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/DSVSA/DSVSA_WITH_CONTACTS.csv',
}

def load_emails_from_csv(filepath, limit=5000):
    """Extract email,company from CSV."""
    contacts = []
    if not Path(filepath).exists():
        return contacts

    with open(filepath, 'r', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Try common email column names
            email = None
            for col in ['email', 'Email', 'email_1', 'EMAIL', 'e-mail']:
                if col in row and row[col] and '@' in row[col]:
                    email = row[col].strip().lower()
                    break

            if not email:
                continue

            # Get company
            company = ''
            for col in ['company', 'company_name', 'Company', 'employer', 'nume_firma']:
                if col in row and row[col]:
                    company = to_ascii(row[col].strip())[:100]
                    break

            contacts.append({'email': email, 'company': company})
            if len(contacts) >= limit:
                break

    return contacts

def get_existing_emails(campaign):
    """Get all emails already in campaign (contacts + sent logs)."""
    existing = set()

    contacts_file = CAMPAIGNS_DIR / campaign / 'contacts' / 'contacts.csv'
    if contacts_file.exists():
        with open(contacts_file, 'r', errors='ignore') as f:
            for row in csv.DictReader(f):
                email = (row.get('email') or '').strip().lower()
                if email:
                    existing.add(email)

    log_dir = CAMPAIGNS_DIR / campaign / 'logs'
    if log_dir.exists():
        for log in log_dir.glob('sent_*.log'):
            for line in log.read_text(errors='ignore').splitlines():
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 2:
                        existing.add(parts[1].strip().lower())

    return existing

def create_nordic_campaigns():
    """Create/feed SWEDEN, NORWAY, FINLAND campaigns."""
    print("\n=== Creating Nordic Campaigns ===\n")

    # NORWAY - from existing Norway data
    norway_contacts = []
    for src in ['NORWAY', 'NORWAY_CARE']:
        if src in DATA_SOURCES:
            norway_contacts.extend(load_emails_from_csv(DATA_SOURCES[src], 3000))

    if norway_contacts:
        camp_dir = CAMPAIGNS_DIR / 'NORWAY_BREVO'
        camp_dir.mkdir(exist_ok=True)
        (camp_dir / 'contacts').mkdir(exist_ok=True)
        (camp_dir / 'templates').mkdir(exist_ok=True)
        (camp_dir / 'logs').mkdir(exist_ok=True)

        # Dedupe
        seen = set()
        unique = []
        for c in norway_contacts:
            if c['email'] not in seen:
                seen.add(c['email'])
                unique.append(c)

        random.shuffle(unique)
        unique = unique[:2000]

        with open(camp_dir / 'contacts' / 'contacts.csv', 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=['email', 'company'])
            w.writeheader()
            w.writerows(unique)

        # Template
        template = """Subject: Workforce Solutions for Norway

Dear {company},

We provide skilled workers for companies in Norway.

Available positions:
- Healthcare and eldercare workers
- Construction and trades
- Hospitality and service industry

All workers have EU documentation and are ready to relocate.

Interested in discussing your needs?

Best regards,
European Staffing Solutions
"""
        (camp_dir / 'templates' / '01_english.txt').write_text(template)
        print(f"NORWAY_BREVO: {len(unique)} contacts")

    # SWEDEN - from HORECA (many Swedish companies there)
    sweden_contacts = load_emails_from_csv(DATA_SOURCES.get('HORECA', ''), 2000)

    if sweden_contacts:
        camp_dir = CAMPAIGNS_DIR / 'SWEDEN_BREVO'
        camp_dir.mkdir(exist_ok=True)
        (camp_dir / 'contacts').mkdir(exist_ok=True)
        (camp_dir / 'templates').mkdir(exist_ok=True)
        (camp_dir / 'logs').mkdir(exist_ok=True)

        seen = set()
        unique = [c for c in sweden_contacts if c['email'] not in seen and not seen.add(c['email'])]
        random.shuffle(unique)
        unique = unique[:1500]

        with open(camp_dir / 'contacts' / 'contacts.csv', 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=['email', 'company'])
            w.writeheader()
            w.writerows(unique)

        template = """Subject: Workers Available for Sweden

Dear {company},

We recruit workers for the Swedish market.

We can provide:
- Hotel and restaurant staff
- Warehouse and logistics workers
- Production and factory workers

Ready for immediate placement with full documentation.

Would you like to learn more?

Best regards,
European Staffing Solutions
"""
        (camp_dir / 'templates' / '01_english.txt').write_text(template)
        print(f"SWEDEN_BREVO: {len(unique)} contacts")

    # FINLAND - from ANOFM (some Finnish companies)
    finland_contacts = load_emails_from_csv(DATA_SOURCES.get('ANOFM', ''), 1500)

    if finland_contacts:
        camp_dir = CAMPAIGNS_DIR / 'FINLAND_BREVO'
        camp_dir.mkdir(exist_ok=True)
        (camp_dir / 'contacts').mkdir(exist_ok=True)
        (camp_dir / 'templates').mkdir(exist_ok=True)
        (camp_dir / 'logs').mkdir(exist_ok=True)

        seen = set()
        unique = [c for c in finland_contacts if c['email'] not in seen and not seen.add(c['email'])]
        random.shuffle(unique)
        unique = unique[:1000]

        with open(camp_dir / 'contacts' / 'contacts.csv', 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=['email', 'company'])
            w.writeheader()
            w.writerows(unique)

        template = """Subject: Workforce for Finland

Dear {company},

We provide workers for Finnish companies.

Available:
- Care and healthcare workers
- Cleaning and facility services
- Manufacturing and production

All candidates have work permits and relevant experience.

Interested?

Best regards,
European Staffing Solutions
"""
        (camp_dir / 'templates' / '01_english.txt').write_text(template)
        print(f"FINLAND_BREVO: {len(unique)} contacts")

def feed_low_campaigns():
    """Feed campaigns with < 500 contacts."""
    print("\n=== Feeding Low-Contact Campaigns ===\n")

    # Target campaigns and their data sources
    feed_map = {
        'WAREHOUSE_BREVO': ['CONSTRUCT', 'ANOFM'],
        'CUMPARLEGUME_BREVO': ['HORECA', 'DSVSA'],
        'SEICARESCU_BREVO': ['ANOFM', 'CONSTRUCT'],
    }

    for campaign, sources in feed_map.items():
        camp_dir = CAMPAIGNS_DIR / campaign
        if not camp_dir.exists():
            continue

        existing = get_existing_emails(campaign)
        print(f"{campaign}: {len(existing)} existing")

        # Gather new contacts
        new_contacts = []
        for src in sources:
            if src in DATA_SOURCES:
                contacts = load_emails_from_csv(DATA_SOURCES[src], 2000)
                new_contacts.extend([c for c in contacts if c['email'] not in existing])

        # Dedupe
        seen = set()
        unique = []
        for c in new_contacts:
            if c['email'] not in seen:
                seen.add(c['email'])
                unique.append(c)

        if not unique:
            print(f"  No new contacts found")
            continue

        random.shuffle(unique)
        to_add = unique[:500]

        contacts_file = camp_dir / 'contacts' / 'contacts.csv'
        with open(contacts_file, 'a', newline='') as f:
            w = csv.DictWriter(f, fieldnames=['email', 'company'])
            if contacts_file.stat().st_size == 0:
                w.writeheader()
            w.writerows(to_add)

        print(f"  Added {len(to_add)} contacts")

def bounce_cleanup():
    """Remove bounced emails from all campaign contact files."""
    print("\n=== Bounce Cleanup ===\n")

    # Collect all bounced emails from logs
    bounced = set()

    for camp_dir in CAMPAIGNS_DIR.iterdir():
        if not camp_dir.is_dir():
            continue
        log_dir = camp_dir / 'logs'
        if not log_dir.exists():
            continue

        for log in log_dir.glob('*.log'):
            for line in log.read_text(errors='ignore').splitlines():
                if 'FAIL' in line or 'bounce' in line.lower() or '550' in line:
                    if '|' in line:
                        parts = line.split('|')
                        if len(parts) >= 2:
                            email = parts[1].strip().lower()
                            if '@' in email:
                                bounced.add(email)

    # Also check blacklist
    blacklist = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/EMAIL_CLEANUP/blacklist.txt')
    if blacklist.exists():
        for line in blacklist.read_text().splitlines():
            email = line.strip().lower()
            if '@' in email:
                bounced.add(email)

    print(f"Found {len(bounced)} bounced emails")

    # Remove from each campaign
    total_removed = 0
    for camp_dir in CAMPAIGNS_DIR.iterdir():
        if not camp_dir.is_dir():
            continue

        contacts_file = camp_dir / 'contacts' / 'contacts.csv'
        if not contacts_file.exists():
            continue

        # Read contacts
        contacts = []
        removed = 0
        with open(contacts_file, 'r', errors='ignore') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                email = (row.get('email') or '').strip().lower()
                if email in bounced:
                    removed += 1
                else:
                    contacts.append(row)

        if removed > 0:
            # Rewrite file without bounced
            with open(contacts_file, 'w', newline='') as f:
                w = csv.DictWriter(f, fieldnames=fieldnames)
                w.writeheader()
                w.writerows(contacts)
            print(f"{camp_dir.name}: removed {removed} bounced")
            total_removed += removed

    print(f"\nTotal removed: {total_removed}")

def main():
    parser = argparse.ArgumentParser(description='Campaign Operations')
    parser.add_argument('--create-nordic', action='store_true', help='Create Nordic campaigns')
    parser.add_argument('--feed-low', action='store_true', help='Feed low-contact campaigns')
    parser.add_argument('--bounce-cleanup', action='store_true', help='Remove bounced emails')
    parser.add_argument('--all', action='store_true', help='Run all operations')
    args = parser.parse_args()

    if args.all:
        create_nordic_campaigns()
        feed_low_campaigns()
        bounce_cleanup()
    elif args.create_nordic:
        create_nordic_campaigns()
    elif args.feed_low:
        feed_low_campaigns()
    elif args.bounce_cleanup:
        bounce_cleanup()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
