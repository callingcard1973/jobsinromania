#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
Email Validator Skill
Validates, fixes, and cleans email addresses in CSVs and scraper output.

Usage:
    python3 email_validator.py test@gmailcom                    # Validate single email
    python3 email_validator.py --csv contacts.csv               # Scan CSV for bad emails
    python3 email_validator.py --csv contacts.csv --fix         # Fix bad emails in-place
    python3 email_validator.py --csv contacts.csv --fix --out clean.csv  # Fix to new file
    python3 email_validator.py --scan /opt/ACTIVE/OPENDATA/DATA/ROMANIA/ANOFM/  # Scan dir for bad emails
    python3 email_validator.py --scan-recent                    # Scan scraper output from last 24h
    python3 email_validator.py --mx contacts.csv                # Full MX validation (slow)

[AI: Claude Code]
"""

import sys
import csv
import argparse
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS/lib')
from email_validator import (
    validate_and_fix, validate_email, fix_email, sanitize_email,
    validate_email_full, validate_csv_with_mx
)


def validate_single(email):
    """Validate and fix a single email."""
    result = validate_and_fix(email)
    print(f"Input:    {email}")
    print(f"Fixed:    {result['fixed']}")
    print(f"Valid:    {result['is_valid']}")
    if result['was_fixed']:
        print(f"Changed:  {result['message']}")
    elif not result['is_valid']:
        print(f"Error:    {result['message']}")
    else:
        print(f"Status:   OK")


def scan_csv(csv_path, email_columns=None, fix=False, output=None):
    """Scan CSV for bad emails, optionally fix them."""
    path = Path(csv_path)
    if not path.exists():
        print(f"ERROR: File not found: {csv_path}")
        return

    with open(path, encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # Find email columns
    if not email_columns:
        email_columns = [c for c in fieldnames if 'email' in c.lower()]
    if not email_columns:
        print(f"ERROR: No email columns found in {fieldnames}")
        return

    print(f"File: {csv_path}")
    print(f"Rows: {len(rows)}")
    print(f"Email columns: {email_columns}")
    print()

    total = 0
    fixed_count = 0
    invalid_count = 0
    fixes = []

    for i, row in enumerate(rows, 2):
        for col in email_columns:
            email = (row.get(col) or '').strip()
            if not email or '@' not in email:
                continue
            total += 1

            result = validate_and_fix(email)

            if result['was_fixed'] and result['is_valid']:
                fixes.append((i, col, email, result['fixed'], result['message']))
                fixed_count += 1
                if fix:
                    row[col] = result['fixed']
            elif not result['is_valid']:
                fixes.append((i, col, email, '', result['message']))
                invalid_count += 1

    # Report
    print(f"Scanned: {total} emails")
    print(f"Fixable: {fixed_count}")
    print(f"Invalid: {invalid_count}")

    if fixes:
        print(f"\nIssues found:")
        for line, col, original, fixed, msg in fixes:
            if fixed:
                print(f"  Line {line} [{col}]: {original} -> {fixed} ({msg})")
            else:
                print(f"  Line {line} [{col}]: {original} - INVALID: {msg}")

    if fix and (fixed_count > 0 or invalid_count > 0):
        out_path = output or str(path)
        with open(out_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nSaved: {out_path} ({fixed_count} fixed, {invalid_count} still invalid)")
    elif fix:
        print("\nNo changes needed.")


def scan_directory(dir_path, hours=24):
    """Scan directory for CSVs with bad emails."""
    path = Path(dir_path)
    if not path.exists():
        print(f"ERROR: Directory not found: {dir_path}")
        return

    cutoff = datetime.now() - timedelta(hours=hours)
    csvs = sorted(path.rglob('*.csv'), key=lambda p: p.stat().st_mtime, reverse=True)

    if hours < 9999:
        csvs = [c for c in csvs if c.stat().st_mtime > cutoff.timestamp()]

    print(f"Directory: {dir_path}")
    print(f"CSVs found: {len(csvs)} (last {hours}h)")
    print()

    total_issues = 0
    for csv_file in csvs:
        try:
            with open(csv_file, encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames or []
                email_cols = [c for c in fieldnames if 'email' in c.lower()]
                if not email_cols:
                    continue

                issues = []
                for i, row in enumerate(reader, 2):
                    for col in email_cols:
                        email = (row.get(col) or '').strip()
                        if not email or '@' not in email:
                            continue
                        result = validate_and_fix(email)
                        if result['was_fixed'] or not result['is_valid']:
                            issues.append((i, col, email, result))

                if issues:
                    print(f"  {csv_file.name}: {len(issues)} issues")
                    for line, col, email, result in issues[:5]:
                        if result['is_valid']:
                            print(f"    Line {line}: {email} -> {result['fixed']}")
                        else:
                            print(f"    Line {line}: {email} - INVALID")
                    if len(issues) > 5:
                        print(f"    ... +{len(issues) - 5} more")
                    total_issues += len(issues)

        except Exception as e:
            print(f"  {csv_file.name}: ERROR: {e}")

    print(f"\nTotal issues: {total_issues}")


def scan_recent():
    """Scan recent scraper output across all data dirs."""
    data_dirs = [
        '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/ANOFM/',
        '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/IAJOB/',
        '/opt/ACTIVE/OPENDATA/DATA/EMPLOYERS_RO/',
        '/opt/ACTIVE/EMAIL/CAMPAIGNS/',
    ]
    for d in data_dirs:
        if Path(d).exists():
            print(f"\n{'='*60}")
            scan_directory(d, hours=24)


def main():
    parser = argparse.ArgumentParser(description='Email Validator Skill')
    parser.add_argument('email', nargs='?', help='Single email to validate')
    parser.add_argument('--csv', help='CSV file to scan')
    parser.add_argument('--fix', action='store_true', help='Fix emails in-place')
    parser.add_argument('--out', help='Output file (default: overwrite input)')
    parser.add_argument('--col', help='Email column name(s), comma-separated')
    parser.add_argument('--scan', help='Scan directory for CSVs with bad emails')
    parser.add_argument('--hours', type=int, default=24, help='Hours to look back (default: 24)')
    parser.add_argument('--scan-recent', action='store_true', help='Scan all recent scraper output')
    parser.add_argument('--mx', help='CSV file for full MX validation')
    args = parser.parse_args()

    if args.email:
        validate_single(args.email)
    elif args.csv:
        cols = args.col.split(',') if args.col else None
        scan_csv(args.csv, email_columns=cols, fix=args.fix, output=args.out)
    elif args.scan:
        scan_directory(args.scan, hours=args.hours)
    elif args.scan_recent:
        scan_recent()
    elif args.mx:
        validate_csv_with_mx(args.mx, check_mx=True)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
