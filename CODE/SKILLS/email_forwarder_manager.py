#!/usr/bin/env python3
"""
Email Forwarder Manager for A2 Hosting
Checks and configures email forwarders for campaign domains.
[AI: Claude Code]

Usage:
    python3 email_forwarder_manager.py --status          # Check all domains
    python3 email_forwarder_manager.py --check domain    # Check specific domain
    python3 email_forwarder_manager.py --add domain      # Add forwarder
    python3 email_forwarder_manager.py --fix-all         # Fix missing forwarders
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Default forward destination
DEFAULT_FORWARD_TO = "manpower.dristor@gmail.com"

# Campaign domains and their office emails
CAMPAIGN_DOMAINS = {
    'nepalezi.com': {'office': 'office@nepalezi.com', 'campaign': 'NORWAY'},
    'cifn.info': {'office': 'office@cifn.info', 'campaign': 'CIFN_NEPAL'},
    'careworkers.eu': {'office': 'office@careworkers.eu', 'campaign': 'CAREWORKERS'},
    'warehouseworkers.eu': {'office': 'office@warehouseworkers.eu', 'campaign': 'WAREHOUSE'},
    'mivromania.info': {'office': 'office@mivromania.info', 'campaign': 'HORECA2026'},
    'mivromania.online': {'office': 'office@mivromania.online', 'campaign': 'TOURISM_RO'},
    'buildjobs.eu': {'office': 'office@buildjobs.eu', 'campaign': 'FACTORY_EU'},
    'factoryjobs.eu': {'office': 'office@factoryjobs.eu', 'campaign': 'TRANSPORT_EU'},
    'expatsinromania.org': {'office': 'office@expatsinromania.org', 'campaign': 'POLAND_AGENCIES'},
    'interjob.ro': {'office': 'office@interjob.ro', 'campaign': 'ANOFM'},
}

# A2 Hosting config
A2_HOST = "nl1-cl8-ats1.a2hosting.com"
A2_USER = "loaiidil"
A2_PORT = 7822


def load_a2_config() -> Dict:
    """Load A2 Hosting configuration."""
    config = {
        'host': A2_HOST,
        'user': A2_USER,
        'port': A2_PORT,
        'token': None
    }

    env_file = Path.home() / '.a2hosting.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    if key == 'A2_CPANEL_TOKEN':
                        config['token'] = value

    return config


def ssh_command(cmd: str, timeout: int = 30) -> Tuple[bool, str]:
    """Execute SSH command on A2 Hosting."""
    ssh_cmd = [
        'ssh', '-p', str(A2_PORT),
        '-o', 'ConnectTimeout=10',
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'BatchMode=yes',
        f'{A2_USER}@{A2_HOST}',
        cmd
    ]

    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            return True, result.stdout
        return False, result.stderr
    except subprocess.TimeoutExpired:
        return False, "SSH timeout"
    except Exception as e:
        return False, str(e)


def get_forwarders_ssh() -> Dict[str, List[Dict]]:
    """Get email forwarders via SSH."""
    success, output = ssh_command('uapi --output=json Email list_forwarders')

    if not success:
        return {'error': output}

    try:
        data = json.loads(output)
        fwds = data.get('result', {}).get('data', [])

        by_domain = {}
        for f in fwds:
            domain = f.get('domain', 'unknown')
            if domain not in by_domain:
                by_domain[domain] = []
            by_domain[domain].append({
                'from': f.get('dest', ''),
                'to': f.get('forward', '')
            })

        return by_domain
    except json.JSONDecodeError as e:
        return {'error': f'JSON parse error: {e}'}


def add_forwarder_ssh(email: str, forward_to: str) -> Tuple[bool, str]:
    """Add email forwarder via SSH."""
    domain = email.split('@')[1]
    cmd = f'uapi Email add_forwarder domain={domain} email={email} fwdopt=fwd fwdemail={forward_to}'
    return ssh_command(cmd)


def check_domain_status(domain: str, forwarders: Dict) -> Dict:
    """Check if domain has correct forwarder setup."""
    info = CAMPAIGN_DOMAINS.get(domain, {})
    office_email = info.get('office', f'office@{domain}')

    result = {
        'domain': domain,
        'office_email': office_email,
        'campaign': info.get('campaign', 'Unknown'),
        'has_forwarder': False,
        'forwards_to_gmail': False,
        'forward_destination': None,
        'status': 'MISSING'
    }

    if domain in forwarders:
        for fw in forwarders[domain]:
            if fw['from'].lower() == office_email.lower():
                result['has_forwarder'] = True
                result['forward_destination'] = fw['to']

                if 'manpower.dristor' in fw['to'].lower():
                    result['forwards_to_gmail'] = True
                    result['status'] = 'OK'
                else:
                    result['status'] = 'WRONG_DEST'
                break

    return result


def print_status_report(results: List[Dict]):
    """Print formatted status report."""
    print("\n=== EMAIL FORWARDER STATUS ===\n")

    ok_count = 0
    missing_count = 0
    wrong_count = 0

    for r in results:
        status = r['status']
        if status == 'OK':
            mark = 'OK'
            ok_count += 1
        elif status == 'MISSING':
            mark = 'MISSING'
            missing_count += 1
        else:
            mark = 'WRONG'
            wrong_count += 1

        print(f"[{mark:7}] {r['domain']:25} ({r['campaign']})")
        if r['has_forwarder']:
            print(f"          {r['office_email']} -> {r['forward_destination']}")
        else:
            print(f"          {r['office_email']} -> (no forwarder)")
        print()

    print("=== SUMMARY ===")
    print(f"OK:      {ok_count}")
    print(f"Missing: {missing_count}")
    print(f"Wrong:   {wrong_count}")

    if missing_count > 0 or wrong_count > 0:
        print(f"\nTo fix: python3 {__file__} --fix-all")


def main():
    parser = argparse.ArgumentParser(description='Email Forwarder Manager')
    parser.add_argument('--status', action='store_true', help='Check all domain forwarders')
    parser.add_argument('--check', type=str, help='Check specific domain')
    parser.add_argument('--add', type=str, help='Add forwarder for domain')
    parser.add_argument('--fix-all', action='store_true', help='Fix all missing forwarders')
    parser.add_argument('--forward-to', type=str, default=DEFAULT_FORWARD_TO, help='Forward destination')
    parser.add_argument('--manual', action='store_true', help='Show manual cPanel instructions')
    args = parser.parse_args()

    if args.manual:
        print_manual_instructions()
        return

    if args.status or not any([args.check, args.add, args.fix_all]):
        # Get forwarders
        print("Fetching forwarders from A2 Hosting...")
        forwarders = get_forwarders_ssh()

        if 'error' in forwarders:
            print(f"\nError: {forwarders['error']}")
            print("\nSSH connection failed. Use --manual for cPanel instructions.")
            print_manual_instructions()
            return

        # Check each domain
        results = []
        for domain in CAMPAIGN_DOMAINS:
            result = check_domain_status(domain, forwarders)
            results.append(result)

        print_status_report(results)

    elif args.check:
        forwarders = get_forwarders_ssh()
        if 'error' in forwarders:
            print(f"Error: {forwarders['error']}")
            return

        result = check_domain_status(args.check, forwarders)
        print(f"\nDomain: {result['domain']}")
        print(f"Office: {result['office_email']}")
        print(f"Campaign: {result['campaign']}")
        print(f"Status: {result['status']}")
        if result['forward_destination']:
            print(f"Forwards to: {result['forward_destination']}")

    elif args.add:
        domain = args.add
        if domain not in CAMPAIGN_DOMAINS:
            print(f"Warning: {domain} not in campaign domains list")

        office_email = CAMPAIGN_DOMAINS.get(domain, {}).get('office', f'office@{domain}')
        print(f"Adding forwarder: {office_email} -> {args.forward_to}")

        success, output = add_forwarder_ssh(office_email, args.forward_to)
        if success:
            print("Forwarder added successfully!")
        else:
            print(f"Error: {output}")

    elif args.fix_all:
        forwarders = get_forwarders_ssh()
        if 'error' in forwarders:
            print(f"Error: {forwarders['error']}")
            print("\nUse --manual for cPanel instructions.")
            return

        for domain, info in CAMPAIGN_DOMAINS.items():
            result = check_domain_status(domain, forwarders)
            if result['status'] != 'OK':
                office_email = info['office']
                print(f"Fixing: {office_email} -> {args.forward_to}")
                success, output = add_forwarder_ssh(office_email, args.forward_to)
                if success:
                    print(f"  OK")
                else:
                    print(f"  Error: {output}")


def print_manual_instructions():
    """Print manual cPanel instructions."""
    print("""
=== MANUAL CPANEL INSTRUCTIONS ===

Since SSH is not available, configure forwarders manually in cPanel:

1. Login to cPanel: https://nl1-cl8-ats1.a2hosting.com:2083
   Username: loaiidil

2. Go to: Email > Forwarders

3. For each domain below, click "Add Forwarder":

   DOMAINS TO CONFIGURE:
   ---------------------
""")

    for domain, info in CAMPAIGN_DOMAINS.items():
        print(f"   {info['office']:35} -> {DEFAULT_FORWARD_TO}")

    print(f"""
4. For each forwarder:
   - Address to Forward: office
   - Domain: (select domain)
   - Forward to Email Address: {DEFAULT_FORWARD_TO}
   - Click "Add Forwarder"

5. Verify by sending test emails to each office@ address.

=== ALTERNATIVE: FreeScout ===

FreeScout at http://raspibig:8087 already handles incoming emails.
Check if mailboxes are configured there instead.
""")


if __name__ == '__main__':
    main()
