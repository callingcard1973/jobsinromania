#!/usr/bin/env python3
"""
ConnectAmericas Brazilian Exporters Scraper

Scrapes the ConnectAmericas Brazilian Exporters Catalog which contains 20K+ companies.
Uses the brazil4export.com backend search.

Usage:
    python3 connectamericas_scraper.py --search "lithium"
    python3 connectamericas_scraper.py --hs-code 0409  # Honey
    python3 connectamericas_scraper.py --state "Sao Paulo"
    python3 connectamericas_scraper.py --all --limit 5000

Data available:
- Company name
- Products exported
- HS codes
- State (Brazilian)
- Export volume tier (up to $1M, $1-10M, $10-50M, $50M+)
"""

import os
import sys
import csv
import re
import json
import time
import random
import logging
import argparse
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, quote_plus

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, sanitize

# === CONFIG ===
BASE_DIR = Path('/opt/ACTIVE/IDEAS/MERCOSUR/OPENCODE')
OUTPUT_DIR = BASE_DIR / 'data' / 'mercosur'
CACHE_DIR = BASE_DIR / 'data' / 'cache'
LOG_DIR = BASE_DIR / 'logs'

for d in [OUTPUT_DIR, CACHE_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

REQUEST_DELAY = 2.0  # Be respectful
TIMEOUT = 30
MAX_RETRIES = 3

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"connectamericas_{datetime.now():%Y%m%d}.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# === PATTERNS ===
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', re.I)
PHONE_BR_PATTERN = re.compile(r'(?:\+55|0055)?[\s.-]?\(?(?:1[1-9]|2[1-9]|[3-9][1-9])\)?[\s.-]?(?:9?[0-9]{4})[\s.-]?[0-9]{4}')

# Brazilian states
BR_STATES = [
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS',
    'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC',
    'SP', 'SE', 'TO'
]

# Key HS codes for Mercosur-EU trade
HS_CODES = {
    '0409': 'Honey',
    '02': 'Meat',
    '03': 'Fish',
    '09': 'Coffee, tea, spices',
    '12': 'Oil seeds (soy)',
    '17': 'Sugar',
    '22': 'Beverages',
    '26': 'Ores, slag',
    '27': 'Mineral fuels',
    '44': 'Wood',
    '71': 'Precious stones',
    '72': 'Iron, steel',
    '81': 'Other base metals (niobium)',
    '84': 'Machinery',
    '85': 'Electrical machinery'
}

# Volume tiers
VOLUME_TIERS = {
    '1': 'Up to $1M',
    '2': '$1M - $10M',
    '3': '$10M - $50M',
    '4': 'Over $50M'
}


def get_session() -> requests.Session:
    """Create HTTP session."""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,pt-BR;q=0.8',
    })
    return session


class ConnectAmericasScraper:
    """Scrape ConnectAmericas / Brazil4Export database."""

    # The actual search seems to go through ConnectAmericas API
    SEARCH_URL = "https://connectamericas.com/api/v1/businesses"
    CATALOG_URL = "http://brazil4export.com"

    def __init__(self):
        self.session = get_session()
        self.companies: List[Dict] = []
        self.seen: Set[str] = set()
        self.cache_file = CACHE_DIR / 'connectamericas_cache.json'

    def search_by_keyword(self, keyword: str, limit: int = 100) -> List[Dict]:
        """Search companies by keyword."""
        log.info(f"Searching for: {keyword}")
        companies = []

        # ConnectAmericas search endpoint
        params = {
            'q': keyword,
            'country': 'BR',
            'limit': min(limit, 100),
            'offset': 0
        }

        while len(companies) < limit:
            try:
                time.sleep(REQUEST_DELAY)
                resp = self.session.get(self.SEARCH_URL, params=params, timeout=TIMEOUT)

                if resp.status_code != 200:
                    log.warning(f"Search returned {resp.status_code}")
                    break

                data = resp.json()
                results = data.get('results', data.get('data', []))

                if not results:
                    break

                for item in results:
                    company = self._parse_company(item)
                    if company and company['name'] not in self.seen:
                        self.seen.add(company['name'])
                        companies.append(company)

                # Pagination
                params['offset'] += len(results)
                if len(results) < params['limit']:
                    break

            except Exception as e:
                log.error(f"Search error: {e}")
                break

        log.info(f"Found {len(companies)} companies for '{keyword}'")
        return companies

    def search_by_hs_code(self, hs_code: str, limit: int = 500) -> List[Dict]:
        """Search by HS code."""
        log.info(f"Searching HS code: {hs_code} ({HS_CODES.get(hs_code, 'Unknown')})")
        return self.search_by_keyword(f"hs:{hs_code}", limit)

    def search_by_state(self, state: str, limit: int = 500) -> List[Dict]:
        """Search by Brazilian state."""
        if state.upper() not in BR_STATES:
            log.warning(f"Unknown state: {state}")
        return self.search_by_keyword(f"state:{state}", limit)

    def _parse_company(self, data: Dict) -> Optional[Dict]:
        """Parse company data from API response."""
        if not data:
            return None

        company = {
            'name': sanitize(data.get('name', data.get('company_name', '')), 'company'),
            'country': 'BR',
            'source': 'connectamericas',
            'scraped_at': datetime.now().isoformat()
        }

        if not company['name']:
            return None

        # Extract available fields
        if data.get('email'):
            company['email'] = sanitize(data['email'], 'email')
        if data.get('phone'):
            company['phone'] = sanitize(data['phone'], 'phone')
        if data.get('website'):
            company['website'] = sanitize(data['website'], 'url')
        if data.get('state'):
            company['state'] = sanitize(data['state'], 'short')
        if data.get('city'):
            company['city'] = sanitize(data['city'], 'city')
        if data.get('products'):
            company['products'] = sanitize(str(data['products']), 'description')
        if data.get('hs_codes'):
            company['hs_codes'] = str(data['hs_codes'])
        if data.get('export_volume'):
            company['export_volume'] = VOLUME_TIERS.get(str(data['export_volume']), data['export_volume'])
        if data.get('description'):
            company['description'] = sanitize(data['description'], 'description')

        return company

    def scrape_all_sectors(self, limit_per_sector: int = 200) -> List[Dict]:
        """Scrape all key HS codes."""
        for hs_code, desc in HS_CODES.items():
            log.info(f"Scraping HS {hs_code}: {desc}")
            companies = self.search_by_hs_code(hs_code, limit_per_sector)
            for c in companies:
                c['sector'] = desc
                c['hs_code_searched'] = hs_code
            self.companies.extend(companies)
            self.save_cache()

        return self.companies

    def scrape_priority_sectors(self, limit: int = 1000) -> List[Dict]:
        """Scrape priority sectors for EU-Mercosur trade."""
        priority_codes = ['0409', '81', '26', '02', '22', '44']  # Honey, niobium, ores, meat, beverages, wood

        for hs_code in priority_codes:
            companies = self.search_by_hs_code(hs_code, limit // len(priority_codes))
            for c in companies:
                c['sector'] = HS_CODES.get(hs_code, 'Unknown')
                c['hs_code_searched'] = hs_code
            self.companies.extend(companies)

        return self.companies

    def load_cache(self) -> List[Dict]:
        """Load from cache."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file) as f:
                    self.companies = json.load(f)
                    for c in self.companies:
                        self.seen.add(c.get('name', ''))
                    return self.companies
            except Exception as e:
                log.warning(f"Cache load failed: {e}")
        return []

    def save_cache(self):
        """Save to cache."""
        with open(self.cache_file, 'w') as f:
            json.dump(self.companies, f, indent=2)

    def deduplicate(self):
        """Remove duplicates."""
        seen = set()
        unique = []
        for c in self.companies:
            key = c.get('name', '').lower().strip()
            if key and key not in seen:
                seen.add(key)
                unique.append(c)
        self.companies = unique

    def export_csv(self, output_file: Optional[Path] = None) -> Path:
        """Export to CSV."""
        if not output_file:
            output_file = OUTPUT_DIR / f"connectamericas_exporters_{datetime.now():%Y%m%d}.csv"

        fieldnames = [
            'name', 'sector', 'hs_code_searched', 'email', 'phone', 'website',
            'state', 'city', 'products', 'export_volume', 'description',
            'country', 'source', 'scraped_at'
        ]

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(self.companies)

        log.info(f"Exported {len(self.companies)} companies to {output_file}")
        return output_file

    def get_stats(self) -> Dict:
        """Get statistics."""
        return {
            'total': len(self.companies),
            'with_email': sum(1 for c in self.companies if c.get('email')),
            'with_phone': sum(1 for c in self.companies if c.get('phone')),
            'with_website': sum(1 for c in self.companies if c.get('website')),
            'by_sector': self._count_by('sector'),
            'by_state': self._count_by('state'),
            'by_volume': self._count_by('export_volume')
        }

    def _count_by(self, field: str) -> Dict[str, int]:
        """Count companies by field."""
        counts = {}
        for c in self.companies:
            val = c.get(field, 'Unknown')
            counts[val] = counts.get(val, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: -x[1]))


def main():
    parser = argparse.ArgumentParser(description='ConnectAmericas Brazilian Exporters Scraper')
    parser.add_argument('--search', type=str, help='Search keyword')
    parser.add_argument('--hs-code', type=str, help='Search by HS code (e.g., 0409 for honey)')
    parser.add_argument('--state', type=str, help='Search by Brazilian state')
    parser.add_argument('--all', action='store_true', help='Scrape all key sectors')
    parser.add_argument('--priority', action='store_true', help='Scrape priority EU-Mercosur sectors')
    parser.add_argument('--limit', type=int, default=500, help='Max companies')
    parser.add_argument('--output', type=str, help='Output CSV file')
    parser.add_argument('--stats', action='store_true', help='Show cache statistics')
    parser.add_argument('--from-cache', action='store_true', help='Export from cache')

    args = parser.parse_args()
    scraper = ConnectAmericasScraper()

    if args.stats:
        scraper.load_cache()
        stats = scraper.get_stats()
        print("\n=== STATISTICS ===")
        print(f"Total: {stats['total']}")
        print(f"With email: {stats['with_email']}")
        print(f"With phone: {stats['with_phone']}")
        print(f"\nBy sector:")
        for k, v in list(stats['by_sector'].items())[:10]:
            print(f"  {k}: {v}")
        print(f"\nBy volume:")
        for k, v in stats['by_volume'].items():
            print(f"  {k}: {v}")
        return

    if args.from_cache:
        scraper.load_cache()
        scraper.deduplicate()
        output = Path(args.output) if args.output else None
        scraper.export_csv(output)
        return

    if args.search:
        scraper.search_by_keyword(args.search, args.limit)
    elif args.hs_code:
        scraper.search_by_hs_code(args.hs_code, args.limit)
    elif args.state:
        scraper.search_by_state(args.state, args.limit)
    elif args.priority:
        scraper.scrape_priority_sectors(args.limit)
    elif args.all:
        scraper.scrape_all_sectors(args.limit // len(HS_CODES))
    else:
        parser.print_help()
        return

    scraper.deduplicate()
    scraper.save_cache()
    output = Path(args.output) if args.output else None
    scraper.export_csv(output)

    stats = scraper.get_stats()
    print(f"\n=== COMPLETE ===")
    print(f"Total: {stats['total']} companies")
    print(f"With email: {stats['with_email']}")


if __name__ == '__main__':
    main()
