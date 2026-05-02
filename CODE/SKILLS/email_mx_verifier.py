#!/usr/bin/env python3
"""
Email MX Verifier - Validate emails before sending

Checks:
- MX record exists for domain
- Domain is not a known typo (gamil.com -> gmail.com)
- Email format is valid
- Not a disposable/temporary email

Usage:
    python3 email_mx_verifier.py user@domain.com              # Single email
    python3 email_mx_verifier.py --file contacts.csv          # Verify file
    python3 email_mx_verifier.py --campaign HORECA2026        # Verify campaign
    python3 email_mx_verifier.py --clean contacts.csv         # Remove invalid
    python3 email_mx_verifier.py --stats                      # Show verification stats

No external API - uses DNS queries only.
"""

import os
import sys
import csv
import json
import re
import dns.resolver
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

try:
    from skills_common import to_ascii
except ImportError:
    def to_ascii(text):
        if not text:
            return text
        import unicodedata
        return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii')

# Paths
STATE_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/.mx_verifier_state.json")
CAMPAIGNS_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/CAMPAIGNS")

# Known typo domains
TYPO_DOMAINS = {
    "gamil.com": "gmail.com",
    "gmial.com": "gmail.com",
    "gmal.com": "gmail.com",
    "gnail.com": "gmail.com",
    "gmai.com": "gmail.com",
    "gmail.ro": "gmail.com",
    "gmail.co": "gmail.com",
    "hotmal.com": "hotmail.com",
    "hotmai.com": "hotmail.com",
    "hotmial.com": "hotmail.com",
    "outlok.com": "outlook.com",
    "outloo.com": "outlook.com",
    "yaho.com": "yahoo.com",
    "yahooo.com": "yahoo.com",
    "yhoo.com": "yahoo.com",
}

# Disposable email domains
DISPOSABLE_DOMAINS = [
    "tempmail.com", "throwaway.email", "mailinator.com", "guerrillamail.com",
    "10minutemail.com", "trashmail.com", "fakeinbox.com", "sharklasers.com"
]

# MX cache to avoid repeated lookups
MX_CACHE = {}


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"verified": 0, "invalid": 0, "typo_fixed": 0, "last_run": None}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def get_mx_records(domain):
    """Get MX records for domain."""
    if domain in MX_CACHE:
        return MX_CACHE[domain]

    try:
        answers = dns.resolver.resolve(domain, 'MX')
        mx_records = [str(r.exchange).rstrip('.') for r in answers]
        MX_CACHE[domain] = mx_records
        return mx_records
    except Exception:
        MX_CACHE[domain] = None
        return None


def is_valid_format(email):
    """Check email format."""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.lower().strip()))


def fix_typo_domain(email):
    """Fix known typo domains."""
    if not email or '@' not in email:
        return email, False

    local, domain = email.lower().split('@', 1)

    if domain in TYPO_DOMAINS:
        fixed = f"{local}@{TYPO_DOMAINS[domain]}"
        return fixed, True

    return email.lower(), False


def is_disposable(email):
    """Check if email is from disposable provider."""
    if not email or '@' not in email:
        return False

    domain = email.lower().split('@')[1]
    return domain in DISPOSABLE_DOMAINS


def verify_email(email):
    """Verify single email."""
    result = {
        'email': email,
        'original': email,
        'valid': False,
        'reason': '',
        'mx_records': None,
        'typo_fixed': False
    }

    # Check format
    if not is_valid_format(email):
        result['reason'] = 'invalid_format'
        return result

    # Fix typos
    fixed_email, was_typo = fix_typo_domain(email)
    if was_typo:
        result['email'] = fixed_email
        result['typo_fixed'] = True
        email = fixed_email

    # Check disposable
    if is_disposable(email):
        result['reason'] = 'disposable'
        return result

    # Get domain
    domain = email.lower().split('@')[1]

    # Check MX records
    mx_records = get_mx_records(domain)
    if mx_records:
        result['valid'] = True
        result['mx_records'] = mx_records
        result['reason'] = 'ok'
    else:
        result['reason'] = 'no_mx'

    return result


def verify_file(filepath, email_column='email'):
    """Verify all emails in CSV file."""
    filepath = Path(filepath)
    if not filepath.exists():
        log(f"File not found: {filepath}")
        return []

    results = []

    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = row.get(email_column, '').strip()
            if email:
                result = verify_email(email)
                result['row'] = row
                results.append(result)

    return results


def clean_file(filepath, output=None, email_column='email'):
    """Remove invalid emails from file."""
    filepath = Path(filepath)
    if not filepath.exists():
        log(f"File not found: {filepath}")
        return

    results = verify_file(filepath, email_column)

    valid_rows = []
    invalid_count = 0
    fixed_count = 0

    for r in results:
        if r['valid']:
            row = r['row']
            # Update email if typo was fixed
            if r['typo_fixed']:
                row[email_column] = r['email']
                fixed_count += 1
            valid_rows.append(row)
        else:
            invalid_count += 1

    # Write output
    output_path = Path(output) if output else filepath.with_suffix('.clean.csv')

    if valid_rows:
        fieldnames = valid_rows[0].keys()
        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(valid_rows)

    log(f"Cleaned: {len(valid_rows)} valid, {invalid_count} removed, {fixed_count} typos fixed")
    log(f"Output: {output_path}")

    return output_path


def verify_campaign(campaign_name):
    """Verify emails in campaign contacts."""
    contacts_file = CAMPAIGNS_DIR / campaign_name / "contacts" / "contacts.csv"
    if not contacts_file.exists():
        log(f"Campaign contacts not found: {contacts_file}")
        return []

    log(f"Verifying campaign: {campaign_name}")
    results = verify_file(contacts_file)

    # Summary
    valid = sum(1 for r in results if r['valid'])
    invalid = sum(1 for r in results if not r['valid'])
    typos = sum(1 for r in results if r['typo_fixed'])

    log(f"Results: {valid} valid, {invalid} invalid, {typos} typos")

    # Group by reason
    reasons = {}
    for r in results:
        reason = r['reason']
        reasons[reason] = reasons.get(reason, 0) + 1

    log("By reason:")
    for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
        print(f"  {reason}: {count}")

    return results


def show_stats():
    """Show verification stats."""
    state = load_state()

    print("\n=== Email MX Verifier Stats ===\n")
    print(f"Total verified: {state.get('verified', 0)}")
    print(f"Invalid found: {state.get('invalid', 0)}")
    print(f"Typos fixed: {state.get('typo_fixed', 0)}")
    print(f"Last run: {state.get('last_run', 'Never')}")

    print("\nKnown typo domains:")
    for typo, correct in list(TYPO_DOMAINS.items())[:5]:
        print(f"  {typo} -> {correct}")

    print(f"\nMX cache entries: {len(MX_CACHE)}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Email MX Verifier")
    parser.add_argument("email", nargs="?", help="Single email to verify")
    parser.add_argument("--file", help="CSV file to verify")
    parser.add_argument("--campaign", help="Campaign to verify")
    parser.add_argument("--clean", help="Clean invalid emails from file")
    parser.add_argument("--output", help="Output file for cleaned emails")
    parser.add_argument("--column", default="email", help="Email column name")
    parser.add_argument("--stats", action="store_true", help="Show stats")

    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    state = load_state()

    if args.email:
        result = verify_email(args.email)
        print(json.dumps(result, indent=2))

        state['verified'] = state.get('verified', 0) + 1
        if not result['valid']:
            state['invalid'] = state.get('invalid', 0) + 1
        if result['typo_fixed']:
            state['typo_fixed'] = state.get('typo_fixed', 0) + 1

    elif args.file:
        results = verify_file(args.file, args.column)
        valid = sum(1 for r in results if r['valid'])
        invalid = sum(1 for r in results if not r['valid'])
        print(f"Verified {len(results)} emails: {valid} valid, {invalid} invalid")

        state['verified'] = state.get('verified', 0) + len(results)
        state['invalid'] = state.get('invalid', 0) + invalid

    elif args.clean:
        clean_file(args.clean, args.output, args.column)

    elif args.campaign:
        verify_campaign(args.campaign)

    else:
        parser.print_help()
        return

    state['last_run'] = datetime.now().isoformat()
    save_state(state)


if __name__ == "__main__":
    main()
