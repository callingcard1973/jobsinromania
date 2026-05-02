#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
Norway Campaign Daily Report - Telegram digest at 20:00.
Per-campaign stats, bounce rates, response counts, enrichment progress.

Usage:
    python3 norway_campaign_report.py          # Send report
    python3 norway_campaign_report.py --print  # Print only, no Telegram
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS')

import argparse
import psycopg2
from datetime import datetime, date

DB_CONFIG = dict(host='localhost', dbname='norway_emails', user='tudor', password='tudor')

try:
    from alerting import send_telegram
except Exception:
    def send_telegram(msg): print(msg)

CAMPAIGNS = [
    'NORWAY_TIER1', 'NORWAY_CONSTRUCTION', 'NORWAY_HEALTHCARE', 'NORWAY_HORECA',
    'NORWAY_STAFFING', 'NORWAY_AGRICULTURE', 'NORWAY_LOGISTICS',
    'NORWAY_MANUFACTURING', 'NORWAY_IT_CONSULTING', 'NORWAY_VOLUME',
]


def get_report():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    today = date.today().isoformat()

    lines = [f"NORWAY CAMPAIGNS - {today}", "=" * 35]

    total_sent = 0
    total_today = 0
    total_bounces = 0

    for campaign in CAMPAIGNS:
        cur.execute("SELECT COUNT(*) FROM norway_send_log WHERE campaign = %s", (campaign,))
        sent = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM norway_send_log WHERE campaign = %s AND sent_at::date = %s", (campaign, today))
        sent_today = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM norway_send_log WHERE campaign = %s AND status = 'bounced'", (campaign,))
        bounces = cur.fetchone()[0]

        total_sent += sent
        total_today += sent_today
        total_bounces += bounces

        bounce_pct = f"{bounces/sent*100:.1f}%" if sent > 0 else "0%"

        if sent > 0 or sent_today > 0:
            short_name = campaign.replace('NORWAY_', '')
            lines.append(f"{short_name}: {sent_today} today / {sent} total (B:{bounce_pct})")

    lines.append("-" * 35)

    # Responses
    cur.execute("SELECT COUNT(*) FROM norway_responses")
    responses = cur.fetchone()[0]
    cur.execute("SELECT response_type, COUNT(*) FROM norway_responses GROUP BY response_type")
    resp_types = cur.fetchall()

    # Enrichment progress
    cur.execute("SELECT COUNT(*) FROM norway_emails WHERE employees_count IS NOT NULL")
    emp_filled = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM norway_emails WHERE hr_email IS NOT NULL")
    hr_found = cur.fetchone()[0]

    # Campaign status breakdown
    cur.execute("SELECT campaign_status, COUNT(*) FROM norway_emails GROUP BY campaign_status")
    statuses = dict(cur.fetchall())

    conn.close()

    lines.append(f"TOTAL: {total_today} today / {total_sent} sent / {total_bounces} bounced")
    lines.append(f"Responses: {responses}")
    for rtype, count in resp_types:
        lines.append(f"  {rtype}: {count}")
    lines.append(f"\nEnrichment:")
    lines.append(f"  Employee data: {emp_filled}/324898")
    lines.append(f"  HR emails: {hr_found}")
    lines.append(f"\nStatus: pending={statuses.get('pending', 0)} sent={statuses.get('sent', 0)} responded={statuses.get('responded', 0)}")

    # Bounce rate alert
    if total_sent > 100 and total_bounces / total_sent > 0.05:
        lines.append(f"\n!! ALERT: Bounce rate {total_bounces/total_sent*100:.1f}% > 5%")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--print', action='store_true', help='Print only')
    args = parser.parse_args()

    report = get_report()

    if args.print:
        print(report)
    else:
        print(report)
        try:
            send_telegram(report)
        except Exception as e:
            print(f"Telegram error: {e}")


if __name__ == '__main__':
    main()
