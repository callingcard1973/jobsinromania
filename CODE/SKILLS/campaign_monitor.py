#!/usr/bin/env python3
"""
Campaign Monitor - Alerts when campaigns fail to send.

Checks all brevo campaigns and alerts if:
1. Campaign didn't send when scheduled
2. Contact pool exhausted
3. API issues detected

Schedule: Run after all campaigns should have completed (e.g., 12:00)
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import json
import subprocess
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

# Try to import alerting, fall back to print
try:
    from alerting import send_telegram
    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False
    def send_telegram(msg, chat_id=None):
        print(f"[TELEGRAM] {msg}")

TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_ALERT_CHAT_ID', '547047851')

# Campaign definitions with schedules
CAMPAIGNS = {
    'BUILDJOBS': {
        'script': 'brevo_buildjobs.py',
        'schedule': '10:00',
        'state_file': '/opt/ACTIVE/OPENDATA/DATA/brevo_state/BUILDJOBS_state.json',
        'min_contacts': 100,
    },
    'FACTORYJOBS': {
        'script': 'brevo_factoryjobs.py',
        'schedule': '10:30',
        'state_file': '/opt/ACTIVE/OPENDATA/DATA/brevo_state/FACTORYJOBS_state.json',
        'min_contacts': 100,
    },
    'WAREHOUSEWORKERS': {
        'script': 'brevo_warehouseworkers.py',
        'schedule': '11:00',
        'state_file': '/opt/ACTIVE/OPENDATA/DATA/brevo_state/WAREHOUSEWORKERS_state.json',
        'min_contacts': 100,
    },
    'CAREWORKERS': {
        'script': 'brevo_careworkers.py',
        'schedule': '09:40',
        'state_file': '/opt/ACTIVE/OPENDATA/DATA/brevo_state/CAREWORKERS_state.json',
        'min_contacts': 20,
    },
    'CUMPARLEGUME': {
        'script': 'brevo_cumparlegume.py',
        'schedule': '09:20',
        'state_file': '/opt/ACTIVE/OPENDATA/DATA/brevo_state/CUMPARLEGUME_state.json',
        'min_contacts': 50,
    },
    'CIFN': {
        'script': 'brevo_cifn.py',
        'schedule': '09:50',
        'state_file': '/opt/ACTIVE/OPENDATA/DATA/brevo_state/CIFN_state.json',
        'min_contacts': 50,
    },
    'MIVROMANIA': {
        'script': 'brevo_mivromania.py',
        'schedule': '11:30',
        'state_file': '/opt/ACTIVE/OPENDATA/DATA/brevo_state/MIVROMANIA_state.json',
        'min_contacts': 100,
    },
}


def load_state(state_file):
    """Load campaign state file."""
    try:
        if Path(state_file).exists():
            with open(state_file) as f:
                return json.load(f)
    except Exception:
        pass
    return {"sent": [], "last_send": None, "sent_today": 0}


def get_remaining_contacts(script):
    """Get remaining contacts count from script --status."""
    try:
        result = subprocess.run(
            ['python3', f'/opt/ACTIVE/INFRA/SKILLS/{script}', '--status'],
            capture_output=True, text=True, timeout=60
        )
        for line in result.stdout.split('\n'):
            if 'Remaining:' in line:
                # Extract number from "Remaining: 123" or "Remaining: 123 (text)"
                parts = line.split(':')[1].strip().split()
                return int(parts[0])
    except Exception:
        pass
    return None


def check_campaign(name, config):
    """Check a single campaign and return issues."""
    issues = []
    today = datetime.now().strftime('%Y-%m-%d')

    state = load_state(config['state_file'])
    last_send = state.get('last_send')
    sent_today = state.get('sent_today', 0)

    # Check if sent today
    if last_send != today:
        issues.append(f"Did not send today (last: {last_send or 'never'})")
    elif sent_today == 0:
        issues.append("Sent 0 emails today")

    # Check remaining contacts
    remaining = get_remaining_contacts(config['script'])
    if remaining is not None:
        if remaining == 0:
            issues.append("EXHAUSTED - 0 contacts remaining")
        elif remaining < config['min_contacts']:
            issues.append(f"LOW - only {remaining} contacts remaining")

    return {
        'name': name,
        'schedule': config['schedule'],
        'last_send': last_send,
        'sent_today': sent_today,
        'remaining': remaining,
        'issues': issues,
    }


def run_check(alert=True, verbose=False):
    """Run full campaign check."""
    print(f"\n{'='*50}")
    print(f"CAMPAIGN MONITOR - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    results = []
    critical = []
    warnings = []
    ok = []

    for name, config in CAMPAIGNS.items():
        result = check_campaign(name, config)
        results.append(result)

        if result['issues']:
            if 'EXHAUSTED' in str(result['issues']) or 'Did not send' in str(result['issues']):
                critical.append(result)
            else:
                warnings.append(result)
        else:
            ok.append(result)

    # Print results
    if critical:
        print("CRITICAL:")
        for r in critical:
            print(f"  {r['name']}: {', '.join(r['issues'])}")
            print(f"    Schedule: {r['schedule']}, Today: {r['sent_today']}, Remaining: {r['remaining']}")

    if warnings:
        print("\nWARNINGS:")
        for r in warnings:
            print(f"  {r['name']}: {', '.join(r['issues'])}")

    if ok:
        print("\nOK:")
        for r in ok:
            print(f"  {r['name']}: sent {r['sent_today']} today, {r['remaining']} remaining")

    # Send alert if critical issues
    if critical and alert:
        msg_lines = [f"CAMPAIGN ALERT - {datetime.now().strftime('%H:%M')}"]
        for r in critical:
            msg_lines.append(f"\n{r['name']}: {', '.join(r['issues'])}")

        if warnings:
            msg_lines.append(f"\n\n{len(warnings)} warnings")

        msg = '\n'.join(msg_lines)
        send_telegram(msg, chat_id=TELEGRAM_CHAT_ID)
        print(f"\nAlert sent to Telegram")

    # Summary
    print(f"\n{'='*50}")
    print(f"Summary: {len(critical)} critical, {len(warnings)} warnings, {len(ok)} ok")
    print(f"{'='*50}")

    return len(critical) == 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Campaign Monitor")
    parser.add_argument('--no-alert', action='store_true', help='Suppress Telegram alerts')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    args = parser.parse_args()

    success = run_check(alert=not args.no_alert, verbose=args.verbose)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
