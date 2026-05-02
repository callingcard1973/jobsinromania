#!/usr/bin/env python3
"""
Campaign Verification Skill

Automatically verifies email campaigns have proper setup:
- nohup (survives logout)
- Resume from where left off (state tracking)
- Dedup (skip already sent)
- Email rules (SenderRules validation)
- Bounce handling

Usage:
    python3 campaign_verify.py                    # Check all running campaigns
    python3 campaign_verify.py /path/to/sender.py # Check specific script
    python3 campaign_verify.py --campaign TOURISM_RO
"""

import sys
import os
import re
import json
import subprocess
from pathlib import Path
from datetime import datetime

# Required patterns in campaign scripts
REQUIRED_PATTERNS = {
    'state_tracking': [
        r'state.*=.*load_state|json\.load.*state',
        r'save_state|json\.dump.*state'
    ],
    'dedup': [
        r'sent_emails.*=.*set|set\(.*sent',
        r'if.*email.*not.*in.*sent|email.*not.*sent_emails'
    ],
    'email_rules': [
        r'from email_sender_rules import|SenderRules',
        r'check_send_allowed'
    ],
    'bounce_handling': [
        r'handle_send_result'
    ],
    'daily_limit': [
        r'DAILY_LIMIT|daily_limit|daily_sent'
    ],
    'delay': [
        r'DELAY_SECONDS|time\.sleep'
    ]
}

# Campaign directories to scan
CAMPAIGN_DIRS = [
    '/opt/ACTIVE/EMAIL/CAMPAIGNS',
]


def check_script(script_path: str) -> dict:
    """Check a campaign script for required patterns."""
    results = {
        'script': script_path,
        'exists': False,
        'checks': {},
        'issues': [],
        'warnings': []
    }

    if not os.path.exists(script_path):
        results['issues'].append(f"Script not found: {script_path}")
        return results

    results['exists'] = True

    with open(script_path, 'r') as f:
        content = f.read()

    # Check each required pattern
    for check_name, patterns in REQUIRED_PATTERNS.items():
        found = False
        for pattern in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                found = True
                break
        results['checks'][check_name] = found
        if not found:
            results['issues'].append(f"Missing: {check_name}")

    # Additional checks
    if 'nohup' not in content and 'background' not in content.lower():
        results['warnings'].append("Script doesn't mention nohup - ensure running with nohup")

    # Check for hardcoded paths
    if 'CONTACTS_FILE' in content or 'contacts' in content.lower():
        results['checks']['contacts_file'] = True

    if 'TEMPLATE_FILE' in content or 'template' in content.lower():
        results['checks']['template_file'] = True

    return results


def check_running_campaigns() -> list:
    """Check currently running campaign processes."""
    result = subprocess.run(
        ['ps', 'aux'],
        capture_output=True,
        text=True
    )

    campaigns = []
    for line in result.stdout.split('\n'):
        if 'python' in line and ('send_' in line or 'campaign' in line.lower()):
            if 'grep' not in line:
                # Extract PID and command
                parts = line.split()
                if len(parts) >= 11:
                    pid = parts[1]
                    cmd = ' '.join(parts[10:])
                    campaigns.append({
                        'pid': pid,
                        'command': cmd,
                        'running': True
                    })

    return campaigns


def check_state_file(state_path: str) -> dict:
    """Check campaign state file."""
    results = {
        'path': state_path,
        'exists': False,
        'sent_count': 0,
        'daily_sent': 0,
        'last_date': None
    }

    if not os.path.exists(state_path):
        return results

    results['exists'] = True

    try:
        with open(state_path) as f:
            state = json.load(f)

        results['sent_count'] = len(state.get('sent', state.get('sent_emails', [])))
        results['daily_sent'] = state.get('daily_sent', 0)
        results['last_date'] = state.get('last_date', state.get('last_send', 'N/A'))
    except Exception as e:
        results['error'] = str(e)

    return results


def find_campaign_scripts(campaign_dir: str = None) -> list:
    """Find all campaign sender scripts."""
    scripts = []

    dirs = [campaign_dir] if campaign_dir else CAMPAIGN_DIRS

    for base_dir in dirs:
        if not os.path.exists(base_dir):
            continue

        for root, _, files in os.walk(base_dir):
            for f in files:
                if f.endswith('.py') and ('send' in f.lower() or 'sender' in f.lower()):
                    scripts.append(os.path.join(root, f))

    return scripts


def verify_campaign(script_path: str) -> dict:
    """Full verification of a campaign."""
    result = {
        'script': script_path,
        'timestamp': datetime.now().isoformat(),
        'script_check': check_script(script_path),
        'state_check': None,
        'running': False,
        'pid': None,
        'overall': 'UNKNOWN'
    }

    # Find state file
    script_dir = os.path.dirname(script_path)
    script_name = os.path.basename(script_path).replace('.py', '')

    # Common state file patterns
    state_patterns = [
        os.path.join(script_dir, 'state.json'),
        os.path.join(script_dir, f'state_{script_name}.json'),
        os.path.join(script_dir, f'.{script_name}_state.json'),
    ]

    for state_path in state_patterns:
        if os.path.exists(state_path):
            result['state_check'] = check_state_file(state_path)
            break

    # Check if running
    running = check_running_campaigns()
    for proc in running:
        if script_name in proc['command'] or os.path.basename(script_path) in proc['command']:
            result['running'] = True
            result['pid'] = proc['pid']
            break

    # Determine overall status
    checks = result['script_check']['checks']
    issues = result['script_check']['issues']

    if not result['script_check']['exists']:
        result['overall'] = 'ERROR'
    elif len(issues) > 2:
        result['overall'] = 'FAIL'
    elif len(issues) > 0:
        result['overall'] = 'WARN'
    else:
        result['overall'] = 'PASS'

    return result


def print_report(results: list):
    """Print verification report."""
    print("=" * 60)
    print("CAMPAIGN VERIFICATION REPORT")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    for r in results:
        script_name = os.path.basename(r['script'])
        status = r['overall']
        status_icon = {'PASS': '✓', 'WARN': '⚠', 'FAIL': '✗', 'ERROR': '!', 'UNKNOWN': '?'}

        print(f"\n{status_icon.get(status, '?')} {script_name} [{status}]")
        print(f"  Path: {r['script']}")

        if r['running']:
            print(f"  Running: Yes (PID {r['pid']})")
        else:
            print(f"  Running: No")

        # Script checks
        checks = r['script_check']['checks']
        print(f"  Checks:")
        for check, passed in checks.items():
            icon = '✓' if passed else '✗'
            print(f"    {icon} {check}")

        # State
        if r['state_check']:
            state = r['state_check']
            if state['exists']:
                print(f"  State: {state['sent_count']} sent, {state['daily_sent']} today")
            else:
                print(f"  State: No state file found")

        # Issues
        if r['script_check']['issues']:
            print(f"  Issues:")
            for issue in r['script_check']['issues']:
                print(f"    - {issue}")

        # Warnings
        if r['script_check']['warnings']:
            print(f"  Warnings:")
            for warn in r['script_check']['warnings']:
                print(f"    - {warn}")

    print("\n" + "=" * 60)

    # Summary
    passed = sum(1 for r in results if r['overall'] == 'PASS')
    warned = sum(1 for r in results if r['overall'] == 'WARN')
    failed = sum(1 for r in results if r['overall'] in ['FAIL', 'ERROR'])

    print(f"Summary: {passed} passed, {warned} warnings, {failed} failed")
    print("=" * 60)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Verify email campaign setup')
    parser.add_argument('script', nargs='?', help='Specific script to check')
    parser.add_argument('--campaign', '-c', help='Campaign directory name')
    parser.add_argument('--all', '-a', action='store_true', help='Check all campaigns')
    parser.add_argument('--json', '-j', action='store_true', help='Output as JSON')

    args = parser.parse_args()

    results = []

    if args.script:
        # Check specific script
        results.append(verify_campaign(args.script))
    elif args.campaign:
        # Check specific campaign
        campaign_dir = f'/opt/ACTIVE/EMAIL/CAMPAIGNS/{args.campaign}'
        scripts = find_campaign_scripts(campaign_dir)
        for script in scripts:
            results.append(verify_campaign(script))
    else:
        # Check running campaigns or all
        running = check_running_campaigns()
        if running and not args.all:
            # Check only running campaigns
            for proc in running:
                # Extract script path from command
                cmd = proc['command']
                for part in cmd.split():
                    if part.endswith('.py') and os.path.exists(part):
                        results.append(verify_campaign(part))
                        break

        if not results or args.all:
            # Check all campaign scripts
            scripts = find_campaign_scripts()
            for script in scripts:
                results.append(verify_campaign(script))

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print_report(results)

    # Exit code based on results
    if any(r['overall'] in ['FAIL', 'ERROR'] for r in results):
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
