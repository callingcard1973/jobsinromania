#!/usr/bin/env python3
"""
Listafirme.ro Scraper - Extract company website URLs

Scrapes listafirme.ro to get website URLs for Romanian companies,
which can then be used to extract email addresses from contact pages.

Usage:
  python3 listafirme_scraper.py --county Bucuresti --limit 1000
  python3 listafirme_scraper.py --all-counties --resume
  python3 listafirme_scraper.py --status
  python3 listafirme_scraper.py --export

Output:
  /opt/ACTIVE/OPENDATA/DATA/ROMANIA/LISTAFIRME/urls_by_county/
  /opt/ACTIVE/OPENDATA/DATA/ROMANIA/LISTAFIRME/all_urls.csv
"""

import sys
import csv
import json
import time
import random
import argparse
import re
from pathlib import Path
from datetime import datetime
from urllib.parse import quote

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii

# Try to import HTTP clients
try:
    import httpx
    HTTP_CLIENT = 'httpx'
except ImportError:
    import requests
    HTTP_CLIENT = 'requests'

# Paths
OUTPUT_DIR = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/LISTAFIRME'
STATE_FILE = f'{OUTPUT_DIR}/scraper_state.json'
URLS_OUTPUT = f'{OUTPUT_DIR}/all_urls.csv'

# Romanian counties
COUNTIES = [
    'Alba', 'Arad', 'Arges', 'Bacau', 'Bihor', 'Bistrita-Nasaud', 'Botosani',
    'Braila', 'Brasov', 'Bucuresti', 'Buzau', 'Calarasi', 'Caras-Severin',
    'Cluj', 'Constanta', 'Covasna', 'Dambovita', 'Dolj', 'Galati', 'Giurgiu',
    'Gorj', 'Harghita', 'Hunedoara', 'Ialomita', 'Iasi', 'Ilfov', 'Maramures',
    'Mehedinti', 'Mures', 'Neamt', 'Olt', 'Prahova', 'Salaj', 'Satu-Mare',
    'Sibiu', 'Suceava', 'Teleorman', 'Timis', 'Tulcea', 'Valcea', 'Vaslui', 'Vrancea'
]

# User agents
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]


def get_headers():
    """Get random headers"""
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ro-RO,ro;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }


def fetch_page(url, retries=3):
    """Fetch a page with retries"""
    for attempt in range(retries):
        try:
            if HTTP_CLIENT == 'httpx':
                with httpx.Client(timeout=30, follow_redirects=True) as client:
                    response = client.get(url, headers=get_headers())
            else:
                response = requests.get(url, headers=get_headers(), timeout=30)

            if response.status_code == 200:
                return response.text
            elif response.status_code == 429:
                print(f"    Rate limited, waiting 60s...")
                time.sleep(60)
            else:
                print(f"    HTTP {response.status_code}")

        except Exception as e:
            print(f"    Error: {e}")
            time.sleep(5)

    return None


def extract_companies_from_page(html):
    """Extract company data from listafirme search results page"""
    companies = []

    # Pattern for company links: /firma/COMPANY-NAME-CUI
    # Example: /firma/sc-example-srl-12345678
    pattern = r'href="/firma/([^"]+)-(\d{6,10})"[^>]*>([^<]+)</a>'

    for match in re.finditer(pattern, html, re.IGNORECASE):
        slug, cui, name = match.groups()

        # Extract website if present nearby
        # Look for website pattern near this company
        website = ''
        website_pattern = rf'{cui}[^<]*<[^>]*href="(https?://[^"]+)"[^>]*target="_blank"'
        website_match = re.search(website_pattern, html)
        if website_match:
            website = website_match.group(1)

        companies.append({
            'cui': cui,
            'company_name': to_ascii(name.strip()),
            'slug': slug,
            'website': website,
            'source_url': f'https://www.listafirme.ro/firma/{slug}-{cui}'
        })

    return companies


def extract_company_details(html, cui):
    """Extract detailed info from company page"""
    data = {'cui': cui}

    # Website
    website_match = re.search(r'href="(https?://(?!www\.listafirme)[^"]+)"[^>]*target="_blank"', html)
    if website_match:
        data['website'] = website_match.group(1)

    # Phone
    phone_match = re.search(r'tel:(\+?[\d\s-]+)', html)
    if phone_match:
        data['phone'] = phone_match.group(1).strip()

    # Email (sometimes visible)
    email_match = re.search(r'mailto:([^"]+@[^"]+)', html)
    if email_match:
        data['email'] = email_match.group(1)

    # Address
    address_match = re.search(r'itemprop="address"[^>]*>([^<]+)', html)
    if address_match:
        data['address'] = to_ascii(address_match.group(1).strip())

    return data


def scrape_county(county, limit=None, delay=2):
    """Scrape all companies from a county"""
    print(f"\nScraping {county}...")

    results = []
    page = 1
    base_url = f'https://www.listafirme.ro/judet/{county.lower().replace("-", "-").replace(" ", "-")}/'

    while True:
        url = f'{base_url}?pag={page}' if page > 1 else base_url
        print(f"  Page {page}: {url}")

        html = fetch_page(url)
        if not html:
            print(f"    Failed to fetch page {page}")
            break

        companies = extract_companies_from_page(html)
        if not companies:
            print(f"    No more companies found")
            break

        results.extend(companies)
        print(f"    Found {len(companies)} companies (total: {len(results)})")

        if limit and len(results) >= limit:
            results = results[:limit]
            break

        page += 1
        time.sleep(delay + random.uniform(0, 1))

        # Safety limit
        if page > 500:
            print("    Reached page limit")
            break

    return results


def scrape_company_details(companies, delay=1):
    """Scrape detailed info for each company"""
    print(f"\nScraping details for {len(companies)} companies...")

    for i, company in enumerate(companies):
        if company.get('website'):
            continue  # Already has website

        url = company.get('source_url')
        if not url:
            continue

        print(f"  [{i+1}/{len(companies)}] {company['cui']}")

        html = fetch_page(url)
        if html:
            details = extract_company_details(html, company['cui'])
            company.update(details)

        time.sleep(delay + random.uniform(0, 0.5))

    return companies


def load_state():
    """Load scraper state"""
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {'completed_counties': [], 'total_urls': 0, 'last_run': None}


def save_state(state):
    """Save scraper state"""
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def save_county_results(county, companies):
    """Save results for a county"""
    county_dir = f'{OUTPUT_DIR}/urls_by_county'
    Path(county_dir).mkdir(parents=True, exist_ok=True)

    output_file = f'{county_dir}/{county.lower().replace(" ", "_")}.csv'

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['cui', 'company_name', 'website', 'phone', 'email', 'address', 'source_url']
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(companies)

    print(f"  Saved {len(companies)} to {output_file}")
    return len(companies)


def merge_all_counties():
    """Merge all county files into one"""
    print("\nMerging all county files...")

    county_dir = f'{OUTPUT_DIR}/urls_by_county'
    all_companies = []

    for csv_file in Path(county_dir).glob('*.csv'):
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                row['county'] = csv_file.stem.replace('_', ' ').title()
                all_companies.append(row)

    # Deduplicate by CUI
    seen = set()
    unique = []
    for c in all_companies:
        if c['cui'] not in seen:
            seen.add(c['cui'])
            unique.append(c)

    # Save merged file
    with open(URLS_OUTPUT, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['cui', 'company_name', 'website', 'phone', 'email', 'address', 'county', 'source_url']
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(unique)

    print(f"Merged {len(unique)} unique companies to {URLS_OUTPUT}")

    # Stats
    with_website = len([c for c in unique if c.get('website')])
    with_email = len([c for c in unique if c.get('email')])
    print(f"  With website: {with_website:,}")
    print(f"  With email: {with_email:,}")

    return unique


def show_status():
    """Show scraper status"""
    state = load_state()

    print("\n" + "="*60)
    print("LISTAFIRME SCRAPER STATUS")
    print("="*60)

    print(f"\nCompleted counties: {len(state.get('completed_counties', []))}/{len(COUNTIES)}")
    print(f"Total URLs scraped: {state.get('total_urls', 0):,}")
    print(f"Last run: {state.get('last_run', 'Never')}")

    if state.get('completed_counties'):
        print(f"\nCompleted: {', '.join(state['completed_counties'][:10])}...")

    remaining = [c for c in COUNTIES if c not in state.get('completed_counties', [])]
    if remaining:
        print(f"\nRemaining: {', '.join(remaining[:10])}...")

    # Check existing files
    county_dir = f'{OUTPUT_DIR}/urls_by_county'
    if Path(county_dir).exists():
        files = list(Path(county_dir).glob('*.csv'))
        total_lines = sum(sum(1 for _ in open(f)) - 1 for f in files)
        print(f"\nExisting files: {len(files)}")
        print(f"Total records: {total_lines:,}")


def main():
    parser = argparse.ArgumentParser(description='Scrape listafirme.ro for company URLs')
    parser.add_argument('--county', help='Scrape specific county')
    parser.add_argument('--all-counties', action='store_true', help='Scrape all counties')
    parser.add_argument('--resume', action='store_true', help='Resume from last state')
    parser.add_argument('--limit', type=int, help='Limit companies per county')
    parser.add_argument('--delay', type=float, default=2, help='Delay between requests')
    parser.add_argument('--details', action='store_true', help='Scrape company detail pages')
    parser.add_argument('--status', action='store_true', help='Show status')
    parser.add_argument('--export', action='store_true', help='Merge and export all')

    args = parser.parse_args()

    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    if args.status:
        show_status()
        return

    if args.export:
        merge_all_counties()
        return

    state = load_state()

    if args.county:
        counties_to_scrape = [args.county]
    elif args.all_counties:
        if args.resume:
            counties_to_scrape = [c for c in COUNTIES if c not in state.get('completed_counties', [])]
        else:
            counties_to_scrape = COUNTIES
    else:
        print("Specify --county NAME or --all-counties")
        return

    print(f"Will scrape {len(counties_to_scrape)} counties")
    print(f"Delay: {args.delay}s, Limit: {args.limit or 'None'}")

    for county in counties_to_scrape:
        try:
            companies = scrape_county(county, limit=args.limit, delay=args.delay)

            if args.details and companies:
                companies = scrape_company_details(companies)

            if companies:
                count = save_county_results(county, companies)
                state['completed_counties'].append(county)
                state['total_urls'] = state.get('total_urls', 0) + count
                state['last_run'] = datetime.now().isoformat()
                save_state(state)

        except KeyboardInterrupt:
            print("\nInterrupted! Saving state...")
            save_state(state)
            break
        except Exception as e:
            print(f"Error scraping {county}: {e}")
            continue

    # Merge at the end
    if len(counties_to_scrape) > 1 or args.export:
        merge_all_counties()


if __name__ == '__main__':
    main()
