#!/usr/bin/env python3
"""
Hot Lead Alert - Telegram notifications for high-value leads

Monitors:
- New high-score leads (score >= 70)
- Interested replies from inbox
- Corporate email contacts
- Leads from priority sectors

Usage:
    python3 hot_lead_alert.py                  # Check and alert
    python3 hot_lead_alert.py --threshold 50   # Lower threshold
    python3 hot_lead_alert.py --watch          # Continuous monitoring
    python3 hot_lead_alert.py --test           # Test Telegram
    python3 hot_lead_alert.py --status         # Show alert history

Runs via cron every 30 min or as daemon with --watch.
"""

import os
import sys
import csv
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

try:
    from alerting import send_telegram
except ImportError:
    def send_telegram(msg):
        print(f"[TELEGRAM] {msg}")

# Paths
CAEN_EXPORT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/CAEN_EXPORTS")
REPLIES_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/REPLIES")
STATE_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/.hot_lead_state.json")

# Alert settings
DEFAULT_THRESHOLD = 70
PRIORITY_SECTORS = ["horeca", "construction", "manufacturing", "transport"]
CORPORATE_DOMAINS = [".eu", ".com", ".ro", ".pl", ".cz", ".de"]  # Non-free email


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "alerted_emails": {},
        "last_check": None,
        "total_alerts": 0
    }


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def is_corporate_email(email):
    """Check if email is corporate (not free provider)."""
    free_providers = ['gmail.', 'yahoo.', 'hotmail.', 'outlook.', 'wp.pl',
                      'onet.pl', 'o2.pl', 'seznam.cz', 'centrum.cz', 'interia.']
    email_lower = email.lower()
    return not any(fp in email_lower for fp in free_providers)


def find_hot_leads(threshold=DEFAULT_THRESHOLD):
    """Find high-score leads from CAEN exports."""
    hot_leads = []

    for sector in PRIORITY_SECTORS:
        filepath = CAEN_EXPORT_DIR / f"{sector}_with_email.csv"
        if not filepath.exists():
            continue

        try:
            with open(filepath, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        score = int(row.get('score', 0) or 0)
                    except:
                        score = 0

                    email = row.get('email', '').lower()

                    if score >= threshold and email:
                        # Bonus for corporate email
                        if is_corporate_email(email):
                            score += 10

                        hot_leads.append({
                            'email': email,
                            'company': row.get('company', ''),
                            'score': score,
                            'sector': sector,
                            'city': row.get('city', ''),
                            'phone': row.get('phone', ''),
                            'corporate': is_corporate_email(email)
                        })
        except Exception as e:
            log(f"Error reading {filepath}: {e}")

    # Sort by score descending
    hot_leads.sort(key=lambda x: x['score'], reverse=True)

    return hot_leads


def find_interested_replies():
    """Find interested replies from classifier."""
    interested = []

    classified_file = REPLIES_DIR / "classified_replies.csv"
    if not classified_file.exists():
        return interested

    try:
        with open(classified_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('category') == 'INTERESTED':
                    interested.append({
                        'email': row.get('sender_email', ''),
                        'subject': row.get('subject', ''),
                        'date': row.get('date', ''),
                        'account': row.get('account', '')
                    })
    except Exception as e:
        log(f"Error reading replies: {e}")

    return interested


def send_alerts(hot_leads, interested_replies, state):
    """Send Telegram alerts for new hot leads."""
    new_alerts = []

    # Check hot leads
    for lead in hot_leads[:20]:  # Top 20
        email = lead['email']
        if email not in state['alerted_emails']:
            new_alerts.append(lead)
            state['alerted_emails'][email] = {
                'alerted_at': datetime.now().isoformat(),
                'score': lead['score'],
                'type': 'high_score'
            }

    # Check interested replies
    for reply in interested_replies:
        email = reply['email']
        if email not in state['alerted_emails']:
            new_alerts.append({
                'email': email,
                'company': reply.get('subject', '')[:50],
                'score': 100,  # Interested = highest priority
                'sector': 'reply',
                'city': '',
                'type': 'interested_reply'
            })
            state['alerted_emails'][email] = {
                'alerted_at': datetime.now().isoformat(),
                'score': 100,
                'type': 'interested_reply'
            }

    if not new_alerts:
        log("No new hot leads to alert")
        return 0

    # Build message
    msg = f"🔥 HOT LEADS ({len(new_alerts)} new)\n\n"

    # Group by type
    high_score = [a for a in new_alerts if a.get('type') != 'interested_reply']
    replies = [a for a in new_alerts if a.get('type') == 'interested_reply']

    if replies:
        msg += "📩 INTERESTED REPLIES:\n"
        for r in replies[:5]:
            msg += f"• {r['email']}\n"
        msg += "\n"

    if high_score:
        msg += "⭐ HIGH-SCORE LEADS:\n"
        for lead in high_score[:10]:
            corp = "🏢" if lead.get('corporate') else ""
            msg += f"• {corp}{lead['company'][:30]} ({lead['sector']})\n"
            msg += f"  {lead['email']} [score:{lead['score']}]\n"
        msg += "\n"

    msg += f"Total tracked: {len(state['alerted_emails'])}"

    send_telegram(msg)
    state['total_alerts'] += len(new_alerts)

    log(f"Sent alert for {len(new_alerts)} new leads")
    return len(new_alerts)


def watch_mode(threshold, interval=1800):
    """Continuous monitoring mode."""
    log(f"Starting watch mode (check every {interval}s, threshold={threshold})")

    while True:
        try:
            state = load_state()
            hot_leads = find_hot_leads(threshold)
            interested = find_interested_replies()

            send_alerts(hot_leads, interested, state)

            state['last_check'] = datetime.now().isoformat()
            save_state(state)

        except Exception as e:
            log(f"Watch error: {e}")

        time.sleep(interval)


def show_status():
    """Show alert status."""
    state = load_state()

    print("\n=== Hot Lead Alert Status ===\n")
    print(f"Last check: {state.get('last_check', 'Never')}")
    print(f"Total alerts sent: {state.get('total_alerts', 0)}")
    print(f"Emails tracked: {len(state.get('alerted_emails', {}))}")

    # Recent alerts
    alerts = state.get('alerted_emails', {})
    recent = sorted(alerts.items(), key=lambda x: x[1].get('alerted_at', ''), reverse=True)[:10]

    if recent:
        print("\nRecent alerts:")
        for email, info in recent:
            print(f"  {email}: score={info.get('score')} type={info.get('type')}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Hot Lead Alert")
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD, help="Score threshold")
    parser.add_argument("--watch", action="store_true", help="Continuous monitoring")
    parser.add_argument("--interval", type=int, default=1800, help="Watch interval (seconds)")
    parser.add_argument("--test", action="store_true", help="Test Telegram")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--reset", action="store_true", help="Reset alert history")

    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.reset:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        print("Alert history reset.")
        return

    if args.test:
        send_telegram("🧪 Hot Lead Alert test message")
        print("Test message sent.")
        return

    if args.watch:
        watch_mode(args.threshold, args.interval)
        return

    # Single check
    state = load_state()

    log(f"Checking for hot leads (threshold={args.threshold})")

    hot_leads = find_hot_leads(args.threshold)
    log(f"Found {len(hot_leads)} leads above threshold")

    interested = find_interested_replies()
    log(f"Found {len(interested)} interested replies")

    send_alerts(hot_leads, interested, state)

    state['last_check'] = datetime.now().isoformat()
    save_state(state)


if __name__ == "__main__":
    main()
