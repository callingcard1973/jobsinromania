#!/usr/bin/env python3
"""
MADR Land Alerts Management Skill

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/madr_alerts.py status
    python3 /opt/ACTIVE/INFRA/SKILLS/madr_alerts.py run
    python3 /opt/ACTIVE/INFRA/SKILLS/madr_alerts.py test
    python3 /opt/ACTIVE/INFRA/SKILLS/madr_alerts.py subscribe <email> [small|large|xl]
    python3 /opt/ACTIVE/INFRA/SKILLS/madr_alerts.py subscribers
"""

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

BASE = Path("/opt/ACTIVE/SCRAPERS/ROMANIA/MADR")
STATE_FILE = BASE / "DATA/alert_state.json"
SUBSCRIBERS_FILE = BASE / "CODE/alert_subscribers.json"
ALERT_SCRIPT = BASE / "CODE/land_alerts_v2.py"


def status():
    """Show alert system status."""
    print("=== MADR LAND ALERTS STATUS ===\n")

    # State
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())
        last_check = state.get('last_check', 'Never')
        last_run = state.get('last_run', {})
        counts = last_run.get('counts', {})

        print(f"Last check: {last_check}")
        print(f"Last run: {last_run.get('timestamp', 'N/A')}")
        print(f"Counts: Small={counts.get('small', 0)}, Large={counts.get('large', 0)}, XL={counts.get('xl', 0)}")
    else:
        print("No state file - alerts not yet run")

    print()

    # Subscribers
    if SUBSCRIBERS_FILE.exists():
        subs = json.loads(SUBSCRIBERS_FILE.read_text())
        print("Subscribers:")
        for category, data in subs.items():
            if category != 'counties':
                emails = data.get('email', [])
                print(f"  {category}: {len(emails)} emails")
    else:
        print("No subscribers configured")

    print()

    # Cron
    result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
    cron_line = [l for l in result.stdout.split('\n') if 'run_alerts' in l]
    if cron_line:
        print(f"Cron: {cron_line[0]}")
    else:
        print("Cron: NOT CONFIGURED")


def run():
    """Run alerts now."""
    print("Running alerts...")
    subprocess.run([sys.executable, str(ALERT_SCRIPT)])


def test():
    """Test alerts with recent data."""
    print("Testing alerts (last 7 days)...")
    subprocess.run([sys.executable, str(ALERT_SCRIPT), '--test'])


def subscribe(email, category='all'):
    """Add email subscriber."""
    if not SUBSCRIBERS_FILE.exists():
        subs = {"small_plots": {"email": []}, "large_plots": {"email": []}, "xl_plots": {"email": []}}
    else:
        subs = json.loads(SUBSCRIBERS_FILE.read_text())

    categories = ['small_plots', 'large_plots', 'xl_plots'] if category == 'all' else [f'{category}_plots']

    for cat in categories:
        if cat in subs and email not in subs[cat].get('email', []):
            if 'email' not in subs[cat]:
                subs[cat]['email'] = []
            subs[cat]['email'].append(email)
            print(f"Added {email} to {cat}")

    SUBSCRIBERS_FILE.write_text(json.dumps(subs, indent=2))
    print("Saved")


def subscribers():
    """List all subscribers."""
    if not SUBSCRIBERS_FILE.exists():
        print("No subscribers")
        return

    subs = json.loads(SUBSCRIBERS_FILE.read_text())
    print("=== SUBSCRIBERS ===\n")
    for category, data in subs.items():
        if category != 'counties':
            print(f"{category}:")
            for email in data.get('email', []):
                print(f"  - {email}")
            print()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == 'status':
        status()
    elif cmd == 'run':
        run()
    elif cmd == 'test':
        test()
    elif cmd == 'subscribe':
        email = sys.argv[2] if len(sys.argv) > 2 else None
        category = sys.argv[3] if len(sys.argv) > 3 else 'all'
        if email:
            subscribe(email, category)
        else:
            print("Usage: subscribe <email> [small|large|xl|all]")
    elif cmd == 'subscribers':
        subscribers()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
