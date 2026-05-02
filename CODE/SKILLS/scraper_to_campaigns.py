#!/usr/bin/env python3
"""
Scraper to Campaign Auto-Feed
Automatically feeds fresh contacts from scrapers to email campaigns.
NO MX VALIDATION - just format and typo checks.

Usage:
    scraper_to_campaigns.py                    # Feed all campaigns
    scraper_to_campaigns.py --campaign NAME    # Feed specific campaign
    scraper_to_campaigns.py --status           # Show status only
    scraper_to_campaigns.py --dry-run          # Show what would be added
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import csv
import json
import re
from datetime import datetime
from pathlib import Path
from glob import glob
import argparse

# Import shared modules
from skills_common import to_ascii

# Paths
SCRAPER_DATA = Path("/opt/ACTIVE/SCRAPER_DATA")
CAMPAIGNS_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/CAMPAIGNS")

# Simple email validation (no MX)
def is_valid_email(email):
    """Basic email format validation - no MX checks."""
    if not email or not isinstance(email, str):
        return False
    email = email.strip().lower()
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return False
    # Block disposable domains
    disposable = ['tempmail', 'guerrilla', '10minute', 'throwaway', 'mailinator']
    for d in disposable:
        if d in email:
            return False
    return True

# Typo fixes
TYPO_DOMAINS = {
    'gamil.com': 'gmail.com', 'gmial.com': 'gmail.com', 'gmal.com': 'gmail.com',
    'gnail.com': 'gmail.com', 'gmai.com': 'gmail.com', 'gmail.ro': 'gmail.com',
    'hotmal.com': 'hotmail.com', 'hotmai.com': 'hotmail.com',
    'yaho.com': 'yahoo.com', 'yahooo.com': 'yahoo.com',
    'outlok.com': 'outlook.com', 'outloo.com': 'outlook.com',
}

def fix_typo(email):
    """Fix common email typos."""
    if not email:
        return email
    email = email.strip().lower()
    for typo, correct in TYPO_DOMAINS.items():
        if email.endswith(typo):
            return email.replace(typo, correct)
    return email

# Scraper to Campaign mapping
MAPPINGS = {
    "FACTORY_EU": {
        "scraper_path": SCRAPER_DATA / "csv" / "SWEDEN",
        "file_pattern": "Sweden_MASTER_50.csv",
        "source_fields": {"email": "email_1", "company": "company_name", "phone": "phone_1", "city": "company_city", "country": "country_name"},
        "contacts_file": "all_contacts.csv",
        "country": None
    },
    "ANOFM": {
        "scraper_path": SCRAPER_DATA / "csv" / "ANOFM",
        "file_pattern": "anofm_*.csv",
        "source_fields": {"email": "email_1", "company": "company_name", "phone": "phone_1", "city": "city", "country": "country_name"},
        "contacts_file": "contacts.csv",
        "country": "Romania"
    },
    "AGRI": {
        "scraper_path": Path("/opt/ACTIVE/OPENDATA/DATA/EU_AGRI_DATABASE"),
        "file_pattern": "eu_agri_coops_contacts.csv",
        "source_fields": {"email": "email", "company": "name", "phone": "phone", "city": "city", "country": "country"},
        "contacts_file": "all_contacts.csv",
        "country": None
    },
    "HORECA_RO": {
        "scraper_path": SCRAPER_DATA / "csv" / "ANOFM_SEGMENTS",
        "file_pattern": "anofm_horeca_*.csv",
        "source_fields": {"email": "email_1", "company": "company_name", "phone": "phone_1", "city": "city", "country": "country_name"},
        "contacts_file": "contacts.csv",
        "country": "Romania",
        "target_campaign": "LUCIAN_HORECA_2026"
    },
    "FACTORY_RO": {
        "scraper_path": SCRAPER_DATA / "csv" / "ANOFM_SEGMENTS",
        "file_pattern": "anofm_factory_*.csv",
        "source_fields": {"email": "email_1", "company": "company_name", "phone": "phone_1", "city": "city", "country": "country_name"},
        "contacts_file": "contacts.csv",
        "country": "Romania",
        "target_campaign": "NECALIFICATI_FEB_2026"
    },
    "CONSTRUCTION_RO": {
        "scraper_path": SCRAPER_DATA / "csv" / "ANOFM_SEGMENTS",
        "file_pattern": "anofm_construction_*.csv",
        "source_fields": {"email": "email_1", "company": "company_name", "phone": "phone_1", "city": "city", "country": "country_name"},
        "contacts_file": "contacts.csv",
        "country": "Romania"
    },
    "TRANSPORT_RO": {
        "scraper_path": SCRAPER_DATA / "csv" / "ANOFM_SEGMENTS",
        "file_pattern": "anofm_transport_*.csv",
        "source_fields": {"email": "email_1", "company": "company_name", "phone": "phone_1", "city": "city", "country": "country_name"},
        "contacts_file": "contacts.csv",
        "country": "Romania"
    },
    "RETAIL_RO": {
        "scraper_path": SCRAPER_DATA / "csv" / "ANOFM_SEGMENTS",
        "file_pattern": "anofm_retail_*.csv",
        "source_fields": {"email": "email_1", "company": "company_name", "phone": "phone_1", "city": "city", "country": "country_name"},
        "contacts_file": "contacts.csv",
        "country": "Romania"
    },
    "AGRI_RO": {
        "scraper_path": SCRAPER_DATA / "csv" / "ANOFM_SEGMENTS",
        "file_pattern": "anofm_agri_*.csv",
        "source_fields": {"email": "email_1", "company": "company_name", "phone": "phone_1", "city": "city", "country": "country_name"},
        "contacts_file": "contacts.csv",
        "country": "Romania",
        "target_campaign": "AGRI"
    },
    "HIGH_VOLUME_RO": {
        "scraper_path": SCRAPER_DATA / "csv" / "ANOFM_TARGETS",
        "file_pattern": "high_volume_*.csv",
        "source_fields": {"email": "email_1", "company": "company_name", "phone": "phone_1", "city": "cities", "country": None},
        "contacts_file": "contacts.csv",
        "country": "Romania",
        "target_campaign": "NECALIFICATI_FEB_2026"
    },
    "NEW_EMPLOYERS_RO": {
        "scraper_path": SCRAPER_DATA / "csv" / "ANOFM_TARGETS",
        "file_pattern": "new_employers_*.csv",
        "source_fields": {"email": "email_1", "company": "company_name", "phone": "phone_1", "city": "city", "country": None},
        "contacts_file": "contacts.csv",
        "country": "Romania",
        "target_campaign": "NECALIFICATI_FEB_2026"
    },
}

def get_latest_file(path, pattern):
    """Get most recent file matching pattern."""
    files = sorted(glob(str(path / pattern)), key=lambda x: Path(x).stat().st_mtime, reverse=True)
    return Path(files[0]) if files else None

def load_existing_emails(campaign_dir):
    """Load all emails already in campaign."""
    emails = set()

    # Check contacts directory
    contacts_dir = campaign_dir / "contacts"
    if contacts_dir.exists():
        for csv_file in contacts_dir.glob("*.csv"):
            try:
                with open(csv_file, 'r', encoding='utf-8-sig', errors='ignore') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        email = row.get('email', row.get('email_1', '')).strip().lower()
                        if email:
                            emails.add(email)
            except:
                pass

    # Check sent logs
    logs_dir = campaign_dir / "logs"
    if logs_dir.exists():
        for log_file in logs_dir.glob("sent_*.log"):
            try:
                with open(log_file, 'r') as f:
                    for line in f:
                        if '@' in line:
                            parts = line.split()
                            for p in parts:
                                if '@' in p and '.' in p:
                                    emails.add(p.strip().lower())
            except:
                pass

    return emails

def feed_campaign(name, mapping, dry_run=False):
    """Feed contacts from scraper to campaign."""
    print(f"\n=== {name} ===")

    # Get source file
    source_file = get_latest_file(mapping["scraper_path"], mapping["file_pattern"])
    if not source_file:
        print(f"  No source file found: {mapping['scraper_path']}/{mapping['file_pattern']}")
        return {"success": False, "added": 0}

    # File age
    age_hours = (datetime.now().timestamp() - source_file.stat().st_mtime) / 3600
    print(f"  Source: {source_file.name}")
    print(f"  Age: {age_hours:.1f} hours")

    # Target campaign
    target = mapping.get("target_campaign", name)
    campaign_dir = CAMPAIGNS_DIR / target
    if not campaign_dir.exists():
        print(f"  Campaign directory not found: {campaign_dir}")
        return {"success": False, "added": 0}

    # Load existing emails
    existing = load_existing_emails(campaign_dir)
    print(f"  Already sent: {len(existing)}")

    # Load source and extract new contacts
    fields = mapping["source_fields"]
    new_contacts = []
    skipped = 0

    with open(source_file, 'r', encoding='utf-8-sig', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = row.get(fields["email"], '').strip().lower()
            email = fix_typo(email)

            if not email or not is_valid_email(email):
                continue

            if email in existing:
                skipped += 1
                continue

            existing.add(email)  # Prevent duplicates within batch

            contact = {
                "email": email,
                "company": to_ascii(row.get(fields["company"], '')),
                "phone": row.get(fields.get("phone", ""), ''),
                "city": to_ascii(row.get(fields.get("city", ""), '')),
                "country": mapping.get("country") or row.get(fields.get("country", ""), ''),
            }
            new_contacts.append(contact)

    print(f"  Valid contacts in source: {len(new_contacts) + skipped}")
    print(f"  New contacts to add: {len(new_contacts)}")
    print(f"  Skipped (already in system): {skipped}")

    if dry_run or not new_contacts:
        return {"success": True, "added": 0, "would_add": len(new_contacts)}

    # Write to campaign contacts
    contacts_dir = campaign_dir / "contacts"
    contacts_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = contacts_dir / f"auto_feed_{timestamp}.csv"

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["email", "company", "phone", "city", "country"])
        writer.writeheader()
        writer.writerows(new_contacts)

    # Count total
    total = len(existing)
    print(f"  ADDED {len(new_contacts)} contacts -> Total: {total}")

    return {"success": True, "added": len(new_contacts), "total": total}

def show_status():
    """Show status of all mappings."""
    print("=" * 60)
    print("SCRAPER TO CAMPAIGN STATUS")
    print("=" * 60)

    for name, mapping in MAPPINGS.items():
        print(f"\n{name}:")

        source_file = get_latest_file(mapping["scraper_path"], mapping["file_pattern"])
        if source_file:
            size_kb = source_file.stat().st_size / 1024
            age_hours = (datetime.now().timestamp() - source_file.stat().st_mtime) / 3600
            print(f"  Source: {source_file.name} ({size_kb:.0f}KB, {age_hours:.1f}h old)")
        else:
            print(f"  Source: NOT FOUND")
            continue

        target = mapping.get("target_campaign", name)
        campaign_dir = CAMPAIGNS_DIR / target
        if campaign_dir.exists():
            existing = load_existing_emails(campaign_dir)
            print(f"  Campaign: {len(existing)} contacts")
        else:
            print(f"  Campaign: No contacts file")

def main():
    parser = argparse.ArgumentParser(description='Scraper to Campaign Auto-Feed')
    parser.add_argument('--campaign', '-c', type=str, help='Feed specific campaign')
    parser.add_argument('--status', '-s', action='store_true', help='Show status only')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Dry run')
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    print("=" * 60)
    print("SCRAPER TO CAMPAIGN AUTO-FEED")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    results = {}

    if args.campaign:
        if args.campaign in MAPPINGS:
            results[args.campaign] = feed_campaign(args.campaign, MAPPINGS[args.campaign], args.dry_run)
        else:
            print(f"Unknown campaign: {args.campaign}")
            print(f"Available: {', '.join(MAPPINGS.keys())}")
            return
    else:
        for name, mapping in MAPPINGS.items():
            results[name] = feed_campaign(name, mapping, args.dry_run)

    # Summary
    print("\n" + "-" * 60)
    print("SUMMARY")
    print("-" * 60)

    total_added = 0
    for name, result in results.items():
        added = result.get("added", 0)
        if added > 0:
            print(f"  {name}: +{added} contacts")
            total_added += added
        elif result.get("would_add", 0) > 0:
            print(f"  {name}: Would add {result['would_add']} contacts")
        else:
            print(f"  {name}: No new contacts")

    print(f"\nTotal added: {total_added}")
    print("=" * 60)

if __name__ == "__main__":
    main()
