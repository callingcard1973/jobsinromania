#!/usr/bin/env python3
"""
Auto-Pause Bad Sectors - Stop campaigns if bounce rate exceeds threshold

Monitors bounce rates per sector/campaign and auto-pauses when:
- Bounce rate > 5% (configurable)
- Spam complaints detected
- Multiple delivery failures

Usage:
    python3 auto_pause_sectors.py                  # Check and pause if needed
    python3 auto_pause_sectors.py --threshold 3    # Lower threshold (3%)
    python3 auto_pause_sectors.py --status         # Show sector health
    python3 auto_pause_sectors.py --resume SECTOR  # Resume paused sector
    python3 auto_pause_sectors.py --watch          # Continuous monitoring

Sends Telegram alert when pausing.
"""

import os
import sys
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

try:
    from alerting import send_telegram
except ImportError:
    def send_telegram(msg):
        print(f"[TELEGRAM] {msg}")

# Paths
CAMPAIGNS_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/CAMPAIGNS")
STATE_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/.sector_health_state.json")
LOGS_DIR = Path("/opt/ACTIVE/INFRA/LOGS/campaigns")

# Thresholds
DEFAULT_BOUNCE_THRESHOLD = 5.0  # 5%
DEFAULT_SPAM_THRESHOLD = 1  # Any spam = pause
MIN_SENDS_FOR_CHECK = 20  # Need at least 20 sends to calculate rate


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "paused_sectors": {},
        "sector_stats": {},
        "last_check": None
    }


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def get_campaign_stats(campaign_name, days=1):
    """Get send/bounce stats for campaign."""
    stats = {
        "sent": 0,
        "bounced": 0,
        "spam": 0,
        "bounce_rate": 0.0
    }

    # Check logs from last N days
    for i in range(days):
        date_str = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
        log_file = LOGS_DIR / f"{campaign_name}_{date_str}.log"

        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    content = f.read().lower()
                    # Count sends
                    stats['sent'] += content.count('sent to') + content.count('success')
                    # Count bounces
                    stats['bounced'] += content.count('bounce') + content.count('failed') + content.count('rejected')
                    # Count spam
                    stats['spam'] += content.count('spam')
            except:
                pass

    # Also check campaign state file
    state_file = CAMPAIGNS_DIR / campaign_name / ".state.json"
    if state_file.exists():
        try:
            with open(state_file) as f:
                state = json.load(f)
                stats['sent'] = max(stats['sent'], state.get('sent_count', 0))
        except:
            pass

    if stats['sent'] > 0:
        stats['bounce_rate'] = round(stats['bounced'] / stats['sent'] * 100, 2)

    return stats


def check_all_campaigns(bounce_threshold=DEFAULT_BOUNCE_THRESHOLD):
    """Check all campaigns for health issues."""
    state = load_state()
    issues = []

    for campaign_dir in CAMPAIGNS_DIR.iterdir():
        if not campaign_dir.is_dir():
            continue

        campaign_name = campaign_dir.name

        # Skip already paused
        if campaign_name in state.get('paused_sectors', {}):
            continue

        stats = get_campaign_stats(campaign_name, days=3)

        # Need minimum sends
        if stats['sent'] < MIN_SENDS_FOR_CHECK:
            continue

        # Check bounce rate
        if stats['bounce_rate'] > bounce_threshold:
            issues.append({
                'campaign': campaign_name,
                'issue': 'high_bounce',
                'bounce_rate': stats['bounce_rate'],
                'sent': stats['sent'],
                'bounced': stats['bounced']
            })

        # Check spam
        if stats['spam'] >= DEFAULT_SPAM_THRESHOLD:
            issues.append({
                'campaign': campaign_name,
                'issue': 'spam_detected',
                'spam_count': stats['spam']
            })

        # Update stats
        state['sector_stats'][campaign_name] = {
            'sent': stats['sent'],
            'bounced': stats['bounced'],
            'bounce_rate': stats['bounce_rate'],
            'spam': stats['spam'],
            'last_check': datetime.now().isoformat()
        }

    state['last_check'] = datetime.now().isoformat()
    save_state(state)

    return issues


def pause_campaign(campaign_name, reason):
    """Pause a campaign by disabling it."""
    state = load_state()

    # Mark as paused
    state['paused_sectors'][campaign_name] = {
        'paused_at': datetime.now().isoformat(),
        'reason': reason
    }

    # Try to disable in config (update state file)
    state_file = CAMPAIGNS_DIR / campaign_name / ".state.json"
    if state_file.exists():
        try:
            with open(state_file) as f:
                campaign_state = json.load(f)
            campaign_state['paused'] = True
            campaign_state['pause_reason'] = reason
            with open(state_file, 'w') as f:
                json.dump(campaign_state, f, indent=2)
        except:
            pass

    save_state(state)
    log(f"Paused campaign: {campaign_name} ({reason})")


def resume_campaign(campaign_name):
    """Resume a paused campaign."""
    state = load_state()

    if campaign_name in state.get('paused_sectors', {}):
        del state['paused_sectors'][campaign_name]

    # Update state file
    state_file = CAMPAIGNS_DIR / campaign_name / ".state.json"
    if state_file.exists():
        try:
            with open(state_file) as f:
                campaign_state = json.load(f)
            campaign_state['paused'] = False
            campaign_state.pop('pause_reason', None)
            with open(state_file, 'w') as f:
                json.dump(campaign_state, f, indent=2)
        except:
            pass

    save_state(state)
    log(f"Resumed campaign: {campaign_name}")


def show_status():
    """Show sector health status."""
    state = load_state()

    print("\n=== Sector Health Status ===\n")
    print(f"Last check: {state.get('last_check', 'Never')}")

    # Paused campaigns
    paused = state.get('paused_sectors', {})
    if paused:
        print(f"\n🔴 PAUSED CAMPAIGNS ({len(paused)}):")
        for camp, info in paused.items():
            print(f"  {camp}: {info.get('reason')} (since {info.get('paused_at', 'unknown')[:10]})")
    else:
        print("\n✅ No paused campaigns")

    # Stats
    print("\nCampaign Stats (last 3 days):")
    stats = state.get('sector_stats', {})
    for camp, s in sorted(stats.items(), key=lambda x: -x[1].get('bounce_rate', 0)):
        rate = s.get('bounce_rate', 0)
        indicator = "🔴" if rate > 5 else "🟡" if rate > 2 else "🟢"
        print(f"  {indicator} {camp}: {s.get('sent', 0)} sent, {rate}% bounce")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Auto-Pause Bad Sectors")
    parser.add_argument("--threshold", type=float, default=DEFAULT_BOUNCE_THRESHOLD, help="Bounce rate threshold")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--resume", help="Resume paused campaign")
    parser.add_argument("--watch", action="store_true", help="Continuous monitoring")
    parser.add_argument("--interval", type=int, default=1800, help="Watch interval (seconds)")

    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.resume:
        resume_campaign(args.resume)
        send_telegram(f"▶️ Resumed campaign: {args.resume}")
        return

    if args.watch:
        import time
        log(f"Starting watch mode (interval={args.interval}s, threshold={args.threshold}%)")
        while True:
            try:
                issues = check_all_campaigns(args.threshold)
                for issue in issues:
                    pause_campaign(issue['campaign'], f"{issue['issue']}: {issue.get('bounce_rate', issue.get('spam_count'))}%")
                    send_telegram(f"⏸️ Auto-paused {issue['campaign']}: {issue['issue']} ({issue.get('bounce_rate', 'N/A')}% bounce)")
            except Exception as e:
                log(f"Watch error: {e}")
            time.sleep(args.interval)
        return

    # Single check
    log(f"Checking campaigns (threshold={args.threshold}%)")
    issues = check_all_campaigns(args.threshold)

    if issues:
        log(f"Found {len(issues)} issues")
        for issue in issues:
            pause_campaign(issue['campaign'], f"{issue['issue']}: {issue.get('bounce_rate', issue.get('spam_count'))}")
            send_telegram(f"⏸️ Auto-paused {issue['campaign']}: {issue['issue']}")
    else:
        log("All campaigns healthy")


if __name__ == "__main__":
    main()
