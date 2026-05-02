#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
ONRC Email Enricher - Add emails to Romanian company database.

Takes ONRC companies (2.5M) and enriches with:
- Emails from company websites
- Emails from Google search
- Cross-reference with ANOFM, EUFUNDS data

Usage:
    python3 onrc_enricher.py --status              # Show current stats
    python3 onrc_enricher.py --enrich --limit 100  # Enrich 100 companies
    python3 onrc_enricher.py --enrich --batch      # Batch mode (1000/run)
    python3 onrc_enricher.py --export              # Export enriched only

See /opt/CLAUDE.md for shared code rules.
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import re
import csv
import json
import time
import logging
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed

from skills_common import to_ascii, sanitize, fetch_url

# Paths
ONRC_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/ONRC')
OUTPUT_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/ONRC_ENRICHED')
DB_FILE = OUTPUT_DIR / 'enrichment.db'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Email pattern
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')


class ONRCEnricher:
    """Enriches ONRC company data with email addresses."""

    def __init__(self):
        self.db = sqlite3.connect(str(DB_FILE))
        self._init_db()
        self.stats = {'processed': 0, 'emails_found': 0, 'errors': 0}

    def _init_db(self):
        """Initialize tracking database."""
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS enrichment (
                cui TEXT PRIMARY KEY,
                company_name TEXT,
                website TEXT,
                email TEXT,
                phone TEXT,
                source TEXT,
                enriched_date TEXT,
                status TEXT
            )
        ''')
        self.db.execute('CREATE INDEX IF NOT EXISTS idx_status ON enrichment(status)')
        self.db.commit()

    def load_onrc(self, limit: int = None) -> List[Dict]:
        """Load ONRC companies that need enrichment."""
        onrc_file = ONRC_DIR / 'onrc_firme_clean.csv'

        if not onrc_file.exists():
            onrc_file = ONRC_DIR / 'od_firme_20260102.csv'

        if not onrc_file.exists():
            logger.error("ONRC file not found")
            return []

        # Get already processed CUIs
        cursor = self.db.execute('SELECT cui FROM enrichment')
        processed = {row[0] for row in cursor}
        logger.info(f"Already processed: {len(processed)}")

        companies = []
        with open(onrc_file, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cui = row.get('cui', row.get('CUI', ''))
                if cui and cui not in processed:
                    companies.append({
                        'cui': cui,
                        'name': row.get('denumire', row.get('DENUMIRE', '')),
                        'address': row.get('adresa', row.get('ADRESA', '')),
                        'city': row.get('localitate', row.get('LOCALITATE', '')),
                        'county': row.get('judet', row.get('JUDET', '')),
                    })

                    if limit and len(companies) >= limit:
                        break

        logger.info(f"Loaded {len(companies)} companies to enrich")
        return companies

    def extract_emails(self, html: str) -> List[str]:
        """Extract emails from HTML."""
        if not html:
            return []

        emails = EMAIL_PATTERN.findall(html.lower())

        # Filter valid emails
        valid = []
        for email in emails:
            if any(x in email for x in ['example.', 'test.', 'noreply', '.png', '.jpg', '.gif']):
                continue
            if email.endswith('.ro') or email.endswith('.com') or email.endswith('.eu'):
                valid.append(email)

        return list(set(valid))[:3]  # Max 3 emails

    def search_website(self, company_name: str, cui: str) -> Optional[str]:
        """Search for company website."""
        try:
            # Try common patterns
            clean_name = re.sub(r'[^a-z0-9]', '', company_name.lower())[:20]

            patterns = [
                f"https://www.{clean_name}.ro",
                f"https://{clean_name}.ro",
            ]

            for url in patterns:
                try:
                    html = fetch_url(url)
                    if html and len(html) > 500:
                        return url
                except Exception:
                    continue

        except Exception:
            pass

        return None

    def enrich_company(self, company: Dict) -> Dict:
        """Enrich a single company with email."""
        result = {
            'cui': company['cui'],
            'company_name': company['name'],
            'website': '',
            'email': '',
            'phone': '',
            'source': '',
            'enriched_date': datetime.now().strftime('%Y-%m-%d'),
            'status': 'no_email',
        }

        try:
            # Try to find website
            website = self.search_website(company['name'], company['cui'])

            if website:
                result['website'] = website

                # Scrape website for email
                html = fetch_url(website)
                emails = self.extract_emails(html)

                if emails:
                    result['email'] = emails[0]
                    result['source'] = 'website'
                    result['status'] = 'enriched'
                    self.stats['emails_found'] += 1

                    # Try contact page
                    for suffix in ['/contact', '/contact.html', '/contacte']:
                        try:
                            contact_html = fetch_url(website.rstrip('/') + suffix)
                            more_emails = self.extract_emails(contact_html)
                            if more_emails and more_emails[0] != result['email']:
                                result['email'] += ',' + more_emails[0]
                        except Exception:
                            pass

        except Exception as e:
            result['status'] = 'error'
            self.stats['errors'] += 1

        self.stats['processed'] += 1
        return result

    def save_result(self, result: Dict):
        """Save enrichment result to database."""
        self.db.execute('''
            INSERT OR REPLACE INTO enrichment
            (cui, company_name, website, email, phone, source, enriched_date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            result['cui'], result['company_name'], result['website'],
            result['email'], result['phone'], result['source'],
            result['enriched_date'], result['status']
        ))
        self.db.commit()

    def enrich_batch(self, companies: List[Dict], workers: int = 5):
        """Enrich batch of companies."""
        logger.info(f"Enriching {len(companies)} companies with {workers} workers...")

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(self.enrich_company, c): c for c in companies}

            for i, future in enumerate(as_completed(futures), 1):
                result = future.result()
                self.save_result(result)

                if i % 10 == 0:
                    logger.info(f"Progress: {i}/{len(companies)}, {self.stats['emails_found']} emails found")

                time.sleep(0.5)  # Rate limit

    def show_status(self):
        """Show enrichment status."""
        print("=" * 50)
        print("ONRC ENRICHMENT STATUS")
        print("=" * 50)

        # Total in ONRC
        onrc_file = ONRC_DIR / 'onrc_firme_clean.csv'
        if onrc_file.exists():
            with open(onrc_file, 'r', errors='ignore') as f:
                total = sum(1 for _ in f) - 1
            print(f"Total ONRC companies: {total:,}")

        # Enrichment stats
        cursor = self.db.execute('SELECT status, COUNT(*) FROM enrichment GROUP BY status')
        stats = dict(cursor.fetchall())

        print(f"\nEnrichment Progress:")
        print(f"  Processed: {sum(stats.values()):,}")
        print(f"  With email: {stats.get('enriched', 0):,}")
        print(f"  No email: {stats.get('no_email', 0):,}")
        print(f"  Errors: {stats.get('error', 0):,}")

        if total:
            pct = sum(stats.values()) / total * 100
            print(f"\n  Coverage: {pct:.1f}%")

    def export_enriched(self):
        """Export companies with emails."""
        output_file = OUTPUT_DIR / f"onrc_enriched_{datetime.now().strftime('%Y%m%d')}.csv"

        cursor = self.db.execute('''
            SELECT cui, company_name, website, email, phone, source, enriched_date
            FROM enrichment WHERE status = 'enriched'
        ''')

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['cui', 'company_name', 'website', 'email', 'phone', 'source', 'enriched_date'])
            for row in cursor:
                writer.writerow(row)

        count = self.db.execute('SELECT COUNT(*) FROM enrichment WHERE status = "enriched"').fetchone()[0]
        print(f"Exported {count} enriched companies to: {output_file}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='ONRC Email Enricher')
    parser.add_argument('--status', action='store_true', help='Show status')
    parser.add_argument('--enrich', action='store_true', help='Run enrichment')
    parser.add_argument('--limit', type=int, default=100, help='Limit companies')
    parser.add_argument('--batch', action='store_true', help='Batch mode (1000)')
    parser.add_argument('--export', action='store_true', help='Export enriched')
    parser.add_argument('--workers', type=int, default=3, help='Parallel workers')

    args = parser.parse_args()

    enricher = ONRCEnricher()

    if args.export:
        enricher.export_enriched()
    elif args.enrich:
        limit = 1000 if args.batch else args.limit
        companies = enricher.load_onrc(limit=limit)
        if companies:
            enricher.enrich_batch(companies, workers=args.workers)
            print(json.dumps(enricher.stats, indent=2))
    else:
        enricher.show_status()


if __name__ == '__main__':
    main()
