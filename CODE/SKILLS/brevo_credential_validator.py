#!/usr/bin/env python3
"""
Brevo Credentials Validator

Checks that all expected Brevo domains have complete credentials:
- API_KEY (for API sending)
- SMTP_USER (for SMTP sending)
- SMTP_KEY (for SMTP sending)

Usage:
    python3 brevo_credential_validator.py
    python3 brevo_credential_validator.py --test   # Test API connectivity
"""
import os
import sys
import argparse
from pathlib import Path
from dotenv import dotenv_values

# Expected Brevo domains (all should have full credentials)
EXPECTED_DOMAINS = [
    'BUILDJOBS',
    'FACTORYJOBS',
    'CAREWORKERS',
    'WAREHOUSEWORKERS',
    'MIVROMANIA',
    'MIVROMANIA_ONLINE',
    'CIFN',
    'INTERJOB',
    'NEPALEZI',
    'EXPATSINROMANIA',
    'CUMPARLEGUME',
]

# Required credential types per domain
REQUIRED_CREDS = ['API_KEY', 'SMTP_USER', 'SMTP_KEY']

ENV_FILE = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')


def load_env():
    """Load .env file and return as dict."""
    if not ENV_FILE.exists():
        print(f"ERROR: {ENV_FILE} not found")
        sys.exit(1)
    return dotenv_values(ENV_FILE)


def validate_credentials():
    """Check all expected domains have complete credentials."""
    env = load_env()

    results = {
        'complete': [],
        'missing': [],
        'partial': [],
    }

    print("=== Brevo Credentials Validator ===\n")
    print(f"Checking {len(EXPECTED_DOMAINS)} domains...\n")

    for domain in EXPECTED_DOMAINS:
        missing = []
        present = []

        for cred_type in REQUIRED_CREDS:
            key = f'BREVO_{domain}_{cred_type}'
            value = env.get(key, '')

            if value:
                # Validate format
                if cred_type == 'SMTP_USER' and not value.endswith('@smtp-brevo.com'):
                    missing.append(f"{cred_type} (invalid format)")
                elif cred_type == 'SMTP_KEY' and not value.startswith('xsmtpsib-'):
                    missing.append(f"{cred_type} (invalid format)")
                elif cred_type == 'API_KEY' and not value.startswith('xkeysib-'):
                    missing.append(f"{cred_type} (invalid format)")
                else:
                    present.append(cred_type)
            else:
                missing.append(cred_type)

        if not missing:
            results['complete'].append(domain)
            print(f"[OK] {domain}: Complete")
        elif len(present) > 0:
            results['partial'].append((domain, missing))
            print(f"[!!] {domain}: Missing {', '.join(missing)}")
        else:
            results['missing'].append(domain)
            print(f"[XX] {domain}: NO CREDENTIALS")

    # Summary
    print(f"\n=== Summary ===")
    print(f"Complete: {len(results['complete'])}/{len(EXPECTED_DOMAINS)}")
    print(f"Partial:  {len(results['partial'])}/{len(EXPECTED_DOMAINS)}")
    print(f"Missing:  {len(results['missing'])}/{len(EXPECTED_DOMAINS)}")

    # Action items
    if results['partial'] or results['missing']:
        print(f"\n=== Action Required ===")

        for domain, missing in results['partial']:
            print(f"\n{domain} needs:")
            for m in missing:
                key_name = f"BREVO_{domain}_{m.split()[0]}"
                print(f"  {key_name}=...")

        for domain in results['missing']:
            print(f"\n{domain} needs ALL credentials:")
            for cred_type in REQUIRED_CREDS:
                key_name = f"BREVO_{domain}_{cred_type}"
                print(f"  {key_name}=...")

        print("\n=== How to Get Credentials ===")
        print("1. Login to Brevo: https://app.brevo.com")
        print("2. Go to: SMTP & API > SMTP")
        print("3. Create SMTP key for each domain")
        print("4. SMTP_USER format: xxx@smtp-brevo.com")
        print("5. SMTP_KEY format: xsmtpsib-...")
        print("6. API_KEY format: xkeysib-...")

        return False

    print("\nAll credentials are complete!")
    return True


def test_api_connectivity():
    """Test API connectivity for all domains with API keys."""
    try:
        import requests
    except ImportError:
        print("ERROR: requests library not installed")
        return False

    env = load_env()

    print("=== Testing API Connectivity ===\n")

    success = 0
    failed = 0

    for domain in EXPECTED_DOMAINS:
        api_key = env.get(f'BREVO_{domain}_API_KEY', '')
        if not api_key:
            print(f"[--] {domain}: No API key")
            continue

        try:
            resp = requests.get(
                'https://api.brevo.com/v3/account',
                headers={'api-key': api_key},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                email = data.get('email', 'unknown')
                credits = data.get('plan', [{}])[0].get('credits', 0)
                print(f"[OK] {domain}: {email} ({credits} credits)")
                success += 1
            else:
                print(f"[XX] {domain}: HTTP {resp.status_code}")
                failed += 1
        except Exception as e:
            print(f"[XX] {domain}: {str(e)[:40]}")
            failed += 1

    print(f"\nConnectivity: {success} OK, {failed} failed")
    return failed == 0


def main():
    parser = argparse.ArgumentParser(description='Brevo Credentials Validator')
    parser.add_argument('--test', action='store_true', help='Test API connectivity')
    args = parser.parse_args()

    valid = validate_credentials()

    if args.test:
        print()
        test_api_connectivity()

    sys.exit(0 if valid else 1)


if __name__ == '__main__':
    main()
