#!/usr/bin/env python3
"""
APEX Brasil / Brazilian Exporters Scraper

Scrapes Brazilian exporters from multiple sources:
1. B2Brazil.com - Company directory with contact info
2. ComexStat API - Official MDIC trade statistics
3. Sector-specific directories

Usage:
    python3 apex_brasil_scraper.py --sector food --limit 1000
    python3 apex_brasil_scraper.py --all-sectors --limit 5000
    python3 apex_brasil_scraper.py --test
    python3 apex_brasil_scraper.py --stats

Output: CSV with company name, sector, email, phone, website, export volume
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
from urllib.parse import urljoin, urlparse, quote
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, sanitize, FIELD_LIMITS

# === CONFIG ===
BASE_DIR = Path('/opt/ACTIVE/IDEAS/MERCOSUR/OPENCODE')
OUTPUT_DIR = BASE_DIR / 'data' / 'mercosur'
CACHE_DIR = BASE_DIR / 'data' / 'cache'
LOG_DIR = BASE_DIR / 'logs'

for d in [OUTPUT_DIR, CACHE_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Rate limiting
REQUEST_DELAY = 1.0  # seconds between requests
TIMEOUT = 15
MAX_WORKERS = 3
MAX_RETRIES = 3

# === LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"apex_scraper_{datetime.now():%Y%m%d}.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# === PATTERNS ===
EMAIL_PATTERN = re.compile(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    re.IGNORECASE
)

PHONE_BR_PATTERN = re.compile(
    r'(?:\+55|0055)?[\s.-]?\(?(?:1[1-9]|2[1-9]|[3-9][1-9])\)?[\s.-]?(?:9?[0-9]{4})[\s.-]?[0-9]{4}',
    re.IGNORECASE
)

# === SECTORS ===
SECTORS = {
    'food': {
        'name': 'Food & Beverages',
        'hs_codes': ['02', '03', '04', '07', '08', '09', '15', '16', '17', '18', '19', '20', '21', '22'],
        'keywords': ['food', 'alimentos', 'bebidas', 'meat', 'carne', 'coffee', 'cafe', 'sugar', 'acucar']
    },
    'minerals': {
        'name': 'Minerals & Metals',
        'hs_codes': ['25', '26', '27', '28', '71', '72', '73', '74', '75', '76', '78', '79', '80', '81'],
        'keywords': ['lithium', 'niobium', 'niobio', 'iron', 'ferro', 'steel', 'aco', 'minerals', 'minerais']
    },
    'agriculture': {
        'name': 'Agriculture',
        'hs_codes': ['01', '06', '07', '08', '10', '11', '12', '14', '23', '24'],
        'keywords': ['soy', 'soja', 'corn', 'milho', 'cotton', 'algodao', 'agriculture', 'agro']
    },
    'machinery': {
        'name': 'Machinery & Equipment',
        'hs_codes': ['84', '85', '87', '88', '89', '90'],
        'keywords': ['machinery', 'maquinas', 'equipment', 'equipamentos', 'industrial']
    },
    'honey': {
        'name': 'Honey & Bee Products',
        'hs_codes': ['0409'],
        'keywords': ['honey', 'mel', 'bee', 'apicultura', 'propolis']
    },
    'wood': {
        'name': 'Wood & Furniture',
        'hs_codes': ['44', '94'],
        'keywords': ['wood', 'madeira', 'furniture', 'moveis', 'timber']
    }
}

# === HTTP CLIENT ===
def get_session() -> requests.Session:
    """Create session with proper headers."""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7',
    })
    return session


def fetch_with_retry(session: requests.Session, url: str, retries: int = MAX_RETRIES) -> Optional[requests.Response]:
    """Fetch URL with exponential backoff retry."""
    for attempt in range(retries):
        try:
            time.sleep(REQUEST_DELAY + random.uniform(0, 0.5))
            resp = session.get(url, timeout=TIMEOUT)
            if resp.status_code == 200:
                return resp
            elif resp.status_code == 429:  # Rate limited
                wait = (2 ** attempt) * 5
                log.warning(f"Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                log.warning(f"HTTP {resp.status_code} for {url}")
                return None
        except requests.RequestException as e:
            log.warning(f"Request failed ({attempt+1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    return None


# === B2BRAZIL SCRAPER ===
class B2BrazilScraper:
    """Scrape company profiles from b2brazil.com."""

    BASE_URL = "https://b2brazil.com"

    def __init__(self, session: requests.Session):
        self.session = session
        self.seen_companies: Set[str] = set()

    def get_sector_urls(self, sector: str) -> List[str]:
        """Get URLs to scrape for a sector."""
        sector_map = {
            'food': ['/food', '/agriculture', '/beverages'],
            'minerals': ['/minerals', '/metals', '/mining'],
            'agriculture': ['/agriculture', '/agribusiness'],
            'machinery': ['/machinery', '/industrial-equipment'],
            'honey': ['/food', '/agriculture'],  # Honey is under food
            'wood': ['/furniture', '/wood']
        }
        return [f"{self.BASE_URL}{path}" for path in sector_map.get(sector, ['/'])]

    def scrape_listing_page(self, url: str) -> List[Dict]:
        """Scrape company listings from a category page."""
        companies = []
        resp = fetch_with_retry(self.session, url)
        if not resp:
            return companies

        html = resp.text

        # Extract company profile links (pattern: /hotsite/company-name)
        profile_links = re.findall(r'href=["\'](/hotsite/[^"\']+)["\']', html)
        profile_links = list(set(profile_links))

        log.info(f"Found {len(profile_links)} company links on {url}")

        for link in profile_links[:50]:  # Limit per page
            company = self.scrape_company_profile(f"{self.BASE_URL}{link}")
            if company:
                companies.append(company)

        return companies

    def scrape_company_profile(self, url: str) -> Optional[Dict]:
        """Scrape individual company profile."""
        resp = fetch_with_retry(self.session, url)
        if not resp:
            return None

        html = resp.text
        company = {}

        # Extract company name from title or h1
        name_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
        if name_match:
            company['name'] = sanitize(name_match.group(1), 'company')
        else:
            # Try title
            title_match = re.search(r'<title>([^<|]+)', html)
            if title_match:
                company['name'] = sanitize(title_match.group(1).split('-')[0].strip(), 'company')

        if not company.get('name') or company['name'] in self.seen_companies:
            return None

        self.seen_companies.add(company['name'])

        # Extract emails
        emails = EMAIL_PATTERN.findall(html)
        emails = [e for e in emails if not any(x in e.lower() for x in ['example', 'test', 'noreply', '.png', '.jpg', '.gif'])]
        if emails:
            company['email'] = sanitize(emails[0], 'email')

        # Extract phones (Brazilian format)
        phones = PHONE_BR_PATTERN.findall(html)
        if phones:
            company['phone'] = sanitize(phones[0], 'phone')

        # Extract website
        website_match = re.search(r'(?:site|website|www)[:\s]*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', html, re.I)
        if website_match:
            company['website'] = sanitize(website_match.group(1), 'url')

        # Extract description
        desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html, re.I)
        if desc_match:
            company['description'] = sanitize(desc_match.group(1), 'description')

        company['source'] = 'b2brazil'
        company['source_url'] = url
        company['scraped_at'] = datetime.now().isoformat()

        return company


# === COMEXSTAT API ===
class ComexStatAPI:
    """Query ComexStat API for export statistics."""

    BASE_URL = "https://api-comexstat.mdic.gov.br"

    def __init__(self, session: requests.Session):
        self.session = session

    def get_top_exporters_by_hs(self, hs_code: str, year: int = 2024) -> List[Dict]:
        """Get top exporters for an HS code chapter."""
        # ComexStat API endpoint for exports by NCM
        url = f"{self.BASE_URL}/general"

        # Note: ComexStat API provides aggregate data, not company-level
        # This is for reference/validation
        params = {
            'year': year,
            'type': 'exp',
            'ncm': hs_code
        }

        try:
            resp = self.session.get(url, params=params, timeout=30, verify=False)
            if resp.status_code == 200:
                return resp.json().get('data', [])
        except Exception as e:
            log.warning(f"ComexStat API error: {e}")

        return []


# === SECTOR DIRECTORIES ===
class SectorDirectoryScraper:
    """Scrape sector-specific directories."""

    def __init__(self, session: requests.Session):
        self.session = session
        self.seen_companies: Set[str] = set()

    def scrape_abemel_honey(self) -> List[Dict]:
        """Scrape ABEMEL (Brazilian Honey Exporters Association)."""
        companies = []

        # ABEMEL member list (would need actual URL)
        # This is a placeholder for the actual scraping logic
        log.info("ABEMEL scraping would require membership access")

        return companies

    def scrape_abiec_beef(self) -> List[Dict]:
        """Scrape ABIEC (Brazilian Beef Exporters Association)."""
        companies = []
        # Similar placeholder
        return companies


# === MAIN SCRAPER ===
class BrazilExportersScraper:
    """Main scraper orchestrator."""

    def __init__(self):
        self.session = get_session()
        self.b2brazil = B2BrazilScraper(self.session)
        self.comexstat = ComexStatAPI(self.session)
        self.sector_dirs = SectorDirectoryScraper(self.session)
        self.all_companies: List[Dict] = []
        self.cache_file = CACHE_DIR / 'brazil_exporters_cache.json'

    def load_cache(self) -> List[Dict]:
        """Load cached companies."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file) as f:
                    return json.load(f)
            except Exception as e:
                log.warning(f"Cache load failed: {e}")
        return []

    def save_cache(self):
        """Save companies to cache."""
        with open(self.cache_file, 'w') as f:
            json.dump(self.all_companies, f, indent=2)

    def scrape_sector(self, sector: str, limit: int = 500) -> List[Dict]:
        """Scrape companies for a sector."""
        if sector not in SECTORS:
            log.error(f"Unknown sector: {sector}")
            return []

        log.info(f"Scraping sector: {SECTORS[sector]['name']}")
        companies = []

        # 1. Scrape B2Brazil
        for url in self.b2brazil.get_sector_urls(sector):
            sector_companies = self.b2brazil.scrape_listing_page(url)
            for c in sector_companies:
                c['sector'] = sector
                c['sector_name'] = SECTORS[sector]['name']
            companies.extend(sector_companies)

            if len(companies) >= limit:
                break

        # 2. Special handling for specific sectors
        if sector == 'honey':
            companies.extend(self.sector_dirs.scrape_abemel_honey())

        log.info(f"Scraped {len(companies)} companies for {sector}")
        return companies[:limit]

    def scrape_all_sectors(self, limit_per_sector: int = 500) -> List[Dict]:
        """Scrape all sectors."""
        for sector in SECTORS:
            sector_companies = self.scrape_sector(sector, limit_per_sector)
            self.all_companies.extend(sector_companies)
            self.save_cache()

        return self.all_companies

    def deduplicate(self):
        """Remove duplicate companies by name."""
        seen = set()
        unique = []
        for c in self.all_companies:
            key = c.get('name', '').lower().strip()
            if key and key not in seen:
                seen.add(key)
                unique.append(c)
        self.all_companies = unique
        log.info(f"Deduplicated to {len(unique)} unique companies")

    def export_csv(self, output_file: Optional[Path] = None) -> Path:
        """Export companies to CSV."""
        if not output_file:
            output_file = OUTPUT_DIR / f"brazil_exporters_{datetime.now():%Y%m%d}.csv"

        fieldnames = [
            'name', 'sector', 'sector_name', 'email', 'phone', 'website',
            'description', 'source', 'source_url', 'scraped_at'
        ]

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for company in self.all_companies:
                writer.writerow(company)

        log.info(f"Exported {len(self.all_companies)} companies to {output_file}")
        return output_file

    def get_stats(self) -> Dict:
        """Get scraping statistics."""
        stats = {
            'total_companies': len(self.all_companies),
            'with_email': sum(1 for c in self.all_companies if c.get('email')),
            'with_phone': sum(1 for c in self.all_companies if c.get('phone')),
            'with_website': sum(1 for c in self.all_companies if c.get('website')),
            'by_sector': {},
            'by_source': {}
        }

        for c in self.all_companies:
            sector = c.get('sector', 'unknown')
            source = c.get('source', 'unknown')
            stats['by_sector'][sector] = stats['by_sector'].get(sector, 0) + 1
            stats['by_source'][source] = stats['by_source'].get(source, 0) + 1

        return stats


# === CLI ===
def main():
    parser = argparse.ArgumentParser(description='Brazilian Exporters Scraper')
    parser.add_argument('--sector', choices=list(SECTORS.keys()), help='Sector to scrape')
    parser.add_argument('--all-sectors', action='store_true', help='Scrape all sectors')
    parser.add_argument('--limit', type=int, default=500, help='Max companies per sector')
    parser.add_argument('--output', type=str, help='Output CSV file path')
    parser.add_argument('--test', action='store_true', help='Test mode (scrape 10 companies)')
    parser.add_argument('--stats', action='store_true', help='Show statistics from cache')
    parser.add_argument('--from-cache', action='store_true', help='Export from cache only')

    args = parser.parse_args()

    scraper = BrazilExportersScraper()

    if args.stats:
        scraper.all_companies = scraper.load_cache()
        stats = scraper.get_stats()
        print("\n=== SCRAPER STATISTICS ===")
        print(f"Total companies: {stats['total_companies']}")
        print(f"With email: {stats['with_email']} ({stats['with_email']*100//max(stats['total_companies'],1)}%)")
        print(f"With phone: {stats['with_phone']} ({stats['with_phone']*100//max(stats['total_companies'],1)}%)")
        print(f"With website: {stats['with_website']}")
        print("\nBy sector:")
        for sector, count in sorted(stats['by_sector'].items(), key=lambda x: -x[1]):
            print(f"  {sector}: {count}")
        print("\nBy source:")
        for source, count in sorted(stats['by_source'].items(), key=lambda x: -x[1]):
            print(f"  {source}: {count}")
        return

    if args.from_cache:
        scraper.all_companies = scraper.load_cache()
        scraper.deduplicate()
        output = Path(args.output) if args.output else None
        scraper.export_csv(output)
        return

    if args.test:
        log.info("Running test mode...")
        companies = scraper.scrape_sector('food', limit=10)
        print(f"\nTest results: {len(companies)} companies")
        for c in companies[:5]:
            print(f"  - {c.get('name')}: {c.get('email', 'no email')}")
        return

    if args.all_sectors:
        scraper.scrape_all_sectors(limit_per_sector=args.limit)
    elif args.sector:
        companies = scraper.scrape_sector(args.sector, limit=args.limit)
        scraper.all_companies = companies
    else:
        parser.print_help()
        return

    scraper.deduplicate()
    output = Path(args.output) if args.output else None
    output_file = scraper.export_csv(output)

    stats = scraper.get_stats()
    print(f"\n=== COMPLETE ===")
    print(f"Total: {stats['total_companies']} companies")
    print(f"With email: {stats['with_email']}")
    print(f"Output: {output_file}")


if __name__ == '__main__':
    main()
