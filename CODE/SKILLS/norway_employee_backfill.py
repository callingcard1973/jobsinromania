#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
Norway Employee Count Backfill - Fetches employee data from Bronnysundregistrene API.
Target: ~297K companies with NULL employees_count.
Rate: 5 req/sec, 1000/run. Daily cron at 03:00.

Usage:
    python3 norway_employee_backfill.py              # Run batch (1000)
    python3 norway_employee_backfill.py --limit 500  # Custom limit
    python3 norway_employee_backfill.py --stats      # Show progress
"""
import sys
import time
import logging
import argparse
import requests
import psycopg2
from datetime import datetime
from pathlib import Path

DB_CONFIG = dict(host='localhost', dbname='norway_emails', user='tudor', password='tudor')
API_BASE = 'https://data.brreg.no/enhetsregisteret/api/enheter'
LOG_DIR = Path('/opt/ACTIVE/INFRA/LOGS/norway_backfill')
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / f"backfill_{datetime.now():%Y%m%d}.log")
    ]
)
logger = logging.getLogger(__name__)

try:
    from alerting import send_telegram
except Exception:
    def send_telegram(msg): pass


def get_employee_count(org_number):
    """Fetch employee count from Bronnysundregistrene API."""
    try:
        r = requests.get(f"{API_BASE}/{org_number}", timeout=10,
                         headers={'Accept': 'application/json'})
        if r.status_code == 200:
            data = r.json()
            emp = data.get('antallAnsatte')
            return emp if emp is not None else 0
        elif r.status_code == 404:
            return -1  # Not found
        else:
            return None  # Error, retry later
    except Exception:
        return None


def update_tier(employees_count):
    """Calculate tier from employee count."""
    if employees_count is None or employees_count < 0:
        return 'T4'
    if employees_count >= 1000:
        return 'T1'
    if employees_count >= 50:
        return 'T2'
    if employees_count >= 1:
        return 'T3'
    return 'T4'


def show_stats():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM norway_emails WHERE employees_count IS NULL")
    null_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM norway_emails WHERE employees_count IS NOT NULL")
    filled = cur.fetchone()[0]
    cur.execute("SELECT tier, COUNT(*) FROM norway_emails GROUP BY tier ORDER BY tier")
    tiers = cur.fetchall()
    conn.close()

    print(f"\nEmployee Backfill Progress")
    print(f"{'=' * 40}")
    print(f"Filled:    {filled:>8}")
    print(f"Remaining: {null_count:>8}")
    print(f"Progress:  {filled/(filled+null_count)*100:.1f}%")
    print(f"\nTier breakdown:")
    for tier, count in tiers:
        print(f"  {tier}: {count:>8}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=1000)
    parser.add_argument('--stats', action='store_true')
    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Get companies with NULL employees_count
    cur.execute(
        "SELECT id, org_number FROM norway_emails WHERE employees_count IS NULL AND org_number IS NOT NULL LIMIT %s",
        (args.limit,)
    )
    rows = cur.fetchall()
    logger.info(f"Processing {len(rows)} companies")

    updated = 0
    errors = 0
    not_found = 0

    for i, (row_id, org_number) in enumerate(rows):
        if not org_number:
            continue

        emp = get_employee_count(org_number)

        if emp is None:
            errors += 1
            if errors > 50:
                logger.warning("Too many errors, stopping")
                break
        elif emp == -1:
            not_found += 1
            cur.execute(
                "UPDATE norway_emails SET employees_count = 0, tier = 'T4' WHERE id = %s",
                (row_id,)
            )
        else:
            tier = update_tier(emp)
            cur.execute(
                "UPDATE norway_emails SET employees_count = %s, tier = %s WHERE id = %s",
                (emp, tier, row_id)
            )
            updated += 1

        if (i + 1) % 100 == 0:
            conn.commit()
            logger.info(f"Progress: {i+1}/{len(rows)} (updated:{updated} errors:{errors})")

        # Rate limit: 5 req/sec
        time.sleep(0.2)

    conn.commit()
    conn.close()

    logger.info(f"Done: {updated} updated, {not_found} not found, {errors} errors")
    try:
        send_telegram(f"Norway backfill: {updated} updated, {not_found} not found, {errors} errors")
    except Exception:
        pass


if __name__ == '__main__':
    main()
