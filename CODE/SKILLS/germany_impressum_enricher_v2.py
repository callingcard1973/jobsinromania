#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
Germany Impressum Enricher v2 - Incremental saves to master CSV

Saves enriched companies to master CSV every N companies (default 40).
Runs continuously, picks up where it left off using cache.

Usage:
    python3 germany_impressum_enricher_v2.py                    # Full run, save every 40
    python3 germany_impressum_enricher_v2.py --batch-size 100   # Save every 100
    python3 germany_impressum_enricher_v2.py --status           # Show progress
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
from typing import Dict, List, Optional, Tuple
from filelock import FileLock

from skills_common import to_ascii

# Paths
OUTPUT_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/GERMANY_ENRICHED')
MASTER_CSV = OUTPUT_DIR / 'Germany_ENRICHED_MASTER.csv'
CACHE_FILE = OUTPUT_DIR / 'domain_cache.json'
PROGRESS_FILE = OUTPUT_DIR / 'progress.json'
LOGS_DIR = Path('/opt/ACTIVE/INFRA/LOGS/enricher')

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / f"enricher_{datetime.now().strftime('%Y%m%d')}.log")
    ]
)
logger = logging.getLogger(__name__)

# HTTP config
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
}
TIMEOUT = 8
DELAY = 0.5

EMAIL_BLACKLIST = [
    'example', 'test', 'sentry', 'google', 'facebook', 'twitter',
    'cookie', 'privacy', 'noreply', 'no-reply', 'wixpress', 'schema.org',
    '.png', '.jpg', '.gif', '.svg', '.avif', '.webp', 'datenschutz', 'webmaster',
    'mustermann', 'beispiel', 'muster@', 'platzhalter', 'dummy', 'query@'
]

MASTER_COLUMNS = [
    'company', 'email', 'website', 'city', 'region', 'source', 'enriched_date'
]


class IncrementalEnricher:
    """Enricher with incremental saves to master CSV."""

    def __init__(self, batch_size: int = 40):
        self.batch_size = batch_size
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.cache = self._load_json(CACHE_FILE, {})
        self.progress = self._load_json(PROGRESS_FILE, {'processed': [], 'stats': {}})
        self.current_batch = []
        self.stats = {'total': 0, 'found': 0, 'cached': 0, 'failed': 0}

    def _load_json(self, path: Path, default: dict) -> dict:
        if path.exists():
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except:
                pass
        return default

    def _save_json(self, path: Path, data: dict):
        with open(path, 'w') as f:
            json.dump(data, f)

    def _save_cache(self):
        self._save_json(CACHE_FILE, self.cache)

    def _save_progress(self):
        self.progress['stats'] = self.stats
        self.progress['last_update'] = datetime.now().isoformat()
        self._save_json(PROGRESS_FILE, self.progress)

    def company_to_domains(self, company_name: str) -> List[str]:
        name = company_name.lower()
        for suffix in [r'\s*gmbh\s*&\s*co\.?\s*kg', r'\s*gmbh', r'\s*ag', r'\s*kg',
                       r'\s*ohg', r'\s*ug', r'\s*e\.?v\.?', r'\s*mbh', r'\s*se',
                       r'\s*niederlassung\s+\w+', r'\s*nl\s+\w+']:
            name = re.sub(suffix, '', name, flags=re.I)
        name = name.strip()
        if not name:
            return []

        domains = []
        slug = re.sub(r'[^a-z0-9äöüß]+', '-', name)
        slug = slug.replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
        slug = slug.strip('-')

        if slug:
            domains.extend([f"{slug}.de", f"{slug}.com"])
            no_dash = slug.replace('-', '')
            if no_dash != slug:
                domains.append(f"{no_dash}.de")
            first = slug.split('-')[0]
            if len(first) > 3 and first != slug:
                domains.append(f"{first}.de")
        return domains[:5]

    def extract_emails(self, html: str) -> List[str]:
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(pattern, html)
        valid = [e for e in emails if not any(bl in e.lower() for bl in EMAIL_BLACKLIST) and len(e) < 100]
        return list(dict.fromkeys(valid))[:2]

    def try_domain(self, domain: str) -> Optional[Tuple[str, List[str]]]:
        if domain in self.cache:
            cached = self.cache[domain]
            if cached.get('emails'):
                self.stats['cached'] += 1
                return (domain, cached['emails'])
            return None

        paths = ['/', '/impressum', '/kontakt', '/contact']
        for prefix in [f'https://www.{domain}', f'https://{domain}']:
            for path in paths:
                try:
                    resp = self.session.get(f"{prefix}{path}", timeout=TIMEOUT, allow_redirects=True)
                    if resp.status_code == 200:
                        emails = self.extract_emails(resp.text)
                        if emails:
                            self.cache[domain] = {'emails': emails, 'url': f"{prefix}{path}"}
                            return (domain, emails)
                except:
                    pass

        self.cache[domain] = {'emails': [], 'url': None}
        return None

    def enrich_company(self, company_name: str, city: str = '', region: str = '') -> Optional[Dict]:
        self.stats['total'] += 1

        # Skip if already processed
        if company_name in self.progress['processed']:
            return None

        domains = self.company_to_domains(company_name)
        if not domains:
            self.stats['failed'] += 1
            self.progress['processed'].append(company_name)
            return None

        for domain in domains:
            result = self.try_domain(domain)
            if result:
                self.stats['found'] += 1
                self.progress['processed'].append(company_name)
                return {
                    'company': to_ascii(company_name),
                    'email': result[1][0],
                    'website': f"https://www.{result[0]}",
                    'city': to_ascii(city),
                    'region': to_ascii(region),
                    'source': 'arbeitsagentur',
                    'enriched_date': datetime.now().strftime('%Y-%m-%d')
                }
            time.sleep(DELAY / 3)

        self.stats['failed'] += 1
        self.progress['processed'].append(company_name)
        return None

    def append_to_master(self, records: List[Dict]):
        """Append records to master CSV (thread-safe)."""
        if not records:
            return

        lock = FileLock(str(MASTER_CSV) + '.lock')
        with lock:
            file_exists = MASTER_CSV.exists()
            with open(MASTER_CSV, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=MASTER_COLUMNS)
                if not file_exists:
                    writer.writeheader()
                for r in records:
                    writer.writerow(r)

        logger.info(f"📁 Appended {len(records)} records to master CSV")

    def run(self, companies: List[Tuple[str, str, str]]):
        """Run enrichment with incremental saves."""
        logger.info(f"Starting enrichment: {len(companies)} companies, batch size {self.batch_size}")

        batch = []
        for i, (company, city, region) in enumerate(companies):
            result = self.enrich_company(company, city, region)

            if result:
                batch.append(result)
                logger.info(f"✅ {company[:35]} → {result['email']}")

            # Save batch every N companies
            if len(batch) >= self.batch_size:
                self.append_to_master(batch)
                self._save_cache()
                self._save_progress()
                batch = []

            # Progress update every 100
            if (i + 1) % 100 == 0:
                logger.info(f"Progress: {i+1}/{len(companies)} ({100*(i+1)/len(companies):.0f}%)")

            time.sleep(DELAY)

        # Final batch
        if batch:
            self.append_to_master(batch)
            self._save_cache()
            self._save_progress()

        return self.stats


def load_arbeitsagentur_companies() -> List[Tuple[str, str, str]]:
    """Load companies with city and region from Arbeitsagentur."""
    csv_file = Path('/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/GERMANY/OUTPUT/Germany_ARBEITSAGENTUR_MASTER.csv')

    if not csv_file.exists():
        logger.error(f"File not found: {csv_file}")
        return []

    companies = []
    seen = set()

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get('company_name', '').strip()
            city = row.get('location_city', '').strip()
            region = row.get('location_region', '').strip()

            if name and len(name) > 3 and name not in seen:
                if not any(x in name.lower() for x in ['privat', 'anonym', 'vertraulich']):
                    seen.add(name)
                    companies.append((name, city, region))

    logger.info(f"Loaded {len(companies)} unique companies")
    return companies


def show_status():
    """Show current enrichment status."""
    progress = {}
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            progress = json.load(f)

    master_count = 0
    if MASTER_CSV.exists():
        with open(MASTER_CSV) as f:
            master_count = len(f.readlines()) - 1

    cache_count = 0
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            cache_count = len(json.load(f))

    print("=== GERMANY ENRICHMENT STATUS ===")
    print(f"Master CSV:      {master_count} enriched companies")
    print(f"Processed:       {len(progress.get('processed', []))} companies")
    print(f"Cache entries:   {cache_count} domains")
    print(f"Last update:     {progress.get('last_update', 'Never')}")
    print(f"Stats:           {progress.get('stats', {})}")


def main():
    parser = argparse.ArgumentParser(description='Germany Impressum Enricher v2')
    parser.add_argument('--batch-size', type=int, default=40, help='Save every N companies')
    parser.add_argument('--status', action='store_true', help='Show status')
    parser.add_argument('--reset', action='store_true', help='Reset progress (start fresh)')
    parser.add_argument('--shard', type=str, default=None, help='Shard N/M: process only companies where hash %% M == N-1 (e.g., --shard 1/3)')
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.reset:
        for f in [PROGRESS_FILE, MASTER_CSV]:
            if f.exists():
                f.unlink()
        print("Progress reset. Run again to start fresh.")
        return

    companies = load_arbeitsagentur_companies()
    if not companies:
        return

    enricher = IncrementalEnricher(batch_size=args.batch_size)

    # Filter out already processed
    processed = set(enricher.progress.get('processed', []))
    remaining = [(c, city, reg) for c, city, reg in companies if c not in processed]

    # Shard filtering for parallel execution
    if args.shard:
        try:
            shard_n, shard_m = args.shard.split('/')
            shard_n, shard_m = int(shard_n), int(shard_m)
            remaining = [(c, city, reg) for c, city, reg in remaining if hash(c) % shard_m == shard_n - 1]
            logger.info(f"Shard {shard_n}/{shard_m}: processing {len(remaining)} companies")
        except (ValueError, ZeroDivisionError):
            logger.error(f"Invalid shard format: {args.shard}. Use N/M (e.g., 1/3)")
            return

    logger.info(f"Already processed: {len(processed)}, Remaining: {len(remaining)}")

    if not remaining:
        logger.info("All companies processed!")
        show_status()
        return

    start = time.time()
    stats = enricher.run(remaining)
    elapsed = time.time() - start

    print(f"\n{'='*50}")
    print("ENRICHMENT COMPLETE")
    print(f"{'='*50}")
    print(f"Processed:    {stats['total']}")
    print(f"Found:        {stats['found']} ({100*stats['found']/max(stats['total'],1):.1f}%)")
    print(f"From cache:   {stats['cached']}")
    print(f"Time:         {elapsed/60:.1f} minutes")
    show_status()


if __name__ == '__main__':
    main()
