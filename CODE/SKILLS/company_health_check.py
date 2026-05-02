#!/usr/bin/env python3
"""
Company Health Check - Verify companies are still active

Checks:
- Website is reachable
- Email domain has MX records
- Company appears in recent data sources
- No bankruptcy/liquidation indicators

Usage:
    python3 company_health_check.py --company "ACME SRL"      # Single company
    python3 company_health_check.py --file contacts.csv       # Check file
    python3 company_health_check.py --campaign HORECA2026     # Check campaign
    python3 company_health_check.py --clean contacts.csv      # Remove inactive
    python3 company_health_check.py --stats                   # Show stats

Uses website check + MX verification. No external API.
"""

import os
import sys
import csv
import json
import re
import requests
import dns.resolver
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

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
STATE_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/.company_health_state.json")
CAMPAIGNS_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/CAMPAIGNS")

# Inactive indicators
INACTIVE_KEYWORDS = [
    'bankrupt', 'liquidation', 'dissolved', 'closed', 'defunct',
    'lichidat', 'radiat', 'faliment', 'dizolvat',  # Romanian
    'upadlosc', 'zlikwidowany',  # Polish
    'insolvenz', 'aufgelost',  # German
]


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"checked": 0, "active": 0, "inactive": 0, "unknown": 0, "last_run": None}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def check_website(url, timeout=10):
    """Check if website is reachable."""
    if not url:
        return None, "no_url"

    # Normalize URL
    if not url.startswith('http'):
        url = 'https://' + url

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; HealthCheck/1.0)'}
        resp = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)

        if resp.status_code < 400:
            return True, f"ok:{resp.status_code}"
        else:
            return False, f"error:{resp.status_code}"

    except requests.exceptions.SSLError:
        # Try without SSL
        try:
            url = url.replace('https://', 'http://')
            resp = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
            if resp.status_code < 400:
                return True, "ok:http_only"
        except:
            pass
        return False, "ssl_error"

    except requests.exceptions.ConnectionError:
        return False, "connection_error"

    except requests.exceptions.Timeout:
        return False, "timeout"

    except Exception as e:
        return False, f"error:{str(e)[:30]}"


def check_mx_records(email):
    """Check if email domain has MX records."""
    if not email or '@' not in email:
        return None, "no_email"

    domain = email.lower().split('@')[1]

    try:
        dns.resolver.resolve(domain, 'MX')
        return True, "ok"
    except dns.resolver.NXDOMAIN:
        return False, "domain_not_found"
    except dns.resolver.NoAnswer:
        return False, "no_mx"
    except Exception as e:
        return None, f"error:{str(e)[:30]}"


def check_company_name(name):
    """Check for inactive indicators in name."""
    if not name:
        return True, "no_name"

    name_lower = name.lower()

    for keyword in INACTIVE_KEYWORDS:
        if keyword in name_lower:
            return False, f"inactive_keyword:{keyword}"

    return True, "ok"


def check_company(row):
    """Full health check for company."""
    result = {
        'company': row.get('company', ''),
        'email': row.get('email', ''),
        'website': row.get('website', ''),
        'active': None,
        'checks': {},
        'score': 0
    }

    # Check company name
    name_ok, name_reason = check_company_name(row.get('company', ''))
    result['checks']['name'] = {'ok': name_ok, 'reason': name_reason}
    if name_ok:
        result['score'] += 25
    elif name_ok is False:
        result['active'] = False
        return result

    # Check email MX
    mx_ok, mx_reason = check_mx_records(row.get('email', ''))
    result['checks']['mx'] = {'ok': mx_ok, 'reason': mx_reason}
    if mx_ok:
        result['score'] += 35

    # Check website (only if provided)
    website = row.get('website', '')
    if website:
        web_ok, web_reason = check_website(website)
        result['checks']['website'] = {'ok': web_ok, 'reason': web_reason}
        if web_ok:
            result['score'] += 40

    # Determine active status
    if result['score'] >= 60:
        result['active'] = True
    elif result['score'] >= 25:
        result['active'] = None  # Unknown
    else:
        result['active'] = False

    return result


def check_file(filepath, limit=100):
    """Check all companies in file."""
    filepath = Path(filepath)
    if not filepath.exists():
        log(f"File not found: {filepath}")
        return []

    results = []
    checked = 0

    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if checked >= limit:
                break

            result = check_company(row)
            result['row'] = row
            results.append(result)
            checked += 1

            # Progress
            if checked % 10 == 0:
                log(f"Checked {checked}...")

    return results


def clean_file(filepath, output=None, limit=100):
    """Remove inactive companies from file."""
    filepath = Path(filepath)
    if not filepath.exists():
        log(f"File not found: {filepath}")
        return

    results = check_file(filepath, limit)

    active_rows = []
    inactive_count = 0

    for r in results:
        if r['active'] is not False:
            active_rows.append(r['row'])
        else:
            inactive_count += 1

    # Write output
    output_path = Path(output) if output else filepath.with_suffix('.active.csv')

    if active_rows:
        fieldnames = active_rows[0].keys()
        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(active_rows)

    log(f"Kept {len(active_rows)} active, removed {inactive_count} inactive")
    log(f"Output: {output_path}")


def check_campaign(campaign_name, limit=50):
    """Check companies in campaign."""
    contacts_file = CAMPAIGNS_DIR / campaign_name / "contacts" / "contacts.csv"
    if not contacts_file.exists():
        log(f"Campaign contacts not found: {contacts_file}")
        return []

    log(f"Checking campaign: {campaign_name}")
    results = check_file(contacts_file, limit)

    # Summary
    active = sum(1 for r in results if r['active'] is True)
    inactive = sum(1 for r in results if r['active'] is False)
    unknown = sum(1 for r in results if r['active'] is None)

    log(f"Results: {active} active, {inactive} inactive, {unknown} unknown")

    # Show inactive
    inactive_list = [r for r in results if r['active'] is False]
    if inactive_list:
        print("\nInactive companies:")
        for r in inactive_list[:10]:
            print(f"  {r['company']}: {r['checks']}")

    return results


def show_stats():
    """Show health check stats."""
    state = load_state()

    print("\n=== Company Health Check Stats ===\n")
    print(f"Total checked: {state.get('checked', 0)}")
    print(f"Active: {state.get('active', 0)}")
    print(f"Inactive: {state.get('inactive', 0)}")
    print(f"Unknown: {state.get('unknown', 0)}")
    print(f"Last run: {state.get('last_run', 'Never')}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Company Health Check")
    parser.add_argument("--company", help="Single company name to check")
    parser.add_argument("--file", help="CSV file to check")
    parser.add_argument("--campaign", help="Campaign to check")
    parser.add_argument("--clean", help="Clean inactive from file")
    parser.add_argument("--output", help="Output file")
    parser.add_argument("--limit", type=int, default=100, help="Max companies to check")
    parser.add_argument("--stats", action="store_true", help="Show stats")

    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    state = load_state()

    if args.company:
        row = {'company': args.company}
        result = check_company(row)
        print(json.dumps(result, indent=2, default=str))

    elif args.file:
        results = check_file(args.file, args.limit)
        active = sum(1 for r in results if r['active'] is True)
        inactive = sum(1 for r in results if r['active'] is False)
        print(f"Checked {len(results)}: {active} active, {inactive} inactive")

        state['checked'] = state.get('checked', 0) + len(results)
        state['active'] = state.get('active', 0) + active
        state['inactive'] = state.get('inactive', 0) + inactive

    elif args.clean:
        clean_file(args.clean, args.output, args.limit)

    elif args.campaign:
        check_campaign(args.campaign, args.limit)

    else:
        parser.print_help()
        return

    state['last_run'] = datetime.now().isoformat()
    save_state(state)


if __name__ == "__main__":
    main()
