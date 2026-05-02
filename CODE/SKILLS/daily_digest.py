#!/usr/bin/env python3
"""
Daily Digest - Morning Telegram summary of campaign performance

Sends daily briefing at 8 AM with:
- Emails sent yesterday
- Bounce rate per campaign
- Hot leads received
- Campaigns running low
- Top performing sectors

Usage:
    python3 daily_digest.py                # Send digest now
    python3 daily_digest.py --preview      # Preview without sending
    python3 daily_digest.py --status       # Show digest history

Cron (8 AM daily):
    0 8 * * * /usr/bin/python3 /opt/ACTIVE/INFRA/SKILLS/daily_digest.py
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
CAEN_EXPORT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/CAEN_EXPORTS")
REPLIES_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/REPLIES")
STATE_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/.digest_state.json")
LOGS_DIR = Path("/opt/ACTIVE/INFRA/LOGS/campaigns")


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_digest": None, "digests_sent": 0}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def get_yesterday_stats():
    """Get email stats from yesterday's logs."""
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

    stats = {
        "total_sent": 0,
        "total_bounced": 0,
        "campaigns": {}
    }

    # Check campaign logs
    for log_file in LOGS_DIR.glob(f"*_{yesterday}.log"):
        campaign = log_file.stem.replace(f"_{yesterday}", "")

        sent = 0
        bounced = 0

        try:
            with open(log_file, 'r') as f:
                for line in f:
                    if "sent to" in line.lower() or "success" in line.lower():
                        sent += 1
                    if "bounce" in line.lower() or "failed" in line.lower():
                        bounced += 1
        except:
            pass

        if sent > 0 or bounced > 0:
            stats["campaigns"][campaign] = {
                "sent": sent,
                "bounced": bounced,
                "bounce_rate": round(bounced / max(sent, 1) * 100, 1)
            }
            stats["total_sent"] += sent
            stats["total_bounced"] += bounced

    return stats


def get_campaign_contacts():
    """Get contact counts per campaign."""
    contacts = {}

    for campaign_dir in CAMPAIGNS_DIR.iterdir():
        if not campaign_dir.is_dir():
            continue

        contacts_file = campaign_dir / "contacts" / "contacts.csv"
        if contacts_file.exists():
            try:
                with open(contacts_file, 'r') as f:
                    count = sum(1 for _ in f) - 1
                contacts[campaign_dir.name] = count
            except:
                pass

    return contacts


def get_sector_stats():
    """Get CAEN sector stats."""
    sectors = {}

    for filepath in CAEN_EXPORT_DIR.glob("*_with_email.csv"):
        sector = filepath.stem.replace("_with_email", "")

        try:
            with open(filepath, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

                total = len(rows)
                high_score = sum(1 for r in rows if int(r.get('score', 0) or 0) >= 50)

                sectors[sector] = {
                    "total": total,
                    "high_score": high_score
                }
        except:
            pass

    return sectors


def get_hot_leads_count():
    """Get count of interested replies."""
    classified_file = REPLIES_DIR / "classified_replies.csv"
    if not classified_file.exists():
        return 0

    try:
        with open(classified_file, 'r') as f:
            reader = csv.DictReader(f)
            return sum(1 for r in reader if r.get('category') == 'INTERESTED')
    except:
        return 0


def build_digest():
    """Build the daily digest message."""
    yesterday_stats = get_yesterday_stats()
    campaign_contacts = get_campaign_contacts()
    sector_stats = get_sector_stats()
    hot_leads = get_hot_leads_count()

    today = datetime.now().strftime("%Y-%m-%d")

    msg = f"📊 DAILY DIGEST - {today}\n\n"

    # Yesterday's performance
    msg += "📧 YESTERDAY'S SENDS:\n"
    if yesterday_stats['total_sent'] > 0:
        bounce_rate = round(yesterday_stats['total_bounced'] / yesterday_stats['total_sent'] * 100, 1)
        msg += f"  Total: {yesterday_stats['total_sent']} sent\n"
        msg += f"  Bounced: {yesterday_stats['total_bounced']} ({bounce_rate}%)\n"

        # Per campaign
        for camp, stats in sorted(yesterday_stats['campaigns'].items(), key=lambda x: -x[1]['sent'])[:5]:
            indicator = "🔴" if stats['bounce_rate'] > 5 else "🟢"
            msg += f"  {indicator} {camp}: {stats['sent']} ({stats['bounce_rate']}% bounce)\n"
    else:
        msg += "  No sends recorded\n"

    msg += "\n"

    # Hot leads
    if hot_leads > 0:
        msg += f"🔥 HOT LEADS: {hot_leads} interested replies\n\n"

    # Low campaigns
    low_campaigns = [(c, n) for c, n in campaign_contacts.items() if n < 100]
    if low_campaigns:
        msg += "⚠️ LOW CONTACTS:\n"
        for camp, count in sorted(low_campaigns, key=lambda x: x[1])[:5]:
            msg += f"  {camp}: {count} remaining\n"
        msg += "\n"

    # Top sectors
    msg += "📈 SECTOR LEADS:\n"
    for sector, stats in sorted(sector_stats.items(), key=lambda x: -x[1]['total'])[:5]:
        msg += f"  {sector}: {stats['total']} ({stats['high_score']} high-score)\n"

    # Summary
    total_leads = sum(s['total'] for s in sector_stats.values())
    total_contacts = sum(campaign_contacts.values())
    msg += f"\n📌 TOTALS: {total_leads} leads, {total_contacts} in campaigns"

    return msg


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Daily Digest")
    parser.add_argument("--preview", action="store_true", help="Preview without sending")
    parser.add_argument("--status", action="store_true", help="Show digest history")

    args = parser.parse_args()

    if args.status:
        state = load_state()
        print("\n=== Daily Digest Status ===\n")
        print(f"Last digest: {state.get('last_digest', 'Never')}")
        print(f"Total sent: {state.get('digests_sent', 0)}")
        return

    log("Building daily digest...")
    digest = build_digest()

    if args.preview:
        print("\n" + "="*50)
        print(digest)
        print("="*50)
        return

    send_telegram(digest)

    state = load_state()
    state['last_digest'] = datetime.now().isoformat()
    state['digests_sent'] = state.get('digests_sent', 0) + 1
    save_state(state)

    log("Digest sent!")


if __name__ == "__main__":
    main()
