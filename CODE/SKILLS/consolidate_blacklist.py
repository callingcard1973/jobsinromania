#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
Master Blacklist Consolidator
Merges all campaign blacklists/suppression lists into one centralized file.
Also cleans dirty data (phone+email concatenation, double dots, etc.)

Usage:
    python3 consolidate_blacklist.py                # Consolidate all sources
    python3 consolidate_blacklist.py --dry-run      # Show what would be merged
    python3 consolidate_blacklist.py --stats        # Show blacklist stats
    python3 consolidate_blacklist.py --add email    # Manually add email
    python3 consolidate_blacklist.py --check email  # Check if email is blacklisted

[AI: Claude Code]
"""

import sys
import os
import csv
import json
import re
import argparse
import unicodedata
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS/lib')
from email_validator import validate_and_fix

MASTER_BLACKLIST = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/master_blacklist.csv')
SOURCES = {
    'blacklist_txt': Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/EMAIL_CLEANUP/blacklist.txt'),
    'master_dnc': Path('/opt/ACTIVE/OPENDATA/DATA/MASTER_DNC.csv'),
    'warehouse_suppression': Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/WAREHOUSE/suppression_list.json'),
    'poland_suppression': Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/POLAND_EMPLOYERS/suppression_list.txt'),
}

# Find all per-campaign suppression files
CAMPAIGN_DIR = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS')


def clean_email(raw):
    """Clean a raw email entry: strip phones, fix typos, ASCII-only."""
    raw = str(raw).strip()
    if not raw:
        return None

    # Strip leading phone numbers (+46313151485mari@ -> mari@)
    raw = re.sub(r'^\+?\d{8,15}', '', raw)

    # Strip trailing phone numbers (email@domain0799 -> email@domain)
    raw = re.sub(r'\d{4,15}$', '', raw)

    # Strip diacritics
    raw = unicodedata.normalize('NFKD', raw).encode('ascii', 'ignore').decode('ascii')

    raw = raw.strip().lower()

    if '@' not in raw:
        return None

    # Handle comma-separated emails in one field
    emails = []
    for part in re.split(r'[,;\s]+', raw):
        part = part.strip()
        if '@' not in part:
            continue
        result = validate_and_fix(part)
        if result['is_valid']:
            emails.append(result['fixed'])

    return emails if emails else None


def load_blacklist_txt(path):
    """Load plain text blacklist (one email per line)."""
    emails = {}
    if not path.exists():
        return emails
    with open(path) as f:
        for line in f:
            cleaned = clean_email(line.strip())
            if cleaned:
                for e in cleaned:
                    if e not in emails:
                        emails[e] = {'type': 'blacklist', 'reason': 'imported', 'source': path.name, 'date': ''}
    return emails


def load_master_dnc(path):
    """Load MASTER_DNC.csv."""
    emails = {}
    if not path.exists():
        return emails
    with open(path, encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw = row.get('email', '')
            cleaned = clean_email(raw)
            if cleaned:
                for e in cleaned:
                    if e not in emails:
                        emails[e] = {
                            'type': row.get('type', 'blacklist'),
                            'reason': row.get('reason', ''),
                            'source': 'master_dnc',
                            'date': row.get('date', ''),
                        }
    return emails


def load_suppression_json(path):
    """Load suppression_list.json (WAREHOUSE format)."""
    emails = {}
    if not path.exists():
        return emails
    with open(path) as f:
        data = json.load(f)

    email_list = data if isinstance(data, list) else data.get('emails', [])
    for raw in email_list:
        cleaned = clean_email(str(raw))
        if cleaned:
            for e in cleaned:
                if e not in emails:
                    emails[e] = {'type': 'suppression', 'reason': 'campaign_suppressed', 'source': path.parent.name, 'date': ''}
    return emails


def load_suppression_txt(path):
    """Load suppression_list.txt."""
    return load_blacklist_txt(path)


def find_campaign_suppression_files():
    """Find all suppression files across campaigns."""
    files = []
    for pattern in ['suppression_list.json', 'suppression_list.txt', 'suppression*.json', 'suppression*.txt']:
        files.extend(CAMPAIGN_DIR.rglob(pattern))
    return list(set(files))


def consolidate(dry_run=False):
    """Consolidate all sources into master blacklist."""
    all_emails = {}

    # Load main sources
    print("Loading sources...")

    bl = load_blacklist_txt(SOURCES['blacklist_txt'])
    print(f"  blacklist.txt: {len(bl)} valid emails")
    all_emails.update(bl)

    dnc = load_master_dnc(SOURCES['master_dnc'])
    print(f"  MASTER_DNC.csv: {len(dnc)} valid emails")
    for e, info in dnc.items():
        if e not in all_emails:
            all_emails[e] = info

    # Campaign-specific suppression files
    suppression_files = find_campaign_suppression_files()
    for sf in suppression_files:
        if sf.suffix == '.json':
            entries = load_suppression_json(sf)
        else:
            entries = load_suppression_txt(sf)
        new = sum(1 for e in entries if e not in all_emails)
        print(f"  {sf.parent.name}/{sf.name}: {len(entries)} ({new} new)")
        for e, info in entries.items():
            if e not in all_emails:
                all_emails[e] = info

    # Load existing master blacklist (preserve manual adds)
    if MASTER_BLACKLIST.exists():
        existing = {}
        with open(MASTER_BLACKLIST, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get('email', '').strip().lower()
                if email:
                    existing[email] = row
        new_in_master = sum(1 for e in existing if e not in all_emails)
        print(f"  master_blacklist.csv (existing): {len(existing)} ({new_in_master} unique)")
        for e, row in existing.items():
            if e not in all_emails:
                all_emails[e] = {
                    'type': row.get('type', 'blacklist'),
                    'reason': row.get('reason', ''),
                    'source': row.get('source', 'master_blacklist'),
                    'date': row.get('date', ''),
                }

    print(f"\nTotal unique emails: {len(all_emails)}")

    if dry_run:
        print("\n[DRY RUN] Would write to:", MASTER_BLACKLIST)
        return all_emails

    # Write consolidated master blacklist
    with open(MASTER_BLACKLIST, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['email', 'type', 'reason', 'source', 'date'])
        writer.writeheader()
        for email in sorted(all_emails.keys()):
            info = all_emails[email]
            writer.writerow({
                'email': email,
                'type': info.get('type', 'blacklist'),
                'reason': info.get('reason', ''),
                'source': info.get('source', ''),
                'date': info.get('date', ''),
            })

    print(f"Written: {MASTER_BLACKLIST} ({len(all_emails)} entries)")

    # Also update blacklist.txt for backwards compatibility
    bl_path = SOURCES['blacklist_txt']
    with open(bl_path, 'w') as f:
        for email in sorted(all_emails.keys()):
            f.write(email + '\n')
    print(f"Updated: {bl_path} ({len(all_emails)} entries)")

    return all_emails


def show_stats():
    """Show blacklist statistics."""
    if not MASTER_BLACKLIST.exists():
        print("Master blacklist not found. Run consolidation first.")
        return

    by_type = {}
    by_source = {}
    total = 0

    with open(MASTER_BLACKLIST, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            t = row.get('type', 'unknown')
            s = row.get('source', 'unknown')
            by_type[t] = by_type.get(t, 0) + 1
            by_source[s] = by_source.get(s, 0) + 1

    print(f"=== Master Blacklist Stats ===")
    print(f"Total: {total}")
    print(f"\nBy type:")
    for t, c in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {t:20s} {c:5d}")
    print(f"\nBy source:")
    for s, c in sorted(by_source.items(), key=lambda x: -x[1]):
        print(f"  {s:30s} {c:5d}")


def add_email(email, reason='manual', source='cli'):
    """Add email to master blacklist."""
    result = validate_and_fix(email)
    clean = result['fixed'] if result['is_valid'] else email.strip().lower()

    existing = set()
    if MASTER_BLACKLIST.exists():
        with open(MASTER_BLACKLIST, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing.add(row.get('email', '').lower())

    if clean in existing:
        print(f"Already blacklisted: {clean}")
        return

    with open(MASTER_BLACKLIST, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['email', 'type', 'reason', 'source', 'date'])
        writer.writerow({
            'email': clean,
            'type': 'blacklist',
            'reason': reason,
            'source': source,
            'date': datetime.now().isoformat()[:10],
        })

    # Also add to blacklist.txt
    with open(SOURCES['blacklist_txt'], 'a') as f:
        f.write(clean + '\n')

    print(f"Added: {clean} (reason: {reason})")


def check_email(email):
    """Check if email is blacklisted."""
    result = validate_and_fix(email)
    clean = result['fixed'] if result['is_valid'] else email.strip().lower()

    if not MASTER_BLACKLIST.exists():
        print("Master blacklist not found.")
        return False

    with open(MASTER_BLACKLIST, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('email', '').lower() == clean:
                print(f"BLACKLISTED: {clean}")
                print(f"  Type: {row.get('type', '')}")
                print(f"  Reason: {row.get('reason', '')}")
                print(f"  Source: {row.get('source', '')}")
                print(f"  Date: {row.get('date', '')}")
                return True

    print(f"NOT blacklisted: {clean}")
    return False


def main():
    parser = argparse.ArgumentParser(description='Master Blacklist Consolidator')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be merged')
    parser.add_argument('--stats', action='store_true', help='Show blacklist stats')
    parser.add_argument('--add', help='Add email to blacklist')
    parser.add_argument('--reason', default='manual', help='Reason for --add')
    parser.add_argument('--check', help='Check if email is blacklisted')
    args = parser.parse_args()

    if args.stats:
        show_stats()
    elif args.add:
        add_email(args.add, reason=args.reason)
    elif args.check:
        check_email(args.check)
    else:
        consolidate(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
