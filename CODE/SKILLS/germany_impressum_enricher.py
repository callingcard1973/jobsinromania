#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
Germany Impressum Enricher - Extract emails from German company websites

German law (§5 TMG) requires commercial websites to have an Impressum with contact info.
This script finds company websites and extracts emails from their Impressum pages.

Usage:
    python3 germany_impressum_enricher.py                    # Enrich all Arbeitsagentur companies
    python3 germany_impressum_enricher.py --limit 100        # Limit to 100 companies
    python3 germany_impressum_enricher.py --test             # Test with 10 companies
    python3 germany_impressum_enricher.py --input file.csv   # Custom input file

Input: CSV with 'company_name' column
Output: CSV with added 'enriched_email', 'enriched_website' columns

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
import argparse
import requests
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

from skills_common import to_ascii

# Paths
BASE_DIR = Path('/opt/ACTIVE/INFRA/SKILLS')
OUTPUT_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/GERMANY_ENRICHED')
LOGS_DIR = Path('/opt/ACTIVE/INFRA/LOGS/enricher')
CACHE_FILE = OUTPUT_DIR / 'domain_cache.json'

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / f"impressum_{datetime.now().strftime('%Y%m%d')}.log")
    ]
)
logger = logging.getLogger(__name__)

# HTTP config
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
}
TIMEOUT = 8
DELAY = 0.5  # Seconds between requests

# Email blacklist patterns
EMAIL_BLACKLIST = [
    'example', 'test', 'sentry', 'google', 'facebook', 'twitter', 'instagram',
    'cookie', 'privacy', 'noreply', 'no-reply', 'wixpress', 'schema.org',
    'jquery', 'bootstrap', '.png', '.jpg', '.gif', '.svg', 'datenschutz',
    'webmaster', 'hostmaster', 'postmaster', 'abuse@', 'spam@'
]


class ImpressumEnricher:
    """Extract company emails from German Impressum pages."""

    def __init__(self, use_cache: bool = True):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.cache = self._load_cache() if use_cache else {}
        self.stats = {'total': 0, 'found': 0, 'cached': 0, 'failed': 0}

    def _load_cache(self) -> Dict:
        """Load domain cache from disk."""
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_cache(self):
        """Save domain cache to disk."""
        try:
            with open(CACHE_FILE, 'w') as f:
                json.dump(self.cache, f)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    def company_to_domains(self, company_name: str) -> List[str]:
        """Generate possible domain names from company name."""
        name = company_name.lower()

        # Remove German legal suffixes
        suffixes = [
            r'\s*gmbh\s*&\s*co\.?\s*kg',
            r'\s*gmbh', r'\s*ag', r'\s*kg', r'\s*ohg', r'\s*ug',
            r'\s*e\.?v\.?', r'\s*mbh', r'\s*se', r'\s*kgaa',
            r'\s*niederlassung\s+\w+', r'\s*nl\s+\w+',
            r'\s*filiale\s+\w+'
        ]
        for suffix in suffixes:
            name = re.sub(suffix, '', name, flags=re.I)

        name = name.strip()
        if not name:
            return []

        domains = []

        # Generate slug (e.g., "Company Name" -> "company-name")
        slug = re.sub(r'[^a-z0-9äöüß]+', '-', name)
        slug = slug.replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
        slug = slug.strip('-')

        if slug:
            domains.append(f"{slug}.de")
            domains.append(f"{slug}.com")

            # Without hyphens
            no_dash = slug.replace('-', '')
            if no_dash != slug:
                domains.append(f"{no_dash}.de")

            # First word only (for long names)
            first = slug.split('-')[0]
            if len(first) > 3 and first != slug:
                domains.append(f"{first}.de")

        return domains[:5]

    def extract_emails(self, html: str) -> List[str]:
        """Extract valid emails from HTML content."""
        # Standard email regex
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(pattern, html)

        # Filter invalid/unwanted
        valid = []
        for email in emails:
            email_lower = email.lower()
            if any(bl in email_lower for bl in EMAIL_BLACKLIST):
                continue
            if len(email) > 100:  # Too long
                continue
            valid.append(email)

        # Deduplicate preserving order
        return list(dict.fromkeys(valid))[:3]

    def try_domain(self, domain: str) -> Optional[Tuple[str, List[str]]]:
        """Try to fetch email from a domain's Impressum/Kontakt pages."""
        # Check cache first
        if domain in self.cache:
            cached = self.cache[domain]
            if cached.get('emails'):
                self.stats['cached'] += 1
                return (domain, cached['emails'])
            return None

        paths = ['/', '/impressum', '/impressum/', '/kontakt', '/kontakt/', '/contact', '/ueber-uns']
        prefixes = [f'https://www.{domain}', f'https://{domain}']

        for prefix in prefixes:
            for path in paths:
                url = f"{prefix}{path}"
                try:
                    resp = self.session.get(url, timeout=TIMEOUT, allow_redirects=True)
                    if resp.status_code == 200:
                        emails = self.extract_emails(resp.text)
                        if emails:
                            # Cache success
                            self.cache[domain] = {'emails': emails, 'url': url}
                            return (domain, emails)
                except requests.RequestException:
                    pass
                except Exception:
                    pass

        # Cache failure
        self.cache[domain] = {'emails': [], 'url': None}
        return None

    def enrich_company(self, company_name: str) -> Dict:
        """Find email for a company."""
        self.stats['total'] += 1

        domains = self.company_to_domains(company_name)
        if not domains:
            self.stats['failed'] += 1
            return {'company': company_name, 'email': None, 'website': None}

        for domain in domains:
            result = self.try_domain(domain)
            if result:
                self.stats['found'] += 1
                return {
                    'company': company_name,
                    'email': result[1][0],  # Primary email
                    'emails_all': result[1],
                    'website': f"https://www.{result[0]}"
                }
            time.sleep(DELAY / 2)  # Smaller delay between domain attempts

        self.stats['failed'] += 1
        return {'company': company_name, 'email': None, 'website': None}

    def enrich_batch(self, companies: List[str], workers: int = 3) -> List[Dict]:
        """Enrich multiple companies (sequential to avoid rate limiting)."""
        results = []

        for i, company in enumerate(companies):
            if i > 0 and i % 50 == 0:
                logger.info(f"Progress: {i}/{len(companies)} ({100*i/len(companies):.0f}%)")
                self._save_cache()  # Periodic save

            result = self.enrich_company(company)
            results.append(result)

            if result['email']:
                logger.info(f"✅ {company[:40]} → {result['email']}")

            time.sleep(DELAY)

        self._save_cache()
        return results

    def get_stats(self) -> Dict:
        """Get enrichment statistics."""
        return {
            **self.stats,
            'success_rate': f"{100 * self.stats['found'] / max(self.stats['total'], 1):.1f}%",
            'cache_size': len(self.cache)
        }


def load_arbeitsagentur_companies(limit: int = None) -> List[str]:
    """Load unique company names from Arbeitsagentur data."""
    csv_file = Path('/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/GERMANY/OUTPUT/Germany_ARBEITSAGENTUR_MASTER.csv')

    if not csv_file.exists():
        logger.error(f"Arbeitsagentur file not found: {csv_file}")
        return []

    companies = set()
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get('company_name', '').strip()
            if name and len(name) > 3:
                # Skip obvious non-companies
                if any(x in name.lower() for x in ['privat', 'anonym', 'vertraulich']):
                    continue
                companies.add(name)

    companies = sorted(list(companies))
    if limit:
        companies = companies[:limit]

    logger.info(f"Loaded {len(companies)} unique companies")
    return companies


def main():
    parser = argparse.ArgumentParser(description='Enrich German companies with emails from Impressum')
    parser.add_argument('--input', type=str, help='Input CSV file with company_name column')
    parser.add_argument('--output', type=str, help='Output CSV file')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of companies')
    parser.add_argument('--test', action='store_true', help='Test mode (10 companies)')
    parser.add_argument('--no-cache', action='store_true', help='Disable domain cache')
    parser.add_argument('--stats', action='store_true', help='Show cache stats only')
    args = parser.parse_args()

    enricher = ImpressumEnricher(use_cache=not args.no_cache)

    if args.stats:
        print(f"Cache entries: {len(enricher.cache)}")
        found = sum(1 for v in enricher.cache.values() if v.get('emails'))
        print(f"Domains with email: {found}")
        return

    # Load companies
    if args.input:
        # Custom input
        companies = []
        with open(args.input, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get('company_name', row.get('company', '')).strip()
                if name:
                    companies.append(name)
    else:
        # Default: Arbeitsagentur
        limit = 10 if args.test else args.limit
        companies = load_arbeitsagentur_companies(limit)

    if not companies:
        logger.error("No companies to process")
        return

    # Enrich
    logger.info(f"Starting enrichment of {len(companies)} companies...")
    start_time = time.time()

    results = enricher.enrich_batch(companies)

    elapsed = time.time() - start_time
    stats = enricher.get_stats()

    # Output
    output_file = args.output or (OUTPUT_DIR / f"enriched_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    output_file = Path(output_file)

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['company', 'email', 'website'])
        writer.writeheader()
        for r in results:
            writer.writerow({
                'company': r['company'],
                'email': r.get('email', ''),
                'website': r.get('website', '')
            })

    # Summary
    print(f"\n{'='*50}")
    print("ENRICHMENT COMPLETE")
    print(f"{'='*50}")
    print(f"Total companies: {stats['total']}")
    print(f"Emails found:    {stats['found']} ({stats['success_rate']})")
    print(f"From cache:      {stats['cached']}")
    print(f"Not found:       {stats['failed']}")
    print(f"Time:            {elapsed:.1f}s")
    print(f"Output:          {output_file}")
    print(f"Cache size:      {stats['cache_size']} domains")


if __name__ == '__main__':
    main()
