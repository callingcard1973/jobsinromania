#!/opt/ACTIVE/INFRA/venv/bin/python3
"""Feed enriched contacts to campaigns"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
import csv
import os
from pathlib import Path
from datetime import datetime
from skills_common import to_ascii

# Enriched sources -> Campaign mapping
FEEDS = {
    # Nordic -> FACTORY_EU and NORDIC campaigns
    '/opt/ACTIVE/OPENDATA/DATA/ENRICHED/SE_ENRICHED.csv': {
        'campaign': '/opt/ACTIVE/EMAIL/CAMPAIGNS/FACTORY_EU/contacts/enriched_nordic.csv',
        'country': 'Sweden'
    },
    '/opt/ACTIVE/OPENDATA/DATA/ENRICHED/NO_ENRICHED.csv': {
        'campaign': '/opt/ACTIVE/EMAIL/CAMPAIGNS/FACTORY_EU/contacts/enriched_nordic.csv',
        'country': 'Norway'
    },
    '/opt/ACTIVE/OPENDATA/DATA/ENRICHED/DK_ENRICHED.csv': {
        'campaign': '/opt/ACTIVE/EMAIL/CAMPAIGNS/FACTORY_EU/contacts/enriched_nordic.csv',
        'country': 'Denmark'
    },
    '/opt/ACTIVE/OPENDATA/DATA/ENRICHED/FI_ENRICHED.csv': {
        'campaign': '/opt/ACTIVE/EMAIL/CAMPAIGNS/FACTORY_EU/contacts/enriched_nordic.csv',
        'country': 'Finland'
    },
    # Germany -> FACTORY_EU
    '/opt/ACTIVE/OPENDATA/DATA/GERMANY_ENRICHED/Germany_ENRICHED_MASTER.csv': {
        'campaign': '/opt/ACTIVE/EMAIL/CAMPAIGNS/FACTORY_EU/contacts/enriched_germany.csv',
        'country': 'Germany'
    },
    '/opt/ACTIVE/OPENDATA/DATA/GERMANY_ENRICHED/EURES_Germany_ENRICHED.csv': {
        'campaign': '/opt/ACTIVE/EMAIL/CAMPAIGNS/FACTORY_EU/contacts/enriched_germany.csv',
        'country': 'Germany'
    },
}

# Standard output format
HEADERS = ['email', 'company', 'country', 'website', 'source', 'added_date']

def load_existing_emails(campaign_file):
    """Load existing emails to avoid duplicates"""
    emails = set()
    if os.path.exists(campaign_file):
        with open(campaign_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('email'):
                    emails.add(row['email'].lower().strip())
    return emails

def feed_enriched():
    stats = {}
    
    for source, config in FEEDS.items():
        if not os.path.exists(source):
            print(f"SKIP: {source} not found")
            continue
        
        campaign_file = config['campaign']
        country = config['country']
        
        # Load existing to avoid dupes
        existing = load_existing_emails(campaign_file)
        
        # Read source
        new_contacts = []
        with open(source, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get('email', '').lower().strip()
                if email and '@' in email and email not in existing:
                    new_contacts.append({
                        'email': email,
                        'company': to_ascii(row.get('company', row.get('domain', ''))),
                        'country': country,
                        'website': row.get('website', ''),
                        'source': 'enriched',
                        'added_date': datetime.now().strftime('%Y-%m-%d')
                    })
                    existing.add(email)
        
        if new_contacts:
            # Append to campaign file
            file_exists = os.path.exists(campaign_file)
            with open(campaign_file, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=HEADERS)
                if not file_exists:
                    writer.writeheader()
                writer.writerows(new_contacts)
            
            stats[f"{country} -> {Path(campaign_file).name}"] = len(new_contacts)
            print(f"OK: {country} - {len(new_contacts)} new contacts -> {campaign_file}")
        else:
            print(f"SKIP: {country} - no new contacts")
    
    return stats

if __name__ == '__main__':
    print("=== FEEDING ENRICHED CONTACTS TO CAMPAIGNS ===")
    print(f"Time: {datetime.now()}\n")
    stats = feed_enriched()
    print(f"\n=== SUMMARY ===")
    total = sum(stats.values())
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print(f"\nTotal new contacts added: {total}")
