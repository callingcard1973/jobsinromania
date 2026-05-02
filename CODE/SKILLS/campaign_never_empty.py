#!/usr/bin/env python3
"""
Campaign Never Empty - Ensures campaigns always have contacts.

Automatically restores from backups or enriches with ANOFM data when
a campaign's contacts.csv is empty or has too few contacts.

Usage:
    python3 campaign_never_empty.py --check           # Check all campaigns
    python3 campaign_never_empty.py --fix             # Fix empty campaigns
    python3 campaign_never_empty.py --campaign NAME   # Check specific campaign
    python3 campaign_never_empty.py --threshold 50    # Min contacts (default: 10)
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import csv
import re
import glob
import shutil
import argparse
from datetime import datetime
from pathlib import Path

from skills_common import to_ascii
from alerting import send_telegram

CAMPAIGNS_DIR = "/opt/ACTIVE/EMAIL/CAMPAIGNS"
MIN_CONTACTS = 10  # Campaigns with fewer contacts are considered empty
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

# Email column aliases to search for
EMAIL_COLUMNS = ['email', 'anofm_email', 'email_1', 'fuzzy_email', 'web_email', 'best_email']


def find_email_column(headers):
    """Find the email column from various possible names."""
    headers_lower = [h.lower() for h in headers]
    for col in EMAIL_COLUMNS:
        if col.lower() in headers_lower:
            idx = headers_lower.index(col.lower())
            return headers[idx]
    # Check for any column containing 'email'
    for h in headers:
        if 'email' in h.lower():
            return h
    return None


def count_valid_emails(csv_path):
    """Count valid emails in a CSV file."""
    if not os.path.exists(csv_path):
        return 0, None, []

    try:
        with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if not rows:
                return 0, None, []

            email_col = find_email_column(reader.fieldnames)
            if not email_col:
                return 0, reader.fieldnames, rows

            valid_count = 0
            for row in rows:
                email = (row.get(email_col) or '').strip().lower()
                if email and EMAIL_REGEX.match(email):
                    valid_count += 1

            return valid_count, email_col, rows
    except Exception as e:
        print(f"  Error reading {csv_path}: {e}")
        return 0, None, []


def find_backup_files(contacts_dir):
    """Find backup CSV files in the contacts directory."""
    backups = []
    patterns = [
        'contacts_backup_*.csv',
        '*_backup.csv',
        '*_backup_*.csv',
        '*.csv.bak',
    ]
    for pattern in patterns:
        backups.extend(glob.glob(os.path.join(contacts_dir, pattern)))

    # Also check for other CSV files that might have data
    all_csvs = glob.glob(os.path.join(contacts_dir, '*.csv'))
    for csv_file in all_csvs:
        if csv_file not in backups and not csv_file.endswith('contacts.csv'):
            backups.append(csv_file)

    # Sort by modification time (newest first)
    backups.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return backups


def restore_from_backup(contacts_csv, backup_file):
    """Restore contacts.csv from a backup file, normalizing email column."""
    print(f"  Restoring from: {os.path.basename(backup_file)}")

    with open(backup_file, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if not rows:
            print(f"  Backup is empty")
            return 0

        email_col = find_email_column(reader.fieldnames)
        if not email_col:
            print(f"  No email column found in backup")
            return 0

        # Extract valid rows with normalized schema
        valid_rows = []
        for row in rows:
            email = (row.get(email_col) or '').strip().lower()
            if email and EMAIL_REGEX.match(email):
                # Try to find company name column
                company = ''
                for col in ['denumire', 'company_name', 'company', 'name', 'firma']:
                    if col in row:
                        company = row[col]
                        break
                if not company:
                    company = row.get(reader.fieldnames[0], '')

                # Try to find phone column
                phone = ''
                for col in ['anaf_phone', 'phone', 'phone1', 'telefon']:
                    if col in row:
                        phone = row[col]
                        break

                valid_rows.append({
                    'denumire': to_ascii(company),
                    'anaf_phone': phone,
                    'email': email
                })

        if not valid_rows:
            print(f"  No valid emails in backup")
            return 0

        # Write normalized contacts.csv
        with open(contacts_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['denumire', 'anaf_phone', 'email'])
            writer.writeheader()
            writer.writerows(valid_rows)

        print(f"  Restored {len(valid_rows)} valid contacts")
        return len(valid_rows)


def enrich_with_anofm(contacts_dir):
    """Try to enrich data with ANOFM emails using fuzzy_enrich.py."""
    # Look for any CSV with CUI column
    csvs = glob.glob(os.path.join(contacts_dir, '*.csv'))

    for csv_file in csvs:
        if 'contacts.csv' in csv_file:
            continue

        try:
            with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []

            # Check if it has CUI and company name
            has_cui = any('cui' in h.lower() for h in headers)
            has_company = any(c in [h.lower() for h in headers] for c in
                            ['denumire', 'company_name', 'company', 'name', 'firma'])

            if has_cui or has_company:
                print(f"  Found enrichable file: {os.path.basename(csv_file)}")

                # Find column names
                cui_col = next((h for h in headers if 'cui' in h.lower()), None)
                name_col = next((h for h in headers if h.lower() in
                               ['denumire', 'company_name', 'company', 'name', 'firma']), headers[0])

                # Run fuzzy_enrich
                import subprocess
                cmd = [
                    '/opt/ACTIVE/INFRA/venv/bin/python3', '/opt/ACTIVE/INFRA/SKILLS/fuzzy_enrich.py',
                    csv_file, '--name-col', name_col
                ]
                if cui_col:
                    cmd.extend(['--cui-col', cui_col])

                result = subprocess.run(cmd, capture_output=True, text=True, cwd=contacts_dir)

                # Check for output file
                enriched_file = csv_file.replace('.csv', '.fuzzy_enriched.csv')
                if os.path.exists(enriched_file):
                    count = restore_from_backup(
                        os.path.join(contacts_dir, 'contacts.csv'),
                        enriched_file
                    )
                    if count > 0:
                        return count

        except Exception as e:
            print(f"  Error processing {csv_file}: {e}")
            continue

    return 0


def check_campaign(campaign_path, fix=False, min_contacts=MIN_CONTACTS):
    """Check a single campaign and optionally fix it."""
    campaign_name = os.path.basename(campaign_path)
    contacts_dir = os.path.join(campaign_path, 'contacts')
    contacts_csv = os.path.join(contacts_dir, 'contacts.csv')

    if not os.path.exists(contacts_dir):
        return None  # Not a real campaign

    valid_count, email_col, _ = count_valid_emails(contacts_csv)

    result = {
        'name': campaign_name,
        'valid_emails': valid_count,
        'email_column': email_col,
        'status': 'ok' if valid_count >= min_contacts else 'empty',
        'fixed': False,
        'fixed_count': 0
    }

    if valid_count >= min_contacts:
        return result

    print(f"\n{campaign_name}: {valid_count} valid emails (threshold: {min_contacts})")

    if not fix:
        result['status'] = 'needs_fix'
        return result

    # Try to fix

    # 1. Look for backups
    backups = find_backup_files(contacts_dir)
    for backup in backups:
        print(f"  Trying backup: {os.path.basename(backup)}")
        count = restore_from_backup(contacts_csv, backup)
        if count >= min_contacts:
            result['fixed'] = True
            result['fixed_count'] = count
            result['status'] = 'fixed_from_backup'
            return result

    # 2. Try ANOFM enrichment
    print(f"  Trying ANOFM enrichment...")
    count = enrich_with_anofm(contacts_dir)
    if count > 0:
        result['fixed'] = True
        result['fixed_count'] = count
        result['status'] = 'fixed_from_enrichment'
        return result

    result['status'] = 'unfixable'
    return result


def check_all_campaigns(fix=False, min_contacts=MIN_CONTACTS):
    """Check all campaigns in CAMPAIGNS_DIR."""
    results = []

    campaigns = sorted(glob.glob(os.path.join(CAMPAIGNS_DIR, '*')))

    for campaign_path in campaigns:
        if not os.path.isdir(campaign_path):
            continue

        result = check_campaign(campaign_path, fix=fix, min_contacts=min_contacts)
        if result:
            results.append(result)

    return results


def print_summary(results):
    """Print summary of campaign status."""
    print("\n" + "=" * 60)
    print("CAMPAIGN STATUS SUMMARY")
    print("=" * 60)

    ok = [r for r in results if r['status'] == 'ok']
    empty = [r for r in results if r['status'] in ('empty', 'needs_fix')]
    fixed = [r for r in results if r['status'].startswith('fixed')]
    unfixable = [r for r in results if r['status'] == 'unfixable']

    print(f"\nOK ({len(ok)} campaigns with sufficient contacts)")

    if empty:
        print(f"\nEMPTY/LOW ({len(empty)} campaigns need attention):")
        for r in empty:
            print(f"  - {r['name']}: {r['valid_emails']} valid emails")

    if fixed:
        print(f"\nFIXED ({len(fixed)} campaigns restored):")
        for r in fixed:
            print(f"  - {r['name']}: {r['fixed_count']} contacts ({r['status']})")

    if unfixable:
        print(f"\nUNFIXABLE ({len(unfixable)} campaigns - manual intervention needed):")
        for r in unfixable:
            print(f"  - {r['name']}")

    print()
    return empty, unfixable


def main():
    parser = argparse.ArgumentParser(description='Ensure campaigns never go empty')
    parser.add_argument('--check', action='store_true', help='Check all campaigns')
    parser.add_argument('--fix', action='store_true', help='Fix empty campaigns')
    parser.add_argument('--campaign', type=str, help='Check specific campaign')
    parser.add_argument('--threshold', type=int, default=MIN_CONTACTS,
                       help=f'Minimum contacts threshold (default: {MIN_CONTACTS})')
    parser.add_argument('--alert', action='store_true', help='Send Telegram alert for issues')

    args = parser.parse_args()

    if args.campaign:
        campaign_path = os.path.join(CAMPAIGNS_DIR, args.campaign)
        if not os.path.exists(campaign_path):
            print(f"Campaign not found: {args.campaign}")
            sys.exit(1)

        result = check_campaign(campaign_path, fix=args.fix, min_contacts=args.threshold)
        if result:
            print(f"\n{result['name']}: {result['valid_emails']} valid emails")
            print(f"Status: {result['status']}")
            if result['fixed']:
                print(f"Fixed: {result['fixed_count']} contacts restored")

    elif args.check or args.fix:
        results = check_all_campaigns(fix=args.fix, min_contacts=args.threshold)
        empty, unfixable = print_summary(results)

        if args.alert and (empty or unfixable):
            msg = "Campaign Status Alert\n\n"
            if empty:
                msg += f"Empty campaigns: {len(empty)}\n"
                for r in empty[:5]:
                    msg += f"- {r['name']}: {r['valid_emails']} emails\n"
            if unfixable:
                msg += f"\nUnfixable: {len(unfixable)}\n"
                for r in unfixable[:5]:
                    msg += f"- {r['name']}\n"
            send_telegram(msg)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
