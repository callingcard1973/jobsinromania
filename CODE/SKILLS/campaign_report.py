#!/usr/bin/env python3
"""
Campaign Analytics Report — daily summary of all email campaigns.

Features:
  - Sends per campaign (today / total)
  - Bounce rate per Gmail sender
  - Reply/lead count
  - Blacklist growth
  - Queue remaining
  - Sender scoring (best/worst performers)
  - Log archival (>90 days → archive)

Usage:
    python3 campaign_report.py                # Full daily report
    python3 campaign_report.py --json         # JSON output
    python3 campaign_report.py --archive      # Archive old log entries
    python3 campaign_report.py --score        # Show sender scores
"""

import os
import sys
import json
import csv
from pathlib import Path
from datetime import datetime, date, timedelta
from collections import defaultdict

sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS')
sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS/lib')

# === Config ===

CAMPAIGNS = {
    'NECALIFICATI_FEB_2026': {
        'state': '/opt/ACTIVE/EMAIL/CAMPAIGNS/NECALIFICATI_FEB_2026/.state.json',
        'contacts': '/opt/ACTIVE/EMAIL/CAMPAIGNS/NECALIFICATI_FEB_2026/contacts/contacts.csv',
    },
    'ANOFM_YAHOO': {
        'state': '/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM/gmail_yahoo_state.json',
        'contacts': [
            '/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM/contacts/contacts_yahoo.csv',
            '/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM/contacts/contacts_nonyahoo.csv',
        ],
    },
}

GLOBAL_SEND_LOG = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/global_send_log.csv')
GLOBAL_SEND_ARCHIVE = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/global_send_log_archive.csv')
BLACKLIST_FILE = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/master_blacklist.csv')
LEADS_FILE = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/leads.json')
SENDER_SCORES_FILE = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/sender_scores.json')
REPORT_LOG = Path('/opt/ACTIVE/INFRA/LOGS/campaign_report.log')


# === Campaign Stats ===

def get_campaign_stats():
    """Get per-campaign send stats."""
    stats = {}
    today = date.today().isoformat()

    for name, cfg in CAMPAIGNS.items():
        state_path = cfg['state']
        if not os.path.exists(state_path):
            stats[name] = {'error': 'state file missing'}
            continue

        with open(state_path) as f:
            state = json.load(f)

        sent = state.get('sent', {})
        if isinstance(sent, list):
            total_sent = len(sent)
        else:
            total_sent = len(sent)

        # Today's sends
        daily = state.get('daily', {})
        today_data = daily.get(today, {})
        today_sent = sum(today_data.values()) if isinstance(today_data, dict) else 0

        # Contact count
        contacts_paths = cfg.get('contacts', [])
        if isinstance(contacts_paths, str):
            contacts_paths = [contacts_paths]
        total_contacts = 0
        for cp in contacts_paths:
            if os.path.exists(cp):
                total_contacts += sum(1 for _ in open(cp)) - 1

        # Failed
        failed = state.get('failed', {})
        total_failed = len(failed) if isinstance(failed, dict) else len(failed) if isinstance(failed, list) else 0

        # Queue remaining
        remaining = max(0, total_contacts - total_sent - total_failed)

        # Last 7 days trend
        week_sends = {}
        for i in range(7):
            d = (date.today() - timedelta(days=i)).isoformat()
            day_data = daily.get(d, {})
            week_sends[d] = sum(day_data.values()) if isinstance(day_data, dict) else 0

        stats[name] = {
            'total_sent': total_sent,
            'today_sent': today_sent,
            'total_failed': total_failed,
            'total_contacts': total_contacts,
            'remaining': remaining,
            'week_sends': week_sends,
        }

    return stats


# === Sender Scoring ===

def calculate_sender_scores():
    """Calculate per-sender bounce/success rates from global send log."""
    if not GLOBAL_SEND_LOG.exists():
        return {}

    sender_stats = defaultdict(lambda: {'sent': 0, 'bounced': 0, 'recent_sent': 0})
    cutoff_30d = (date.today() - timedelta(days=30)).isoformat()

    # Read blacklist for bounce detection
    blacklist = set()
    if BLACKLIST_FILE.exists():
        try:
            with open(BLACKLIST_FILE) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    email = (row.get('email') or '').strip().lower()
                    if email:
                        blacklist.add(email)
        except Exception:
            pass

    with open(GLOBAL_SEND_LOG) as f:
        reader = csv.reader(f)
        next(reader, None)  # skip header
        for row in reader:
            if len(row) < 4:
                continue
            send_date, email, campaign, sender = row[0], row[1], row[2], row[3] if len(row) > 3 else ''
            if not sender:
                continue

            sender_stats[sender]['sent'] += 1
            if send_date >= cutoff_30d:
                sender_stats[sender]['recent_sent'] += 1
            if email.lower() in blacklist:
                sender_stats[sender]['bounced'] += 1

    # Calculate scores (0-100, higher is better)
    scores = {}
    for sender, data in sender_stats.items():
        if data['sent'] == 0:
            continue
        bounce_rate = (data['bounced'] / data['sent']) * 100
        # Score: 100 - bounce_rate, min 0
        score = max(0, min(100, 100 - bounce_rate * 10))
        scores[sender] = {
            'score': round(score, 1),
            'total_sent': data['sent'],
            'recent_sent': data['recent_sent'],
            'bounced': data['bounced'],
            'bounce_rate': round(bounce_rate, 2),
        }

    # Save scores
    with open(SENDER_SCORES_FILE, 'w') as f:
        json.dump(scores, f, indent=2)

    return scores


def get_dynamic_delay(sender_name):
    """Get recommended delay for a sender based on their score.
    0% bounces → 240s, 1-2% → 300s, >2% → 360s"""
    if not SENDER_SCORES_FILE.exists():
        return 300  # default

    scores = json.loads(SENDER_SCORES_FILE.read_text())
    data = scores.get(sender_name, {})
    bounce_rate = data.get('bounce_rate', 1.0)

    if bounce_rate == 0:
        return 240
    elif bounce_rate <= 2:
        return 300
    else:
        return 360


# === Log Archival ===

def archive_old_logs():
    """Move global_send_log entries older than 90 days to archive file."""
    if not GLOBAL_SEND_LOG.exists():
        print('No global send log to archive')
        return

    cutoff = (date.today() - timedelta(days=90)).isoformat()
    kept = []
    archived = 0

    with open(GLOBAL_SEND_LOG) as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if row and row[0] and row[0] < cutoff:
                # Archive this row
                with open(GLOBAL_SEND_ARCHIVE, 'a', newline='') as af:
                    csv.writer(af).writerow(row)
                archived += 1
            else:
                kept.append(row)

    # Rewrite active log with only recent entries
    with open(GLOBAL_SEND_LOG, 'w', newline='') as f:
        writer = csv.writer(f)
        if header:
            writer.writerow(header)
        writer.writerows(kept)

    print(f'Archived {archived} entries (>90 days), kept {len(kept)} recent')


# === Blacklist Stats ===

def get_blacklist_stats():
    """Get blacklist growth info."""
    if not BLACKLIST_FILE.exists():
        return {'total': 0, 'today_added': 0}

    total = 0
    today_added = 0
    today_str = date.today().isoformat()

    with open(BLACKLIST_FILE) as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            if (row.get('date') or '').startswith(today_str):
                today_added += 1

    return {'total': total, 'today_added': today_added}


# === Leads Stats ===

def get_leads_stats():
    """Get reply/lead counts."""
    if not LEADS_FILE.exists():
        return {'total': 0, 'today': 0}

    leads = json.loads(LEADS_FILE.read_text())
    today_str = date.today().isoformat()
    today_leads = sum(1 for l in leads if (l.get('detected_at') or '').startswith(today_str))

    return {'total': len(leads), 'today': today_leads}


# === Global Send Stats ===

def get_global_send_stats():
    """Get overall send statistics."""
    if not GLOBAL_SEND_LOG.exists():
        return {'total': 0, 'today': 0, 'last_7_days': 0}

    total = 0
    today_count = 0
    week_count = 0
    today_str = date.today().isoformat()
    week_cutoff = (date.today() - timedelta(days=7)).isoformat()

    with open(GLOBAL_SEND_LOG) as f:
        next(f, None)  # skip header
        for line in f:
            total += 1
            parts = line.strip().split(',')
            if parts[0] == today_str:
                today_count += 1
            if parts[0] >= week_cutoff:
                week_count += 1

    return {'total': total, 'today': today_count, 'last_7_days': week_count}


# === Main Report ===

def generate_report(as_json=False):
    """Generate full campaign analytics report."""
    campaign_stats = get_campaign_stats()
    sender_scores = calculate_sender_scores()
    blacklist_stats = get_blacklist_stats()
    leads_stats = get_leads_stats()
    global_stats = get_global_send_stats()

    if as_json:
        report = {
            'date': date.today().isoformat(),
            'campaigns': campaign_stats,
            'sender_scores': sender_scores,
            'blacklist': blacklist_stats,
            'leads': leads_stats,
            'global': global_stats,
        }
        print(json.dumps(report, indent=2))
        return report

    # Text report
    print('=' * 65)
    print(f'  CAMPAIGN ANALYTICS REPORT — {date.today().isoformat()}')
    print('=' * 65)

    # Global overview
    print(f'\n  Global: {global_stats["total"]:,} total sends | '
          f'{global_stats["today"]} today | {global_stats["last_7_days"]} last 7d')
    print(f'  Leads: {leads_stats["total"]} total ({leads_stats["today"]} today)')
    print(f'  Blacklist: {blacklist_stats["total"]:,} entries ({blacklist_stats["today_added"]} added today)')

    # Per-campaign
    print(f'\n{"Campaign":<30} {"Today":>6} {"Total":>7} {"Failed":>7} {"Queue":>7}')
    print('-' * 65)
    for name, stats in campaign_stats.items():
        if 'error' in stats:
            print(f'  {name:<28} {stats["error"]}')
            continue
        print(f'  {name:<28} {stats["today_sent"]:>6} {stats["total_sent"]:>7} '
              f'{stats["total_failed"]:>7} {stats["remaining"]:>7}')

    # 7-day trend
    print(f'\n  7-Day Trend:')
    for name, stats in campaign_stats.items():
        if 'week_sends' not in stats:
            continue
        trend = ' '.join(f'{v}' for v in list(stats['week_sends'].values())[::-1])
        print(f'    {name}: {trend}')

    # Sender scores (top 10)
    if sender_scores:
        print(f'\n{"Sender":<35} {"Score":>6} {"Sent":>6} {"Bounce%":>8}')
        print('-' * 65)
        sorted_senders = sorted(sender_scores.items(), key=lambda x: x[1]['score'], reverse=True)
        for sender, data in sorted_senders[:10]:
            print(f'  {sender:<33} {data["score"]:>6.1f} {data["total_sent"]:>6} '
                  f'{data["bounce_rate"]:>7.2f}%')

        # Recommended delays
        print(f'\n  Recommended Delays:')
        for sender, data in sorted_senders[:10]:
            delay = get_dynamic_delay(sender)
            print(f'    {sender}: {delay}s', end='')
            if data['bounce_rate'] == 0:
                print(' (excellent)')
            elif data['bounce_rate'] <= 2:
                print(' (good)')
            else:
                print(' (needs attention)')

    print('\n' + '=' * 65)

    # Log the report
    try:
        with open(REPORT_LOG, 'a') as f:
            f.write(f'{datetime.now().isoformat()} Report generated: '
                    f'{global_stats["total"]} total, {global_stats["today"]} today, '
                    f'{leads_stats["total"]} leads, {blacklist_stats["total"]} blacklist\n')
    except Exception:
        pass

    return campaign_stats


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Campaign Analytics Report')
    parser.add_argument('--json', action='store_true', help='JSON output')
    parser.add_argument('--archive', action='store_true', help='Archive old log entries (>90 days)')
    parser.add_argument('--score', action='store_true', help='Show sender scores only')
    args = parser.parse_args()

    if args.archive:
        archive_old_logs()
        return

    if args.score:
        scores = calculate_sender_scores()
        for sender, data in sorted(scores.items(), key=lambda x: x[1]['score'], reverse=True):
            print(f'{sender:<35} score:{data["score"]:>6.1f}  sent:{data["total_sent"]:>6}  '
                  f'bounce:{data["bounce_rate"]:.2f}%  delay:{get_dynamic_delay(sender)}s')
        return

    generate_report(args.json)


if __name__ == '__main__':
    main()
