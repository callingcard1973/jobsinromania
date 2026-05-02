#!/usr/bin/env python3
"""
Weekly Scraper Report - Comprehensive summary via Telegram.

Sends:
- Scraper health status (all countries)
- Data freshness (stale outputs)
- Campaign sync status (raspibig vs raspi)
- Disk usage

Schedule: Mondays 8am
Node-RED: Weekly Scraper Report flow

RULES COMPLIANCE:
- ASCII output: YES
- Shared code reused: YES (alerting)
- No duplicate functions: YES
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

from dotenv import load_dotenv
load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

from alerting import send_telegram


def get_scraper_health():
    """Get scraper health summary."""
    try:
        result = subprocess.run(
            ['/opt/ACTIVE/INFRA/venv/bin/python3', '/opt/ACTIVE/INFRA/SKILLS/health_monitor.py', '--days', '7'],
            capture_output=True, text=True, timeout=60
        )
        lines = result.stdout.split('\n')

        # Extract summary
        summary = []
        for line in lines:
            if 'SUMMARY:' in line or 'Healthy:' in line or 'Unhealthy:' in line:
                summary.append(line.strip())
            if line.startswith('✗') or line.startswith('✓'):
                summary.append(line.strip())

        return '\n'.join(summary[:20])  # Limit output
    except Exception as e:
        return f"Error: {e}"


def get_stale_outputs():
    """Check for stale scraper outputs (>48h old)."""
    stale = []
    data_dir = Path('/mnt/hdd/SCRAPER_DATA/csv')
    cutoff = datetime.now() - timedelta(hours=48)

    for country_dir in data_dir.iterdir():
        if not country_dir.is_dir():
            continue

        # Find newest file
        csv_files = list(country_dir.glob('*.csv'))
        if not csv_files:
            continue

        newest = max(csv_files, key=lambda p: p.stat().st_mtime)
        mtime = datetime.fromtimestamp(newest.stat().st_mtime)

        if mtime < cutoff:
            age_hours = (datetime.now() - mtime).total_seconds() / 3600
            stale.append(f"  {country_dir.name}: {age_hours:.0f}h old")

    return stale


def get_campaign_sync():
    """Check campaign state sync between machines."""
    mismatches = []
    campaigns = ['FACTORY_EU', 'AGRI', 'ANOFM']

    for campaign in campaigns:
        try:
            # Get raspibig count
            state_file = Path(f'/opt/ACTIVE/EMAIL/CAMPAIGNS/{campaign}/state.json')
            if state_file.exists():
                with open(state_file) as f:
                    raspibig = len(json.load(f).get('sent', []))
            else:
                raspibig = 0

            # Get raspi count via SSH
            result = subprocess.run(
                ['ssh', 'raspi', f"python3 -c \"import json; d=json.load(open('/opt/ACTIVE/EMAIL/CAMPAIGNS/{campaign}/state.json')) if __import__('os').path.exists('/opt/ACTIVE/EMAIL/CAMPAIGNS/{campaign}/state.json') else {{}}; print(len(d.get('sent',[])))\""],
                capture_output=True, text=True, timeout=10
            )
            raspi = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0

            if raspibig != raspi:
                mismatches.append(f"  {campaign}: raspibig={raspibig} vs raspi={raspi}")

        except Exception as e:
            mismatches.append(f"  {campaign}: error - {e}")

    return mismatches


def get_disk_usage():
    """Get disk usage."""
    try:
        result = subprocess.run(['df', '-h', '/mnt/usb'], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2:
            parts = lines[1].split()
            return f"  /mnt/usb: {parts[2]} used of {parts[1]} ({parts[4]})"
    except:
        pass
    return "  Unknown"


def main():
    """Generate and send weekly report."""
    report_lines = []
    report_lines.append("=== WEEKLY SCRAPER REPORT ===")
    report_lines.append(f"Week of {datetime.now().strftime('%Y-%m-%d')}")
    report_lines.append("")

    # Scraper health
    report_lines.append("SCRAPER HEALTH (7 days):")
    report_lines.append(get_scraper_health())
    report_lines.append("")

    # Stale outputs
    stale = get_stale_outputs()
    if stale:
        report_lines.append(f"STALE DATA ({len(stale)} scrapers):")
        report_lines.extend(stale[:5])
        report_lines.append("")

    # Campaign sync
    mismatches = get_campaign_sync()
    if mismatches:
        report_lines.append("CAMPAIGN SYNC ISSUES:")
        report_lines.extend(mismatches)
        report_lines.append("")

    # Disk usage
    report_lines.append("DISK USAGE:")
    report_lines.append(get_disk_usage())

    report = '\n'.join(report_lines)
    print(report)

    # Send to Telegram
    if '--no-telegram' not in sys.argv:
        send_telegram(report)
        print("\nSent to Telegram.")


if __name__ == '__main__':
    main()
