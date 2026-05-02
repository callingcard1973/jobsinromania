#!/usr/bin/env python3
"""
Campaign Capacity Monitor - Alert when contacts running low.
Warns when less than 3 days worth of contacts remain.
"""
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from alerting import send_telegram

EMAIL_DIR = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS')
DAILY_RATES = {
    'FACTORY_EU': 290,
    'POLAND_AGENCIES': 290,
    'TOURISM_RO': 290,
    'CAREWORKERS': 290,
    'BUILDJOBS': 290,
    'HORECA2026': 290,
}
WARNING_DAYS = 3
CRITICAL_DAYS = 1

def count_remaining(campaign_dir):
    """Count unsent contacts in campaign."""
    # Check multiple possible state files
    state_files = [
        campaign_dir / 'state.json',
        campaign_dir / '.state.json',
    ]
    # Also check for sender-specific state files
    for f in campaign_dir.glob('.*_state.json'):
        state_files.append(f)

    # Check multiple possible contact directories
    contacts_dirs = [
        campaign_dir / 'contacts',
        campaign_dir / 'segments',
    ]

    # Count total contacts from CSV files
    total = 0
    for contacts_dir in contacts_dirs:
        if contacts_dir.exists():
            for csv_file in contacts_dir.glob('*.csv'):
                # Skip backup files
                if '.bak.' in csv_file.name:
                    continue
                try:
                    with open(csv_file, 'r') as f:
                        total += sum(1 for line in f) - 1  # Minus header
                except:
                    pass

    # Get sent count from state (check all state files)
    sent = 0
    for state_file in state_files:
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text())
                # Different formats
                if 'sent_count' in state:
                    sent = max(sent, state.get('sent_count', 0))
                elif 'sent_emails' in state:
                    sent = max(sent, len(state.get('sent_emails', [])))
            except:
                pass

    return max(0, total - sent)

def check_capacities():
    """Check all campaigns for low capacity."""
    low = []
    critical = []
    status = []

    for campaign, daily_rate in DAILY_RATES.items():
        campaign_dir = EMAIL_DIR / campaign
        if not campaign_dir.exists():
            continue

        remaining = count_remaining(campaign_dir)
        days_left = remaining / daily_rate if daily_rate > 0 else 0

        status.append({
            'campaign': campaign,
            'remaining': remaining,
            'daily_rate': daily_rate,
            'days_left': round(days_left, 1)
        })

        if days_left < CRITICAL_DAYS:
            critical.append(f"{campaign}: {remaining} contacts ({days_left:.1f} days)")
        elif days_left < WARNING_DAYS:
            low.append(f"{campaign}: {remaining} contacts ({days_left:.1f} days)")

    return status, low, critical

def trigger_scraper(campaign):
    """Trigger appropriate scraper for a campaign."""
    # Map campaigns to their source scrapers
    scraper_map = {
        'FACTORY_EU': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/EURES/run_eures.sh',
        'POLAND_AGENCIES': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/POLAND/poland_scraper.py',
        'TOURISM_RO': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ROMANIA/ANOFM/anofm_scraper.py',
        'BUILDJOBS': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/EURES/run_eures.sh',
    }

    if campaign in scraper_map:
        print(f"Would trigger: {scraper_map[campaign]}")
        # Don't auto-trigger yet - just alert
        return True
    return False

def main():
    status, low, critical = check_capacities()

    # Print status table
    print(f"\n=== CAMPAIGN CAPACITY ({datetime.now():%Y-%m-%d %H:%M}) ===\n")
    print(f"{'Campaign':<20} {'Remaining':>10} {'Rate/day':>10} {'Days Left':>10}")
    print("-" * 55)
    for s in status:
        days_str = f"{s['days_left']:.1f}"
        if s['days_left'] < CRITICAL_DAYS:
            days_str += " [CRITICAL]"
        elif s['days_left'] < WARNING_DAYS:
            days_str += " [LOW]"
        print(f"{s['campaign']:<20} {s['remaining']:>10} {s['daily_rate']:>10} {days_str:>15}")
    print()

    # Alert if problems
    if critical:
        msg = f"🚨 CAMPAIGNS RUNNING DRY\n\n" + "\n".join(critical)
        msg += "\n\nRun: python3 /opt/ACTIVE/INFRA/SKILLS/scraper_to_campaigns.py"
        print(msg)
        if '--alert' in sys.argv:
            send_telegram(msg)
        return 2

    if low:
        msg = f"⚠️ CAMPAIGNS LOW ON CONTACTS\n\n" + "\n".join(low)
        msg += "\n\nConsider running scrapers soon."
        print(msg)
        if '--alert' in sys.argv:
            send_telegram(msg)
        return 1

    print("All campaigns have adequate capacity.")
    return 0

if __name__ == '__main__':
    sys.exit(main())
