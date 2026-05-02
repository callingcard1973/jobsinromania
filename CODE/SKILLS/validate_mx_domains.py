#!/usr/bin/env python3
"""
MX Domain Validator - Check email domains for valid MX records.

Validates domains before importing to campaigns. Especially useful for:
- Romanian hotel/pension domains (often defunct)
- Shipyard/maritime domains (companies closed)
- Small business domains (high turnover)

Usage:
    # Check single domain
    python3 validate_mx_domains.py --domain pensiuneamilica.ro

    # Validate CSV file
    python3 validate_mx_domains.py --csv contacts.csv --email-col email

    # Check Romanian hotel domains in file
    python3 validate_mx_domains.py --csv hotels.csv --filter-hotel

    # Add invalid domains to blacklist
    python3 validate_mx_domains.py --csv contacts.csv --update-blacklist

    # Check all domains in blacklist have no MX
    python3 validate_mx_domains.py --verify-blacklist
"""

import os
import sys
import csv
import argparse
import dns.resolver
from typing import List, Tuple, Set, Optional
from pathlib import Path

# Paths
DOMAIN_BLACKLIST = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/EMAIL_CLEANUP/domain_blacklist.txt")

# Romanian hotel/pension keywords
HOTEL_KEYWORDS = [
    'hotel', 'pension', 'pensiune', 'motel', 'hostel', 'vila', 'cabana',
    'resort', 'spa', 'boutique', 'house', 'lodge', 'inn', 'casa', 'casa-',
    '-hotel', '-pension', '-resort'
]

# DNS timeout
DNS_TIMEOUT = 5


def check_mx(domain: str) -> Tuple[bool, str]:
    """
    Check if domain has valid MX records.

    Returns:
        (has_mx, message)
    """
    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = DNS_TIMEOUT
        resolver.lifetime = DNS_TIMEOUT

        answers = resolver.resolve(domain, 'MX')
        mx_records = [str(r.exchange).rstrip('.') for r in answers]
        return True, f"MX: {', '.join(mx_records[:3])}"

    except dns.resolver.NXDOMAIN:
        return False, "NXDOMAIN (domain does not exist)"
    except dns.resolver.NoAnswer:
        return False, "No MX records"
    except dns.resolver.NoNameservers:
        return False, "No nameservers"
    except dns.resolver.Timeout:
        return False, "DNS timeout"
    except Exception as e:
        return False, f"Error: {str(e)[:50]}"


def is_hotel_domain(domain: str) -> bool:
    """Check if domain looks like a hotel/pension."""
    domain_lower = domain.lower()
    for keyword in HOTEL_KEYWORDS:
        if keyword in domain_lower:
            return True
    return False


def load_blacklist() -> Set[str]:
    """Load domain blacklist."""
    domains = set()
    if DOMAIN_BLACKLIST.exists():
        with open(DOMAIN_BLACKLIST) as f:
            for line in f:
                domain = line.strip().lower()
                if domain:
                    domains.add(domain)
    return domains


def save_to_blacklist(domains: List[str]) -> int:
    """Append domains to blacklist."""
    existing = load_blacklist()
    added = 0

    with open(DOMAIN_BLACKLIST, 'a') as f:
        for domain in domains:
            domain = domain.lower().strip()
            if domain and domain not in existing:
                f.write(f"{domain}\n")
                existing.add(domain)
                added += 1

    return added


def validate_csv(csv_path: str, email_col: str = 'email',
                 filter_hotel: bool = False) -> Tuple[List[dict], List[dict]]:
    """
    Validate domains in CSV file.

    Returns:
        (valid_rows, invalid_rows)
    """
    valid = []
    invalid = []
    checked_domains = {}  # Cache results

    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = row.get(email_col, '').strip()
            if not email or '@' not in email:
                continue

            domain = email.split('@')[1].lower()

            # Skip if already checked
            if domain in checked_domains:
                has_mx = checked_domains[domain]
            else:
                # Filter by hotel if requested
                if filter_hotel and not is_hotel_domain(domain):
                    checked_domains[domain] = True
                    valid.append(row)
                    continue

                has_mx, msg = check_mx(domain)
                checked_domains[domain] = has_mx
                print(f"  {domain}: {'OK' if has_mx else 'INVALID'} - {msg}")

            if has_mx:
                valid.append(row)
            else:
                invalid.append(row)

    return valid, invalid


def verify_blacklist() -> Tuple[int, int]:
    """
    Verify all blacklisted domains still have no MX.
    Returns (still_invalid, now_valid) counts.
    """
    domains = load_blacklist()
    still_invalid = 0
    now_valid = 0

    for domain in sorted(domains):
        has_mx, msg = check_mx(domain)
        if has_mx:
            print(f"  {domain}: NOW VALID - {msg}")
            now_valid += 1
        else:
            still_invalid += 1

    return still_invalid, now_valid


def main():
    parser = argparse.ArgumentParser(description='Validate MX records for email domains')
    parser.add_argument('--domain', help='Check single domain')
    parser.add_argument('--csv', help='CSV file to validate')
    parser.add_argument('--email-col', default='email', help='Email column name')
    parser.add_argument('--filter-hotel', action='store_true',
                        help='Only check hotel/pension domains')
    parser.add_argument('--update-blacklist', action='store_true',
                        help='Add invalid domains to blacklist')
    parser.add_argument('--verify-blacklist', action='store_true',
                        help='Verify blacklisted domains still invalid')
    parser.add_argument('--output', help='Output file for clean CSV')
    args = parser.parse_args()

    if args.domain:
        has_mx, msg = check_mx(args.domain)
        print(f"{args.domain}: {'VALID' if has_mx else 'INVALID'} - {msg}")
        sys.exit(0 if has_mx else 1)

    if args.verify_blacklist:
        print(f"Verifying {len(load_blacklist())} blacklisted domains...")
        still_invalid, now_valid = verify_blacklist()
        print(f"\nResults: {still_invalid} still invalid, {now_valid} now valid")
        if now_valid > 0:
            print("Consider removing valid domains from blacklist")
        return

    if args.csv:
        print(f"Validating {args.csv}...")
        valid, invalid = validate_csv(args.csv, args.email_col, args.filter_hotel)

        print(f"\nResults: {len(valid)} valid, {len(invalid)} invalid")

        # Collect invalid domains
        invalid_domains = set()
        for row in invalid:
            email = row.get(args.email_col, '')
            if '@' in email:
                invalid_domains.add(email.split('@')[1].lower())

        if invalid_domains:
            print(f"\nInvalid domains ({len(invalid_domains)}):")
            for d in sorted(invalid_domains):
                print(f"  - {d}")

            if args.update_blacklist:
                added = save_to_blacklist(list(invalid_domains))
                print(f"\nAdded {added} domains to blacklist")

        # Save clean CSV if requested
        if args.output and valid:
            with open(args.output, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=valid[0].keys())
                writer.writeheader()
                writer.writerows(valid)
            print(f"\nSaved {len(valid)} valid rows to {args.output}")

        return

    parser.print_help()


if __name__ == '__main__':
    main()
