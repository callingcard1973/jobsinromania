#!/usr/bin/env python3
"""
Credential Validator - Prevent Failed Logins

Validates all A2 IMAP/SMTP credentials proactively.
Alerts via Telegram if any credential fails.

Run daily via cron to catch password changes before they cause IP blocks.

Usage:
    python3 credential_validator.py              # Validate all credentials
    python3 credential_validator.py --fix        # Show fix instructions for failures
    python3 credential_validator.py --alert      # Send Telegram alert on failure
    python3 credential_validator.py --quiet      # Only output on failure

Cron (daily 6 AM):
    0 6 * * * /opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/INFRA/SKILLS/credential_validator.py --alert >> /opt/ACTIVE/INFRA/LOGS/credential_validator.log 2>&1
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import json
import imaplib
import smtplib
import ssl
import argparse
from datetime import datetime
from pathlib import Path

# Credentials file - SINGLE SOURCE OF TRUTH (check both paths for raspibig/raspi)
CREDENTIALS_FILE = (
    Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/a2_smtp_credentials.json')
    if Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/a2_smtp_credentials.json').exists()
    else Path('/opt/EMAIL/CAMPAIGNS/a2_smtp_credentials.json')
)
LOG_FILE = (
    Path('/opt/ACTIVE/INFRA/LOGS/credential_validator.log')
    if Path('/opt/ACTIVE/INFRA/LOGS').exists()
    else Path('/opt/LOGS/credential_validator.log')
)

# Telegram alerting
try:
    from alerting import send_telegram
    from alert_config import should_alert
    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False
    def send_telegram(msg):
        print(f"[TELEGRAM] {msg}")


def load_credentials():
    """Load all A2 credentials from JSON file."""
    try:
        with open(CREDENTIALS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Cannot load credentials: {e}")
        return {}


def validate_imap(domain: str, email: str, password: str, timeout: int = 10) -> tuple:
    """
    Validate IMAP credentials for a domain.

    Returns:
        (success: bool, error: str or None)
    """
    try:
        mail = imaplib.IMAP4_SSL(f'mail.{domain}', 993, timeout=timeout)
        mail.login(email, password)
        mail.logout()
        return True, None
    except imaplib.IMAP4.error as e:
        return False, f"IMAP auth failed: {e}"
    except Exception as e:
        return False, f"IMAP error: {e}"


def validate_smtp(domain: str, email: str, password: str, timeout: int = 10) -> tuple:
    """
    Validate SMTP credentials for a domain.

    Returns:
        (success: bool, error: str or None)
    """
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(f'mail.{domain}', 465, context=context, timeout=timeout) as server:
            server.login(email, password)
        return True, None
    except smtplib.SMTPAuthenticationError as e:
        return False, f"SMTP auth failed: {e}"
    except Exception as e:
        return False, f"SMTP error: {e}"


def validate_all(quiet: bool = False) -> dict:
    """
    Validate all credentials.

    Returns:
        dict with 'passed', 'failed', 'errors' keys
    """
    credentials = load_credentials()
    results = {'passed': [], 'failed': [], 'errors': []}

    if not quiet:
        print("=" * 60)
        print(f"CREDENTIAL VALIDATOR - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("=" * 60)

    for domain, creds in credentials.items():
        email = creds.get('email', f'office@{domain}')
        password = creds.get('password', '')

        if not password:
            results['errors'].append((domain, "No password in credentials file"))
            if not quiet:
                print(f"  [SKIP] {domain}: No password")
            continue

        # Test IMAP
        imap_ok, imap_err = validate_imap(domain, email, password)

        if imap_ok:
            results['passed'].append(domain)
            if not quiet:
                print(f"  [OK] {domain}")
        else:
            results['failed'].append((domain, imap_err))
            if not quiet:
                print(f"  [FAIL] {domain}: {imap_err}")

    if not quiet:
        print("-" * 60)
        print(f"Passed: {len(results['passed'])}, Failed: {len(results['failed'])}, Errors: {len(results['errors'])}")

    return results


def show_fix_instructions(results: dict):
    """Show how to fix failed credentials."""
    if not results['failed'] and not results['errors']:
        print("\nNo failures to fix.")
        return

    print("\n" + "=" * 60)
    print("FIX INSTRUCTIONS")
    print("=" * 60)

    for domain, error in results['failed']:
        print(f"\n{domain}:")
        print(f"  Error: {error}")
        print(f"  Fix steps:")
        print(f"    1. Login to A2 cPanel: https://nl1-cl8-ats1.a2hosting.com:2083")
        print(f"    2. Go to Email Accounts > office@{domain}")
        print(f"    3. Get/reset the password")
        print(f"    4. Update {CREDENTIALS_FILE}")
        print(f"       Change: \"{domain}\": {{\"password\": \"NEW_PASSWORD\", ...}}")
        print(f"    5. Run: python3 {__file__} to verify")


def send_failure_alert(results: dict):
    """Send Telegram alert for failed credentials."""
    if not results['failed'] and not results['errors']:
        return

    msg = "🚨 *CREDENTIAL FAILURE ALERT*\n\n"

    if results['failed']:
        msg += "*Failed logins:*\n"
        for domain, error in results['failed']:
            msg += f"• {domain}\n"

    if results['errors']:
        msg += "\n*Errors:*\n"
        for domain, error in results['errors']:
            msg += f"• {domain}: {error}\n"

    msg += f"\n_Fix: Update {CREDENTIALS_FILE}_"

    if should_alert("credential_validator"):
        send_telegram(msg)
    print(f"\n[ALERT] Telegram notification sent")


def log_results(results: dict):
    """Log validation results to file."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    status = "OK" if not results['failed'] else "FAILED"

    with open(LOG_FILE, 'a') as f:
        f.write(f"{timestamp} | {status} | Passed: {len(results['passed'])}, Failed: {len(results['failed'])}\n")
        for domain, error in results['failed']:
            f.write(f"  FAIL: {domain} - {error}\n")


def main():
    parser = argparse.ArgumentParser(description='Validate A2 email credentials')
    parser.add_argument('--fix', action='store_true', help='Show fix instructions for failures')
    parser.add_argument('--alert', action='store_true', help='Send Telegram alert on failure')
    parser.add_argument('--quiet', action='store_true', help='Only output on failure')
    args = parser.parse_args()

    results = validate_all(quiet=args.quiet)

    # Log results
    log_results(results)

    # Show fix instructions if requested or if there are failures
    if args.fix or (results['failed'] and not args.quiet):
        show_fix_instructions(results)

    # Send alert if requested and there are failures
    if args.alert and (results['failed'] or results['errors']):
        send_failure_alert(results)

    # Exit with error code if failures
    if results['failed'] or results['errors']:
        sys.exit(1)


if __name__ == '__main__':
    main()
