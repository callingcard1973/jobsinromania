#!/usr/bin/env python3
"""
Romania Website Email/Phone Scraper

Extracts contact information from company websites.

Usage:
  python3 romania_website_scraper.py --input domains.csv --output contacts.csv
  python3 romania_website_scraper.py --test example.ro  # Test single domain
  python3 romania_website_scraper.py --resume  # Resume from last position
  python3 romania_website_scraper.py --stats  # Show statistics

Output:
  /opt/ACTIVE/OPENDATA/DATA/ROMANIA/WEBSITE_CONTACTS/extracted_YYYYMMDD.csv
"""

import sys
import csv
import json
import re
import time
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin, urlparse

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii

try:
    import aiohttp
    from aiohttp_socks import ProxyConnector
except ImportError:
    print("Install: pip install aiohttp aiohttp-socks")
    sys.exit(1)

# Paths
INPUT_DEFAULT = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/DOMAINS/all_ro_domains.csv'
OUTPUT_DIR = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/WEBSITE_CONTACTS'
STATE_FILE = f'{OUTPUT_DIR}/scraper_state.json'
CACHE_FILE = f'{OUTPUT_DIR}/domain_cache.json'

# Email regex
EMAIL_PATTERN = re.compile(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    re.IGNORECASE
)

# Phone patterns for Romania
PHONE_PATTERNS = [
    re.compile(r'\+40\s*\d{2,3}[\s.-]?\d{3}[\s.-]?\d{3,4}'),  # +40 21 123 4567
    re.compile(r'0040\s*\d{2,3}[\s.-]?\d{3}[\s.-]?\d{3,4}'),  # 0040 21 123 4567
    re.compile(r'0\d{2,3}[\s.-]?\d{3}[\s.-]?\d{3,4}'),        # 021 123 4567
    re.compile(r'07\d{2}[\s.-]?\d{3}[\s.-]?\d{3}'),           # 07XX XXX XXX (mobile)
]

# Contact page paths to try
CONTACT_PATHS = ['/', '/contact', '/contact.html', '/contacte', '/despre', '/despre-noi', '/about']

# Email exclusions
EMAIL_BLACKLIST = [
    'noreply', 'no-reply', 'donotreply', 'newsletter', 'mailer-daemon',
    'postmaster', 'abuse', 'spam', 'example.com', 'test.com', 'sentry.io',
    'wixpress.com', 'wordpress.com', 'mailchimp.com', 'google.com',
    '.png', '.jpg', '.gif', '.jpeg', 'facebook.com', 'instagram.com'
]

# User agents
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
]


def is_valid_email(email):
    """Check if email is valid and not blacklisted"""
    email_lower = email.lower()
    for blacklist in EMAIL_BLACKLIST:
        if blacklist in email_lower:
            return False
    return '@' in email and '.' in email.split('@')[1]


def normalize_phone(phone):
    """Normalize Romanian phone number to +40 format"""
    digits = re.sub(r'[^\d+]', '', phone)
    if digits.startswith('0040'):
        digits = '+40' + digits[4:]
    elif digits.startswith('00'):
        digits = '+' + digits[2:]
    elif digits.startswith('0') and len(digits) >= 10:
        digits = '+40' + digits[1:]
    elif not digits.startswith('+'):
        return None  # Unknown format
    return digits if len(digits) >= 10 else None


def extract_emails(html):
    """Extract valid emails from HTML"""
    if not html:
        return []
    emails = EMAIL_PATTERN.findall(html)
    valid = []
    seen = set()
    for email in emails:
        email = email.lower().strip()
        if email not in seen and is_valid_email(email):
            seen.add(email)
            valid.append(email)
    return valid[:3]  # Max 3 emails


def extract_phones(html):
    """Extract Romanian phone numbers from HTML"""
    if not html:
        return []
    phones = []
    seen = set()
    for pattern in PHONE_PATTERNS:
        for match in pattern.findall(html):
            normalized = normalize_phone(match)
            if normalized and normalized not in seen:
                seen.add(normalized)
                phones.append(normalized)
    return phones[:2]  # Max 2 phones


async def fetch_url(session, url, timeout=10):
    """Fetch URL with timeout and error handling"""
    try:
        headers = {
            'User-Agent': USER_AGENTS[hash(url) % len(USER_AGENTS)],
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'ro-RO,ro;q=0.9,en;q=0.8',
        }
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
            if response.status == 200:
                return await response.text(errors='ignore')
    except Exception:
        pass
    return None


async def scrape_domain(session, domain, domain_data):
    """Scrape a single domain for contacts"""
    result = {
        'domain': domain,
        'cui': domain_data.get('cui', ''),
        'company_name': domain_data.get('company_name', ''),
        'original_url': domain_data.get('original_url', ''),
        'source': domain_data.get('source', ''),
        'email_1': '',
        'email_2': '',
        'email_3': '',
        'phone_1': '',
        'phone_2': '',
        'success': False,
        'scraped_at': datetime.now().isoformat()
    }

    # Build base URL
    base_url = f'https://{domain}'

    # Try contact pages
    all_html = ''
    for path in CONTACT_PATHS:
        url = urljoin(base_url, path)
        html = await fetch_url(session, url)
        if html:
            all_html += html + '\n'
            # Found content, check for contacts
            emails = extract_emails(html)
            phones = extract_phones(html)
            if emails or phones:
                break  # Found contacts, stop trying paths
        await asyncio.sleep(0.1)  # Small delay between paths

    # Try www. variant if no content
    if not all_html:
        base_url = f'https://www.{domain}'
        for path in CONTACT_PATHS[:2]:  # Only try main pages
            url = urljoin(base_url, path)
            html = await fetch_url(session, url)
            if html:
                all_html += html + '\n'
                break
            await asyncio.sleep(0.1)

    # Extract contacts from all HTML
    emails = extract_emails(all_html)
    phones = extract_phones(all_html)

    # Populate result
    if emails:
        result['email_1'] = emails[0] if len(emails) > 0 else ''
        result['email_2'] = emails[1] if len(emails) > 1 else ''
        result['email_3'] = emails[2] if len(emails) > 2 else ''
    if phones:
        result['phone_1'] = phones[0] if len(phones) > 0 else ''
        result['phone_2'] = phones[1] if len(phones) > 1 else ''

    result['success'] = bool(emails or phones or all_html)

    return result


async def scrape_batch(domains_batch, use_tor=False):
    """Scrape a batch of domains concurrently"""
    connector = None
    if use_tor:
        try:
            connector = ProxyConnector.from_url('socks5://127.0.0.1:9050')
        except:
            print("  Tor not available, using direct connection")

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [scrape_domain(session, domain, data) for domain, data in domains_batch]
        return await asyncio.gather(*tasks, return_exceptions=True)


def load_state():
    """Load scraper state"""
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {'processed': 0, 'with_email': 0, 'with_phone': 0, 'failed': 0}


def save_state(state):
    """Save scraper state"""
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)


def load_cache():
    """Load domain cache"""
    try:
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}


def save_cache(cache):
    """Save domain cache"""
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)


def load_domains(input_file):
    """Load domains from CSV"""
    domains = {}
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            domain = row.get('domain', '').strip().lower()
            if domain:
                domains[domain] = row
    return domains


def append_results(results, output_file):
    """Append results to output CSV"""
    fieldnames = ['domain', 'cui', 'company_name', 'email_1', 'email_2', 'email_3',
                  'phone_1', 'phone_2', 'success', 'source', 'scraped_at']

    file_exists = Path(output_file).exists()

    with open(output_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        if not file_exists:
            writer.writeheader()
        for result in results:
            if not isinstance(result, Exception):
                writer.writerow(result)


async def test_domain(domain):
    """Test scraping a single domain"""
    print(f"Testing {domain}...")

    data = {'domain': domain, 'cui': '', 'company_name': domain, 'source': 'test'}
    async with aiohttp.ClientSession() as session:
        result = await scrape_domain(session, domain, data)

    print(f"\nResults for {domain}:")
    print(f"  Success: {result['success']}")
    print(f"  Emails: {result['email_1']}, {result['email_2']}, {result['email_3']}")
    print(f"  Phones: {result['phone_1']}, {result['phone_2']}")


async def main_scraper(input_file, output_file, concurrent=20, delay=2.0, use_tor=False, limit=None):
    """Main scraper function"""
    print(f"\n{'='*60}")
    print("ROMANIA WEBSITE EMAIL SCRAPER")
    print(f"{'='*60}")
    print(f"Input: {input_file}")
    print(f"Output: {output_file}")
    print(f"Concurrent: {concurrent}")
    print(f"Delay: {delay}s")
    print(f"Tor: {'Yes' if use_tor else 'No'}")

    # Load domains
    print("\nLoading domains...")
    domains = load_domains(input_file)
    print(f"  Loaded {len(domains):,} domains")

    # Load cache to skip already processed
    cache = load_cache()
    unprocessed = {d: data for d, data in domains.items() if d not in cache}
    print(f"  Already cached: {len(cache):,}")
    print(f"  To process: {len(unprocessed):,}")

    if limit:
        unprocessed = dict(list(unprocessed.items())[:limit])
        print(f"  Limited to: {limit}")

    # Load state
    state = load_state()

    # Process in batches
    domain_list = list(unprocessed.items())
    total = len(domain_list)
    batch_size = concurrent

    print(f"\nStarting scraper...")
    start_time = time.time()

    for i in range(0, total, batch_size):
        batch = domain_list[i:i+batch_size]
        print(f"\n  Batch {i//batch_size + 1}/{(total + batch_size - 1)//batch_size}: {len(batch)} domains")

        # Scrape batch
        results = await scrape_batch(batch, use_tor=use_tor)

        # Process results
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                state['failed'] += 1
                continue

            domain = result['domain']
            cache[domain] = {
                'success': result['success'],
                'has_email': bool(result['email_1']),
                'scraped_at': result['scraped_at']
            }

            state['processed'] += 1
            if result['email_1']:
                state['with_email'] += 1
            if result['phone_1']:
                state['with_phone'] += 1

            valid_results.append(result)

        # Save results
        if valid_results:
            append_results(valid_results, output_file)

        # Progress
        elapsed = time.time() - start_time
        rate = state['processed'] / elapsed if elapsed > 0 else 0
        email_rate = 100 * state['with_email'] / state['processed'] if state['processed'] > 0 else 0
        print(f"    Processed: {state['processed']:,} | Emails: {state['with_email']:,} ({email_rate:.1f}%) | Rate: {rate:.1f}/s")

        # Save state and cache periodically
        if i % (batch_size * 10) == 0:
            save_state(state)
            save_cache(cache)

        # Rate limiting delay
        await asyncio.sleep(delay)

    # Final save
    save_state(state)
    save_cache(cache)

    # Summary
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print("SCRAPING COMPLETE")
    print(f"{'='*60}")
    print(f"Total processed: {state['processed']:,}")
    print(f"With email: {state['with_email']:,} ({100*state['with_email']/max(state['processed'],1):.1f}%)")
    print(f"With phone: {state['with_phone']:,} ({100*state['with_phone']/max(state['processed'],1):.1f}%)")
    print(f"Failed: {state['failed']:,}")
    print(f"Time: {elapsed/60:.1f} minutes")
    print(f"Output: {output_file}")


def show_stats():
    """Show scraper statistics"""
    state = load_state()
    cache = load_cache()

    print(f"\n{'='*60}")
    print("SCRAPER STATISTICS")
    print(f"{'='*60}")
    print(f"Processed: {state.get('processed', 0):,}")
    print(f"With email: {state.get('with_email', 0):,}")
    print(f"With phone: {state.get('with_phone', 0):,}")
    print(f"Failed: {state.get('failed', 0):,}")
    print(f"Cached domains: {len(cache):,}")

    # Check output files
    for f in Path(OUTPUT_DIR).glob('extracted_*.csv'):
        lines = sum(1 for _ in open(f)) - 1
        print(f"\n{f.name}: {lines:,} records")


def main():
    parser = argparse.ArgumentParser(description='Scrape Romanian websites for contacts')
    parser.add_argument('--input', '-i', default=INPUT_DEFAULT, help='Input CSV with domains')
    parser.add_argument('--output', '-o', help='Output CSV path')
    parser.add_argument('--concurrent', '-c', type=int, default=20, help='Concurrent requests')
    parser.add_argument('--delay', '-d', type=float, default=2.0, help='Delay between batches')
    parser.add_argument('--tor', action='store_true', help='Use Tor proxy')
    parser.add_argument('--limit', '-l', type=int, help='Limit domains to process')
    parser.add_argument('--test', metavar='DOMAIN', help='Test single domain')
    parser.add_argument('--resume', action='store_true', help='Resume from last position')
    parser.add_argument('--stats', action='store_true', help='Show statistics')

    args = parser.parse_args()

    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    if args.stats:
        show_stats()
        return

    if args.test:
        asyncio.run(test_domain(args.test))
        return

    # Output file
    if args.output:
        output_file = args.output
    else:
        date_str = datetime.now().strftime('%Y%m%d')
        output_file = f'{OUTPUT_DIR}/extracted_{date_str}.csv'

    # Run scraper
    asyncio.run(main_scraper(
        input_file=args.input,
        output_file=output_file,
        concurrent=args.concurrent,
        delay=args.delay,
        use_tor=args.tor,
        limit=args.limit
    ))


if __name__ == '__main__':
    main()
