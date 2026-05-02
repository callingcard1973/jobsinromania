#!/usr/bin/env python3
"""
Campaign Contact Cleaner - Pre-validate contacts before sending.

Removes:
- Blacklisted emails
- Already sent emails
- Invalid email formats
- Typo domains (gamil.com, yahooo.com, etc.)
- No-reply addresses
- Duplicate emails

Usage:
    python3 campaign_cleaner.py --campaign POLAND
    python3 campaign_cleaner.py --campaign POLAND --dry-run
    python3 campaign_cleaner.py --all
    python3 campaign_cleaner.py --status
"""

import csv
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
try:
    from skills_common import to_ascii
except ImportError:
    def to_ascii(text):
        import unicodedata
        if not text:
            return text
        normalized = unicodedata.normalize('NFKD', str(text))
        return normalized.encode('ascii', 'ignore').decode('ascii')

# Paths
CAMPAIGNS_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS")
BLACKLIST_FILE = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/EMAIL_CLEANUP/blacklist.txt")

# Typo domains to reject (user should fix manually)
TYPO_DOMAINS = {
    'gamil.com', 'gmial.com', 'gmal.com', 'gnail.com', 'gmai.com',
    'gmail.ro', 'gmail.co', 'hotmal.com', 'hotmai.com', 'hotmial.com',
    'outlok.com', 'outloo.com', 'yaho.com', 'yahooo.com', 'yhoo.com'
}

# Invalid patterns
INVALID_PREFIXES = ['noreply', 'no-reply', 'donotreply', 'do-not-reply', 
                    'mailer-daemon', 'postmaster', 'bounce', 'admin@localhost']


def load_blacklist():
    """Load blacklist emails."""
    blacklist = set()
    if BLACKLIST_FILE.exists():
        with open(BLACKLIST_FILE) as f:
            for line in f:
                email = line.strip().lower()
                if email and '@' in email:
                    blacklist.add(email)
    return blacklist


def load_sent_emails(campaign_path):
    """Load already sent emails from sent_emails.txt."""
    sent = set()
    sent_file = campaign_path / "sent_emails.txt"
    if sent_file.exists():
        with open(sent_file) as f:
            for line in f:
                email = line.strip().lower()
                if email and '@' in email:
                    sent.add(email)
    return sent


def is_invalid_email(email):
    """Check if email is invalid."""
    email = email.lower().strip()
    
    if not email or '@' not in email:
        return True, "missing @"
    
    parts = email.split('@')
    if len(parts) != 2:
        return True, "multiple @"
    
    local, domain = parts
    if not local or not domain:
        return True, "empty local/domain"
    
    if '.' not in domain:
        return True, "no TLD"
    
    # Check typo domains
    if domain in TYPO_DOMAINS:
        return True, f"typo domain ({domain})"
    
    # Check invalid prefixes
    for prefix in INVALID_PREFIXES:
        if local.startswith(prefix):
            return True, f"no-reply address"
    
    return False, None


def clean_campaign(campaign_name, dry_run=False):
    """Clean contacts for a single campaign."""
    campaign_path = CAMPAIGNS_DIR / campaign_name
    contacts_dir = campaign_path / "contacts"
    
    if not contacts_dir.exists():
        print(f"Campaign {campaign_name}: No contacts directory")
        return None
    
    # Find contacts file
    contacts_file = contacts_dir / "contacts.csv"
    if not contacts_file.exists():
        # Try other CSV files
        csvs = list(contacts_dir.glob("*.csv"))
        if csvs:
            contacts_file = csvs[0]
        else:
            print(f"Campaign {campaign_name}: No CSV files found")
            return None
    
    print(f"\n=== Cleaning {campaign_name} ===")
    print(f"File: {contacts_file}")
    
    # Load filters
    blacklist = load_blacklist()
    sent = load_sent_emails(campaign_path)
    
    print(f"Blacklist: {len(blacklist)} emails")
    print(f"Already sent: {len(sent)} emails")
    
    # Process contacts
    stats = {
        'total': 0,
        'blacklisted': 0,
        'sent': 0,
        'invalid': 0,
        'duplicate': 0,
        'kept': 0
    }
    
    seen_emails = set()
    rows_to_keep = []
    invalid_reasons = {}
    
    with open(contacts_file) as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        
        for row in reader:
            stats['total'] += 1
            email = row.get('email', '').strip().lower()
            
            # Skip empty
            if not email:
                stats['invalid'] += 1
                continue
            
            # Check blacklist
            if email in blacklist:
                stats['blacklisted'] += 1
                continue
            
            # Check sent
            if email in sent:
                stats['sent'] += 1
                continue
            
            # Check valid format
            is_invalid, reason = is_invalid_email(email)
            if is_invalid:
                stats['invalid'] += 1
                invalid_reasons[reason] = invalid_reasons.get(reason, 0) + 1
                continue
            
            # Check duplicate
            if email in seen_emails:
                stats['duplicate'] += 1
                continue
            
            seen_emails.add(email)
            stats['kept'] += 1
            rows_to_keep.append(row)
    
    # Report
    print(f"\n--- Results ---")
    print(f"Total contacts: {stats['total']}")
    print(f"Removed - Blacklisted: {stats['blacklisted']}")
    print(f"Removed - Already sent: {stats['sent']}")
    print(f"Removed - Invalid: {stats['invalid']}")
    if invalid_reasons:
        for reason, count in sorted(invalid_reasons.items(), key=lambda x: -x[1]):
            print(f"         - {reason}: {count}")
    print(f"Removed - Duplicate: {stats['duplicate']}")
    print(f"Kept (clean): {stats['kept']}")
    
    if dry_run:
        print("\n[DRY RUN - no changes made]")
        return stats
    
    # Backup and write
    if stats['kept'] < stats['total']:
        backup_file = contacts_dir / f"contacts_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Backup original
        import shutil
        shutil.copy(contacts_file, backup_file)
        print(f"\nBackup: {backup_file.name}")
        
        # Write clean file
        with open(contacts_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows_to_keep)
        
        removed = stats['total'] - stats['kept']
        print(f"Cleaned: Removed {removed} contacts ({removed/stats['total']*100:.1f}%)")
    else:
        print("\nNo changes needed - all contacts valid")
    
    return stats


def get_all_campaigns():
    """Get list of campaign directories."""
    campaigns = []
    for d in CAMPAIGNS_DIR.iterdir():
        if d.is_dir() and (d / "contacts").exists():
            campaigns.append(d.name)
    return sorted(campaigns)


def show_status():
    """Show status of all campaigns."""
    campaigns = get_all_campaigns()
    blacklist = load_blacklist()
    
    print("=== Campaign Status ===")
    print(f"Blacklist size: {len(blacklist)}")
    print()
    
    for name in campaigns:
        campaign_path = CAMPAIGNS_DIR / name
        contacts_dir = campaign_path / "contacts"
        
        # Count contacts
        contacts_file = contacts_dir / "contacts.csv"
        if contacts_file.exists():
            with open(contacts_file) as f:
                count = sum(1 for _ in f) - 1  # minus header
        else:
            csvs = list(contacts_dir.glob("*.csv"))
            count = 0
            for csv_file in csvs:
                with open(csv_file) as f:
                    count += sum(1 for _ in f) - 1
        
        # Count sent
        sent = load_sent_emails(campaign_path)
        
        print(f"{name}: {count} contacts, {len(sent)} sent")


def main():
    parser = argparse.ArgumentParser(description="Clean campaign contacts before sending")
    parser.add_argument("--campaign", "-c", help="Campaign name to clean")
    parser.add_argument("--all", "-a", action="store_true", help="Clean all campaigns")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Show what would be removed")
    parser.add_argument("--status", "-s", action="store_true", help="Show status of all campaigns")
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
        return
    
    if args.all:
        campaigns = get_all_campaigns()
        print(f"Cleaning {len(campaigns)} campaigns...")
        for name in campaigns:
            clean_campaign(name, args.dry_run)
    elif args.campaign:
        clean_campaign(args.campaign, args.dry_run)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
