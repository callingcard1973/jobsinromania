#!/usr/bin/env python3
"""
Email Bounce Prevention Skill
[AI: Claude Code]

Prevents email bounces by validating emails before sending:
- MX record validation (domain has mail server)
- Typo domain fix (gmai.com -> gmail.com)
- Disposable email detection
- Format validation

Usage:
    python3 email_bounce_prevention.py --validate email@domain.com
    python3 email_bounce_prevention.py --validate-csv /path/to/contacts.csv
    python3 email_bounce_prevention.py --check-domain domain.com
    python3 email_bounce_prevention.py --stats
    python3 email_bounce_prevention.py --clean-bounces

Components:
    /opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED/email_validation.py - Core validation
    /opt/ACTIVE/EMAIL/CAMPAIGNS/SCRIPTS/bounce_webhook.py - Brevo webhook (port 5001)
    /opt/ACTIVE/OPENDATA/DATA/mx_cache.json - MX cache (persistent)
"""

import sys
import argparse
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

from email_validation import (
    validate_email_full,
    suggest_typo_fix,
    check_mx_record,
    save_mx_cache,
    is_disposable_domain,
    is_role_based,
    DOMAIN_TYPOS,
    DISPOSABLE_DOMAINS
)


def validate_single(email: str) -> dict:
    """Validate a single email address."""
    result = validate_email_full(email, check_mx=True)
    save_mx_cache()
    return result


def validate_csv(csv_path: str, email_col: str = 'email') -> dict:
    """Validate all emails in a CSV file."""
    import csv
    from pathlib import Path

    stats = {
        'total': 0,
        'valid': 0,
        'invalid': 0,
        'fixed': 0,
        'by_reason': {}
    }

    path = Path(csv_path)
    if not path.exists():
        return {'error': f'File not found: {csv_path}'}

    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Find email column
    fieldnames = reader.fieldnames or []
    col = None
    for c in fieldnames:
        if 'email' in c.lower():
            col = c
            break

    if not col:
        return {'error': 'No email column found'}

    # Validate
    invalid_emails = []
    for row in rows:
        email = row.get(col, '').strip().lower()
        if not email:
            continue

        stats['total'] += 1
        result = validate_email_full(email, check_mx=True)

        if result['is_valid']:
            stats['valid'] += 1
            if result['email'] != email:
                stats['fixed'] += 1
        else:
            stats['invalid'] += 1
            reason = result['reason']
            stats['by_reason'][reason] = stats['by_reason'].get(reason, 0) + 1
            invalid_emails.append({'email': email, 'reason': reason})

    save_mx_cache()
    stats['invalid_emails'] = invalid_emails[:20]  # First 20
    return stats


def check_domain(domain: str) -> dict:
    """Check if domain has valid MX record."""
    has_mx = check_mx_record(domain)
    save_mx_cache()
    return {
        'domain': domain,
        'has_mx': has_mx,
        'can_receive_email': has_mx
    }


def get_stats() -> dict:
    """Get MX cache stats."""
    import json
    from pathlib import Path

    cache_file = Path('/opt/ACTIVE/OPENDATA/DATA/mx_cache.json')
    if not cache_file.exists():
        return {'cached_domains': 0, 'valid': 0, 'invalid': 0}

    with open(cache_file) as f:
        cache = json.load(f)

    valid = sum(1 for v in cache.values() if v)
    invalid = sum(1 for v in cache.values() if not v)

    return {
        'cached_domains': len(cache),
        'valid': valid,
        'invalid': invalid,
        'invalid_domains': [d for d, v in cache.items() if not v][:20]
    }


def clean_bounces_from_db(db_name: str = 'anofm_campaign') -> dict:
    """Find and mark bounced emails in database."""
    import psycopg2

    conn = psycopg2.connect(
        host='localhost',
        dbname=db_name,
        user='tudor',
        password='scraper123'
    )

    stats = {'checked': 0, 'invalid': 0, 'fixed': 0}

    with conn.cursor() as cur:
        # Get pending emails
        cur.execute("""
            SELECT id, email FROM contacts
            WHERE campaign_status IS NULL OR campaign_status = 'pending'
            LIMIT 1000
        """)
        rows = cur.fetchall()

        for contact_id, email in rows:
            stats['checked'] += 1
            result = validate_email_full(email, check_mx=True)

            if not result['is_valid']:
                stats['invalid'] += 1
                cur.execute(
                    "UPDATE contacts SET campaign_status = %s WHERE id = %s",
                    (f"invalid_{result['reason']}", contact_id)
                )
            elif result['email'] != email:
                stats['fixed'] += 1
                cur.execute(
                    "UPDATE contacts SET email = %s WHERE id = %s",
                    (result['email'], contact_id)
                )

        conn.commit()

    save_mx_cache()
    conn.close()
    return stats


def main():
    parser = argparse.ArgumentParser(description='Email Bounce Prevention')
    parser.add_argument('--validate', help='Validate single email')
    parser.add_argument('--validate-csv', help='Validate CSV file')
    parser.add_argument('--check-domain', help='Check domain MX record')
    parser.add_argument('--stats', action='store_true', help='Show MX cache stats')
    parser.add_argument('--clean-bounces', help='Clean bounces from DB (db_name)')
    parser.add_argument('--list-typos', action='store_true', help='List known typo domains')

    args = parser.parse_args()

    if args.validate:
        result = validate_single(args.validate)
        print(f"Email: {result['email']}")
        print(f"Valid: {result['is_valid']}")
        print(f"Reason: {result['reason']}")
        print(f"Risky: {result['is_risky']}")

    elif args.validate_csv:
        stats = validate_csv(args.validate_csv)
        print(f"Total: {stats.get('total', 0)}")
        print(f"Valid: {stats.get('valid', 0)}")
        print(f"Invalid: {stats.get('invalid', 0)}")
        print(f"Fixed typos: {stats.get('fixed', 0)}")
        if stats.get('by_reason'):
            print("By reason:")
            for reason, count in stats['by_reason'].items():
                print(f"  {reason}: {count}")

    elif args.check_domain:
        result = check_domain(args.check_domain)
        print(f"Domain: {result['domain']}")
        print(f"Has MX: {result['has_mx']}")
        print(f"Can receive email: {result['can_receive_email']}")

    elif args.stats:
        stats = get_stats()
        print(f"Cached domains: {stats['cached_domains']}")
        print(f"Valid (has MX): {stats['valid']}")
        print(f"Invalid (no MX): {stats['invalid']}")
        if stats.get('invalid_domains'):
            print("Invalid domains (sample):")
            for d in stats['invalid_domains'][:10]:
                print(f"  - {d}")

    elif args.clean_bounces:
        stats = clean_bounces_from_db(args.clean_bounces)
        print(f"Checked: {stats['checked']}")
        print(f"Invalid (marked): {stats['invalid']}")
        print(f"Fixed typos: {stats['fixed']}")

    elif args.list_typos:
        print("Known typo domains:")
        for typo, correct in sorted(DOMAIN_TYPOS.items()):
            print(f"  {typo} -> {correct}")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
