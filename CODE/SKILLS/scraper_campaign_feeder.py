#!/usr/bin/env python3
"""
Scraper to Campaign Auto-Feeder

Filters EURES/ANOFM data by industry and feeds to appropriate Brevo campaigns.
Run daily after scrapers complete.

Usage:
    python3 scraper_campaign_feeder.py --status
    python3 scraper_campaign_feeder.py --feed
    python3 scraper_campaign_feeder.py --feed --campaign BUILDJOBS_BREVO
"""

import os
import sys
import csv
import json
import random
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
try:
    from skills_common import to_ascii
except:
    def to_ascii(t): return t if not t else t.encode('ascii', 'ignore').decode('ascii')

CAMPAIGNS_DIR = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS')
EURES_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/SCRAPER_CSV/EURES')
ANOFM_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/ANOFM')

# Industry keywords for filtering
INDUSTRY_FILTERS = {
    'BUILDJOBS_BREVO': {
        'keywords': ['construction', 'building', 'carpenter', 'mason', 'bricklayer',
                     'painter', 'roofer', 'plumber', 'electrician', 'welder',
                     'bygge', 'snekker', 'murer', 'byggnad', 'constructii'],
        'sources': ['EURES', 'ANOFM'],
    },
    'CAREWORKERS_BREVO': {
        'keywords': ['care', 'nurse', 'healthcare', 'hospital', 'elderly', 'medical',
                     'sykepleier', 'helse', 'omsorg', 'sjukskoterska', 'ingrijire'],
        'sources': ['EURES', 'ANOFM', 'CQC'],
    },
    'FACTORYJOBS_BREVO': {
        'keywords': ['factory', 'production', 'manufacturing', 'machine', 'operator',
                     'assembly', 'industrial', 'fabrik', 'produksjon', 'fabrica'],
        'sources': ['EURES', 'ANOFM'],
    },
    'WAREHOUSE_BREVO': {
        'keywords': ['warehouse', 'logistics', 'forklift', 'picker', 'packing',
                     'storage', 'distribution', 'lager', 'logistik', 'depozit'],
        'sources': ['EURES', 'ANOFM'],
    },
    'CUMPARLEGUME_BREVO': {
        'keywords': ['food', 'restaurant', 'hotel', 'hospitality', 'kitchen', 'cook',
                     'chef', 'catering', 'horeca', 'bucatar', 'alimentatie'],
        'sources': ['EURES', 'ANOFM', 'HORECA'],
    },
    'SEICARESCU_BREVO': {
        'keywords': ['transport', 'driver', 'truck', 'delivery', 'shipping',
                     'sofer', 'transport', 'chauffeur', 'lastbil'],
        'sources': ['EURES', 'ANOFM'],
    },
}

def load_existing_contacts(campaign):
    """Load already-sent emails to avoid duplicates."""
    existing = set()
    contacts_file = CAMPAIGNS_DIR / campaign / 'contacts' / 'contacts.csv'
    if contacts_file.exists():
        with open(contacts_file, 'r', errors='ignore') as f:
            for row in csv.DictReader(f):
                email = row.get('email', '').strip().lower()
                if email:
                    existing.add(email)
    # Also check logs
    log_dir = CAMPAIGNS_DIR / campaign / 'logs'
    if log_dir.exists():
        for log in log_dir.glob('sent_*.log'):
            for line in log.read_text(errors='ignore').splitlines():
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 2:
                        existing.add(parts[1].strip().lower())
    return existing

def scan_eures_for_industry(keywords):
    """Scan EURES CSVs for matching industry contacts."""
    contacts = []
    if not EURES_DIR.exists():
        return contacts

    for csv_file in EURES_DIR.rglob('*.csv'):
        try:
            with open(csv_file, 'r', errors='ignore') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Check if any field matches keywords
                    text = ' '.join(str(v).lower() for v in row.values())
                    if any(kw in text for kw in keywords):
                        email = row.get('email', row.get('Email', '')).strip().lower()
                        company = row.get('company', row.get('Company', row.get('employer', ''))).strip()
                        if email and '@' in email:
                            contacts.append({
                                'email': email,
                                'company': to_ascii(company)[:100]
                            })
        except Exception as e:
            continue
    return contacts

def scan_anofm_for_industry(keywords):
    """Scan ANOFM data for matching industry contacts."""
    contacts = []
    anofm_files = list(Path('/opt/ACTIVE/OPENDATA/DATA').glob('ANOFM*.csv')) + list(Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM/contacts').glob('*.csv'))

    for csv_file in anofm_files:
        try:
            with open(csv_file, 'r', errors='ignore') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    text = ' '.join(str(v).lower() for v in row.values())
                    if any(kw in text for kw in keywords):
                        email = row.get('email', '').strip().lower()
                        company = row.get('company_name', row.get('company', '')).strip()
                        if email and '@' in email:
                            contacts.append({
                                'email': email,
                                'company': to_ascii(company)[:100]
                            })
        except:
            continue
    return contacts

def feed_campaign(campaign, limit=500):
    """Feed new contacts to a campaign."""
    if campaign not in INDUSTRY_FILTERS:
        print(f"Unknown campaign: {campaign}")
        return 0

    config = INDUSTRY_FILTERS[campaign]
    keywords = config['keywords']

    existing = load_existing_contacts(campaign)
    print(f"{campaign}: {len(existing)} existing contacts")

    # Gather new contacts
    new_contacts = []

    if 'EURES' in config['sources']:
        eures = scan_eures_for_industry(keywords)
        new_contacts.extend([c for c in eures if c['email'] not in existing])

    if 'ANOFM' in config['sources']:
        anofm = scan_anofm_for_industry(keywords)
        new_contacts.extend([c for c in anofm if c['email'] not in existing])

    # Deduplicate
    seen = set()
    unique = []
    for c in new_contacts:
        if c['email'] not in seen:
            seen.add(c['email'])
            unique.append(c)

    random.shuffle(unique)
    to_add = unique[:limit]

    if not to_add:
        print(f"{campaign}: No new contacts found")
        return 0

    # Append to contacts file
    contacts_file = CAMPAIGNS_DIR / campaign / 'contacts' / 'contacts.csv'
    file_exists = contacts_file.exists()

    with open(contacts_file, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['email', 'company'])
        if not file_exists:
            w.writeheader()
        w.writerows(to_add)

    print(f"{campaign}: Added {len(to_add)} new contacts")
    return len(to_add)

def show_status():
    """Show current status of all campaigns."""
    print("\n=== Campaign Feed Status ===\n")
    print(f"{'Campaign':<22} {'Contacts':>10} {'Keywords'}")
    print("-" * 70)

    for campaign, config in INDUSTRY_FILTERS.items():
        contacts_file = CAMPAIGNS_DIR / campaign / 'contacts' / 'contacts.csv'
        count = 0
        if contacts_file.exists():
            with open(contacts_file, 'r') as f:
                count = sum(1 for _ in f) - 1
        keywords = ', '.join(config['keywords'][:3]) + '...'
        print(f"{campaign:<22} {count:>10} {keywords}")

def main():
    parser = argparse.ArgumentParser(description='Scraper to Campaign Feeder')
    parser.add_argument('--status', action='store_true', help='Show status')
    parser.add_argument('--feed', action='store_true', help='Feed all campaigns')
    parser.add_argument('--campaign', help='Feed specific campaign')
    parser.add_argument('--limit', type=int, default=500, help='Max contacts to add')
    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.feed:
        if args.campaign:
            feed_campaign(args.campaign, args.limit)
        else:
            total = 0
            for campaign in INDUSTRY_FILTERS.keys():
                total += feed_campaign(campaign, args.limit)
            print(f"\nTotal added: {total} contacts")
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
