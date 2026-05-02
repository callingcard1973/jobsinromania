#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
Nordic Enricher - Fill missing emails in Norway/Denmark MASTER CSVs

These scrapers already get some emails. This enriches the rest via website scraping.

Usage:
    python3 nordic_enricher.py --country NO        # Norway
    python3 nordic_enricher.py --country DK        # Denmark
    python3 nordic_enricher.py --status            # Show stats
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import re
import csv
import json
import time
import logging
import argparse
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from skills_common import to_ascii

COUNTRY_CONFIG = {
    'NO': {
        'name': 'Norway',
        'master_csv': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/NORWAY/OUTPUT/Norway_ULTIMATE_MASTER.csv',
        'tlds': ['.no', '.com'],
        'paths': ['/', '/kontakt', '/om-oss', '/contact'],
        'company_col': 'employer',
        'email_col': 'email1',
    },
    'DK': {
        'name': 'Denmark',
        'master_csv': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/DENMARK/OUTPUT/Denmark_ULTIMATE_MASTER.csv',
        'tlds': ['.dk', '.com'],
        'paths': ['/', '/kontakt', '/om-os', '/contact'],
        'company_col': 'employer',
        'email_col': 'email1',
    },
}

OUTPUT_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/ENRICHED')
CACHE_DIR = OUTPUT_DIR / 'cache'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
TIMEOUT = 8
BATCH_SIZE = 40

EMAIL_BLACKLIST = ['example', 'test', 'google', 'facebook', 'noreply', 'wix', '.png', '.jpg',
                   '.gif', '.svg', '.avif', '.webp', 'bruker@domene', 'eksempel', 'cookie', 'schema.org']

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


class NordicEnricher:
    def __init__(self, country_code: str):
        self.country = country_code.upper()
        self.config = COUNTRY_CONFIG.get(self.country)
        if not self.config:
            raise ValueError(f"Unknown country: {country_code}")

        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.cache_file = CACHE_DIR / f'{self.country}_domain_cache.json'
        self.cache = self._load_cache()
        self.enriched_file = OUTPUT_DIR / f'{self.country}_ENRICHED.csv'
        self.stats = {'total': 0, 'already_has': 0, 'found': 0, 'failed': 0}

    def _load_cache(self) -> dict:
        if self.cache_file.exists():
            try:
                with open(self.cache_file) as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_cache(self):
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f)

    def company_to_domains(self, company: str) -> List[str]:
        name = company.lower().strip()
        # Remove Nordic suffixes
        for suffix in [r'\s*as\b', r'\s*asa\b', r'\s*aps\b', r'\s*a/s\b',
                       r'\s*sf\b', r'\s*ab\b', r'\s*hf\b', r'\s*ehf\b']:
            name = re.sub(suffix, '', name, flags=re.I)
        name = name.strip()
        if not name or len(name) < 2:
            return []

        slug = re.sub(r'[^a-z0-9æøåäö]+', '-', name).strip('-')
        # Handle Nordic chars
        for old, new in [('æ', 'ae'), ('ø', 'o'), ('å', 'a'), ('ä', 'a'), ('ö', 'o')]:
            slug = slug.replace(old, new)

        domains = []
        for tld in self.config['tlds']:
            domains.append(f"{slug}{tld}")

        no_dash = slug.replace('-', '')
        if no_dash != slug and len(no_dash) > 2:
            domains.append(f"{no_dash}{self.config['tlds'][0]}")

        return domains[:4]

    def extract_emails(self, html: str) -> List[str]:
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html)
        valid = [e for e in emails if not any(bl in e.lower() for bl in EMAIL_BLACKLIST)]
        return list(dict.fromkeys(valid))[:2]

    def try_domain(self, domain: str) -> Optional[str]:
        if domain in self.cache:
            return self.cache[domain].get('email')

        for prefix in [f'https://www.{domain}', f'https://{domain}']:
            for path in self.config['paths']:
                try:
                    resp = self.session.get(f"{prefix}{path}", timeout=TIMEOUT, allow_redirects=True)
                    if resp.status_code == 200:
                        emails = self.extract_emails(resp.text)
                        if emails:
                            self.cache[domain] = {'email': emails[0]}
                            return emails[0]
                except:
                    pass

        self.cache[domain] = {'email': None}
        return None

    def load_companies_needing_enrichment(self, limit: int = None) -> List[Dict]:
        """Load companies that don't have emails."""
        csv_path = Path(self.config['master_csv'])
        if not csv_path.exists():
            logger.error(f"Master CSV not found: {csv_path}")
            return []

        companies = []
        seen = set()

        with open(csv_path, 'r', encoding='utf-8-sig', errors='replace') as f:
            reader = csv.DictReader(f)
            for row in reader:
                company = row.get(self.config['company_col'], '').strip()
                email = row.get(self.config['email_col'], '').strip()

                # Skip if already has email or no company name
                if email and '@' in email:
                    self.stats['already_has'] += 1
                    continue

                if company and len(company) > 2 and company not in seen:
                    seen.add(company)
                    companies.append({
                        'company': company,
                        'city': row.get('job_location', '').split(',')[0].strip() if row.get('job_location') else ''
                    })
                    if limit and len(companies) >= limit:
                        break

        logger.info(f"Loaded {len(companies)} companies needing enrichment")
        logger.info(f"Already have email: {self.stats['already_has']}")
        return companies

    def append_to_enriched(self, records: List[Dict]):
        if not records:
            return

        exists = self.enriched_file.exists()
        with open(self.enriched_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['company', 'email', 'website', 'city', 'country', 'date'])
            if not exists:
                writer.writeheader()
            for r in records:
                writer.writerow(r)
        logger.info(f"📁 Saved {len(records)} to {self.enriched_file.name}")

    def run(self, limit: int = None):
        companies = self.load_companies_needing_enrichment(limit)
        if not companies:
            logger.info("No companies need enrichment!")
            return

        batch = []
        for i, comp in enumerate(companies):
            self.stats['total'] += 1
            domains = self.company_to_domains(comp['company'])

            email = None
            for domain in domains:
                email = self.try_domain(domain)
                if email:
                    break
                time.sleep(0.3)

            if email:
                self.stats['found'] += 1
                batch.append({
                    'company': to_ascii(comp['company']),
                    'email': email,
                    'website': f"https://www.{domains[0]}" if domains else '',
                    'city': to_ascii(comp['city']),
                    'country': self.country,
                    'date': datetime.now().strftime('%Y-%m-%d')
                })
                logger.info(f"✅ {comp['company'][:35]} → {email}")
            else:
                self.stats['failed'] += 1

            if len(batch) >= BATCH_SIZE:
                self.append_to_enriched(batch)
                self._save_cache()
                batch = []

            if (i + 1) % 100 == 0:
                logger.info(f"Progress: {i+1}/{len(companies)} ({100*(i+1)/len(companies):.0f}%)")

            time.sleep(0.5)

        if batch:
            self.append_to_enriched(batch)
            self._save_cache()

        print(f"\n=== {self.config['name']} ENRICHMENT ===")
        print(f"Already had email: {self.stats['already_has']}")
        print(f"Needed enrichment: {self.stats['total']}")
        print(f"Found: {self.stats['found']} ({100*self.stats['found']/max(1,self.stats['total']):.0f}%)")
        print(f"Output: {self.enriched_file}")


def show_status():
    print("=== NORDIC ENRICHMENT STATUS ===\n")
    for code, cfg in COUNTRY_CONFIG.items():
        master = Path(cfg['master_csv'])
        enriched = OUTPUT_DIR / f'{code}_ENRICHED.csv'

        master_count = 0
        master_with_email = 0
        if master.exists():
            with open(master, 'r', encoding='utf-8-sig', errors='replace') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    master_count += 1
                    if row.get(cfg['email_col'], '') and '@' in row.get(cfg['email_col'], ''):
                        master_with_email += 1

        enriched_count = 0
        if enriched.exists():
            with open(enriched) as f:
                enriched_count = len(f.readlines()) - 1

        print(f"{code} ({cfg['name']}):")
        print(f"  Master CSV: {master_count} rows, {master_with_email} with email")
        print(f"  Need enrichment: {master_count - master_with_email}")
        print(f"  Enriched so far: {enriched_count}")
        print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--country', type=str, help='NO or DK')
    parser.add_argument('--limit', type=int, help='Limit companies')
    parser.add_argument('--status', action='store_true')
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if not args.country:
        print("Usage: --country NO|DK or --status")
        return

    enricher = NordicEnricher(args.country)
    enricher.run(args.limit)


if __name__ == '__main__':
    main()
