#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
Poland Company Enricher - Extract emails from Polish company websites

Polish companies typically have "Kontakt" pages with contact information.
This script finds company websites and extracts emails/phones.

Usage:
    python3 poland_enricher.py                      # Enrich EURES Poland data
    python3 poland_enricher.py --limit 100          # Limit to 100 companies
    python3 poland_enricher.py --input file.csv     # Custom input file
    python3 poland_enricher.py --test               # Test with 5 companies

Sources checked:
1. Company website (if available) - /kontakt, /contact pages
2. Google search for company email
3. Panoramafirm.pl lookup
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
from urllib.parse import urlparse, urljoin

from skills_common import to_ascii, get_http_client

# Paths
BASE_DIR = Path('/opt/ACTIVE/INFRA/SKILLS')
OUTPUT_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/POLAND_ENRICHED')
LOGS_DIR = Path('/opt/ACTIVE/INFRA/LOGS/enricher')
CACHE_FILE = OUTPUT_DIR / 'poland_cache.json'

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / f'poland_enricher_{datetime.now():%Y%m%d}.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# Polish email patterns
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PHONE_PATTERN = re.compile(r'(?:\+48|0048)?[\s\-]?(?:\d{2,3}[\s\-]?\d{3}[\s\-]?\d{2,3}[\s\-]?\d{2}|\d{3}[\s\-]?\d{3}[\s\-]?\d{3})')

# Contact page patterns for Polish sites
CONTACT_PATHS = ['/kontakt', '/contact', '/kontakt.html', '/kontakty', '/o-nas/kontakt', '/kontakt-z-nami']

# Headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'pl-PL,pl;q=0.9,en;q=0.8',
}


def load_cache() -> dict:
    """Load domain cache."""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE) as f:
                return json.load(f)
        except:
            pass
    return {}


def save_cache(cache: dict):
    """Save domain cache."""
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)


def extract_emails(text: str) -> List[str]:
    """Extract emails from text, filter junk."""
    if not text:
        return []
    emails = EMAIL_PATTERN.findall(text.lower())
    # Filter out image/css/js files and common junk
    junk = ['png', 'jpg', 'gif', 'css', 'js', 'wixpress', 'sentry', 'cloudflare', 'example']
    return [e for e in set(emails) if not any(j in e for j in junk)]


def extract_phones(text: str) -> List[str]:
    """Extract Polish phone numbers."""
    if not text:
        return []
    phones = PHONE_PATTERN.findall(text)
    # Normalize
    normalized = []
    for p in phones:
        clean = re.sub(r'[\s\-]', '', p)
        if len(clean) >= 9:
            if not clean.startswith('+'):
                clean = '+48' + clean.lstrip('0')
            normalized.append(clean)
    return list(set(normalized))[:3]


def fetch_page(url: str, timeout: int = 10) -> Optional[str]:
    """Fetch webpage content."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200:
            return resp.text
    except Exception as e:
        log.debug(f"Fetch error {url}: {e}")
    return None


def guess_domain_from_name(company_name: str) -> List[str]:
    """Guess company domain from name."""
    # Clean name
    name = to_ascii(company_name).lower()
    name = re.sub(r'["\'\(\)]', '', name)
    name = re.sub(r'\s+(sp\.?\s*z\s*o\.?o\.?|s\.?a\.?|s\.?c\.?|spolka.*|spzoo|zoo).*$', '', name, flags=re.I)
    name = re.sub(r'\s+', '', name)[:30]

    domains = []
    if len(name) >= 3:
        domains.append(f"https://{name}.pl")
        domains.append(f"https://www.{name}.pl")
        domains.append(f"https://{name}.com.pl")
    return domains


def find_website_from_duckduckgo(company_name: str) -> Optional[str]:
    """Search DuckDuckGo for company website."""
    try:
        query = f"{company_name} kontakt site:.pl"
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        resp = requests.get(url, headers=HEADERS, timeout=10)

        # Extract URLs from results
        urls = re.findall(r'href="(https?://[^"]+\.pl[^"]*)"', resp.text)
        for u in urls:
            parsed = urlparse(u)
            if parsed.netloc and 'duckduckgo' not in parsed.netloc:
                return f"{parsed.scheme}://{parsed.netloc}"
    except Exception as e:
        log.debug(f"DuckDuckGo search error: {e}")
    return None


def search_krs_ceidg(company_name: str) -> Optional[str]:
    """Search Polish business registry for company info."""
    try:
        # Try biznes.gov.pl search
        clean_name = to_ascii(company_name).replace('"', '')[:50]
        url = f"https://wyszukiwarka-krs.ms.gov.pl/api/wyszukiwarka/krs?nazwa={requests.utils.quote(clean_name)}"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('odpis'):
                # Has results - but KRS doesn't provide emails directly
                pass
    except Exception as e:
        log.debug(f"KRS search error: {e}")
    return None


def enrich_from_website(website: str, cache: dict) -> Tuple[List[str], List[str]]:
    """Extract emails and phones from company website."""
    if not website:
        return [], []

    # Normalize URL
    if not website.startswith('http'):
        website = 'https://' + website

    domain = urlparse(website).netloc

    # Check cache
    if domain in cache:
        cached = cache[domain]
        return cached.get('emails', []), cached.get('phones', [])

    emails, phones = [], []

    # Try homepage first
    content = fetch_page(website)
    if content:
        emails.extend(extract_emails(content))
        phones.extend(extract_phones(content))

    # Try contact pages
    for path in CONTACT_PATHS:
        contact_url = urljoin(website, path)
        content = fetch_page(contact_url)
        if content:
            emails.extend(extract_emails(content))
            phones.extend(extract_phones(content))
            if emails:
                break

    # Deduplicate
    emails = list(set(emails))[:3]
    phones = list(set(phones))[:3]

    # Cache result
    cache[domain] = {'emails': emails, 'phones': phones}

    return emails, phones


def search_panoramafirm(company_name: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Search panoramafirm.pl for company info."""
    try:
        # Simplified search - get company page
        search_name = to_ascii(company_name).lower().replace(' ', '-')[:50]
        url = f"https://panoramafirm.pl/szukaj?k={requests.utils.quote(company_name)}"

        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            # Extract first result link
            match = re.search(r'href="(https://panoramafirm\.pl/[^"]+)"[^>]*class="[^"]*company', resp.text)
            if match:
                company_url = match.group(1)
                company_page = fetch_page(company_url)
                if company_page:
                    emails = extract_emails(company_page)
                    phones = extract_phones(company_page)
                    # Find website
                    website_match = re.search(r'href="(https?://[^"]+)"[^>]*rel="nofollow"', company_page)
                    website = website_match.group(1) if website_match else None
                    return emails[0] if emails else None, phones[0] if phones else None, website
    except Exception as e:
        log.debug(f"Panoramafirm error: {e}")
    return None, None, None


def enrich_company(row: dict, cache: dict) -> dict:
    """Enrich a single company with contact info."""
    company_name = row.get('company_name', '') or row.get('employer', '') or row.get('name', '') or row.get('Name', '')
    existing_email = row.get('email_1', '') or row.get('email', '') or row.get('Email', '')
    existing_phone = row.get('phone_1', '') or row.get('phone', '') or row.get('Phone', '')
    existing_website = row.get('company_website', '') or row.get('website', '') or row.get('Website', '')

    if not company_name:
        return row

    # Skip if already has email
    if existing_email and '@' in existing_email:
        row['enrichment_status'] = 'already_has_email'
        return row

    enriched_email = None
    enriched_phone = None
    enriched_website = existing_website
    source = None

    # 1. Try existing website
    if existing_website:
        emails, phones = enrich_from_website(existing_website, cache)
        if emails:
            enriched_email = emails[0]
            enriched_phone = phones[0] if phones else existing_phone
            source = 'website_kontakt'

    # 2. Try guessing domain from company name
    if not enriched_email:
        guessed_domains = guess_domain_from_name(company_name)
        for domain in guessed_domains:
            emails, phones = enrich_from_website(domain, cache)
            if emails:
                enriched_email = emails[0]
                enriched_phone = phones[0] if phones else existing_phone
                enriched_website = domain
                source = 'guessed_domain'
                break

    # 3. Try DuckDuckGo search for website
    if not enriched_email:
        found_website = find_website_from_duckduckgo(company_name)
        if found_website:
            enriched_website = found_website
            emails, phones = enrich_from_website(found_website, cache)
            if emails:
                enriched_email = emails[0]
                enriched_phone = phones[0] if phones else existing_phone
                source = 'duckduckgo_website'

    # 3. Try Panoramafirm
    if not enriched_email:
        pf_email, pf_phone, pf_website = search_panoramafirm(company_name)
        if pf_email:
            enriched_email = pf_email
            enriched_phone = pf_phone or existing_phone
            enriched_website = pf_website or enriched_website
            source = 'panoramafirm'

    # Update row
    if enriched_email:
        row['email_1'] = enriched_email
        row['enrichment_source'] = source
        row['enrichment_status'] = 'enriched'
        log.info(f"  + {company_name[:40]}: {enriched_email}")
    else:
        row['enrichment_status'] = 'not_found'

    if enriched_phone and not existing_phone:
        row['phone_1'] = enriched_phone

    if enriched_website and not existing_website:
        row['company_website'] = enriched_website

    return row


def load_input_data(input_file: str) -> List[dict]:
    """Load companies from CSV."""
    rows = []
    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def save_enriched(rows: List[dict], output_file: Path):
    """Save enriched data to CSV."""
    if not rows:
        return

    fieldnames = list(rows[0].keys())
    # Ensure enrichment columns exist
    for col in ['enrichment_source', 'enrichment_status']:
        if col not in fieldnames:
            fieldnames.append(col)

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

    log.info(f"Saved {len(rows)} rows to {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Poland Company Enricher')
    parser.add_argument('--input', type=str, help='Input CSV file')
    parser.add_argument('--limit', type=int, default=0, help='Limit companies to process')
    parser.add_argument('--test', action='store_true', help='Test with 5 companies')
    parser.add_argument('--workers', type=int, default=3, help='Parallel workers')
    args = parser.parse_args()

    # Default input: EURES Poland data
    if args.input:
        input_file = args.input
    else:
        # Try EURES Poland
        eures_poland = Path('/mnt/hdd/SCRAPER_DATA/csv/EURES/Poland/Poland_contacts_50.csv')
        kraz_file = Path('/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/POLAND/OUTPUT/kraz_agencies_20260109.csv')

        if eures_poland.exists():
            input_file = str(eures_poland)
        elif kraz_file.exists():
            input_file = str(kraz_file)
        else:
            log.error("No input file found. Use --input to specify.")
            return

    log.info(f"Loading data from: {input_file}")
    rows = load_input_data(input_file)
    log.info(f"Loaded {len(rows)} companies")

    # Apply limits
    if args.test:
        rows = rows[:5]
    elif args.limit:
        rows = rows[:args.limit]

    # Filter: only companies without email
    to_enrich = [r for r in rows if not (r.get('email_1') or r.get('email') or r.get('Email'))]
    # Also include rows that already have email but keep them for tracking
    already_has = len(rows) - len(to_enrich)
    log.info(f"Companies needing enrichment: {len(to_enrich)}")

    if not to_enrich:
        log.info("All companies already have emails!")
        return

    # Load cache
    cache = load_cache()

    # Enrich
    enriched = []
    success_count = 0

    for i, row in enumerate(to_enrich):
        try:
            result = enrich_company(row, cache)
            enriched.append(result)

            if result.get('enrichment_status') == 'enriched':
                success_count += 1

            # Rate limit
            time.sleep(1)

            # Progress
            if (i + 1) % 10 == 0:
                log.info(f"Progress: {i+1}/{len(to_enrich)} ({success_count} enriched)")
                save_cache(cache)

        except KeyboardInterrupt:
            log.info("Interrupted by user")
            break
        except Exception as e:
            log.error(f"Error enriching {row.get('company_name', 'unknown')}: {e}")
            enriched.append(row)

    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    output_file = OUTPUT_DIR / f'poland_enriched_{timestamp}.csv'
    save_enriched(enriched, output_file)
    save_cache(cache)

    # Stats
    log.info("=" * 50)
    log.info(f"ENRICHMENT COMPLETE")
    log.info(f"  Total processed: {len(enriched)}")
    log.info(f"  Successfully enriched: {success_count}")
    log.info(f"  Success rate: {success_count/len(enriched)*100:.1f}%" if enriched else "N/A")
    log.info(f"  Output: {output_file}")
    log.info("=" * 50)


if __name__ == '__main__':
    main()
