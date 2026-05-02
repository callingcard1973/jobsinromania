#!/usr/bin/env python3
"""
Phone Carrier Check - Validate and normalize phone numbers

Validates:
- Country prefix format
- Number length per country
- Known carrier prefixes (mobile vs landline)
- Common typos and formats

Usage:
    python3 phone_carrier_check.py +40721234567              # Single phone
    python3 phone_carrier_check.py --file contacts.csv       # Verify file
    python3 phone_carrier_check.py --campaign HORECA2026     # Verify campaign
    python3 phone_carrier_check.py --normalize contacts.csv  # Normalize all
    python3 phone_carrier_check.py --stats                   # Show stats

No external API - uses format rules only.
"""

import os
import sys
import csv
import json
import re
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

# Paths
STATE_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/.phone_check_state.json")
CAMPAIGNS_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/CAMPAIGNS")

# Country phone formats
PHONE_FORMATS = {
    "RO": {"prefix": "+40", "length": 10, "mobile": ["7"], "landline": ["2", "3"]},
    "PL": {"prefix": "+48", "length": 9, "mobile": ["5", "6", "7", "8"], "landline": ["1", "2", "3", "4"]},
    "CZ": {"prefix": "+420", "length": 9, "mobile": ["6", "7"], "landline": ["2", "3", "4", "5"]},
    "SK": {"prefix": "+421", "length": 9, "mobile": ["9"], "landline": ["2"]},
    "HU": {"prefix": "+36", "length": 9, "mobile": ["2", "3", "7"], "landline": ["1"]},
    "BG": {"prefix": "+359", "length": 9, "mobile": ["8", "9"], "landline": ["2"]},
    "DE": {"prefix": "+49", "length": [10, 11], "mobile": ["1"], "landline": ["2", "3", "4", "5", "6", "7", "8", "9"]},
    "AT": {"prefix": "+43", "length": [10, 11], "mobile": ["6"], "landline": ["1", "2", "3", "4", "5", "7"]},
    "NL": {"prefix": "+31", "length": 9, "mobile": ["6"], "landline": ["1", "2", "3", "4", "5", "7"]},
    "BE": {"prefix": "+32", "length": 9, "mobile": ["4"], "landline": ["1", "2", "3", "5", "6", "7", "8", "9"]},
    "FR": {"prefix": "+33", "length": 9, "mobile": ["6", "7"], "landline": ["1", "2", "3", "4", "5"]},
    "ES": {"prefix": "+34", "length": 9, "mobile": ["6", "7"], "landline": ["8", "9"]},
    "IT": {"prefix": "+39", "length": [9, 10], "mobile": ["3"], "landline": ["0"]},
    "UK": {"prefix": "+44", "length": 10, "mobile": ["7"], "landline": ["1", "2"]},
    "SE": {"prefix": "+46", "length": 9, "mobile": ["7"], "landline": ["1", "2", "3", "4", "5", "6", "8"]},
    "NO": {"prefix": "+47", "length": 8, "mobile": ["4", "9"], "landline": ["2", "3", "5", "6", "7"]},
    "DK": {"prefix": "+45", "length": 8, "mobile": ["2", "3", "4", "5", "6"], "landline": ["3", "4", "5", "6", "7", "8", "9"]},
    "FI": {"prefix": "+358", "length": 9, "mobile": ["4", "5"], "landline": ["1", "2", "3", "6", "7", "8", "9"]},
}


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"validated": 0, "invalid": 0, "normalized": 0, "last_run": None}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def clean_phone(phone):
    """Remove non-digit characters except +."""
    if not phone:
        return ""
    return re.sub(r'[^\d+]', '', str(phone))


def detect_country(phone):
    """Detect country from phone prefix."""
    phone = clean_phone(phone)

    # Check each country prefix
    for country, fmt in PHONE_FORMATS.items():
        prefix = fmt['prefix'].replace('+', '')
        if phone.startswith('+' + prefix) or phone.startswith(prefix):
            return country

    return None


def normalize_phone(phone, default_country='RO'):
    """Normalize phone number to international format."""
    phone = clean_phone(phone)
    if not phone:
        return "", False

    # Already international format
    if phone.startswith('+'):
        return phone, True

    # Detect or use default country
    country = detect_country(phone) or default_country
    fmt = PHONE_FORMATS.get(country, {})
    prefix = fmt.get('prefix', '')

    # Remove leading zeros
    phone = phone.lstrip('0')

    # Remove country code if present without +
    prefix_digits = prefix.replace('+', '')
    if phone.startswith(prefix_digits):
        phone = phone[len(prefix_digits):]

    # Build international format
    normalized = prefix + phone

    return normalized, True


def validate_phone(phone, country=None):
    """Validate phone number."""
    result = {
        'phone': phone,
        'normalized': '',
        'valid': False,
        'country': None,
        'type': None,  # mobile/landline
        'reason': ''
    }

    phone = clean_phone(phone)
    if not phone:
        result['reason'] = 'empty'
        return result

    # Normalize
    normalized, success = normalize_phone(phone, country or 'RO')
    result['normalized'] = normalized

    if not success:
        result['reason'] = 'normalize_failed'
        return result

    # Detect country
    detected_country = detect_country(normalized)
    if not detected_country:
        result['reason'] = 'unknown_country'
        return result

    result['country'] = detected_country
    fmt = PHONE_FORMATS[detected_country]

    # Extract national number (without prefix)
    prefix = fmt['prefix']
    national = normalized.replace(prefix, '')

    # Check length
    expected_len = fmt['length']
    if isinstance(expected_len, list):
        if len(national) not in expected_len:
            result['reason'] = f'invalid_length:{len(national)}'
            return result
    else:
        if len(national) != expected_len:
            result['reason'] = f'invalid_length:{len(national)}'
            return result

    # Detect type (mobile vs landline)
    first_digit = national[0] if national else ''
    if first_digit in fmt.get('mobile', []):
        result['type'] = 'mobile'
    elif first_digit in fmt.get('landline', []):
        result['type'] = 'landline'
    else:
        result['type'] = 'unknown'

    result['valid'] = True
    result['reason'] = 'ok'

    return result


def validate_file(filepath, phone_column='phone'):
    """Validate all phones in CSV file."""
    filepath = Path(filepath)
    if not filepath.exists():
        log(f"File not found: {filepath}")
        return []

    results = []

    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            phone = row.get(phone_column, '').strip()
            if phone:
                result = validate_phone(phone)
                result['row'] = row
                results.append(result)

    return results


def normalize_file(filepath, output=None, phone_column='phone'):
    """Normalize all phones in file."""
    filepath = Path(filepath)
    if not filepath.exists():
        log(f"File not found: {filepath}")
        return

    rows = []
    normalized_count = 0

    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        for row in reader:
            phone = row.get(phone_column, '').strip()
            if phone:
                result = validate_phone(phone)
                if result['valid'] and result['normalized'] != phone:
                    row[phone_column] = result['normalized']
                    normalized_count += 1
            rows.append(row)

    # Write output
    output_path = Path(output) if output else filepath.with_suffix('.normalized.csv')

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    log(f"Normalized {normalized_count} phones")
    log(f"Output: {output_path}")

    return output_path


def validate_campaign(campaign_name):
    """Validate phones in campaign contacts."""
    contacts_file = CAMPAIGNS_DIR / campaign_name / "contacts" / "contacts.csv"
    if not contacts_file.exists():
        log(f"Campaign contacts not found: {contacts_file}")
        return []

    log(f"Validating campaign: {campaign_name}")
    results = validate_file(contacts_file)

    # Summary
    valid = sum(1 for r in results if r['valid'])
    invalid = sum(1 for r in results if not r['valid'])
    mobile = sum(1 for r in results if r.get('type') == 'mobile')
    landline = sum(1 for r in results if r.get('type') == 'landline')

    log(f"Results: {valid} valid, {invalid} invalid")
    log(f"Types: {mobile} mobile, {landline} landline")

    # Group by country
    countries = {}
    for r in results:
        country = r.get('country', 'unknown')
        countries[country] = countries.get(country, 0) + 1

    log("By country:")
    for country, count in sorted(countries.items(), key=lambda x: -x[1]):
        print(f"  {country}: {count}")

    return results


def show_stats():
    """Show validation stats."""
    state = load_state()

    print("\n=== Phone Carrier Check Stats ===\n")
    print(f"Total validated: {state.get('validated', 0)}")
    print(f"Invalid found: {state.get('invalid', 0)}")
    print(f"Normalized: {state.get('normalized', 0)}")
    print(f"Last run: {state.get('last_run', 'Never')}")

    print("\nSupported countries:")
    for country, fmt in list(PHONE_FORMATS.items())[:10]:
        print(f"  {country}: {fmt['prefix']} ({fmt['length']} digits)")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Phone Carrier Check")
    parser.add_argument("phone", nargs="?", help="Single phone to validate")
    parser.add_argument("--file", help="CSV file to validate")
    parser.add_argument("--campaign", help="Campaign to validate")
    parser.add_argument("--normalize", help="Normalize phones in file")
    parser.add_argument("--output", help="Output file")
    parser.add_argument("--column", default="phone", help="Phone column name")
    parser.add_argument("--stats", action="store_true", help="Show stats")

    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    state = load_state()

    if args.phone:
        result = validate_phone(args.phone)
        print(json.dumps(result, indent=2))
        state['validated'] = state.get('validated', 0) + 1
        if not result['valid']:
            state['invalid'] = state.get('invalid', 0) + 1

    elif args.file:
        results = validate_file(args.file, args.column)
        valid = sum(1 for r in results if r['valid'])
        invalid = sum(1 for r in results if not r['valid'])
        print(f"Validated {len(results)} phones: {valid} valid, {invalid} invalid")

        state['validated'] = state.get('validated', 0) + len(results)
        state['invalid'] = state.get('invalid', 0) + invalid

    elif args.normalize:
        normalize_file(args.normalize, args.output, args.column)

    elif args.campaign:
        validate_campaign(args.campaign)

    else:
        parser.print_help()
        return

    state['last_run'] = datetime.now().isoformat()
    save_state(state)


if __name__ == "__main__":
    main()
