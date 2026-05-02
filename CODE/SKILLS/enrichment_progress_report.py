#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
Enrichment Progress Report - Send via Email and Telegram
Usage: python3 enrichment_progress_report.py
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import json
from pathlib import Path
from datetime import datetime

from alerting import send_telegram, send_email

OUTPUT_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/ENRICHED')
GERMANY_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/GERMANY_ENRICHED')
LOG_DIR = Path('/opt/ACTIVE/INFRA/LOGS/enricher')

COUNTRIES = [
    ('DE', 'Germany', GERMANY_DIR / 'Germany_ENRICHED_MASTER.csv'),
    ('NO', 'Norway', OUTPUT_DIR / 'NO_ENRICHED.csv'),
    ('DK', 'Denmark', OUTPUT_DIR / 'DK_ENRICHED.csv'),
    ('PL', 'Poland', OUTPUT_DIR / 'PL_ENRICHED_MASTER.csv'),
    ('SE', 'Sweden', OUTPUT_DIR / 'SE_ENRICHED_MASTER.csv'),
    ('FI', 'Finland', OUTPUT_DIR / 'FI_ENRICHED_MASTER.csv'),
    ('AT', 'Austria', OUTPUT_DIR / 'AT_ENRICHED_MASTER.csv'),
    ('CH', 'Switzerland', OUTPUT_DIR / 'CH_ENRICHED_MASTER.csv'),
    ('NL', 'Netherlands', OUTPUT_DIR / 'NL_ENRICHED_MASTER.csv'),
    ('BE', 'Belgium', OUTPUT_DIR / 'BE_ENRICHED_MASTER.csv'),
    ('IS', 'Iceland', OUTPUT_DIR / 'IS_ENRICHED_MASTER.csv'),
    ('UK', 'UK', OUTPUT_DIR / 'UK_ENRICHED_MASTER.csv'),
    ('FR', 'France', OUTPUT_DIR / 'FR_ENRICHED_MASTER.csv'),
    ('ES', 'Spain', OUTPUT_DIR / 'ES_ENRICHED_MASTER.csv'),
    ('IT', 'Italy', OUTPUT_DIR / 'IT_ENRICHED_MASTER.csv'),
    ('IE', 'Ireland', OUTPUT_DIR / 'IE_ENRICHED_MASTER.csv'),
]


def count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with open(path) as f:
        return max(0, len(f.readlines()) - 1)


def check_running():
    """Check if enricher is still running."""
    import subprocess
    result = subprocess.run(['pgrep', '-f', 'run_all_enrichers'], capture_output=True)
    return result.returncode == 0


def get_current_country():
    """Get which country is currently being processed from log."""
    log_file = LOG_DIR / 'all_enrichers.log'
    if not log_file.exists():
        return "Unknown"

    with open(log_file) as f:
        lines = f.readlines()

    for line in reversed(lines):
        if '===' in line and '/' in line:
            # Extract country from lines like "=== [4/16] POLAND: ..."
            parts = line.split(']')
            if len(parts) > 1:
                country = parts[1].split(':')[0].strip()
                return country
    return "Unknown"


def generate_report():
    """Generate progress report."""
    total = 0
    rows = []

    for code, name, path in COUNTRIES:
        count = count_csv_rows(path)
        total += count
        if count > 0:
            rows.append(f"  {name}: {count:,}")

    running = check_running()
    current = get_current_country() if running else "Completed"

    report = f"""ENRICHMENT PROGRESS REPORT
{datetime.now().strftime('%Y-%m-%d %H:%M')}

Status: {'RUNNING' if running else 'COMPLETED'}
Current: {current}

ENRICHED COMPANIES BY COUNTRY:
{chr(10).join(rows) if rows else '  (none yet)'}

TOTAL ENRICHED: {total:,} companies

Monitor: tail -f /opt/ACTIVE/INFRA/LOGS/enricher/all_enrichers.log
"""
    return report, total, running


def main():
    report, total, running = generate_report()

    print(report)

    # Send Telegram
    try:
        send_telegram(report)
        print("Telegram sent")
    except Exception as e:
        print(f"Telegram failed: {e}")

    # Send Email
    try:
        subject = f"Enrichment Progress: {total:,} companies"
        if not running:
            subject = f"Enrichment COMPLETE: {total:,} companies"

        send_email(subject, report)
        print("Email sent")
    except Exception as e:
        print(f"Email failed: {e}")


if __name__ == '__main__':
    main()
