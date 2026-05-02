#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
Norway DB Enricher - Scrapes company websites for HR/hiring emails.
Target: 95,398 companies with websites.
Rate: 2 req/sec, 500/run. Daily cron at 01:00.

Usage:
    python3 norway_db_enricher.py              # Run batch (500)
    python3 norway_db_enricher.py --limit 200  # Custom limit
    python3 norway_db_enricher.py --stats      # Show progress
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS')

import re
import time
import json
import logging
import argparse
import requests
import psycopg2
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

DB_CONFIG = dict(host='localhost', dbname='norway_emails', user='tudor', password='tudor')
CACHE_FILE = Path('/opt/ACTIVE/OPENDATA/DATA/ENRICHED/norway_hr_cache.json')
LOG_DIR = Path('/opt/ACTIVE/INFRA/LOGS/norway_enricher')
LOG_DIR.mkdir(parents=True, exist_ok=True)
CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / f"enrich_{datetime.now():%Y%m%d}.log")
    ]
)
logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
# Norwegian career/contact page paths
PATHS = ['', '/karriere', '/jobb', '/ledige-stillinger', '/kontakt', '/om-oss',
         '/contact', '/about', '/career', '/jobs']
# Skip these fake emails
SKIP_EMAILS = {'example.com', 'example.org', '.png', '.jpg', '.gif', 'wixpress.com', 'sentry.io'}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

try:
    from alerting import send_telegram
except Exception:
    def send_telegram(msg): pass


def load_cache():
    if CACHE_FILE.exists():
        return json.load(open(CACHE_FILE))
    return {}


def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)


def extract_domain(url):
    if not url:
        return None
    try:
        parsed = urlparse(url if url.startswith('http') else f'https://{url}')
        return parsed.netloc.lower().replace('www.', '')
    except Exception:
        return None


def find_hr_emails(website):
    """Scrape website for HR/hiring related emails."""
    domain = extract_domain(website)
    if not domain:
        return []

    found_emails = set()
    for path in PATHS:
        try:
            url = f'https://{domain}{path}'
            r = requests.get(url, headers=HEADERS, timeout=8, allow_redirects=True)
            if r.status_code == 200:
                emails = EMAIL_RE.findall(r.text)
                for email in emails:
                    email_lower = email.lower()
                    if not any(skip in email_lower for skip in SKIP_EMAILS):
                        found_emails.add(email_lower)
        except Exception:
            pass
        time.sleep(0.3)

    # Prioritize HR-related emails
    hr_keywords = ['hr@', 'karriere@', 'jobb@', 'rekruttering@', 'hiring@',
                    'career@', 'jobs@', 'recruitment@', 'personal@', 'ansettelse@']
    hr_emails = [e for e in found_emails if any(kw in e for kw in hr_keywords)]

    if hr_emails:
        return hr_emails[:3]
    return list(found_emails)[:3]


def show_stats():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM norway_emails WHERE website IS NOT NULL")
    with_website = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM norway_emails WHERE hr_email IS NOT NULL")
    enriched = cur.fetchone()[0]
    conn.close()

    cache = load_cache()
    print(f"\nWebsite Enrichment Progress")
    print(f"{'=' * 40}")
    print(f"Companies with website: {with_website:>8}")
    print(f"HR emails found:        {enriched:>8}")
    print(f"Domains in cache:       {len(cache):>8}")
    print(f"Remaining:              {with_website - len(cache):>8}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=500)
    parser.add_argument('--stats', action='store_true')
    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    cache = load_cache()
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Get companies with websites that havent been enriched
    cur.execute("""
        SELECT id, website, name FROM norway_emails
        WHERE website IS NOT NULL AND hr_email IS NULL
        ORDER BY employees_count DESC NULLS LAST
        LIMIT %s
    """, (args.limit * 2,))  # Fetch extra to skip cached
    rows = cur.fetchall()

    processed = 0
    found = 0

    for row_id, website, name in rows:
        if processed >= args.limit:
            break

        domain = extract_domain(website)
        if not domain or domain in cache:
            continue

        emails = find_hr_emails(website)
        cache[domain] = {'emails': emails, 'checked': datetime.now().isoformat()}

        if emails:
            hr_email = '; '.join(emails[:3])
            cur.execute(
                "UPDATE norway_emails SET hr_email = %s WHERE id = %s",
                (hr_email, row_id)
            )
            found += 1
            logger.info(f"[{processed+1}] {name}: {hr_email}")
        else:
            logger.debug(f"[{processed+1}] {name}: no emails found")

        processed += 1
        if processed % 50 == 0:
            conn.commit()
            save_cache(cache)
            logger.info(f"Progress: {processed}/{args.limit} (found: {found})")

        time.sleep(0.5)

    conn.commit()
    save_cache(cache)
    conn.close()

    logger.info(f"Done: {processed} processed, {found} HR emails found")
    try:
        send_telegram(f"Norway enricher: {processed} checked, {found} HR emails found")
    except Exception:
        pass


if __name__ == '__main__':
    main()
