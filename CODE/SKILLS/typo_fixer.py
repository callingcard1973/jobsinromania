#!/usr/bin/env python3
"""
Typo Domain Fixer - Auto-fixes common email typos
Runs as pre-commit hook or standalone
"""
import sys
import csv
import re
from pathlib import Path

# Known typo domains
TYPO_DOMAINS = {
    'gamil.com': 'gmail.com',
    'gmial.com': 'gmail.com',
    'gmal.com': 'gmail.com',
    'gnail.com': 'gmail.com',
    'gmai.com': 'gmail.com',
    'gmail.ro': 'gmail.com',
    'gmail.co': 'gmail.com',
    'hotmal.com': 'hotmail.com',
    'hotmai.com': 'hotmail.com',
    'hotmial.com': 'hotmail.com',
    'outlok.com': 'outlook.com',
    'outloo.com': 'outlook.com',
    'yaho.com': 'yahoo.com',
    'yahooo.com': 'yahoo.com',
    'yhoo.com': 'yahoo.com',
}

def fix_email(email):
    """Fix typo in email domain."""
    if not email or '@' not in email:
        return email, False

    local, domain = email.rsplit('@', 1)
    domain_lower = domain.lower()

    if domain_lower in TYPO_DOMAINS:
        return f"{local}@{TYPO_DOMAINS[domain_lower]}", True

    return email, False

def process_csv(filepath, dry_run=False):
    """Process CSV and fix email typos."""
    filepath = Path(filepath)
    if not filepath.exists():
        print(f"Error: {filepath} not found")
        return 0

    # Read file
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        sample = f.read(4096)
        f.seek(0)
        delimiter = ';' if sample.count(';') > sample.count(',') else ','
        reader = csv.DictReader(f, delimiter=delimiter)
        rows = list(reader)
        fieldnames = reader.fieldnames

    # Find email columns
    email_cols = [c for c in fieldnames if 'email' in c.lower() or 'mail' in c.lower()]

    if not email_cols:
        print(f"No email columns found in {filepath}")
        return 0

    # Fix typos
    fixes = []
    for i, row in enumerate(rows):
        for col in email_cols:
            old_val = row.get(col, '')
            new_val, fixed = fix_email(old_val)
            if fixed:
                fixes.append({'row': i+1, 'col': col, 'old': old_val, 'new': new_val})
                if not dry_run:
                    row[col] = new_val

    # Report
    if fixes:
        print(f"Found {len(fixes)} typos in {filepath.name}:")
        for fix in fixes[:10]:  # Show first 10
            print(f"  Row {fix['row']}: {fix['old']} -> {fix['new']}")
        if len(fixes) > 10:
            print(f"  ... and {len(fixes)-10} more")

    # Write back
    if fixes and not dry_run:
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Fixed {len(fixes)} typos in {filepath.name}")

    return len(fixes)

def main():
    if len(sys.argv) < 2:
        print("Usage: typo_fixer.py <file.csv> [--dry-run]")
        sys.exit(1)

    filepath = sys.argv[1]
    dry_run = '--dry-run' in sys.argv

    count = process_csv(filepath, dry_run)

    if dry_run:
        print(f"\nDry run: Would fix {count} typos")

    sys.exit(0 if count == 0 else 1)  # Exit 1 if fixes made (for hooks)

if __name__ == '__main__':
    main()
