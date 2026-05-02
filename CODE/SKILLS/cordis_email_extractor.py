#!/usr/bin/env python3
"""
CORDIS Website Email Extractor

Extracts contact emails from CORDIS organization websites.

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/cordis_email_extractor.py --country DE --limit 100
    python3 /opt/ACTIVE/INFRA/SKILLS/cordis_email_extractor.py --all --workers 5
    python3 /opt/ACTIVE/INFRA/SKILLS/cordis_email_extractor.py --stats
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import re
import csv
import sqlite3
import argparse
import concurrent.futures
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple
from urllib.parse import urlparse
import ssl
import urllib.request

from skills_common import to_ascii, sanitize

# ============================================================
# CONFIGURATION
# ============================================================

EU_DB_PATH = Path('/opt/ACTIVE/OPENDATA/DATA/EU_ENRICHED/eu_data.db')
ENRICHMENT_DB = Path('/opt/ACTIVE/OPENDATA/DATA/EU_ENRICHED/cordis_emails.db')
OUTPUT_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/EU_PROCUREMENT')

# Email regex pattern
EMAIL_PATTERN = re.compile(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    re.IGNORECASE
)

# Domains to exclude
EXCLUDE_DOMAINS = {
    'example.com', 'example.org', 'test.com', 'localhost',
    'facebook.com', 'twitter.com', 'linkedin.com', 'instagram.com',
    'youtube.com', 'tiktok.com', 'pinterest.com', 'google.com',
    'apple.com', 'microsoft.com', 'amazon.com', 'cloudflare.com',
    'w3.org', 'schema.org', 'jquery.com', 'wordpress.org',
}

# Invalid email patterns
INVALID_PATTERNS = [
    r'@sentry\.io',
    r'@wixpress\.com',
    r'@.*\.png',
    r'@.*\.jpg',
    r'@.*\.gif',
    r'\.png@',
    r'\.jpg@',
]

# ============================================================
# DATABASE
# ============================================================

def init_enrichment_db():
    """Initialize enrichment database."""
    ENRICHMENT_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(ENRICHMENT_DB))
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS email_results (
            org_id TEXT PRIMARY KEY,
            org_name TEXT,
            country TEXT,
            website TEXT,
            emails TEXT,
            email_count INTEGER,
            status TEXT,
            extracted_date TEXT
        )
    ''')

    cur.execute('CREATE INDEX IF NOT EXISTS idx_country ON email_results(country)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_status ON email_results(status)')

    conn.commit()
    return conn

# ============================================================
# EMAIL EXTRACTION
# ============================================================

def is_valid_email(email: str) -> bool:
    """Check if email is valid."""
    email = email.lower().strip()

    # Basic checks
    if not email or '@' not in email or len(email) > 254:
        return False

    # Check excluded domains
    domain = email.split('@')[1] if '@' in email else ''
    if any(ex in domain for ex in EXCLUDE_DOMAINS):
        return False

    # Check invalid patterns
    for pattern in INVALID_PATTERNS:
        if re.search(pattern, email, re.IGNORECASE):
            return False

    # Must have valid TLD
    if not re.match(r'.+\.[a-z]{2,}$', domain):
        return False

    return True

def extract_emails_from_html(html: str) -> List[str]:
    """Extract valid emails from HTML."""
    if not html:
        return []

    # Find all email-like strings
    matches = EMAIL_PATTERN.findall(html)

    # Filter and dedupe
    seen = set()
    emails = []
    for email in matches:
        email_lower = email.lower().strip()
        if email_lower not in seen and is_valid_email(email_lower):
            seen.add(email_lower)
            emails.append(email_lower)

    return emails[:5]  # Max 5 emails per org

def fetch_website(url: str, timeout: int = 15) -> Tuple[str, str]:
    """
    Fetch website content.

    Returns:
        Tuple of (html_content, status)
    """
    if not url or not url.startswith('http'):
        return '', 'invalid_url'

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    headers = {'User-Agent': 'Mozilla/5.0 (compatible; ResearchBot/1.0)'}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as response:
            content = response.read(100000)  # Max 100KB
            try:
                html = content.decode('utf-8', errors='ignore')
            except:
                html = content.decode('latin-1', errors='ignore')
            return html, 'success'
    except urllib.request.HTTPError as e:
        return '', f'http_{e.code}'
    except urllib.request.URLError as e:
        return '', 'url_error'
    except TimeoutError:
        return '', 'timeout'
    except Exception as e:
        return '', 'error'

def process_organization(org: tuple) -> dict:
    """Process single organization."""
    org_id, name, country, website = org

    result = {
        'org_id': org_id,
        'org_name': to_ascii(name),
        'country': country,
        'website': website,
        'emails': '',
        'email_count': 0,
        'status': 'pending',
        'extracted_date': datetime.now().isoformat()
    }

    # Fetch website
    html, status = fetch_website(website)
    result['status'] = status

    if html:
        emails = extract_emails_from_html(html)
        if emails:
            result['emails'] = ';'.join(emails)
            result['email_count'] = len(emails)
            result['status'] = 'found'

    return result

# ============================================================
# MAIN PROCESSING
# ============================================================

def get_organizations(country: Optional[str] = None, limit: int = 0, skip_processed: bool = True) -> List[tuple]:
    """Get organizations to process."""
    conn = sqlite3.connect(str(EU_DB_PATH))
    cur = conn.cursor()

    # Build query
    query = '''
        SELECT org_id, name, country, website
        FROM cordis_orgs
        WHERE website IS NOT NULL
    '''
    params = []

    if country:
        query += ' AND country = ?'
        params.append(country)

    if skip_processed:
        # Check which are already processed
        enr_conn = sqlite3.connect(str(ENRICHMENT_DB))
        enr_cur = enr_conn.cursor()
        enr_cur.execute('SELECT org_id FROM email_results')
        processed = {r[0] for r in enr_cur.fetchall()}
        enr_conn.close()

        if processed:
            placeholders = ','.join(['?' for _ in processed])
            query += f' AND org_id NOT IN ({placeholders})'
            params.extend(processed)

    query += ' ORDER BY total_funding DESC'

    if limit:
        query += f' LIMIT {limit}'

    cur.execute(query, params)
    orgs = cur.fetchall()
    conn.close()

    return orgs

def run_extraction(country: Optional[str] = None, limit: int = 100, workers: int = 3):
    """Run email extraction."""
    print(f"CORDIS Email Extractor - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    # Initialize DB
    enr_conn = init_enrichment_db()
    enr_cur = enr_conn.cursor()

    # Get organizations
    orgs = get_organizations(country, limit)
    print(f"Organizations to process: {len(orgs)}")

    if not orgs:
        print("No organizations to process")
        return

    # Process
    found = 0
    errors = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_organization, org): org for org in orgs}

        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            try:
                result = future.result(timeout=30)

                # Save result
                enr_cur.execute('''
                    INSERT OR REPLACE INTO email_results
                    (org_id, org_name, country, website, emails, email_count, status, extracted_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    result['org_id'], result['org_name'], result['country'],
                    result['website'], result['emails'], result['email_count'],
                    result['status'], result['extracted_date']
                ))

                if result['email_count'] > 0:
                    found += 1

                # Progress
                if i % 10 == 0 or i == len(orgs):
                    enr_conn.commit()
                    pct = i * 100 // len(orgs)
                    print(f"\r  Progress: {i}/{len(orgs)} ({pct}%) - Found: {found}", end='', flush=True)

            except Exception as e:
                errors += 1

    enr_conn.commit()
    print(f"\n\nResults:")
    print(f"  Processed: {len(orgs)}")
    print(f"  With emails: {found}")
    print(f"  Errors: {errors}")

    # Show stats
    show_stats()

def show_stats():
    """Show extraction statistics."""
    if not ENRICHMENT_DB.exists():
        print("No extraction data yet")
        return

    conn = sqlite3.connect(str(ENRICHMENT_DB))
    cur = conn.cursor()

    print("\n=== Extraction Statistics ===\n")

    # Overall
    cur.execute('SELECT COUNT(*), SUM(email_count) FROM email_results')
    total, emails = cur.fetchone()
    print(f"Total processed: {total or 0:,}")
    print(f"Total emails found: {emails or 0:,}")

    # By status
    print("\nBy status:")
    cur.execute('SELECT status, COUNT(*) FROM email_results GROUP BY status ORDER BY COUNT(*) DESC')
    for status, cnt in cur.fetchall():
        print(f"  {status}: {cnt:,}")

    # By country
    print("\nTop countries with emails:")
    cur.execute('''
        SELECT country, COUNT(*), SUM(email_count)
        FROM email_results WHERE email_count > 0
        GROUP BY country ORDER BY SUM(email_count) DESC LIMIT 10
    ''')
    for country, orgs, emails in cur.fetchall():
        print(f"  {country}: {orgs:,} orgs, {emails:,} emails")

    conn.close()

def export_emails(output_path: Optional[Path] = None, country: Optional[str] = None):
    """Export extracted emails to CSV."""
    output_path = output_path or OUTPUT_DIR / 'cordis_extracted_emails.csv'

    conn = sqlite3.connect(str(ENRICHMENT_DB))
    cur = conn.cursor()

    query = 'SELECT * FROM email_results WHERE email_count > 0'
    params = []
    if country:
        query += ' AND country = ?'
        params.append(country)
    query += ' ORDER BY email_count DESC'

    cur.execute(query, params)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(zip(cols, row)))

    conn.close()
    print(f"Exported {len(rows):,} organizations with emails to {output_path}")

# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='CORDIS Website Email Extractor')
    parser.add_argument('--country', type=str, help='Filter by country code (e.g., DE, FR)')
    parser.add_argument('--limit', type=int, default=100, help='Max organizations to process')
    parser.add_argument('--workers', type=int, default=3, help='Parallel workers')
    parser.add_argument('--all', action='store_true', help='Process all countries')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--export', action='store_true', help='Export to CSV')

    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    if args.export:
        export_emails(country=args.country)
        return

    # Run extraction
    country = None if args.all else args.country
    limit = 0 if args.all else args.limit
    run_extraction(country, limit, args.workers)

if __name__ == '__main__':
    main()
