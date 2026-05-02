#!/usr/bin/env python3
"""
Email Sending Verification - Unified dashboard for all email campaigns
Checks state files, logs, processes to show if emails are flowing

Usage:
    python3 verify_email_sending.py                    # Quick status all campaigns
    python3 verify_email_sending.py --campaign ANOFM   # Single campaign detail
    python3 verify_email_sending.py --last-hour        # Activity in last hour
    python3 verify_email_sending.py --watch            # Real-time monitor (5s refresh)
    python3 verify_email_sending.py --alert            # Check and alert if issues

Examples:
    python3 verify_email_sending.py --watch --interval 10
    python3 verify_email_sending.py --alert --telegram
"""

import sys
import os
import json
import subprocess
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Paths
CAMPAIGNS_DIR = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS')
ORCHESTRATOR_STATE = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/campaign_orchestrator_state.json')
LOGS_DIR = Path('/opt/ACTIVE/INFRA/LOGS')

# Add shared code
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
try:
    from skills_common import send_telegram
    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False

# Campaign limits (known campaigns)
CAMPAIGN_LIMITS = {
    'ANOFM': 290, 'HORECA2026': 290, 'FACTORY_EU': 290, 'POLAND': 290,
    'NORDIC': 290, 'TRANSPORT_EU': 290, 'GERMANY_AGENCIES': 100,
    'EU_CONTRACTORS': 100, 'BUILDJOBS_EU': 290, 'CAREWORKERS': 290,
    'TOURISM_RO': 290, 'AGENCIES_GERMANY': 290, 'AGENCIES_NORDIC': 290,
}
DEFAULT_LIMIT = 290

# Alert thresholds
SLOW_THRESHOLD_MINUTES = 15  # Yellow if no sends in 15 min
WARNING_THRESHOLD_MINUTES = 30  # Red if no sends in 30 min


@dataclass
class CampaignStatus:
    """Status for a single campaign."""
    name: str
    last_send: Optional[datetime] = None
    sent_today: int = 0
    daily_limit: int = 290
    ok_count: int = 0
    fail_count: int = 0
    process_running: bool = False
    status: str = "UNKNOWN"  # OK, SLOW, WARNING, STOPPED, ERROR

    @property
    def minutes_since_send(self) -> Optional[int]:
        if not self.last_send:
            return None
        delta = datetime.now() - self.last_send
        return int(delta.total_seconds() / 60)

    @property
    def last_send_str(self) -> str:
        mins = self.minutes_since_send
        if mins is None:
            return "never"
        if mins < 1:
            return "just now"
        if mins < 60:
            return f"{mins} min ago"
        hours = mins // 60
        return f"{hours}h ago"

    @property
    def progress_str(self) -> str:
        return f"{self.sent_today}/{self.daily_limit}"


def get_running_campaigns() -> Dict[str, int]:
    """Get currently running campaign processes."""
    running = {}
    try:
        result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.split('\n'):
            if 'send_' in line and '_brevo.py' in line:
                # Extract campaign name from path
                for part in line.split():
                    if '/CAMPAIGNS/' in part:
                        name = part.split('/CAMPAIGNS/')[1].split('/')[0]
                        # Extract PID
                        parts = line.split()
                        if len(parts) > 1:
                            try:
                                pid = int(parts[1])
                                running[name] = pid
                            except ValueError:
                                pass
                        break
            # Also check for kraz_campaign.py (POLAND)
            if 'kraz_campaign.py' in line:
                parts = line.split()
                if len(parts) > 1:
                    try:
                        running['POLAND'] = int(parts[1])
                    except ValueError:
                        pass
    except Exception:
        pass
    return running


def parse_state_file(campaign_dir: Path) -> Tuple[Optional[datetime], int]:
    """Parse state.json to get last send time and count."""
    state_file = campaign_dir / 'state.json'
    if not state_file.exists():
        return None, 0

    try:
        with open(state_file) as f:
            state = json.load(f)

        # Get sent count
        sent_today = state.get('daily_sent', 0)

        # Get last send time
        last_send_str = state.get('last_send')
        if last_send_str:
            # Try multiple formats
            for fmt in ['%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                try:
                    last_send = datetime.strptime(last_send_str.split('+')[0], fmt)
                    return last_send, sent_today
                except ValueError:
                    continue

        # Fallback: count sent_emails
        sent_emails = state.get('sent_emails', [])
        return None, len(sent_emails) if sent_today == 0 else sent_today

    except Exception:
        return None, 0


def parse_log_file(campaign_dir: Path) -> Tuple[Optional[datetime], int, int]:
    """Parse today's log file for last send time and counts."""
    today = datetime.now().strftime('%Y%m%d')
    log_dir = campaign_dir / 'logs'

    if not log_dir.exists():
        return None, 0, 0

    log_file = log_dir / f'sent_{today}.log'
    if not log_file.exists():
        # Try finding most recent log
        logs = sorted(log_dir.glob('sent_*.log'), reverse=True)
        if logs:
            log_file = logs[0]
        else:
            return None, 0, 0

    last_send = None
    ok_count = 0
    fail_count = 0

    try:
        with open(log_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                parts = line.split(' | ')
                if len(parts) >= 3:
                    # Parse timestamp
                    try:
                        ts_str = parts[0].strip()
                        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S']:
                            try:
                                ts = datetime.strptime(ts_str, fmt)
                                last_send = ts
                                break
                            except ValueError:
                                continue
                    except Exception:
                        pass

                    # Count status
                    status = parts[1].strip() if len(parts) > 1 else ''
                    if status == 'OK':
                        ok_count += 1
                    elif status in ['FAIL', 'ERROR', 'SKIP']:
                        fail_count += 1

    except Exception:
        pass

    return last_send, ok_count, fail_count


def get_campaign_status(name: str, running_processes: Dict[str, int]) -> CampaignStatus:
    """Get full status for a campaign."""
    campaign_dir = CAMPAIGNS_DIR / name

    status = CampaignStatus(
        name=name,
        daily_limit=CAMPAIGN_LIMITS.get(name, DEFAULT_LIMIT),
        process_running=name in running_processes
    )

    if not campaign_dir.exists():
        status.status = "NOT_FOUND"
        return status

    # Parse state file
    state_last_send, state_count = parse_state_file(campaign_dir)

    # Parse log file
    log_last_send, ok_count, fail_count = parse_log_file(campaign_dir)

    # Use most recent last_send
    if log_last_send and state_last_send:
        status.last_send = max(log_last_send, state_last_send)
    else:
        status.last_send = log_last_send or state_last_send

    status.sent_today = max(state_count, ok_count)
    status.ok_count = ok_count
    status.fail_count = fail_count

    # Determine status
    mins = status.minutes_since_send
    if mins is None:
        status.status = "NO_DATA"
    elif mins > WARNING_THRESHOLD_MINUTES and not status.process_running:
        status.status = "STOPPED"
    elif mins > WARNING_THRESHOLD_MINUTES:
        status.status = "WARNING"
    elif mins > SLOW_THRESHOLD_MINUTES:
        status.status = "SLOW"
    else:
        status.status = "OK"

    return status


def get_all_campaigns() -> List[str]:
    """Get list of all campaign directories."""
    campaigns = []
    if CAMPAIGNS_DIR.exists():
        for d in CAMPAIGNS_DIR.iterdir():
            if d.is_dir() and not d.name.startswith('.'):
                # Must have state.json or logs dir
                if (d / 'state.json').exists() or (d / 'logs').exists():
                    campaigns.append(d.name)
    return sorted(campaigns)


def print_dashboard(statuses: List[CampaignStatus], show_all: bool = False):
    """Print the status dashboard."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print(f"\n=== EMAIL SENDING STATUS ===")
    print(f"Time: {now}\n")

    # Filter to active campaigns unless show_all
    if not show_all:
        # Show campaigns with recent activity or known important ones
        important = set(CAMPAIGN_LIMITS.keys())
        statuses = [s for s in statuses if s.name in important or s.sent_today > 0 or s.process_running]

    if not statuses:
        print("No active campaigns found.")
        return

    # Header
    print(f"{'CAMPAIGN':<20} | {'LAST SEND':<12} | {'TODAY':<8} | {'STATUS':<8} | PID")
    print("-" * 70)

    total_sent = 0
    running_count = 0
    issues = []

    for s in sorted(statuses, key=lambda x: x.name):
        pid_str = str(running_processes.get(s.name, '')) if s.process_running else ''

        # Status indicator
        status_str = s.status
        if s.status == "OK":
            status_str = "OK"
        elif s.status == "SLOW":
            status_str = "SLOW"
        elif s.status in ["WARNING", "STOPPED"]:
            status_str = s.status
            issues.append(s)

        print(f"{s.name:<20} | {s.last_send_str:<12} | {s.progress_str:<8} | {status_str:<8} | {pid_str}")

        total_sent += s.sent_today
        if s.process_running:
            running_count += 1

    print("-" * 70)
    print(f"Total sent today: {total_sent} emails")
    print(f"Active processes: {running_count}/{len(statuses)} campaigns")

    if issues:
        print(f"\n!!! {len(issues)} campaign(s) need attention !!!")
        for s in issues:
            print(f"  - {s.name}: {s.status} (last send: {s.last_send_str})")


def check_and_alert(statuses: List[CampaignStatus], use_telegram: bool = False):
    """Check for issues and optionally send alerts."""
    issues = [s for s in statuses if s.status in ['WARNING', 'STOPPED']]

    if not issues:
        print("All campaigns OK - no alerts needed.")
        return

    msg_lines = [f"EMAIL ALERT: {len(issues)} campaign(s) with issues"]
    for s in issues:
        msg_lines.append(f"- {s.name}: {s.status} (last: {s.last_send_str})")

    msg = '\n'.join(msg_lines)
    print(msg)

    if use_telegram and HAS_TELEGRAM:
        try:
            send_telegram(msg)
            print("Telegram alert sent.")
        except Exception as e:
            print(f"Failed to send Telegram: {e}")

    # Log alert
    alert_log = LOGS_DIR / 'email_alerts.log'
    try:
        with open(alert_log, 'a') as f:
            f.write(f"{datetime.now().isoformat()} | {msg.replace(chr(10), ' ')}\n")
    except Exception:
        pass


def watch_mode(interval: int = 5):
    """Real-time monitoring with refresh."""
    import time

    print(f"Watching email sending status (refresh every {interval}s)")
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            # Clear screen
            os.system('clear' if os.name != 'nt' else 'cls')

            global running_processes
            running_processes = get_running_campaigns()
            campaigns = get_all_campaigns()
            statuses = [get_campaign_status(c, running_processes) for c in campaigns]
            print_dashboard(statuses, show_all=False)

            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped watching.")


def single_campaign_detail(name: str):
    """Show detailed info for a single campaign."""
    running = get_running_campaigns()
    status = get_campaign_status(name, running)

    print(f"\n=== {name} Campaign Detail ===\n")

    if status.status == "NOT_FOUND":
        print(f"Campaign '{name}' not found in {CAMPAIGNS_DIR}")
        return

    print(f"Status: {status.status}")
    print(f"Last send: {status.last_send_str}")
    if status.last_send:
        print(f"  ({status.last_send.strftime('%Y-%m-%d %H:%M:%S')})")
    print(f"Sent today: {status.sent_today}/{status.daily_limit}")
    print(f"Success/Fail: {status.ok_count}/{status.fail_count}")
    print(f"Process running: {'Yes' if status.process_running else 'No'}")

    if status.process_running and name in running:
        print(f"  PID: {running[name]}")

    # Show recent log entries
    campaign_dir = CAMPAIGNS_DIR / name
    today = datetime.now().strftime('%Y%m%d')
    log_file = campaign_dir / 'logs' / f'sent_{today}.log'

    if log_file.exists():
        print(f"\nLast 10 log entries:")
        print("-" * 50)
        try:
            with open(log_file) as f:
                lines = f.readlines()[-10:]
                for line in lines:
                    print(line.strip())
        except Exception as e:
            print(f"Error reading log: {e}")


def last_hour_activity():
    """Show activity in the last hour across all campaigns."""
    one_hour_ago = datetime.now() - timedelta(hours=1)

    print(f"\n=== Activity in Last Hour ===")
    print(f"Since: {one_hour_ago.strftime('%H:%M:%S')}\n")

    running = get_running_campaigns()
    campaigns = get_all_campaigns()

    total_sent = 0
    active_campaigns = []

    for name in campaigns:
        status = get_campaign_status(name, running)
        if status.last_send and status.last_send > one_hour_ago:
            active_campaigns.append(status)
            # Count only recent sends (approximate)
            total_sent += status.ok_count

    if not active_campaigns:
        print("No email activity in the last hour!")
        return

    print(f"{'CAMPAIGN':<20} | {'LAST SEND':<12} | {'SENT':<6}")
    print("-" * 45)

    for s in sorted(active_campaigns, key=lambda x: x.last_send or datetime.min, reverse=True):
        print(f"{s.name:<20} | {s.last_send_str:<12} | {s.ok_count:<6}")

    print("-" * 45)
    print(f"Active campaigns: {len(active_campaigns)}")


# Global for running processes (set in main)
running_processes: Dict[str, int] = {}


def main():
    parser = argparse.ArgumentParser(description='Verify email sending status')
    parser.add_argument('--campaign', '-c', help='Show detail for specific campaign')
    parser.add_argument('--last-hour', action='store_true', help='Show last hour activity')
    parser.add_argument('--watch', '-w', action='store_true', help='Real-time monitoring')
    parser.add_argument('--interval', '-i', type=int, default=5, help='Watch refresh interval (seconds)')
    parser.add_argument('--alert', '-a', action='store_true', help='Check and alert if issues')
    parser.add_argument('--telegram', '-t', action='store_true', help='Send Telegram alerts')
    parser.add_argument('--all', action='store_true', help='Show all campaigns')

    args = parser.parse_args()

    global running_processes
    running_processes = get_running_campaigns()

    if args.watch:
        watch_mode(args.interval)
    elif args.campaign:
        single_campaign_detail(args.campaign)
    elif args.last_hour:
        last_hour_activity()
    elif args.alert:
        campaigns = get_all_campaigns()
        statuses = [get_campaign_status(c, running_processes) for c in campaigns]
        check_and_alert(statuses, use_telegram=args.telegram)
    else:
        campaigns = get_all_campaigns()
        statuses = [get_campaign_status(c, running_processes) for c in campaigns]
        print_dashboard(statuses, show_all=args.all)


if __name__ == '__main__':
    main()
