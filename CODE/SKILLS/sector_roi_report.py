#!/usr/bin/env python3
"""
Sector ROI Report - Analyze which sectors convert best

Metrics:
- Sends per sector
- Opens/clicks (if tracked)
- Replies received
- Interested responses
- Cost per lead (estimated)

Usage:
    python3 sector_roi_report.py                  # Full report
    python3 sector_roi_report.py --sector horeca  # Single sector
    python3 sector_roi_report.py --days 30        # Last 30 days
    python3 sector_roi_report.py --export         # Export to CSV
    python3 sector_roi_report.py --telegram       # Send summary

Analyzes campaign logs and reply data.
"""

import os
import sys
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

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
CONVERSATIONS_DB = Path("/opt/ACTIVE/OPENDATA/DATA/CONVERSATIONS/conversations.json")
STATE_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/.sector_roi_state.json")
LOGS_DIR = Path("/opt/ACTIVE/INFRA/LOGS/campaigns")

# Sector to campaign mapping
SECTOR_CAMPAIGNS = {
    "horeca": ["LUCIAN_HORECA_2026", "HORECA2026"],
    "construction": ["CONSTRUCT2026", "CONSTRUCTION_EU"],
    "manufacturing": ["FACTORYJOBS", "FACTORY_EU"],
    "transport": ["TRANSPORT_EU"],
    "agriculture": ["AGRI"],
    "retail": ["FACTORY_EU"],
    "recruitment": ["AGENCIES_EUROPE"],
    "it_services": ["FACTORY_EU"],
    "call_centers": ["FACTORY_EU"],
}


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def count_sector_leads():
    """Count leads per sector from CAEN exports."""
    counts = {}

    for filepath in CAEN_EXPORT_DIR.glob("*_with_email.csv"):
        sector = filepath.stem.replace("_with_email", "")
        try:
            with open(filepath, 'r') as f:
                count = sum(1 for _ in f) - 1
            counts[sector] = count
        except:
            pass

    return counts


def count_campaign_sends(campaign_name, days=30):
    """Count sends for campaign from logs."""
    total_sends = 0

    for i in range(days):
        date_str = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
        log_file = LOGS_DIR / f"{campaign_name}_{date_str}.log"

        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    content = f.read().lower()
                    total_sends += content.count('sent to') + content.count('success')
            except:
                pass

    return total_sends


def count_sector_sends(sector, days=30):
    """Count sends for sector across campaigns."""
    total = 0
    campaigns = SECTOR_CAMPAIGNS.get(sector, [])

    for campaign in campaigns:
        total += count_campaign_sends(campaign, days)

    return total


def count_sector_replies(sector):
    """Count replies for sector from conversations."""
    if not CONVERSATIONS_DB.exists():
        return {"total": 0, "interested": 0, "questions": 0}

    try:
        with open(CONVERSATIONS_DB) as f:
            convos = json.load(f)
    except:
        return {"total": 0, "interested": 0, "questions": 0}

    counts = {"total": 0, "interested": 0, "questions": 0}

    for email_hash, convo in convos.items():
        lead_info = convo.get('lead_info', {})
        if lead_info.get('sector') == sector:
            counts['total'] += len(convo.get('messages', []))

            status = convo.get('status', '')
            if status == 'hot':
                counts['interested'] += 1
            elif status == 'engaged':
                counts['questions'] += 1

    return counts


def calculate_sector_roi(sector, days=30):
    """Calculate ROI metrics for sector."""
    leads = count_sector_leads().get(sector, 0)
    sends = count_sector_sends(sector, days)
    replies = count_sector_replies(sector)

    roi = {
        'sector': sector,
        'total_leads': leads,
        'sends_last_n_days': sends,
        'days': days,
        'total_replies': replies['total'],
        'interested': replies['interested'],
        'questions': replies['questions'],
        'send_rate': round(sends / max(leads, 1) * 100, 1),
        'reply_rate': round(replies['total'] / max(sends, 1) * 100, 2),
        'interest_rate': round(replies['interested'] / max(sends, 1) * 100, 2),
        'score': 0
    }

    # Calculate overall score (0-100)
    roi['score'] = min(100, int(
        roi['interest_rate'] * 20 +
        roi['reply_rate'] * 5 +
        roi['send_rate'] * 0.2
    ))

    return roi


def generate_report(days=30, sectors=None):
    """Generate full ROI report."""
    if sectors is None:
        sectors = list(SECTOR_CAMPAIGNS.keys())

    report = []

    for sector in sectors:
        roi = calculate_sector_roi(sector, days)
        report.append(roi)

    # Sort by score
    report.sort(key=lambda x: x['score'], reverse=True)

    return report


def print_report(report):
    """Print formatted report."""
    print("\n" + "="*60)
    print("SECTOR ROI REPORT")
    print("="*60)

    for roi in report:
        indicator = "🟢" if roi['score'] >= 50 else "🟡" if roi['score'] >= 25 else "🔴"
        print(f"\n{indicator} {roi['sector'].upper()} (score: {roi['score']})")
        print(f"  Leads: {roi['total_leads']}")
        print(f"  Sends ({roi['days']}d): {roi['sends_last_n_days']}")
        print(f"  Replies: {roi['total_replies']} ({roi['reply_rate']}%)")
        print(f"  Interested: {roi['interested']} ({roi['interest_rate']}%)")

    print("\n" + "="*60)


def export_report(report, output_file=None):
    """Export report to CSV."""
    output_file = output_file or Path("/opt/ACTIVE/OPENDATA/DATA/sector_roi_report.csv")

    fieldnames = ['sector', 'total_leads', 'sends_last_n_days', 'total_replies',
                  'interested', 'questions', 'reply_rate', 'interest_rate', 'score']

    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(report)

    log(f"Exported to {output_file}")


def send_telegram_summary(report):
    """Send summary via Telegram."""
    msg = "📊 SECTOR ROI REPORT\n\n"

    for roi in report[:5]:
        indicator = "🟢" if roi['score'] >= 50 else "🟡" if roi['score'] >= 25 else "🔴"
        msg += f"{indicator} {roi['sector']}: {roi['score']} pts\n"
        msg += f"   {roi['interested']} interested ({roi['interest_rate']}%)\n"

    msg += f"\nTop performer: {report[0]['sector'].upper()}"

    send_telegram(msg)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Sector ROI Report")
    parser.add_argument("--sector", help="Single sector to analyze")
    parser.add_argument("--days", type=int, default=30, help="Days to analyze")
    parser.add_argument("--export", action="store_true", help="Export to CSV")
    parser.add_argument("--telegram", action="store_true", help="Send via Telegram")

    args = parser.parse_args()

    sectors = [args.sector] if args.sector else None
    report = generate_report(args.days, sectors)

    print_report(report)

    if args.export:
        export_report(report)

    if args.telegram:
        send_telegram_summary(report)


if __name__ == "__main__":
    main()
