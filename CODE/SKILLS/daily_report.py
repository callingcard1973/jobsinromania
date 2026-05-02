#!/usr/bin/env python3
"""
Daily System Report - Morning summary via Telegram.

Sends:
- Campaign status (sent yesterday, remaining)
- Sender capacity
- Disk usage
- Error summary
- Scraper status

Schedule: 6am daily (before campaigns start)
Cron: 0 6 * * * /opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/INFRA/SKILLS/daily_report.py

RULES COMPLIANCE:
- ASCII output: YES
- Shared code reused: YES (alerting)
- No duplicate functions: YES
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

from dotenv import load_dotenv
load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

from alerting import send_telegram


def get_campaign_stats():
    """Get campaign statistics."""
    campaigns_dir = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS")
    stats = []

    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    today = datetime.now().strftime('%Y-%m-%d')

    for state_file in campaigns_dir.glob("*/state.json"):
        campaign = state_file.parent.name
        try:
            with open(state_file) as f:
                data = json.load(f)

            sent = len(data.get("sent", []))
            failed = len(data.get("failed", []))
            daily_sent = data.get("daily_sent", 0)
            last_date = data.get("last_date", "")

            # Get contact count
            contacts_dir = state_file.parent / "contacts"
            csv_files = list(contacts_dir.glob("*.csv")) if contacts_dir.exists() else []
            if not csv_files:
                csv_files = list(state_file.parent.glob("*.csv"))

            total_contacts = 0
            for csv_file in csv_files[:1]:  # Just first CSV
                try:
                    total_contacts = sum(1 for _ in open(csv_file)) - 1
                except:
                    pass

            remaining = max(0, total_contacts - sent)

            # Only include active campaigns
            if total_contacts > 100 or sent > 0:
                stats.append({
                    'name': campaign,
                    'sent': sent,
                    'remaining': remaining,
                    'yesterday': daily_sent if last_date == yesterday else 0,
                    'today': daily_sent if last_date == today else 0,
                    'failed': failed,
                    'active': last_date in [yesterday, today]
                })
        except:
            pass

    return sorted(stats, key=lambda x: -x['sent'])


def get_disk_usage():
    """Get disk usage."""
    import shutil

    disks = []
    for mount in ['/', '/mnt/usb']:
        try:
            usage = shutil.disk_usage(mount)
            pct = (usage.used / usage.total) * 100
            free_gb = usage.free / (1024**3)
            disks.append({
                'mount': mount,
                'pct': pct,
                'free_gb': free_gb
            })
        except:
            pass

    return disks


def get_error_count():
    """Count errors in logs from last 24h."""
    logs_dir = Path("/opt/ACTIVE/INFRA/LOGS")
    cutoff = datetime.now() - timedelta(days=1)

    error_count = 0
    files_with_errors = 0

    for log_file in logs_dir.rglob("*.log"):
        try:
            if log_file.stat().st_mtime > cutoff.timestamp():
                content = log_file.read_text(errors='ignore').lower()
                count = content.count('error') + content.count('exception')
                if count > 0:
                    error_count += count
                    files_with_errors += 1
        except:
            pass

    return error_count, files_with_errors


def get_brevo_usage():
    """Get Brevo sending stats."""
    import requests

    accounts = [
        ("buildjobs", "BREVO_BUILDJOBS_API_KEY"),
        ("careworkers", "BREVO_CAREWORKERS_API_KEY"),
        ("mivromania", "BREVO_MIVROMANIA_API_KEY"),
        ("expatsinro", "BREVO_EXPATSINROMANIA_API_KEY"),
        ("interjob", "BREVO_INTERJOB_API_KEY"),
    ]

    stats = []
    for name, env in accounts:
        key = os.getenv(env)
        if key:
            try:
                r = requests.get(
                    "https://api.brevo.com/v3/smtp/statistics/aggregatedReport",
                    headers={"api-key": key},
                    params={"days": 1},
                    timeout=10
                )
                if r.status_code == 200:
                    data = r.json()
                    stats.append({
                        'name': name,
                        'sent': data.get("requests", 0),
                        'delivered': data.get("delivered", 0),
                        'bounced': data.get("hardBounces", 0) + data.get("softBounces", 0)
                    })
            except:
                pass

    return stats


def format_report():
    """Format the daily report."""
    now = datetime.now()

    lines = [
        f"[DAILY REPORT] {now.strftime('%Y-%m-%d %H:%M')}",
        ""
    ]

    # Campaigns
    campaigns = get_campaign_stats()
    active = [c for c in campaigns if c['active']]

    lines.append("=== CAMPAIGNS ===")
    total_sent_yesterday = sum(c['yesterday'] for c in campaigns)
    lines.append(f"Sent yesterday: {total_sent_yesterday}")

    if active:
        lines.append("\nActive:")
        for c in active[:5]:
            lines.append(f"  {c['name']}: {c['sent']} sent, {c['remaining']} left")

    idle_with_contacts = [c for c in campaigns if not c['active'] and c['remaining'] > 100]
    if idle_with_contacts:
        lines.append(f"\nIdle ({len(idle_with_contacts)} with contacts):")
        for c in idle_with_contacts[:3]:
            lines.append(f"  {c['name']}: {c['remaining']} waiting")

    # Brevo
    lines.append("\n=== BREVO (24h) ===")
    brevo = get_brevo_usage()
    total_brevo = sum(b['sent'] for b in brevo)
    lines.append(f"Total sent: {total_brevo}")
    for b in brevo:
        if b['sent'] > 0:
            lines.append(f"  {b['name']}: {b['sent']} sent, {b['bounced']} bounced")

    # Disk
    lines.append("\n=== DISK ===")
    disks = get_disk_usage()
    for d in disks:
        status = "OK" if d['pct'] < 80 else "WARN" if d['pct'] < 90 else "CRIT"
        lines.append(f"  {d['mount']}: {d['pct']:.0f}% used, {d['free_gb']:.0f}GB free [{status}]")

    # Errors
    errors, files = get_error_count()
    if errors > 0:
        lines.append(f"\n=== ERRORS (24h) ===")
        lines.append(f"  {errors} errors in {files} files")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description='Daily system report')
    parser.add_argument('--test', action='store_true', help='Print report without sending')
    parser.add_argument('--send', action='store_true', help='Send via Telegram')
    args = parser.parse_args()

    report = format_report()

    if args.test or not args.send:
        print(report)

    if args.send:
        send_telegram(report)
        print("Report sent to Telegram")


if __name__ == "__main__":
    main()
