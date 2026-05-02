#!/usr/bin/env python3
"""
Brevo Campaign Manager - Start, stop, and monitor all brevo campaigns.

Usage:
    python3 brevo_manager.py status          # Show all campaign status
    python3 brevo_manager.py start [NAME]    # Start campaign(s)
    python3 brevo_manager.py stop [NAME]     # Stop campaign(s)
    python3 brevo_manager.py run NAME        # Run single campaign (foreground)
    python3 brevo_manager.py fix             # Fix common issues
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import json
import subprocess
import signal
from datetime import datetime
from pathlib import Path

CAMPAIGNS = {
    'BUILDJOBS': 'brevo_buildjobs.py',
    'FACTORYJOBS': 'brevo_factoryjobs.py',
    'WAREHOUSEWORKERS': 'brevo_warehouseworkers.py',
    'CAREWORKERS': 'brevo_careworkers.py',
    'CUMPARLEGUME': 'brevo_cumparlegume.py',
    'CIFN': 'brevo_cifn.py',
    'MIVROMANIA': 'brevo_mivromania.py',
}

SKILLS_DIR = Path('/opt/ACTIVE/INFRA/SKILLS')
STATE_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/brevo_state')


def get_campaign_status(name):
    """Get status for a single campaign."""
    script = CAMPAIGNS.get(name)
    if not script:
        return {'error': f'Unknown campaign: {name}'}

    state_file = STATE_DIR / f'{name}_state.json'

    # Load state
    state = {'sent': [], 'sent_today': 0, 'last_send': None}
    if state_file.exists():
        try:
            state = json.load(open(state_file))
        except:
            pass

    # Get remaining (from --status)
    remaining = None
    try:
        result = subprocess.run(
            ['python3', str(SKILLS_DIR / script), '--status'],
            capture_output=True, text=True, timeout=30
        )
        for line in result.stdout.split('\n'):
            if 'Remaining:' in line:
                remaining = int(line.split(':')[1].strip().split()[0])
                break
    except:
        pass

    # Check if running
    running = False
    try:
        result = subprocess.run(['pgrep', '-f', script], capture_output=True)
        running = result.returncode == 0
    except:
        pass

    return {
        'name': name,
        'script': script,
        'sent': len(state.get('sent', [])),
        'sent_today': state.get('sent_today', 0),
        'last_send': state.get('last_send'),
        'remaining': remaining,
        'running': running,
    }


def show_status(campaign=None):
    """Show status for all or specific campaign."""
    print(f"\n{'='*60}")
    print(f"BREVO CAMPAIGN STATUS - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    campaigns = [campaign] if campaign else CAMPAIGNS.keys()

    print(f"{'Campaign':<18} {'Sent':>6} {'Today':>6} {'Left':>8} {'Running':>8}")
    print(f"{'-'*18} {'-'*6} {'-'*6} {'-'*8} {'-'*8}")

    for name in campaigns:
        if name not in CAMPAIGNS:
            print(f"{name}: Unknown campaign")
            continue

        status = get_campaign_status(name)
        running = 'YES' if status['running'] else 'no'
        remaining = str(status['remaining']) if status['remaining'] is not None else '?'

        print(f"{name:<18} {status['sent']:>6} {status['sent_today']:>6} {remaining:>8} {running:>8}")

    print()


def start_campaign(name):
    """Start a campaign in background."""
    if name not in CAMPAIGNS:
        print(f"Unknown campaign: {name}")
        return False

    script = CAMPAIGNS[name]
    script_path = SKILLS_DIR / script
    log_path = Path(f'/tmp/{name.lower()}_log.txt')

    # Check if already running
    result = subprocess.run(['pgrep', '-f', script], capture_output=True)
    if result.returncode == 0:
        print(f"{name}: Already running")
        return False

    # Start in background
    cmd = f"nohup python3 {script_path} > {log_path} 2>&1 &"
    subprocess.run(cmd, shell=True, cwd=SKILLS_DIR)
    print(f"{name}: Started (log: {log_path})")
    return True


def stop_campaign(name):
    """Stop a running campaign."""
    if name not in CAMPAIGNS:
        print(f"Unknown campaign: {name}")
        return False

    script = CAMPAIGNS[name]
    result = subprocess.run(['pkill', '-f', script], capture_output=True)
    if result.returncode == 0:
        print(f"{name}: Stopped")
        return True
    else:
        print(f"{name}: Not running")
        return False


def start_all():
    """Start all campaigns that aren't running."""
    for name in CAMPAIGNS:
        status = get_campaign_status(name)
        if not status['running'] and (status['remaining'] or 0) > 0:
            start_campaign(name)


def stop_all():
    """Stop all running campaigns."""
    for name in CAMPAIGNS:
        stop_campaign(name)


def fix_common_issues():
    """Fix common campaign issues."""
    print("Checking and fixing common issues...\n")

    fixed = 0

    # 1. Kill zombie processes (multiple instances)
    for name, script in CAMPAIGNS.items():
        result = subprocess.run(['pgrep', '-f', script], capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            if len(pids) > 1:
                print(f"{name}: Multiple instances ({len(pids)}), killing extras...")
                for pid in pids[1:]:
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        fixed += 1
                    except:
                        pass

    # 2. Create missing state directories
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    # 3. Start campaigns with contacts that aren't running
    for name in CAMPAIGNS:
        status = get_campaign_status(name)
        remaining = status.get('remaining') or 0
        if not status['running'] and remaining > 0 and status['sent_today'] < 290:
            print(f"{name}: Has {remaining} contacts, starting...")
            start_campaign(name)
            fixed += 1

    print(f"\nFixed {fixed} issues")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Brevo Campaign Manager")
    parser.add_argument('action', choices=['status', 'start', 'stop', 'run', 'fix'],
                        help='Action to perform')
    parser.add_argument('campaign', nargs='?', help='Campaign name (optional)')
    parser.add_argument('--all', action='store_true', help='Apply to all campaigns')
    args = parser.parse_args()

    if args.action == 'status':
        show_status(args.campaign.upper() if args.campaign else None)

    elif args.action == 'start':
        if args.all or not args.campaign:
            start_all()
        else:
            start_campaign(args.campaign.upper())

    elif args.action == 'stop':
        if args.all or not args.campaign:
            stop_all()
        else:
            stop_campaign(args.campaign.upper())

    elif args.action == 'run':
        if not args.campaign:
            print("Specify campaign name")
            sys.exit(1)
        name = args.campaign.upper()
        if name not in CAMPAIGNS:
            print(f"Unknown: {name}")
            sys.exit(1)
        script = SKILLS_DIR / CAMPAIGNS[name]
        os.execv(sys.executable, ['python3', str(script)])

    elif args.action == 'fix':
        fix_common_issues()


if __name__ == '__main__':
    main()
