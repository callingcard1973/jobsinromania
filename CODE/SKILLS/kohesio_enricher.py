#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
Kohesio Enricher - Add emails to 771K EU subsidy beneficiaries.

Matches Kohesio companies with local data sources:
- ANOFM (4,500+ Romanian companies with emails)
- EU Funds (4,700+ Romanian companies with emails)
- ONRC (6.6M Romanian companies)

Matching strategies:
1. Exact company name match
2. Normalized name match (remove SRL, SA, etc.)
3. CUI match (for Romanian companies)

Usage:
    python3 kohesio_enricher.py --status           # Show status
    python3 kohesio_enricher.py --enrich           # Run enrichment
    python3 kohesio_enricher.py --enrich --country RO  # Romania only
    python3 kohesio_enricher.py --export           # Export enriched

See /opt/CLAUDE.md for shared code rules.
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import re
import csv
import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from skills_common import to_ascii, sanitize
from eu_utils import EU_COUNTRIES, normalize_eu_company

# Paths
OUTPUT_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/EU_SUBSIDY')
ENRICHED_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/EU_ENRICHED')
DB_FILE = ENRICHED_DIR / 'kohesio_enrichment.db'
ENRICHED_DIR.mkdir(parents=True, exist_ok=True)

# Data sources
ANOFM_FILE = Path('/opt/ACTIVE/OPENDATA/DATA/ANOFM/anofm_master.csv')
EUFUNDS_FILE = Path('/opt/ACTIVE/OPENDATA/DATA/FONDURIEUROPENE/ro/fonduri-ue/hot_leads_eu_funds.csv')
ONRC_FILE = Path('/opt/ACTIVE/OPENDATA/DATA/ONRC/onrc_firme_clean.csv')

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


class KohesioEnricher:
    """Enriches Kohesio beneficiaries with emails from local sources."""

    def __init__(self):
        self.db = sqlite3.connect(str(DB_FILE))
        self._init_db()
        self.stats = {
            'total_kohesio': 0,
            'matched': 0,
            'with_email': 0,
            'sources': {},
        }
        # Cache for local data
        self.anofm_cache: Dict[str, Dict] = {}
        self.eufunds_cache: Dict[str, Dict] = {}
        self.onrc_cache: Dict[str, Dict] = {}

    def _init_db(self):
        """Initialize SQLite database for tracking."""
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS enrichment (
                company_id TEXT PRIMARY KEY,
                company_name TEXT,
                country TEXT,
                email TEXT,
                phone TEXT,
                website TEXT,
                source TEXT,
                match_type TEXT,
                enriched_date TEXT
            )
        ''')
        self.db.execute('CREATE INDEX IF NOT EXISTS idx_country ON enrichment(country)')
        self.db.execute('CREATE INDEX IF NOT EXISTS idx_source ON enrichment(source)')
        self.db.commit()

    def _normalize_name(self, name: str) -> str:
        """Normalize company name for matching."""
        if not name:
            return ''
        return normalize_eu_company(name)

    def load_anofm(self) -> int:
        """Load ANOFM data into cache."""
        if not ANOFM_FILE.exists():
            logger.warning(f"ANOFM file not found: {ANOFM_FILE}")
            return 0

        count = 0
        with open(ANOFM_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get('email_1', '').strip().lower()
                if not email or '@' not in email:
                    continue

                name = row.get('company_name', '')
                norm_name = self._normalize_name(name)
                if norm_name:
                    self.anofm_cache[norm_name] = {
                        'email': email,
                        'phone': row.get('phone_1', ''),
                        'website': row.get('company_website', ''),
                        'source': 'ANOFM',
                    }
                    count += 1

        logger.info(f"Loaded {count} ANOFM records with email")
        return count

    def load_eufunds(self) -> int:
        """Load EU Funds data into cache."""
        if not EUFUNDS_FILE.exists():
            logger.warning(f"EU Funds file not found: {EUFUNDS_FILE}")
            return 0

        count = 0
        with open(EUFUNDS_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get('email', '').strip().lower()
                if not email or '@' not in email:
                    continue

                name = row.get('company', '')
                norm_name = self._normalize_name(name)
                if norm_name:
                    self.eufunds_cache[norm_name] = {
                        'email': email,
                        'phone': row.get('phone', ''),
                        'website': '',
                        'source': 'EUFUNDS',
                    }
                    count += 1

        logger.info(f"Loaded {count} EU Funds records with email")
        return count

    def load_onrc(self, limit: int = 100000) -> int:
        """Load ONRC data into cache (subset with websites)."""
        if not ONRC_FILE.exists():
            logger.warning(f"ONRC file not found: {ONRC_FILE}")
            return 0

        count = 0
        with open(ONRC_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            # ONRC uses ^ delimiter
            reader = csv.DictReader(f, delimiter='^')
            for row in reader:
                website = (row.get('WEB') or '').strip()
                if not website:
                    continue

                name = row.get('DENUMIRE') or ''
                cui = row.get('CUI') or ''
                norm_name = self._normalize_name(name)

                if norm_name:
                    self.onrc_cache[norm_name] = {
                        'email': '',  # ONRC doesn't have emails
                        'phone': '',
                        'website': website,
                        'cui': cui,
                        'source': 'ONRC',
                    }
                    count += 1

                if count >= limit:
                    break

        logger.info(f"Loaded {count} ONRC records with website")
        return count

    def match_company(self, name: str, country: str) -> Optional[Dict]:
        """Try to match a company with local data."""
        norm_name = self._normalize_name(name)
        if not norm_name:
            return None

        # Priority 1: ANOFM (has emails)
        if norm_name in self.anofm_cache:
            return {**self.anofm_cache[norm_name], 'match_type': 'exact'}

        # Priority 2: EU Funds (has emails)
        if norm_name in self.eufunds_cache:
            return {**self.eufunds_cache[norm_name], 'match_type': 'exact'}

        # Priority 3: ONRC (has websites)
        if norm_name in self.onrc_cache:
            return {**self.onrc_cache[norm_name], 'match_type': 'exact'}

        # Try partial matching (first 20 chars)
        short_name = norm_name[:20]
        for cache_name, data in self.anofm_cache.items():
            if cache_name.startswith(short_name) or short_name in cache_name:
                return {**data, 'match_type': 'partial'}

        for cache_name, data in self.eufunds_cache.items():
            if cache_name.startswith(short_name) or short_name in cache_name:
                return {**data, 'match_type': 'partial'}

        return None

    def enrich_country(self, country_code: str) -> int:
        """Enrich beneficiaries for a single country."""
        country_name = EU_COUNTRIES.get(country_code, country_code).lower().replace(' ', '_')
        input_file = OUTPUT_DIR / f"{country_code}_{country_name}_beneficiaries.csv"

        if not input_file.exists():
            logger.warning(f"No data for {country_code}")
            return 0

        enriched = 0
        with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                company_id = row.get('company_id', '')
                company_name = row.get('company_name', '')

                if not company_name:
                    continue

                self.stats['total_kohesio'] += 1

                # Check if already enriched
                cursor = self.db.execute(
                    'SELECT email FROM enrichment WHERE company_id = ?',
                    (company_id,)
                )
                existing = cursor.fetchone()
                if existing and existing[0]:
                    continue

                # Try to match
                match = self.match_company(company_name, country_code)

                if match:
                    self.db.execute('''
                        INSERT OR REPLACE INTO enrichment
                        (company_id, company_name, country, email, phone, website, source, match_type, enriched_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        company_id,
                        company_name,
                        country_code,
                        match.get('email', ''),
                        match.get('phone', ''),
                        match.get('website', ''),
                        match.get('source', ''),
                        match.get('match_type', ''),
                        datetime.now().strftime('%Y-%m-%d'),
                    ))

                    enriched += 1
                    self.stats['matched'] += 1

                    if match.get('email'):
                        self.stats['with_email'] += 1

                    source = match.get('source', 'unknown')
                    self.stats['sources'][source] = self.stats['sources'].get(source, 0) + 1

        self.db.commit()
        return enriched

    def enrich(self, countries: List[str] = None):
        """Main enrichment workflow."""
        logger.info("=" * 60)
        logger.info("Kohesio Enrichment Pipeline")
        logger.info("=" * 60)

        # Load local data sources
        logger.info("Loading local data sources...")
        self.load_anofm()
        self.load_eufunds()
        self.load_onrc()

        total_cache = len(self.anofm_cache) + len(self.eufunds_cache) + len(self.onrc_cache)
        logger.info(f"Total cached records: {total_cache}")

        # Determine countries to process
        if countries:
            process_countries = countries
        else:
            # Process countries that have local data (primarily Romania)
            process_countries = ['RO']  # Start with Romania

        # Enrich each country
        for country_code in process_countries:
            logger.info(f"Enriching {country_code}...")
            enriched = self.enrich_country(country_code)
            logger.info(f"{country_code}: {enriched} records enriched")

        logger.info("=" * 60)
        logger.info(f"COMPLETE")
        logger.info(f"Total Kohesio processed: {self.stats['total_kohesio']}")
        logger.info(f"Matched: {self.stats['matched']}")
        logger.info(f"With email: {self.stats['with_email']}")
        logger.info(f"By source: {self.stats['sources']}")
        logger.info("=" * 60)

    def show_status(self):
        """Show enrichment status."""
        print("=" * 60)
        print("KOHESIO ENRICHMENT STATUS")
        print("=" * 60)

        # Total enriched
        cursor = self.db.execute('SELECT COUNT(*) FROM enrichment')
        total = cursor.fetchone()[0]
        print(f"Total enriched: {total:,}")

        # With email
        cursor = self.db.execute("SELECT COUNT(*) FROM enrichment WHERE email != ''")
        with_email = cursor.fetchone()[0]
        print(f"With email: {with_email:,}")

        # By country
        print("\nBy country:")
        cursor = self.db.execute('''
            SELECT country, COUNT(*), SUM(CASE WHEN email != '' THEN 1 ELSE 0 END)
            FROM enrichment GROUP BY country ORDER BY COUNT(*) DESC
        ''')
        for row in cursor:
            print(f"  {row[0]}: {row[1]:,} total, {row[2]:,} with email")

        # By source
        print("\nBy source:")
        cursor = self.db.execute('''
            SELECT source, COUNT(*) FROM enrichment
            WHERE source != '' GROUP BY source ORDER BY COUNT(*) DESC
        ''')
        for row in cursor:
            print(f"  {row[0]}: {row[1]:,}")

    def export_enriched(self):
        """Export enriched data to CSV."""
        output_file = ENRICHED_DIR / f"kohesio_enriched_{datetime.now().strftime('%Y%m%d')}.csv"

        cursor = self.db.execute('''
            SELECT company_id, company_name, country, email, phone, website, source, match_type, enriched_date
            FROM enrichment WHERE email != '' OR website != ''
        ''')

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['company_id', 'company_name', 'country', 'email', 'phone', 'website', 'source', 'match_type', 'enriched_date'])
            for row in cursor:
                writer.writerow(row)

        count = self.db.execute("SELECT COUNT(*) FROM enrichment WHERE email != '' OR website != ''").fetchone()[0]
        print(f"Exported {count} enriched records to: {output_file}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Kohesio Enricher')
    parser.add_argument('--status', action='store_true', help='Show status')
    parser.add_argument('--enrich', action='store_true', help='Run enrichment')
    parser.add_argument('--country', type=str, help='Single country (e.g., RO)')
    parser.add_argument('--export', action='store_true', help='Export enriched')

    args = parser.parse_args()

    enricher = KohesioEnricher()

    if args.export:
        enricher.export_enriched()
    elif args.enrich:
        countries = [args.country.upper()] if args.country else None
        enricher.enrich(countries)
        print(json.dumps(enricher.stats, indent=2))
    else:
        enricher.show_status()


if __name__ == '__main__':
    main()
