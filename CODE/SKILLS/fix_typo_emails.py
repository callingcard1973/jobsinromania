#!/usr/bin/env python3
"""
Fix email typos in blacklist and optionally re-add to campaigns.

Fixes common typo domains:
- yahoo.cpm, yahoo.comn, yahoo.s -> yahoo.com
- gamil.com, gmial.com, gmal.com -> gmail.com
- hotmal.com, hotmai.com -> hotmail.com
- outlok.com -> outlook.com

Usage:
    python3 fix_typo_emails.py --dry-run                    # Preview typos in blacklist
    python3 fix_typo_emails.py                              # Fix blacklist only
    python3 fix_typo_emails.py --campaign /path/to/campaign # Fix + add to campaign
    python3 fix_typo_emails.py --scan /path/to/file.csv     # Scan CSV for typos
"""

import os
import sys
import re
import csv
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii

# Try to import psycopg2 for database updates
try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

# Paths
BLACKLIST_FILE = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/EMAIL_CLEANUP/blacklist.txt')
MASTER_DNC = Path('/opt/ACTIVE/OPENDATA/DATA/MASTER_DNC.csv')

# Typo patterns: regex -> replacement
TYPO_PATTERNS = [
    # Yahoo typos
    (r'@yahoo\.cpm$', '@yahoo.com'),
    (r'@yahoo\.comn$', '@yahoo.com'),
    (r'@yahoo\.com[0-9]+$', '@yahoo.com'),
    (r'@yahoo\.com[\'";]+$', '@yahoo.com'),
    (r'@yahoo\.s$', '@yahoo.com'),
    (r'@yahoo\.c$', '@yahoo.com'),
    (r'@yahoo\.co$', '@yahoo.com'),
    (r'@yahoo\.\.com$', '@yahoo.com'),
    (r'@yahoo\.$', '@yahoo.com'),
    (r'@yaho\.com$', '@yahoo.com'),
    (r'@yahooo\.com$', '@yahoo.com'),
    (r'@yhoo\.com$', '@yahoo.com'),
    (r'@yhaoo\.com$', '@yahoo.com'),
    # Gmail typos
    (r'@gamil\.com$', '@gmail.com'),
    (r'@gmial\.com$', '@gmail.com'),
    (r'@gmal\.com$', '@gmail.com'),
    (r'@gnail\.com$', '@gmail.com'),
    (r'@gmai\.com$', '@gmail.com'),
    (r'@gmail\.ro$', '@gmail.com'),
    (r'@gmail\.co$', '@gmail.com'),
    (r'@gmailcom$', '@gmail.com'),
    (r'@gmail\.com[\'";]+$', '@gmail.com'),
    # Hotmail typos
    (r'@hotmal\.com$', '@hotmail.com'),
    (r'@hotmai\.com$', '@hotmail.com'),
    (r'@hotmial\.com$', '@hotmail.com'),
    (r'@hotamil\.com$', '@hotmail.com'),
    (r'@hotmaill\.com$', '@hotmail.com'),
    # Outlook typos
    (r'@outlok\.com$', '@outlook.com'),
    (r'@outloo\.com$', '@outlook.com'),
    (r'@outlokk\.com$', '@outlook.com'),
    # Generic trailing punctuation
    (r'\.com[\'";:,]+$', '.com'),
    (r'\.ro[\'";:,]+$', '.ro'),
]


def find_typo_emails(source_path, is_csv=False):
    """Find emails with typo domains."""
    typos = []

    if is_csv:
        with open(source_path, encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                for col in ['email', 'email1', 'email2', 'Email', 'EMAIL']:
                    email = (row.get(col) or '').strip().lower()
                    if email:
                        for pattern, replacement in TYPO_PATTERNS:
                            if re.search(pattern, email, re.IGNORECASE):
                                fixed = re.sub(pattern, replacement, email, flags=re.IGNORECASE)
                                typos.append({
                                    'original': email,
                                    'fixed': fixed,
                                    'pattern': pattern,
                                })
                                break
    else:
        with open(source_path) as f:
            for line in f:
                email = line.strip().lower()
                if not email:
                    continue

                for pattern, replacement in TYPO_PATTERNS:
                    if re.search(pattern, email, re.IGNORECASE):
                        fixed = re.sub(pattern, replacement, email, flags=re.IGNORECASE)
                        typos.append({
                            'original': email,
                            'fixed': fixed,
                            'pattern': pattern,
                        })
                        break

    return typos


def remove_from_blacklist(blacklist_path, emails_to_remove):
    """Remove emails from blacklist file."""
    remove_set = set(e.lower() for e in emails_to_remove)

    with open(blacklist_path) as f:
        lines = f.readlines()

    kept = []
    removed = 0
    for line in lines:
        email = line.strip().lower()
        if email in remove_set:
            removed += 1
        else:
            kept.append(line)

    with open(blacklist_path, 'w') as f:
        f.writelines(kept)

    return removed


def add_to_campaign(campaign_dir, fixed_emails):
    """Add fixed emails to campaign contacts."""
    contacts_path = Path(campaign_dir) / 'contacts' / 'contacts.csv'

    if not contacts_path.exists():
        print(f"  Campaign contacts not found: {contacts_path}")
        return 0

    # Load existing emails
    existing = set()
    rows = []
    fieldnames = None

    with open(contacts_path) as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            email = (row.get('email') or '').lower()
            existing.add(email)
            rows.append(row)

    if not fieldnames:
        fieldnames = ['source', 'job_title', 'company', 'city', 'county',
                      'email', 'phone', 'positions', 'salary', 'url']

    # Filter out invalid emails (double @, etc.)
    valid_fixed = [e for e in fixed_emails if e.count('@') == 1 and '.' in e.split('@')[1]]

    # Add new fixed emails
    added = 0
    for email in valid_fixed:
        if email.lower() not in existing:
            row = {fn: '' for fn in fieldnames}
            row['source'] = 'TYPO_FIX'
            row['email'] = email
            rows.append(row)
            existing.add(email.lower())
            added += 1

    # Write back
    with open(contacts_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return added


def update_dnc_database(originals):
    """Remove original typo emails from PostgreSQL dnc_emails table."""
    if not HAS_PSYCOPG2:
        return 0

    try:
        conn = psycopg2.connect(
            host='localhost',
            database='email_sender',
            user='tudor',
            password='scraper123'
        )
        cur = conn.cursor()

        removed = 0
        for email in originals:
            cur.execute("DELETE FROM dnc_emails WHERE email = %s", (email,))
            removed += cur.rowcount

        conn.commit()
        cur.close()
        conn.close()
        return removed
    except Exception as e:
        print(f"  DB error: {e}")
        return 0


def update_master_dnc(master_path, emails_to_remove):
    """Remove fixed emails from MASTER_DNC.csv."""
    if not master_path.exists():
        return 0

    remove_set = set(e.lower() for e in emails_to_remove)

    with open(master_path) as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = [r for r in reader if (r.get('email') or '').lower() not in remove_set]

    original_count = sum(1 for _ in open(master_path)) - 1

    with open(master_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return original_count - len(rows)


def main():
    parser = argparse.ArgumentParser(description='Fix email typos in blacklist and campaigns')
    parser.add_argument('--dry-run', action='store_true', help='Preview mode')
    parser.add_argument('--campaign', type=str, help='Campaign directory to add fixed emails')
    parser.add_argument('--scan', type=str, help='Scan CSV file for typos (no fixes)')
    args = parser.parse_args()

    print("=" * 60)
    print("FIX EMAIL TYPOS")
    print("=" * 60)

    # Scan mode - just find typos in a CSV
    if args.scan:
        print(f"Scanning: {args.scan}")
        typos = find_typo_emails(args.scan, is_csv=True)
        print(f"Found: {len(typos)} typo emails\n")
        for t in typos:
            print(f"  {t['original']} -> {t['fixed']}")
        return

    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    if args.campaign:
        print(f"Campaign: {args.campaign}")
    print()

    # Find typos in blacklist
    print("1. Finding typo emails in blacklist...")
    typos = find_typo_emails(BLACKLIST_FILE)
    print(f"   Found: {len(typos)} typo emails")

    if not typos:
        print("   No typos found.")
        return

    # Show what we found
    print("\n2. Typos found:")
    for t in typos:
        print(f"   {t['original']} -> {t['fixed']}")

    if args.dry_run:
        print("\n[DRY RUN] Would fix these emails. Run without --dry-run to apply.")
        return

    originals = [t['original'] for t in typos]
    fixed = [t['fixed'] for t in typos]

    # Remove from blacklist
    print("\n3. Removing originals from blacklist...")
    removed = remove_from_blacklist(BLACKLIST_FILE, originals)
    print(f"   Removed: {removed}")

    # Add to campaign if specified
    if args.campaign:
        print("\n4. Adding fixed emails to campaign...")
        added = add_to_campaign(args.campaign, fixed)
        print(f"   Added: {added}")

    # Update database
    print("\n5. Updating PostgreSQL dnc_emails...")
    db_removed = update_dnc_database(originals)
    print(f"   Removed from DB: {db_removed}")

    # Update MASTER_DNC
    print("\n6. Updating MASTER_DNC.csv...")
    master_removed = update_master_dnc(MASTER_DNC, originals)
    print(f"   Removed from master: {master_removed}")

    print("\n" + "=" * 60)
    print("COMPLETE")
    print(f"  Typos fixed: {len(typos)}")
    print(f"  Removed from blacklist: {removed}")
    if args.campaign:
        print(f"  Added to campaign: {added}")
    print("=" * 60)


if __name__ == '__main__':
    main()
