#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
Outreach Automation - Daily orchestrator for email + Telegram follow-ups

Runs daily at 11:00 via Node-RED:
1. Detect replies/bounces
2. Get Brevo stats
3. Send email follow-ups
4. Telegram fallback for old non-responders
5. Send summary to admin

Usage:
    python3 outreach_automation.py           # Full run
    python3 outreach_automation.py --status  # Show status only
    python3 outreach_automation.py --dry-run # No actual sends
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
sys.path.insert(0, '/opt/ACTIVE/EMAIL/CAMPAIGNS/TELEGRAM')

import os
import subprocess
import json
import csv
import argparse
from datetime import datetime, timedelta
from pathlib import Path

from alerting import send_telegram

ADMIN_CHAT = 547047851
CAMPAIGNS_DIR = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS')
FOLLOWUP_STATE = CAMPAIGNS_DIR / 'SCRIPTS/.followup_state.json'
DNC_FILE = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/EMAIL_CLEANUP/blacklist.txt')
TELEGRAM_DAYS = 14  # Days before trying Telegram


def run_script(script_path, args=None, capture=True):
    """Run a script and return output"""
    cmd = ['/opt/ACTIVE/INFRA/venv/bin/python3', script_path]
    if args:
        cmd.extend(args)
    try:
        result = subprocess.run(cmd, capture_output=capture, text=True, timeout=300)
        return result.stdout if capture else None
    except Exception as e:
        print(f"Error running {script_path}: {e}")
        return None


def detect_replies():
    """Run reply detector"""
    print("1. Detecting replies...")
    output = run_script('/opt/ACTIVE/EMAIL/CAMPAIGNS/SCRIPTS/reply_detector.py', ['--days', '7'])

    replies = {'positive': 0, 'negative': 0, 'neutral': 0}
    bounces = 0

    if output:
        for line in output.split('\n'):
            if 'positive' in line.lower():
                replies['positive'] += 1
            elif 'negative' in line.lower() or 'unsubscribe' in line.lower():
                replies['negative'] += 1
            elif 'bounce' in line.lower():
                bounces += 1

    print(f"   Replies: {sum(replies.values())}, Bounces: {bounces}")
    return replies, bounces


def get_brevo_stats():
    """Get Brevo email stats"""
    print("2. Getting Brevo stats...")
    output = run_script('/opt/ACTIVE/INFRA/SKILLS/email_campaign_tracker.py', ['--today'])

    stats = {'sent': 0, 'opens': 0, 'clicks': 0}
    if output:
        for line in output.split('\n'):
            if 'sent' in line.lower():
                try:
                    stats['sent'] = int(''.join(filter(str.isdigit, line.split(':')[-1])))
                except:
                    pass
            elif 'open' in line.lower():
                try:
                    stats['opens'] = int(''.join(filter(str.isdigit, line.split(':')[-1])))
                except:
                    pass

    print(f"   Sent: {stats['sent']}, Opens: {stats['opens']}")
    return stats


def send_followups(dry_run=False):
    """Send email follow-ups"""
    print("3. Sending email follow-ups...")
    args = ['--limit', '50']
    if dry_run:
        args.append('--dry-run')

    output = run_script('/opt/ACTIVE/EMAIL/CAMPAIGNS/SCRIPTS/followup_sender.py', args)

    followups_sent = 0
    if output:
        for line in output.split('\n'):
            if 'sent' in line.lower() and 'follow' in line.lower():
                try:
                    followups_sent = int(''.join(filter(str.isdigit, line)))
                except:
                    pass

    print(f"   Follow-ups sent: {followups_sent}")
    return followups_sent


def get_telegram_candidates():
    """Get contacts for Telegram fallback (no response after 14 days)"""
    candidates = []

    # Load DNC list
    dnc = set()
    if DNC_FILE.exists():
        dnc = set(DNC_FILE.read_text().strip().split('\n'))

    # Load followup state
    if not FOLLOWUP_STATE.exists():
        return candidates

    state = json.loads(FOLLOWUP_STATE.read_text())
    contacts = state.get('contacts', {})

    now = datetime.now()
    cutoff = now - timedelta(days=TELEGRAM_DAYS)

    for email, info in contacts.items():
        if email in dnc:
            continue

        stage = info.get('followup_stage', 0)
        last_contact = info.get('last_followup') or info.get('first_sent')

        if not last_contact:
            continue

        try:
            last_dt = datetime.fromisoformat(last_contact)
            if last_dt < cutoff and stage >= 2:
                # Check if we have phone for this contact
                phone = info.get('phone', '')
                if phone:
                    candidates.append({'email': email, 'phone': phone})
        except:
            pass

    return candidates


def send_telegram_fallback(candidates, dry_run=False):
    """Send Telegram messages to non-responders"""
    print(f"4. Telegram fallback ({len(candidates)} candidates)...")

    if not candidates or dry_run:
        print(f"   Skipped (dry_run={dry_run})")
        return 0

    sent = 0
    # Use telegram_outreach for each candidate
    for c in candidates[:10]:  # Limit to 10 per day
        phone = c.get('phone', '')
        if phone:
            output = run_script('/opt/ACTIVE/EMAIL/CAMPAIGNS/TELEGRAM/telegram_outreach.py',
                              ['--phone', phone, '--message',
                               'Buna ziua, v-am trimis un email recent. Ati reusit sa-l cititi?'])
            if output and 'sent' in output.lower():
                sent += 1

    print(f"   Telegram sent: {sent}")
    return sent


def send_daily_report(stats, dry_run=False):
    """Send daily summary via Telegram"""
    report = f"""Daily Outreach Report
{'='*30}
Emails sent today: {stats.get('sent', 0)}
Opens: {stats.get('opens', 0)}
Replies: {stats.get('replies_total', 0)}
 - Positive: {stats.get('replies_positive', 0)}
 - Negative: {stats.get('replies_negative', 0)}
Follow-ups sent: {stats.get('followups', 0)}
Telegram fallback: {stats.get('telegram', 0)}
Bounces: {stats.get('bounces', 0)}
{'='*30}"""

    print("\n5. Sending daily report...")
    print(report)

    if not dry_run:
        try:
            send_telegram(report)
            print("   Report sent to Telegram")
        except Exception as e:
            print(f"   Failed to send report: {e}")


def show_status():
    """Show current status without running anything"""
    print("Outreach Automation Status")
    print("=" * 40)

    # Check followup state
    if FOLLOWUP_STATE.exists():
        state = json.loads(FOLLOWUP_STATE.read_text())
        contacts = state.get('contacts', {})
        print(f"Contacts tracked: {len(contacts)}")

        stages = {0: 0, 1: 0, 2: 0, 3: 0}
        for c in contacts.values():
            s = c.get('followup_stage', 0)
            stages[s] = stages.get(s, 0) + 1

        print(f"Stage 0 (initial): {stages[0]}")
        print(f"Stage 1 (day 3): {stages[1]}")
        print(f"Stage 2 (day 7): {stages[2]}")
        print(f"Stage 3 (day 14): {stages[3]}")

    # Telegram candidates
    candidates = get_telegram_candidates()
    print(f"Telegram candidates: {len(candidates)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    print("Outreach Automation")
    print("=" * 40)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Mode: {'DRY-RUN' if args.dry_run else 'LIVE'}")
    print()

    # Run all steps
    replies, bounces = detect_replies()
    brevo_stats = get_brevo_stats()
    followups = send_followups(args.dry_run)

    # Telegram fallback
    candidates = get_telegram_candidates()
    telegram_sent = send_telegram_fallback(candidates, args.dry_run)

    # Compile stats
    stats = {
        'sent': brevo_stats.get('sent', 0),
        'opens': brevo_stats.get('opens', 0),
        'replies_total': sum(replies.values()),
        'replies_positive': replies.get('positive', 0),
        'replies_negative': replies.get('negative', 0),
        'followups': followups,
        'telegram': telegram_sent,
        'bounces': bounces
    }

    # Send report
    send_daily_report(stats, args.dry_run)

    print("\nDone!")


if __name__ == '__main__':
    main()
