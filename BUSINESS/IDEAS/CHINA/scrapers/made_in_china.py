#!/usr/bin/env python3
"""
Made-in-China.com Supplier Scraper

Scrapes manufacturer/supplier listings with contact details.
Categories: machinery, electronics, construction, agriculture, etc.

Usage:
    python3 made_in_china.py --category machinery --pages 5
    python3 made_in_china.py --category electronics --limit 100
    python3 made_in_china.py --search "steel pipe" --pages 3
"""

import asyncio
import aiohttp
import argparse
import csv
import re
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus

# Try to import shared code, fallback to local implementation
try:
    sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
    from skills_common import to_ascii, clean_text
except ImportError:
    def to_ascii(text):
        if not text:
            return text
        return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii')
    def clean_text(text, max_len=0):
        if not text:
            return ""
        text = ' '.join(str(text).split()).strip()
        text = to_ascii(text)
        return text[:max_len] if max_len > 0 else text

# Paths
BASE_DIR = Path('/opt/ACTIVE/IDEAS/CHINA')
OUTPUT_DIR = BASE_DIR / 'data' / 'manufacturers'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = 'https://www.made-in-china.com'

# Categories to scrape (URL path fragments)
CATEGORIES = {
    'machinery': '/products-search/hot-china-products/Machinery.html',
    'electronics': '/products-search/hot-china-products/Electronics.html',
    'construction': '/products-search/hot-china-products/Construction_Machinery.html',
    'agriculture': '/products-search/hot-china-products/Agriculture.html',
    'automotive': '/products-search/hot-china-products/Auto_Parts.html',
    'textiles': '/products-search/hot-china-products/Textile.html',
    'chemicals': '/products-search/hot-china-products/Chemical.html',
    'medical': '/products-search/hot-china-products/Medical_Equipment.html',
    'lighting': '/products-search/hot-china-products/LED_Lighting.html',
    'packaging': '/products-search/hot-china-products/Packaging_Machinery.html',
    'steel': '/products-search/hot-china-products/Steel.html',
    'plastic': '/products-search/hot-china-products/Plastic_Machinery.html',
}

# Regex patterns
EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PHONE_RE = re.compile(r'\+?86[\s\-]?\d{2,4}[\s\-]?\d{4,8}|\d{3,4}[\s\-]?\d{7,8}')

# Headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
}


async def fetch_page(session, url, retries=3):
    """Fetch a page with retries."""
    for attempt in range(retries):
        try:
            async with session.get(url, headers=HEADERS, timeout=30) as resp:
                if resp.status == 200:
                    return await resp.text()
                elif resp.status == 429:
                    wait = (attempt + 1) * 10
                    print(f'[RATE] 429 received, waiting {wait}s...')
                    await asyncio.sleep(wait)
                else:
                    print(f'[WARN] Status {resp.status} for {url}')
        except Exception as e:
            print(f'[ERR] Attempt {attempt+1} failed: {e}')
            await asyncio.sleep(5)
    return None


def parse_supplier_list(html, base_url):
    """Parse supplier listing page."""
    soup = BeautifulSoup(html, 'html.parser')
    suppliers = []

    # Find company info sections
    company_sections = soup.select('div.company-info')

    for section in company_sections:
        try:
            # Company name - look for company-name class
            name_elem = section.select_one('.company-name, .company-name-popup, a[title]')
            if not name_elem:
                continue

            name = clean_text(name_elem.get_text(), 100)
            if not name or len(name) < 3:
                continue

            # Company URL
            link = section.find('a')
            href = ''
            if link:
                href = link.get('href', '')
                if href and not href.startswith('http'):
                    href = urljoin(base_url, href)

            # Location/Address
            loc_elem = section.select_one('.company-address-info, .address, .location')
            location = clean_text(loc_elem.get_text(), 100) if loc_elem else ''

            # Skip duplicates
            if any(s['company_name'] == name for s in suppliers):
                continue

            suppliers.append({
                'company_name': name,
                'company_url': href,
                'location': location,
                'products': '',
                'info': '',
            })
        except Exception as e:
            continue

    # Also try product listings which have supplier info
    product_items = soup.select('div.product-item, li.sr-b-item, div.list-item')

    for item in product_items:
        try:
            # Find company name in product item
            name_elem = item.select_one('.company-name, .supplier-name, [class*="company"]')
            if not name_elem:
                continue

            name = clean_text(name_elem.get_text(), 100)
            if not name or len(name) < 3:
                continue

            # Skip duplicates
            if any(s['company_name'] == name for s in suppliers):
                continue

            # Company URL
            link = name_elem.find('a') or name_elem.find_parent('a')
            href = ''
            if link:
                href = link.get('href', '')
                if href and not href.startswith('http'):
                    href = urljoin(base_url, href)

            # Product description
            prod_elem = item.select_one('.product-name, .title, h3')
            products = clean_text(prod_elem.get_text(), 200) if prod_elem else ''

            suppliers.append({
                'company_name': name,
                'company_url': href,
                'location': '',
                'products': products,
                'info': '',
            })
        except Exception:
            continue

    return suppliers


async def fetch_supplier_details(session, url):
    """Fetch detailed supplier page for contact info."""
    html = await fetch_page(session, url)
    if not html:
        return {}

    soup = BeautifulSoup(html, 'html.parser')
    details = {}

    # Contact person
    contact_elem = soup.select_one('.contact-name, .contactor, [class*="contact"] .name')
    if contact_elem:
        details['contact_person'] = clean_text(contact_elem.get_text(), 50)

    # Email - look in contact section
    contact_section = soup.select_one('.contact-info, .company-contact, #contact')
    if contact_section:
        text = contact_section.get_text()
        emails = EMAIL_RE.findall(text)
        if emails:
            details['email'] = emails[0].lower()

    # Phone
    if contact_section:
        phones = PHONE_RE.findall(contact_section.get_text())
        if phones:
            phone = re.sub(r'[^\d+]', '', phones[0])
            if not phone.startswith('+'):
                phone = '+86' + phone.lstrip('0')
            details['phone'] = phone

    # Website
    web_elem = soup.select_one('a[href*="http"]:not([href*="made-in-china"])')
    if web_elem:
        details['website'] = web_elem.get('href', '')[:100]

    # Address
    addr_elem = soup.select_one('.address, .location-address, [class*="address"]')
    if addr_elem:
        details['address'] = clean_text(addr_elem.get_text(), 200)

    # Province/City extraction
    for elem in soup.select('.region, .location, .province'):
        text = clean_text(elem.get_text(), 50)
        if 'province' in text.lower() or 'city' in text.lower():
            details['province'] = text
            break

    # Year established
    for elem in soup.select('.year, .established, [class*="year"]'):
        text = elem.get_text()
        year_match = re.search(r'(19|20)\d{2}', text)
        if year_match:
            details['year_established'] = year_match.group()
            break

    # Employees
    for elem in soup.select('.employee, .staff, [class*="employee"]'):
        text = elem.get_text()
        emp_match = re.search(r'(\d+[\-\s]*\d*)\s*(?:people|employees|staff)?', text, re.I)
        if emp_match:
            details['employees'] = clean_text(emp_match.group(1), 20)
            break

    # Certifications
    cert_elems = soup.select('.certification img, .cert-icon, [class*="cert"] img')
    certs = []
    for cert in cert_elems[:5]:
        alt = cert.get('alt', '') or cert.get('title', '')
        if alt:
            certs.append(clean_text(alt, 30))
    if certs:
        details['certifications'] = ', '.join(certs)

    return details


async def scrape_category(category, pages=5, limit=None, search_term=None):
    """Scrape a category or search results."""
    all_suppliers = []

    connector = aiohttp.TCPConnector(limit=5)
    async with aiohttp.ClientSession(connector=connector) as session:

        for page in range(1, pages + 1):
            if search_term:
                url = f'{BASE_URL}/products-search/hot-china-products/{quote_plus(search_term)}.html'
                if page > 1:
                    url = f'{BASE_URL}/products-search/find-china-products/0b0nolimit/{quote_plus(search_term)}-{page}.html'
            else:
                cat_path = CATEGORIES.get(category, f'/products-search/hot-china-products/{category}.html')
                if page == 1:
                    url = f'{BASE_URL}{cat_path}'
                else:
                    # Page 2+ uses different URL pattern
                    cat_name = category.replace('_', ' ').title().replace(' ', '_')
                    url = f'{BASE_URL}/products-search/find-china-products/0b0nolimit/{cat_name}-{page}.html'

            print(f'[PAGE {page}/{pages}] {url}')
            html = await fetch_page(session, url)

            if not html:
                print(f'[SKIP] Failed to fetch page {page}')
                continue

            suppliers = parse_supplier_list(html, BASE_URL)
            print(f'[FOUND] {len(suppliers)} suppliers on page {page}')

            # Fetch details for each supplier
            for i, sup in enumerate(suppliers):
                if limit and len(all_suppliers) >= limit:
                    break

                print(f'  [{i+1}/{len(suppliers)}] {sup["company_name"][:40]}...')

                if sup['company_url']:
                    details = await fetch_supplier_details(session, sup['company_url'])
                    sup.update(details)

                sup['category'] = category
                sup['country'] = 'CN'
                sup['source'] = 'made-in-china.com'
                sup['scraped_date'] = datetime.now().strftime('%Y-%m-%d')

                all_suppliers.append(sup)

                # Rate limiting
                await asyncio.sleep(2)

            if limit and len(all_suppliers) >= limit:
                break

            # Page delay
            await asyncio.sleep(3)

    return all_suppliers


def save_csv(suppliers, filename):
    """Save suppliers to CSV."""
    if not suppliers:
        print('[WARN] No suppliers to save')
        return

    fieldnames = [
        'company_name', 'category', 'country', 'province', 'address',
        'email', 'phone', 'website', 'contact_person', 'products',
        'certifications', 'year_established', 'employees',
        'company_url', 'source', 'scraped_date'
    ]

    output_file = OUTPUT_DIR / filename
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for sup in suppliers:
            # Ensure all values are ASCII
            row = {k: to_ascii(str(v)) if v else '' for k, v in sup.items()}
            writer.writerow(row)

    print(f'[SAVED] {len(suppliers)} suppliers to {output_file}')
    return output_file


async def main():
    parser = argparse.ArgumentParser(description='Scrape Made-in-China.com suppliers')
    parser.add_argument('--category', '-c', default='machinery',
                        choices=list(CATEGORIES.keys()),
                        help='Category to scrape')
    parser.add_argument('--search', '-s', help='Search term instead of category')
    parser.add_argument('--pages', '-p', type=int, default=3,
                        help='Number of pages to scrape')
    parser.add_argument('--limit', '-l', type=int,
                        help='Maximum number of suppliers')
    parser.add_argument('--all-categories', '-a', action='store_true',
                        help='Scrape all categories')

    args = parser.parse_args()

    if args.all_categories:
        all_suppliers = []
        for cat in CATEGORIES:
            print(f'\n=== CATEGORY: {cat.upper()} ===')
            suppliers = await scrape_category(cat, pages=args.pages, limit=args.limit)
            all_suppliers.extend(suppliers)

        filename = f'all_categories_{datetime.now().strftime("%Y%m%d")}.csv'
        save_csv(all_suppliers, filename)

    elif args.search:
        print(f'\n=== SEARCH: {args.search} ===')
        suppliers = await scrape_category(
            args.search,
            pages=args.pages,
            limit=args.limit,
            search_term=args.search
        )
        filename = f'search_{args.search.replace(" ", "_")}_{datetime.now().strftime("%Y%m%d")}.csv'
        save_csv(suppliers, filename)

    else:
        print(f'\n=== CATEGORY: {args.category.upper()} ===')
        suppliers = await scrape_category(
            args.category,
            pages=args.pages,
            limit=args.limit
        )
        filename = f'{args.category}_{datetime.now().strftime("%Y%m%d")}.csv'
        save_csv(suppliers, filename)


if __name__ == '__main__':
    asyncio.run(main())
