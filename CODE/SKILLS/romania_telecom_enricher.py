#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
Romania Telecom Provider Enricher

Finds contact emails and websites for Romanian telecom companies.
Uses company name to derive website, then scrapes contact pages.

Usage:
    python3 romania_telecom_enricher.py --input /opt/ACTIVE/OPENDATA/DATA/SIP_TRUNKING/telecom_providers_raw.csv
    python3 romania_telecom_enricher.py --limit 50
    python3 romania_telecom_enricher.py --priority 1  # Only VoIP/SIP specialists
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
from typing import Dict, List, Optional, Tuple

from skills_common import to_ascii

# Paths
DATA_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/SIP_TRUNKING')
INPUT_CSV = DATA_DIR / 'telecom_providers_raw.csv'
OUTPUT_CSV = DATA_DIR / 'telecom_providers_enriched.csv'
CACHE_FILE = DATA_DIR / 'enrichment_cache.json'
DATA_DIR.mkdir(parents=True, exist_ok=True)

# HTTP
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}
TIMEOUT = 10

# Email blacklist patterns
EMAIL_BLACKLIST = [
    'example', 'test', 'google', 'facebook', 'cookie', 'privacy',
    'noreply', 'wixpress', '.png', '.jpg', 'datenschutz', 'gdpr',
    'subscribe', 'newsletter', 'unsubscribe', 'support@wix'
]

# Romanian telecom TLDs and paths
TLDS = ['.ro', '.com', '.eu', '.net']
CONTACT_PATHS = [
    '/', '/contact', '/contacte', '/despre-noi', '/about', '/about-us',
    '/contact-us', '/pagini/contact', '/servicii', '/business'
]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


class TelecomEnricher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.cache = self._load_cache()
        self.stats = {'total': 0, 'found': 0, 'cached': 0, 'failed': 0}

    def _load_cache(self) -> dict:
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE) as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_cache(self):
        with open(CACHE_FILE, 'w') as f:
            json.dump(self.cache, f, indent=2)

    def company_to_slugs(self, company: str) -> List[str]:
        """Convert company name to potential website slugs."""
        name = company.lower()

        # Remove common Romanian suffixes
        for suffix in [r'\s*s\.?r\.?l\.?', r'\s*s\.?a\.?', r'\s*s\.?c\.?', r'\s*&\s*co']:
            name = re.sub(suffix + r'\.?$', '', name, flags=re.I)
        name = name.strip()

        if not name:
            return []

        # Handle Romanian diacritics
        for old, new in [('a', 'a'), ('i', 'i'), ('s', 's'), ('t', 't')]:
            name = name.replace(old, new)

        # Convert to slug
        slug = re.sub(r'[^a-z0-9]+', '', name)
        slug_dash = re.sub(r'[^a-z0-9]+', '-', name).strip('-')

        # Common Romanian telecom naming patterns
        slugs = []
        for s in [slug, slug_dash]:
            if s:
                slugs.append(s)

        # Also try key word extraction (e.g., "VOIPIT" from "VOIPIT S.R.L.")
        words = [w for w in re.split(r'\s+', name) if len(w) > 2]
        if words:
            slugs.append(words[0].replace('-', ''))

        return list(dict.fromkeys(slugs))[:4]  # Unique, max 4

    def extract_emails(self, html: str) -> List[str]:
        """Extract valid emails from HTML."""
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html)

        valid = []
        for email in emails:
            email_lower = email.lower()
            if not any(bl in email_lower for bl in EMAIL_BLACKLIST):
                # Prefer business emails
                if email_lower not in valid:
                    valid.append(email_lower)

        # Sort: office/contact/info first
        def priority(e):
            if e.startswith(('office@', 'contact@', 'info@', 'sales@', 'comercial@')):
                return 0
            if e.startswith(('support@', 'tehnic@', 'technical@')):
                return 1
            return 2

        return sorted(valid, key=priority)[:3]

    def extract_phones(self, html: str) -> List[str]:
        """Extract Romanian phone numbers."""
        # Romanian patterns: 0721 xxx xxx, +40 721 xxx xxx
        patterns = [
            r'\+?40\s*[27]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}',
            r'0[27]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}',
            r'\+?40\s*[23]\d{1,2}[\s.-]?\d{3}[\s.-]?\d{3,4}'
        ]

        phones = []
        for pattern in patterns:
            for match in re.findall(pattern, html):
                # Normalize
                phone = re.sub(r'[\s.-]', '', match)
                if phone.startswith('0'):
                    phone = '+40' + phone[1:]
                elif not phone.startswith('+'):
                    phone = '+' + phone
                if phone not in phones and len(phone) >= 10:
                    phones.append(phone)

        return phones[:2]

    def try_website(self, company: str, existing_website: str = None) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Try to find website and extract contact info."""
        cache_key = to_ascii(company).lower()

        if cache_key in self.cache:
            cached = self.cache[cache_key]
            self.stats['cached'] += 1
            return cached.get('website'), cached.get('email'), cached.get('phone')

        # Try existing website first
        if existing_website and existing_website.strip():
            website = existing_website.strip()
            if not website.startswith('http'):
                website = 'https://' + website

            email, phone = self._scrape_website(website)
            if email:
                self.cache[cache_key] = {'website': website, 'email': email, 'phone': phone}
                return website, email, phone

        # Derive website from company name
        slugs = self.company_to_slugs(company)

        for slug in slugs:
            for tld in TLDS:
                domain = f"{slug}{tld}"
                for prefix in [f'https://www.{domain}', f'https://{domain}']:
                    email, phone = self._scrape_website(prefix)
                    if email:
                        self.cache[cache_key] = {'website': prefix, 'email': email, 'phone': phone}
                        return prefix, email, phone
                    time.sleep(0.3)

        self.cache[cache_key] = {'website': None, 'email': None, 'phone': None}
        return None, None, None

    def _scrape_website(self, base_url: str) -> Tuple[Optional[str], Optional[str]]:
        """Scrape website for contact info."""
        for path in CONTACT_PATHS:
            url = base_url.rstrip('/') + path
            try:
                resp = self.session.get(url, timeout=TIMEOUT, allow_redirects=True)
                if resp.status_code == 200:
                    emails = self.extract_emails(resp.text)
                    phones = self.extract_phones(resp.text)
                    if emails:
                        return emails[0], phones[0] if phones else None
            except Exception:
                pass

        return None, None

    def load_providers(self, input_csv: Path, priority_filter: int = None, limit: int = None) -> List[Dict]:
        """Load telecom providers from CSV."""
        providers = []

        with open(input_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                priority = int(row.get('priority', 9))

                if priority_filter is not None and priority > priority_filter:
                    continue

                providers.append({
                    'company': row['company'].strip(),
                    'type': row.get('type', '').strip(),
                    'priority': priority,
                    'website': row.get('website', '').strip(),
                    'email': row.get('email', '').strip(),
                })

                if limit and len(providers) >= limit:
                    break

        # Sort by priority
        providers.sort(key=lambda x: x['priority'])
        logger.info(f"Loaded {len(providers)} providers")
        return providers

    def enrich(self, input_csv: Path, output_csv: Path, priority_filter: int = None, limit: int = None):
        """Main enrichment process."""
        providers = self.load_providers(input_csv, priority_filter, limit)
        enriched = []

        for i, prov in enumerate(providers):
            self.stats['total'] += 1
            company = prov['company']

            # Skip if already has email
            if prov['email']:
                enriched.append({
                    'company': to_ascii(company),
                    'type': prov['type'],
                    'priority': prov['priority'],
                    'website': prov['website'],
                    'email': prov['email'],
                    'phone': '',
                    'source': 'manual',
                    'date': datetime.now().strftime('%Y-%m-%d')
                })
                self.stats['found'] += 1
                logger.info(f"[{i+1}/{len(providers)}] {company[:40]} - pre-filled: {prov['email']}")
                continue

            # Try to find website and email
            website, email, phone = self.try_website(company, prov['website'])

            if email:
                self.stats['found'] += 1
                logger.info(f"[{i+1}/{len(providers)}] {company[:40]} -> {email}")
            else:
                self.stats['failed'] += 1
                logger.info(f"[{i+1}/{len(providers)}] {company[:40]} - not found")

            enriched.append({
                'company': to_ascii(company),
                'type': prov['type'],
                'priority': prov['priority'],
                'website': website or '',
                'email': email or '',
                'phone': phone or '',
                'source': 'scraped' if email else 'not_found',
                'date': datetime.now().strftime('%Y-%m-%d')
            })

            # Save periodically
            if (i + 1) % 20 == 0:
                self._save_cache()

            time.sleep(0.5)

        # Save results
        self._save_cache()
        self._save_enriched(enriched, output_csv)

        # Print stats
        print(f"\n=== TELECOM ENRICHMENT COMPLETE ===")
        print(f"Total: {self.stats['total']}")
        print(f"Found: {self.stats['found']} ({100*self.stats['found']/max(1,self.stats['total']):.0f}%)")
        print(f"Cached: {self.stats['cached']}")
        print(f"Failed: {self.stats['failed']}")
        print(f"Output: {output_csv}")

    def _save_enriched(self, data: List[Dict], output_csv: Path):
        """Save enriched data to CSV."""
        if not data:
            return

        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['company', 'type', 'priority', 'website', 'email', 'phone', 'source', 'date']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

        logger.info(f"Saved {len(data)} providers to {output_csv}")


def main():
    parser = argparse.ArgumentParser(description='Enrich Romanian telecom providers with contact info')
    parser.add_argument('--input', type=Path, default=INPUT_CSV, help='Input CSV')
    parser.add_argument('--output', type=Path, default=OUTPUT_CSV, help='Output CSV')
    parser.add_argument('--priority', type=int, help='Max priority filter (1=VoIP specialists, 2=telecom, 3=ISP)')
    parser.add_argument('--limit', type=int, help='Limit number of companies')
    parser.add_argument('--clear-cache', action='store_true', help='Clear cache before running')
    args = parser.parse_args()

    if args.clear_cache and CACHE_FILE.exists():
        CACHE_FILE.unlink()
        print("Cache cleared")

    enricher = TelecomEnricher()
    enricher.enrich(args.input, args.output, args.priority, args.limit)


if __name__ == '__main__':
    main()
