#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
Telecom Provider Enricher

Enriches Romanian companies with emails and phones using ALL available sources:
1. ONRC database - match company name to get CUI
2. ANAF API - get phone by CUI (FREE, no auth)
3. ANOFM database - emails and phones
4. Website scraping - extract emails from contact pages

Usage:
    python3 telecom_enricher.py --input companies.csv --output enriched.csv
    python3 telecom_enricher.py --input companies.csv --limit 50
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
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from skills_common import to_ascii

# Paths
ONRC_CSV = Path('/opt/ACTIVE/OPENDATA/DATA/ROMANIA/ONRC/onrc_firme_clean.csv')
ANOFM_CSV = Path('/opt/ACTIVE/OPENDATA/DATA/ROMANIA/ANOFM/anofm_master.csv')
CACHE_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/ENRICHMENT_CACHE')
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ANAF API
ANAF_API = 'https://webservicesp.anaf.ro/api/PlatitorTvaRest/v9/tva'
ANAF_BATCH_SIZE = 100
ANAF_RATE_LIMIT = 1.2

# HTTP
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
TIMEOUT = 10

# Email blacklist
EMAIL_BLACKLIST = ['example', 'test', 'google', 'facebook', 'cookie', 'privacy',
                   'noreply', 'wixpress', '.png', '.jpg', 'gdpr', 'subscribe']

# Romanian TLDs
TLDS = ['.ro', '.com', '.eu', '.net', '.info']
CONTACT_PATHS = ['/', '/contact', '/contacte', '/despre-noi', '/about']

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def normalize_name(name: str) -> str:
    """Normalize company name for matching."""
    name = to_ascii(name).upper().strip()
    for suffix in [' S.R.L.', ' SRL', ' S.A.', ' SA', ' S.C.', ' SC',
                   ' S.C.S.', ' SCS', ' P.F.A.', ' PFA', ' I.I.', ' II']:
        name = name.replace(suffix, '')
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


class ONRCMatcher:
    """Match company names against ONRC database to get CUI."""

    def __init__(self):
        self.name_to_cui = {}
        self.loaded = False

    def load(self):
        if self.loaded:
            return
        if not ONRC_CSV.exists():
            logger.warning(f"ONRC file not found: {ONRC_CSV}")
            self.loaded = True
            return

        logger.info("Loading ONRC database...")
        count = 0
        with open(ONRC_CSV, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f, delimiter='^')
            for row in reader:
                name = (row.get('DENUMIRE') or '').strip()
                cui = (row.get('CUI') or '').strip()
                if name and cui and cui.isdigit():
                    norm_name = normalize_name(name)
                    if norm_name:
                        self.name_to_cui[norm_name] = cui
                        count += 1
        self.loaded = True
        logger.info(f"Loaded {count:,} companies from ONRC")

    def find_cui(self, company_name: str) -> Optional[str]:
        if not self.loaded:
            self.load()
        return self.name_to_cui.get(normalize_name(company_name))


class ANOFMMatcher:
    """Match company names against ANOFM database for emails/phones."""

    def __init__(self):
        self.name_to_data = {}
        self.loaded = False

    def load(self):
        if self.loaded:
            return
        if not ANOFM_CSV.exists():
            logger.warning(f"ANOFM file not found: {ANOFM_CSV}")
            self.loaded = True
            return

        logger.info("Loading ANOFM database...")
        count = 0
        with open(ANOFM_CSV, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = (row.get('company_name') or '').strip()
                if not name:
                    continue

                norm_name = normalize_name(name)
                if not norm_name:
                    continue

                # Get contact info
                emails = [e.strip() for e in [row.get('email_1'), row.get('email_2'), row.get('email_3')] if e and e.strip() and '@' in e]
                phones = [p.strip() for p in [row.get('phone_1'), row.get('phone_2'), row.get('phone_3')] if p and p.strip()]
                website = (row.get('company_website') or '').strip()
                cui = (row.get('company_org_number') or '').strip()

                if emails or phones:
                    if norm_name not in self.name_to_data:
                        self.name_to_data[norm_name] = {
                            'emails': emails,
                            'phones': phones,
                            'website': website,
                            'cui': cui
                        }
                        count += 1

        self.loaded = True
        logger.info(f"Loaded {count:,} companies from ANOFM")

    def find(self, company_name: str) -> Optional[Dict]:
        if not self.loaded:
            self.load()
        return self.name_to_data.get(normalize_name(company_name))


class ANAFClient:
    """Query ANAF API for phone numbers by CUI."""

    def __init__(self):
        self.cache_file = CACHE_DIR / 'anaf_cache.json'
        self.cache = self._load_cache()

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

    def get_phone(self, cui: str) -> Optional[str]:
        if cui in self.cache:
            return self.cache[cui]

        try:
            today = date.today().isoformat()
            payload = [{"cui": int(cui), "data": today}]
            response = requests.post(ANAF_API, json=payload,
                                     headers={'Content-Type': 'application/json'}, timeout=30)

            if response.status_code == 200:
                data = response.json()
                for item in data.get('found', []):
                    info = item.get('date_generale', {})
                    phone = info.get('telefon', '')
                    if phone:
                        phone = re.sub(r'[\s.-]', '', phone)
                        if phone and len(phone) >= 9:
                            self.cache[cui] = phone
                            self._save_cache()
                            return phone

            self.cache[cui] = None
            time.sleep(ANAF_RATE_LIMIT)
            return None

        except Exception as e:
            logger.debug(f"ANAF error for {cui}: {e}")
            return None


class WebsiteScraper:
    """Scrape websites for email addresses."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.cache_file = CACHE_DIR / 'website_cache.json'
        self.cache = self._load_cache()

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
        name = to_ascii(company).lower()
        for suffix in [r'\s*s\.?r\.?l\.?', r'\s*s\.?a\.?', r'\s*s\.?c\.?']:
            name = re.sub(suffix + r'\.?$', '', name, flags=re.I)
        name = name.strip()

        if not name or len(name) < 3:
            return []

        slug = re.sub(r'[^a-z0-9]+', '', name)
        domains = []
        if slug and len(slug) >= 3:
            for tld in TLDS:
                domains.append(f"{slug}{tld}")

        words = name.split()
        if words and len(words[0]) >= 4:
            first = re.sub(r'[^a-z0-9]', '', words[0])
            if first:
                domains.append(f"{first}.ro")
                domains.append(f"{first}.com")

        return list(dict.fromkeys(domains))[:6]

    def extract_emails(self, html: str) -> List[str]:
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html)
        valid = []
        for email in emails:
            email_lower = email.lower()
            if not any(bl in email_lower for bl in EMAIL_BLACKLIST):
                if email_lower not in valid:
                    valid.append(email_lower)

        def priority(e):
            if e.startswith(('office@', 'contact@', 'info@', 'sales@')):
                return 0
            return 1
        return sorted(valid, key=priority)[:2]

    def find_email(self, company: str) -> Tuple[Optional[str], Optional[str]]:
        cache_key = to_ascii(company).lower()[:50]

        if cache_key in self.cache:
            cached = self.cache[cache_key]
            return cached.get('email'), cached.get('website')

        domains = self.company_to_domains(company)

        for domain in domains:
            for prefix in [f'https://www.{domain}', f'https://{domain}']:
                for path in CONTACT_PATHS:
                    url = prefix + path
                    try:
                        resp = self.session.get(url, timeout=TIMEOUT, allow_redirects=True)
                        if resp.status_code == 200:
                            emails = self.extract_emails(resp.text)
                            if emails:
                                self.cache[cache_key] = {'email': emails[0], 'website': prefix}
                                self._save_cache()
                                return emails[0], prefix
                    except:
                        pass
                    time.sleep(0.2)

        self.cache[cache_key] = {'email': None, 'website': None}
        self._save_cache()
        return None, None


class TelecomEnricher:
    """Main enricher combining all sources."""

    def __init__(self):
        self.onrc = ONRCMatcher()
        self.anofm = ANOFMMatcher()
        self.anaf = ANAFClient()
        self.scraper = WebsiteScraper()
        self.stats = {'total': 0, 'with_cui': 0, 'with_phone': 0, 'with_email': 0}

    def enrich_company(self, company: str) -> Dict:
        result = {
            'company': to_ascii(company),
            'cui': '',
            'phone': '',
            'email': '',
            'website': '',
            'source': []
        }

        # Source 1: ANOFM database (has email + phone)
        anofm_data = self.anofm.find(company)
        if anofm_data:
            if anofm_data.get('emails'):
                result['email'] = anofm_data['emails'][0]
                result['source'].append('anofm')
                self.stats['with_email'] += 1
            if anofm_data.get('phones'):
                result['phone'] = anofm_data['phones'][0]
                if 'anofm' not in result['source']:
                    result['source'].append('anofm')
                self.stats['with_phone'] += 1
            if anofm_data.get('website'):
                result['website'] = anofm_data['website']
            if anofm_data.get('cui'):
                result['cui'] = anofm_data['cui']
                self.stats['with_cui'] += 1

        # Source 2: ONRC for CUI (if not found in ANOFM)
        if not result['cui']:
            cui = self.onrc.find_cui(company)
            if cui:
                result['cui'] = cui
                result['source'].append('onrc')
                self.stats['with_cui'] += 1

        # Source 3: ANAF API for phone (if have CUI but no phone)
        if result['cui'] and not result['phone']:
            phone = self.anaf.get_phone(result['cui'])
            if phone:
                result['phone'] = phone
                result['source'].append('anaf')
                self.stats['with_phone'] += 1

        # Source 4: Website scraping for email (if still missing)
        if not result['email']:
            email, website = self.scraper.find_email(company)
            if email:
                result['email'] = email
                result['source'].append('web')
                self.stats['with_email'] += 1
            if website and not result['website']:
                result['website'] = website

        result['source'] = '+'.join(result['source']) if result['source'] else 'none'
        return result

    def enrich_csv(self, input_path: Path, output_path: Path, limit: int = None):
        # Load input
        companies = []
        with open(input_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            input_fields = reader.fieldnames
            for row in reader:
                company = row.get('company', '').strip()
                if company:
                    companies.append({'original': row, 'company': company})

        if limit:
            companies = companies[:limit]

        self.stats['total'] = len(companies)
        logger.info(f"Enriching {len(companies)} companies...")

        # Pre-load databases
        self.onrc.load()
        self.anofm.load()

        # Enrich each company
        enriched = []
        for i, comp in enumerate(companies):
            result = self.enrich_company(comp['company'])
            merged = {**comp['original'], **result}
            enriched.append(merged)

            # Log progress
            status = []
            if result['cui']:
                status.append(f"CUI:{result['cui']}")
            if result['phone']:
                status.append(f"TEL:{result['phone']}")
            if result['email']:
                status.append(f"EMAIL:{result['email']}")

            status_str = ', '.join(status) if status else 'no data'
            logger.info(f"[{i+1}/{len(companies)}] {comp['company'][:40]} -> {status_str}")

            # Save periodically
            if (i + 1) % 20 == 0:
                self._save_enriched(enriched, output_path, input_fields)

        # Final save
        self._save_enriched(enriched, output_path, input_fields)

        # Print stats
        print(f"\n{'='*50}")
        print(f"ENRICHMENT COMPLETE")
        print(f"{'='*50}")
        print(f"Total: {self.stats['total']}")
        print(f"With CUI: {self.stats['with_cui']} ({100*self.stats['with_cui']/max(1,self.stats['total']):.0f}%)")
        print(f"With Phone: {self.stats['with_phone']} ({100*self.stats['with_phone']/max(1,self.stats['total']):.0f}%)")
        print(f"With Email: {self.stats['with_email']} ({100*self.stats['with_email']/max(1,self.stats['total']):.0f}%)")
        print(f"Output: {output_path}")

    def _save_enriched(self, data: List[Dict], output_path: Path, input_fields: List[str]):
        if not data:
            return
        enrich_fields = ['cui', 'phone', 'email', 'website', 'source']
        all_fields = list(input_fields) + [f for f in enrich_fields if f not in input_fields]

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=all_fields, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(data)


def main():
    parser = argparse.ArgumentParser(description='Enrich Romanian companies with emails/phones')
    parser.add_argument('--input', '-i', type=Path, required=True, help='Input CSV')
    parser.add_argument('--output', '-o', type=Path, help='Output CSV')
    parser.add_argument('--limit', type=int, help='Limit number of companies')
    parser.add_argument('--clear-cache', action='store_true', help='Clear caches')
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)

    output = args.output or args.input.with_name(args.input.stem + '_enriched.csv')

    if args.clear_cache:
        for cache_file in CACHE_DIR.glob('*.json'):
            cache_file.unlink()
        print("Caches cleared")

    enricher = TelecomEnricher()
    enricher.enrich_csv(args.input, output, args.limit)


if __name__ == '__main__':
    main()
