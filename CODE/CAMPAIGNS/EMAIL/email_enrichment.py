#!/usr/bin/env python3
"""
Email Enrichment Script — laptop-first, raspibig fallback.
Scrapes emails from company websites, updates interjob_master on raspibig.

Usage: python3 email_enrichment.py [--country RO] [--limit 1000]
"""

import re
import sys
import time
import signal
import logging
import argparse
import requests
import psycopg2
from urllib.parse import urlparse

DB = {"host": "192.168.100.21", "dbname": "interjob_master",
      "user": "tudor", "password": "tudor"}
DELAY = 1.0
TIMEOUT = 10
BATCH = 20
UA = "Mozilla/5.0 (compatible; BPP-Enrichment/1.0)"

EMAIL_RE = re.compile(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    re.IGNORECASE
)
SKIP_EMAILS = {
    'example.com', 'sentry.io', 'wixpress.com',
    'wordpress.com', 'w3.org', 'schema.org',
    'googleapis.com', 'google.com', 'facebook.com',
    'twitter.com', 'instagram.com', 'youtube.com'
}

import os
_log_dir = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(_log_dir, 'enrichment.log')),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

running = True
def handle_sig(s, f):
    global running
    running = False
    log.info("Stopping gracefully...")
signal.signal(signal.SIGTERM, handle_sig)
signal.signal(signal.SIGINT, handle_sig)


def is_valid_email(email):
    domain = email.split('@')[1].lower()
    if domain in SKIP_EMAILS:
        return False
    if len(email) > 100:
        return False
    if '.png' in email or '.jpg' in email or '.js' in email:
        return False
    return True


def scrape_email(url):
    if not url.startswith('http'):
        url = 'http://' + url
    try:
        r = requests.get(url, timeout=TIMEOUT, headers={'User-Agent': UA},
                         allow_redirects=True, verify=False)
        if r.status_code != 200:
            return None
        emails = EMAIL_RE.findall(r.text)
        for e in emails:
            e = e.lower().strip()
            if is_valid_email(e):
                return e
    except Exception:
        pass
    try:
        parsed = urlparse(url)
        contact_url = f"{parsed.scheme}://{parsed.netloc}/contact"
        r = requests.get(contact_url, timeout=TIMEOUT,
                         headers={'User-Agent': UA},
                         allow_redirects=True, verify=False)
        if r.status_code == 200:
            emails = EMAIL_RE.findall(r.text)
            for e in emails:
                e = e.lower().strip()
                if is_valid_email(e):
                    return e
    except Exception:
        pass
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--country', default='RO')
    parser.add_argument('--limit', type=int, default=5000)
    args = parser.parse_args()

    conn = psycopg2.connect(**DB)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, website FROM companies
        WHERE country = %s
          AND website IS NOT NULL AND website != ''
          AND (email IS NULL OR email = '')
        LIMIT %s
    """, (args.country, args.limit))

    rows = cur.fetchall()
    log.info(f"Found {len(rows)} companies in {args.country} "
             f"with website but no email")

    found = 0
    errors = 0
    for i, (cid, name, website) in enumerate(rows):
        if not running:
            break
        email = scrape_email(website)
        if email:
            cur.execute(
                "UPDATE companies SET email=%s, updated_at=NOW() "
                "WHERE id=%s", (email, cid))
            found += 1
            log.info(f"[{i+1}/{len(rows)}] {name}: {email}")
        else:
            errors += 1

        if (i + 1) % BATCH == 0:
            conn.commit()
            log.info(f"Progress: {i+1}/{len(rows)}, "
                     f"found={found}, errors={errors}")

        time.sleep(DELAY)

    conn.commit()
    cur.close()
    conn.close()
    log.info(f"DONE: {found} emails found out of "
             f"{len(rows)} companies ({args.country})")


if __name__ == '__main__':
    main()
