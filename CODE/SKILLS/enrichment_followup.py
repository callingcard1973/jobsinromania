#!/usr/bin/env python3
"""Enrichment Follow-up - Monitor enrichment runs and alert on failures."""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import argparse
import os
from datetime import datetime, timedelta
from pathlib import Path
import psycopg2

from alerting import send_telegram

LOG_DIR = Path('/opt/ACTIVE/INFRA/LOGS/enricher')
ENRICHER_LOG = Path('/opt/LOGS/enrichment.log')

def get_db():
    return psycopg2.connect(dbname='interjob_master', user='tudor')

def check_log_freshness():
    """Check if enrichment ran in last 25 hours."""
    if not ENRICHER_LOG.exists():
        return False, "Log file missing"
    mtime = datetime.fromtimestamp(ENRICHER_LOG.stat().st_mtime)
    age = datetime.now() - mtime
    if age > timedelta(hours=25):
        return False, f"Stale: {age.total_seconds()/3600:.1f}h old"
    return True, f"Fresh: {age.total_seconds()/3600:.1f}h old"

def check_enrichment_stats():
    """Check enrichment yield from database (fast queries only)."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '5s'")
    stats = {}

    try:
        # EURES domains (small table, fast)
        cur.execute("SELECT COUNT(*) FROM eures_domains WHERE email IS NOT NULL")
        stats['eures_enriched'] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM eures_domains")
        stats['eures_total'] = cur.fetchone()[0]
    except:
        stats['eures_enriched'] = stats['eures_total'] = 0

    try:
        # Use reltuples estimate for large tables
        cur.execute("SELECT reltuples::bigint FROM pg_class WHERE relname='companies'")
        stats['companies_total'] = cur.fetchone()[0] or 0
        cur.execute("SELECT reltuples::bigint FROM pg_class WHERE relname='ted_winners'")
        stats['ted_enriched'] = cur.fetchone()[0] or 0
        stats['companies_enriched'] = 0  # Skip slow query
    except:
        stats['companies_total'] = stats['ted_enriched'] = stats['companies_enriched'] = 0

    conn.close()
    return stats

def check_recent_errors():
    """Scan logs for recent errors."""
    errors = []
    if LOG_DIR.exists():
        for log in LOG_DIR.glob('*.log'):
            try:
                content = log.read_text()[-5000:]  # Last 5KB
                if 'ERROR' in content or 'Exception' in content or 'Traceback' in content:
                    errors.append(log.name)
            except: pass
    return errors

def run_check(alert=True):
    """Run all checks and optionally alert."""
    print(f"=== Enrichment Follow-up: {datetime.now().strftime('%Y-%m-%d %H:%M')} ===\n")

    # Log freshness
    fresh, msg = check_log_freshness()
    status = "OK" if fresh else "ALERT"
    print(f"Log freshness: [{status}] {msg}")

    # Stats
    stats = check_enrichment_stats()
    eures_pct = stats['eures_enriched']/max(stats['eures_total'],1)*100
    comp_pct = stats['companies_enriched']/max(stats['companies_total'],1)*100

    print(f"\nEnrichment stats:")
    print(f"  EURES: {stats['eures_enriched']:,}/{stats['eures_total']:,} ({eures_pct:.1f}%)")
    print(f"  Companies: {stats['companies_enriched']:,}/{stats['companies_total']:,} ({comp_pct:.1f}%)")
    print(f"  TED emails: {stats['ted_enriched']:,}")

    # Errors
    errors = check_recent_errors()
    if errors:
        print(f"\nRecent errors in: {', '.join(errors)}")
    else:
        print(f"\nNo recent errors in logs")

    # Alert if issues
    if alert and (not fresh or errors):
        msg = f"Enrichment Alert:\n"
        if not fresh: msg += f"- Log stale: {check_log_freshness()[1]}\n"
        if errors: msg += f"- Errors in: {', '.join(errors)}\n"
        msg += f"\nStats: EURES {eures_pct:.0f}%, Companies {comp_pct:.0f}%"
        send_telegram(msg)
        print(f"\nTelegram alert sent")

    return fresh and not errors

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--check', '-c', action='store_true', help='Run checks')
    p.add_argument('--no-alert', action='store_true', help='No Telegram alert')
    p.add_argument('--stats', '-s', action='store_true', help='Stats only')
    a = p.parse_args()

    if a.stats:
        stats = check_enrichment_stats()
        for k, v in stats.items():
            print(f"{k}: {v:,}")
        return

    run_check(alert=not a.no_alert)

if __name__ == '__main__': main()
