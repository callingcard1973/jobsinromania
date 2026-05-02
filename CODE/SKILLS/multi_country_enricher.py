#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
Multi-Country Impressum/Contact Enricher

Supports: Germany (DE), Austria (AT), Switzerland (CH), Netherlands (NL), Norway (NO)

Each country has different contact page conventions:
- DE/AT/CH: /impressum (legal requirement)
- NL: /contact, /over-ons
- NO: /kontakt, /om-oss

Usage:
    python3 multi_country_enricher.py --country DE --limit 100
    python3 multi_country_enricher.py --country NO --limit 100
    python3 multi_country_enricher.py --status
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

# Country configs
COUNTRY_CONFIG = {
    'DE': {
        'name': 'Germany',
        'tlds': ['.de', '.com'],
        'paths': ['/', '/impressum', '/kontakt', '/contact', '/ueber-uns'],
        'source_csv': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/GERMANY/OUTPUT/Germany_ARBEITSAGENTUR_MASTER.csv',
        'company_col': 'company_name',
        'city_col': 'location_city',
    },
    'AT': {
        'name': 'Austria',
        'tlds': ['.at', '.com'],
        'paths': ['/', '/impressum', '/kontakt', '/contact', '/ueber-uns'],
        'source_csv': '/mnt/hdd/SCRAPER_DATA/csv/EURES/Austria/Austria_contacts_50.csv',
        'company_col': 'company_name',
        'city_col': 'company_city',
    },
    'CH': {
        'name': 'Switzerland',
        'tlds': ['.ch', '.com'],
        'paths': ['/', '/impressum', '/kontakt', '/contact', '/ueber-uns'],
        'source_csv': '/mnt/hdd/SCRAPER_DATA/csv/EURES/Switzerland/Switzerland_contacts_50.csv',
        'company_col': 'company_name',
        'city_col': 'company_city',
    },
    'NL': {
        'name': 'Netherlands',
        'tlds': ['.nl', '.com'],
        'paths': ['/', '/contact', '/over-ons', '/about', '/contactgegevens'],
        'source_csv': '/mnt/hdd/SCRAPER_DATA/csv/EURES/Netherlands/Netherlands_contacts_50.csv',
        'company_col': 'company_name',
        'city_col': 'company_city',
    },
    'NO': {
        'name': 'Norway',
        'tlds': ['.no', '.com'],
        'paths': ['/', '/kontakt', '/om-oss', '/contact', '/about'],
        'source_csv': '/mnt/hdd/SCRAPER_DATA/csv/EURES/Norway/Norway_contacts_50.csv',
        'company_col': 'company_name',
        'city_col': 'company_city',
    },
    'BE': {
        'name': 'Belgium',
        'tlds': ['.be', '.com'],
        'paths': ['/', '/contact', '/over-ons', '/a-propos', '/about'],
        'source_csv': '/mnt/hdd/SCRAPER_DATA/csv/EURES/Belgium/Belgium_contacts_50.csv',
        'company_col': 'company_name',
        'city_col': 'company_city',
    },
    'PL': {
        'name': 'Poland',
        'tlds': ['.pl', '.com'],
        'paths': ['/', '/kontakt', '/o-nas', '/contact', '/about'],
        'source_csv': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/EURES/OUTPUT/Poland/Poland_contacts_50.csv',
        'company_col': 'company_name',
        'city_col': 'company_city',
    },
    'SE': {
        'name': 'Sweden',
        'tlds': ['.se', '.com'],
        'paths': ['/', '/kontakt', '/om-oss', '/contact', '/about'],
        'source_csv': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/SWEDEN/OUTPUT/Sweden_MASTER.csv',
        'company_col': 'company_name',
        'city_col': 'company_city',
    },
    'FI': {
        'name': 'Finland',
        'tlds': ['.fi', '.com'],
        'paths': ['/', '/yhteystiedot', '/ota-yhteytta', '/contact', '/about'],
        'source_csv': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/FINLAND/MASTER_FINLAND_CONTACTS.csv',
        'company_col': 'organization',
        'city_col': 'location',
    },
    'IS': {
        'name': 'Iceland',
        'tlds': ['.is', '.com'],
        'paths': ['/', '/hafa-samband', '/um-okkur', '/contact', '/about'],
        'source_csv': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/EURES/OUTPUT/Iceland/Iceland_contacts_50.csv',
        'company_col': 'company_name',
        'city_col': 'company_city',
    },
    'UK': {
        'name': 'United Kingdom',
        'tlds': ['.co.uk', '.uk', '.com'],
        'paths': ['/', '/contact', '/contact-us', '/about', '/about-us'],
        'source_csv': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/UK/OUTPUT/UK_MASTER.csv',
        'company_col': 'company_name',
        'city_col': 'company_city',
    },
    'FR': {
        'name': 'France',
        'tlds': ['.fr', '.com'],
        'paths': ['/', '/contact', '/mentions-legales', '/a-propos', '/about'],
        'source_csv': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/FRANCE/OUTPUT/France_MASTER.csv',
        'company_col': 'company_name',
        'city_col': 'company_city',
    },
    'ES': {
        'name': 'Spain',
        'tlds': ['.es', '.com'],
        'paths': ['/', '/contacto', '/aviso-legal', '/sobre-nosotros', '/contact'],
        'source_csv': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/SPAIN/OUTPUT/Spain_MASTER.csv',
        'company_col': 'company_name',
        'city_col': 'company_city',
    },
    'IT': {
        'name': 'Italy',
        'tlds': ['.it', '.com'],
        'paths': ['/', '/contatti', '/chi-siamo', '/contact', '/about'],
        'source_csv': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ITALY/OUTPUT/Italy_MASTER.csv',
        'company_col': 'company_name',
        'city_col': 'company_city',
    },
    'IE': {
        'name': 'Ireland',
        'tlds': ['.ie', '.com'],
        'paths': ['/', '/contact', '/contact-us', '/about', '/about-us'],
        'source_csv': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/IRELAND/OUTPUT/Ireland_MASTER.csv',
        'company_col': 'company_name',
        'city_col': 'company_city',
    },
}

# Paths
OUTPUT_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/ENRICHED')
CACHE_DIR = OUTPUT_DIR / 'cache'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# HTTP
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
TIMEOUT = 8

EMAIL_BLACKLIST = ['example', 'test', 'google', 'facebook', 'cookie', 'privacy',
                   'noreply', 'wixpress', '.png', '.jpg', 'datenschutz']

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


class CountryEnricher:
    def __init__(self, country_code: str, batch_size: int = 40):
        self.country = country_code.upper()
        self.config = COUNTRY_CONFIG.get(self.country)
        if not self.config:
            raise ValueError(f"Unknown country: {country_code}")

        self.batch_size = batch_size
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.cache_file = CACHE_DIR / f'{self.country}_cache.json'
        self.cache = self._load_cache()
        self.master_csv = OUTPUT_DIR / f'{self.country}_ENRICHED_MASTER.csv'
        self.stats = {'total': 0, 'found': 0, 'failed': 0}

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
        name = company.lower()
        # Remove common suffixes
        for suffix in [r'\s*gmbh', r'\s*ag', r'\s*bv', r'\s*nv', r'\s*as', r'\s*aps',
                       r'\s*ab', r'\s*sa', r'\s*srl', r'\s*ltd', r'\s*inc',
                       r'\s*&\s*co', r'\s*kg', r'\s*ohg']:
            name = re.sub(suffix, '', name, flags=re.I)
        name = name.strip()
        if not name:
            return []

        slug = re.sub(r'[^a-z0-9]+', '-', name).strip('-')
        # Handle umlauts
        for old, new in [('ä', 'ae'), ('ö', 'oe'), ('ü', 'ue'), ('ß', 'ss'),
                         ('ø', 'o'), ('æ', 'ae'), ('å', 'a')]:
            slug = slug.replace(old, new)

        domains = []
        for tld in self.config['tlds']:
            domains.append(f"{slug}{tld}")

        no_dash = slug.replace('-', '')
        if no_dash != slug:
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

    def load_companies(self, limit: int = None) -> List[Dict]:
        csv_path = Path(self.config['source_csv'])
        if not csv_path.exists():
            logger.error(f"Source not found: {csv_path}")
            return []

        companies = []
        seen = set()
        with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get(self.config['company_col'], '').strip()
                city = row.get(self.config['city_col'], '').strip()
                if name and len(name) > 3 and name not in seen:
                    seen.add(name)
                    companies.append({'company': name, 'city': city})
                    if limit and len(companies) >= limit:
                        break

        logger.info(f"Loaded {len(companies)} companies from {self.country}")
        return companies

    def append_to_master(self, records: List[Dict]):
        if not records:
            return

        exists = self.master_csv.exists()
        with open(self.master_csv, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['company', 'email', 'website', 'city', 'country', 'date'])
            if not exists:
                writer.writeheader()
            for r in records:
                writer.writerow(r)
        logger.info(f"📁 Saved {len(records)} to {self.master_csv.name}")

    def run(self, limit: int = None):
        companies = self.load_companies(limit)
        if not companies:
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

            if len(batch) >= self.batch_size:
                self.append_to_master(batch)
                self._save_cache()
                batch = []

            if (i + 1) % 100 == 0:
                logger.info(f"Progress: {i+1}/{len(companies)}")

            time.sleep(0.5)

        if batch:
            self.append_to_master(batch)
            self._save_cache()

        print(f"\n=== {self.config['name']} ENRICHMENT ===")
        print(f"Total: {self.stats['total']}")
        print(f"Found: {self.stats['found']} ({100*self.stats['found']/max(1,self.stats['total']):.0f}%)")
        print(f"Master: {self.master_csv}")


def show_status():
    print("=== MULTI-COUNTRY ENRICHMENT STATUS ===\n")
    for code, cfg in COUNTRY_CONFIG.items():
        master = OUTPUT_DIR / f'{code}_ENRICHED_MASTER.csv'
        count = 0
        if master.exists():
            with open(master) as f:
                count = len(f.readlines()) - 1
        print(f"{code} ({cfg['name']:12}): {count:5} enriched companies")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--country', type=str, help='Country code: DE, AT, CH, NL, NO, BE')
    parser.add_argument('--limit', type=int, help='Limit companies')
    parser.add_argument('--batch-size', type=int, default=40)
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--all', action='store_true', help='Run all countries')
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.all:
        for code in COUNTRY_CONFIG.keys():
            try:
                enricher = CountryEnricher(code, args.batch_size)
                enricher.run(args.limit)
            except Exception as e:
                logger.error(f"{code}: {e}")
        return

    if not args.country:
        print("Usage: --country DE|AT|CH|NL|NO|BE or --all")
        show_status()
        return

    enricher = CountryEnricher(args.country, args.batch_size)
    enricher.run(args.limit)


if __name__ == '__main__':
    main()
