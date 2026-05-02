#!/usr/bin/env python3
"""
ANOFM Scraper → romania_emails DB Auto-Feed
Replaces old CSV-based scraper_to_campaigns.py for ANOFM/HIGH_VOLUME/NEW_EMPLOYERS.
Inserts new contacts directly into romania_emails.contacts PostgreSQL table.

Usage:
    python3 anofm_feed_db.py                # Feed latest scrape
    python3 anofm_feed_db.py --dry-run      # Show what would be added
    python3 anofm_feed_db.py --stats        # Show DB stats
"""
import sys
import os
import csv
import re
import argparse
from datetime import datetime
from pathlib import Path
from glob import glob

import psycopg2

# --
DB = {"host": "localhost", "dbname": "romania_emails", "user": "tudor", "password": "tudor"}
SCRAPER_DATA = Path("/opt/ACTIVE/SCRAPER_DATA/csv")
ANOFM_DIR = SCRAPER_DATA / "ANOFM"
TARGETS_DIR = SCRAPER_DATA / "ANOFM_TARGETS"
SEGMENTS_DIR = SCRAPER_DATA / "ANOFM_SEGMENTS"

TYPO_DOMAINS = {
    'gamil.com': 'gmail.com', 'gmial.com': 'gmail.com', 'gmal.com': 'gmail.com',
    'gnail.com': 'gmail.com', 'gmai.com': 'gmail.com', 'gmail.ro': 'gmail.com',
    'hotmal.com': 'hotmail.com', 'hotmai.com': 'hotmail.com',
    'yaho.com': 'yahoo.com', 'yahooo.com': 'yahoo.com',
    'outlok.com': 'outlook.com', 'outloo.com': 'outlook.com',
}

GOV_RE = re.compile(r'@(gov\.ro|edu\.ro|mil\.ro|politia\.ro|anaf\.ro|anofm\.ro|cnp\.ro)$', re.I)
EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

# --
def fix_email(email):
    if not email or '@' not in email:
        return None
    email = email.strip().lower()
    try:
        email.encode('ascii')
    except UnicodeEncodeError:
        return None
    for typo, correct in TYPO_DOMAINS.items():
        if email.endswith(typo):
            email = email.replace(typo, correct)
    if not EMAIL_RE.match(email):
        return None
    if GOV_RE.search(email):
        return None
    return email

def get_latest_file(path, pattern):
    files = sorted(glob(str(path / pattern)), key=lambda x: Path(x).stat().st_mtime, reverse=True)
    return Path(files[0]) if files else None

def load_csv_contacts(filepath, source_label, caen_override=None):
    """Load contacts from ANOFM CSV. Returns list of dicts."""
    contacts = []
    with open(filepath, 'r', encoding='utf-8-sig', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = fix_email(row.get('email_1', '') or row.get('email', ''))
            if not email:
                continue
            caen = caen_override or row.get('caen', row.get('nace', '')).strip()[:10]
            contacts.append({
                'email': email,
                'company_name': row.get('company_name', '').strip()[:200],
                'phone': row.get('phone_1', '').strip()[:50],
                'city': row.get('city', row.get('cities', '')).strip()[:100],
                'county': row.get('county', '').strip()[:50],
                'caen': caen,
                'country': 'RO',
                'source': source_label,
                'source_file': filepath.name,
            })
    return contacts

def insert_contacts(contacts, dry_run=False):
    """Insert new contacts into romania_emails.contacts. Returns count inserted."""
    if not contacts:
        return 0
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    inserted = 0
    skipped = 0
    for c in contacts:
        if dry_run:
            cur.execute(
                "SELECT 1 FROM contacts WHERE COALESCE(lower(email),'') = %s AND source = %s AND COALESCE(source_file,'') = %s",
                (c['email'], c['source'], c['source_file'])
            )
            if cur.fetchone():
                skipped += 1
            else:
                inserted += 1
            continue
        try:
            cur.execute("""
                INSERT INTO contacts (email, company_name, phone, city, county, caen, country, source, source_file, imported_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (COALESCE(lower(email),''), source, COALESCE(source_file,'')) DO NOTHING
            """, (c['email'], c['company_name'], c['phone'], c['city'], c['county'], c['caen'], c['country'], c['source'], c['source_file']))
            if cur.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            skipped += 1
    if not dry_run:
        conn.commit()
    cur.close()
    conn.close()
    return inserted, skipped

def feed_all(dry_run=False):
    """Feed all ANOFM sources into DB."""
    total_inserted = 0
    total_skipped = 0

    sources = [
        (ANOFM_DIR, 'anofm_jobs_*.csv', 'ANOFM_SCRAPES', None),
        (TARGETS_DIR, 'high_volume_*.csv', 'ANOFM_TARGETS', None),
        (TARGETS_DIR, 'new_employers_*.csv', 'ANOFM_TARGETS', None),
    ]
    # Add segment files with CAEN mapping
    SEGMENT_CAEN = {
        'horeca': '56', 'factory': '25', 'construction': '41',
        'transport': '49', 'retail': '47', 'agri': '01',
    }
    for seg, caen in SEGMENT_CAEN.items():
        sources.append((SEGMENTS_DIR, f'anofm_{seg}_*.csv', 'ANOFM_SEGMENTS', caen))

    for path, pattern, source, caen_override in sources:
        f = get_latest_file(path, pattern)
        if not f:
            continue
        age_h = (datetime.now().timestamp() - f.stat().st_mtime) / 3600
        if age_h > 48:
            continue
        contacts = load_csv_contacts(f, source, caen_override)
        if not contacts:
            continue
        ins, skip = insert_contacts(contacts, dry_run)
        label = 'would add' if dry_run else 'added'
        print("  %s: %d emails, %d %s, %d existing | %s (%.1fh old)" % (
            source, len(contacts), ins, label, skip, f.name, age_h))
        total_inserted += ins
        total_skipped += skip

    return total_inserted, total_skipped

def show_stats():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("SELECT source, COUNT(*), COUNT(CASE WHEN campaign_status IS NULL OR campaign_status='pending' THEN 1 END) FROM contacts GROUP BY source ORDER BY COUNT(*) DESC")
    rows = cur.fetchall()
    print("%-20s %8s %8s" % ("Source", "Total", "Pending"))
    print("-" * 40)
    for r in rows:
        print("%-20s %8d %8d" % (r[0], r[1], r[2]))
    cur.close()
    conn.close()

# --
def main():
    p = argparse.ArgumentParser(description='ANOFM → romania_emails DB feed')
    p.add_argument('--dry-run', '-n', action='store_true')
    p.add_argument('--stats', '-s', action='store_true')
    args = p.parse_args()

    if args.stats:
        show_stats()
        return

    print("=== ANOFM DB Feed %s ===" % datetime.now().strftime('%Y-%m-%d %H:%M'))
    ins, skip = feed_all(args.dry_run)
    mode = "DRY RUN" if args.dry_run else "DONE"
    print("--- %s: %d new, %d existing ---" % (mode, ins, skip))

if __name__ == '__main__':
    main()
