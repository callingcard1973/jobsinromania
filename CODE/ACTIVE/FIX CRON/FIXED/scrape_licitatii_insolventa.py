"""
Scraper for licitatii-insolventa.ro — UNPIR auction listings
Extracts ~2,047 listings with publisher contact info (email, phone, name)

Usage:
    python scrape_licitatii_insolventa.py          # full scrape
    python scrape_licitatii_insolventa.py --test    # test with 1 page per category
"""

import requests
from bs4 import BeautifulSoup
import csv
import re
import time
import sys
import os
import subprocess
from datetime import datetime
from urllib.parse import urljoin, unquote, quote

# Ensure paths are configurable
BASE_DIR = '/opt/ACTIVE/FALIMENT'
OUTPUT_DIR = os.path.join(BASE_DIR, 'OUTPUT')

# Ensure ASCII-only output
def to_ascii(text):
    import unicodedata
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')

BASE_URL = "https://www.licitatii-insolventa.ro"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept-Language": "ro-RO,ro;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

CATEGORIES = [
    "afaceri",
    "auto",
    "imobiliare",
    "industrial",
    "office",
    "altele",
]

# Rate limiting
REQUEST_DELAY = 1.5  # seconds between requests
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

def decode_cloudflare_email(encoded_str):
    """Decode CloudFlare email protection encoding.
    The first 2 hex chars are the XOR key, rest is XOR'd email bytes."""
    try:
        if '#' in encoded_str:
            encoded_str = encoded_str.split('#')[1]
        encoded_str = encoded_str.strip()
        key = int(encoded_str[:2], 16)
        decoded = ""
        for i in range(2, len(encoded_str), 2):
            decoded += chr(int(encoded_str[i:i+2], 16) ^ key)
        return decoded
    except Exception:
        return None

def extract_emails_from_text(text):
    """Extract email addresses from text using regex."""
    pattern = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
    return list(set(re.findall(pattern, text)))

def extract_phones_from_text(text):
    """Extract Romanian phone numbers from text. Strict patterns to avoid false positives."""
    patterns = [
        r'0[237]\d{8}',           # 07xx, 02xx, 03xx (10 digits)
        r'\+40\s?[237]\d{8}',     # +40 7xx (international)
        r'0[237]\d[\s.\-]\d{3}[\s.\-]\d{3}',  # 07xx.xxx.xxx
    ]
    phones = []
    for p in patterns:
        phones.extend(re.findall(p, text))
    # Clean up
    cleaned = []
    for phone in phones:
        ph = re.sub(r'[\s.\-]', '', phone)
        if len(ph) == 10 and ph.startswith('0'):
            cleaned.append(ph)
        elif len(ph) == 12 and ph.startswith('+40'):
            cleaned.append(ph)
        elif len(ph) == 11 and ph.startswith('40'):
            cleaned.append('0' + ph[2:])  # normalize 40xxx to 0xxx
    # Remove masked numbers
    cleaned = [p for p in cleaned if 'XXX' not in p]
    return list(set(cleaned))

def fetch_with_curl(url):
    """Fetch URL using curl (handles percent-encoded URLs correctly)."""
    try:
        result = subprocess.run(
            ['curl', '-sL', '-m', '30',
             '-H', f'User-Agent: {HEADERS["User-Agent"]}',
             '-H', 'Accept-Language: ro-RO,ro;q=0.9,en;q=0.8',
             url],
            capture_output=True, text=True, timeout=35, encoding='utf-8', errors='replace'
        )
        if result.returncode == 0 and len(result.stdout) > 500:
            return result.stdout
    except Exception:
        pass
    return None

def get_page(url, retries=2):
    """Fetch page. Uses requests first, falls back to curl for redirect loops."""
    # Try requests first (faster, handles cookies/sessions)
    for attempt in range(retries):
        try:
            time.sleep(REQUEST_DELAY)
            r = SESSION.get(url, timeout=30, allow_redirects=True)
            r.raise_for_status()
            return BeautifulSoup(r.text, 'html.parser'), r.text
        except requests.exceptions.TooManyRedirects:
            break  # fall through to curl
        except Exception as e:
            if attempt == retries - 1:
                print(f"  ERR: {e}")

    # Fallback: curl handles percent-encoded diacritics correctly
    time.sleep(REQUEST_DELAY)
    html = fetch_with_curl(url)
    if html:
        return BeautifulSoup(html, 'html.parser'), html

    print(f"  SKIP (failed)")
    return None, None

def get_listing_urls_from_page(soup):
    """Extract listing detail URLs from a category page."""
    urls = []
    # Listings are in anchor tags with href containing _i followed by digits
    for a in soup.find_all('a', href=True):
        href = a['href']
        if re.search(r'_i\d+$', href):
            full_url = urljoin(BASE_URL, href)
            if full_url not in urls:
                urls.append(full_url)
    return urls

def get_total_pages(soup):
    """Extract total page count from pagination."""
    # Look for "X - Y de Z anunturi" text
    text = soup.get_text()
    m = re.search(r'(\d+)\s*-\s*(\d+)\s+de\s+(\d+)\s+anunturi', text)
    if m:
        total = int(m.group(3))
        per_page = int(m.group(2)) - int(m.group(1)) + 1
        pages = (total + per_page - 1) // per_page
        return pages, total
    return 1, 0

def scrape_detail_page(url):
    """Scrape a single listing detail page for contact info."""
    soup, raw_html = get_page(url)
    if not soup:
        return None

    data = {
        'url': url,
        'listing_id': '',
        'title': '',
        'price': '',
        'currency': '',
        'category': '',
        'subcategory': '',
        'location': '',
        'county': '',
        'publisher_name': '',
        'publisher_profile': '',
        'phone': '',
        'email': '',
        'description_excerpt': '',
        'auction_date': '',
        'publish_date': '',
    }

    # Extract listing ID from URL
    m = re.search(r'_i(\d+)$', url)
    if m:
        data['listing_id'] = m.group(1)

    # Title
    h1 = soup.find('h1')
    if h1:
        data['title'] = h1.get_text(strip=True)

    # Extract category/subcategory from breadcrumbs or URL
    parts = url.replace(BASE_URL, '').strip('/').split('/')
    if len(parts) >= 1:
        data['category'] = unquote(parts[0])
    if len(parts) >= 2:
        data['subcategory'] = unquote(parts[1])

    # CloudFlare email decoding - look for data-cfemail or __cf_email__
    cf_emails = []
    for tag in soup.find_all(attrs={"data-cfemail": True}):
        decoded = decode_cloudflare_email(tag['data-cfemail'])
        if decoded and '@' in decoded:
            cf_emails.append(decoded)

    # Also check href with /cdn-cgi/l/email-protection
    for a in soup.find_all('a', href=True):
        if 'email-protection' in a['href']:
            encoded = a['href']
            decoded = decode_cloudflare_email(encoded)
            if decoded and '@' in decoded:
                cf_emails.append(decoded)

    # Phone numbers - check for unmasked phones in raw HTML
    # Sometimes the full phone is in data attributes, onclick, or href="tel:"
    phones_found = []

    # tel: links
    for a in soup.find_all('a', href=True):
        if a['href'].startswith('tel:'):
            ph = a['href'].replace('tel:', '').strip()
            ph = re.sub(r'[\s.\-]', '', ph)
            if ph and 'XXX' not in ph:
                phones_found.append(ph)

    # data-phone, data-tel, or similar attributes
    for tag in soup.find_all(True):
        for attr in ['data-phone', 'data-tel', 'data-number', 'data-original']:
            val = tag.get(attr, '')
            if val:
                phs = extract_phones_from_text(val)
                phones_found.extend(phs)

    # rel attribute (mentioned in earlier analysis)
    for a in soup.find_all('a', rel=True):
        rel_val = ' '.join(a['rel']) if isinstance(a['rel'], list) else a['rel']
        phs = extract_phones_from_text(rel_val)
        phones_found.extend(phs)

    # Full page text for phones and emails
    page_text = soup.get_text(' ', strip=True)
    phones_from_text = extract_phones_from_text(page_text)
    phones_found.extend(phones_from_text)

    # Also search raw HTML for phone patterns (catches hidden/JS values)
    if raw_html:
        phones_from_raw = extract_phones_from_text(raw_html)
        phones_found.extend(phones_from_raw)

    # Emails from text (backup if CF decode fails)
    emails_from_text = extract_emails_from_text(page_text)
    if raw_html:
        emails_from_text.extend(extract_emails_from_text(raw_html))

    # Fix reversed CF emails and deduplicate

    # Combine emails: CF decoded first, then text-extracted
    all_emails = list(set(cf_emails + emails_from_text))

    # Filter out site-generic, reversed, and garbage emails
    SKIP_EMAILS = {
        'presa@unpir.ro', 'contact@licitatii-insolventa.ro',
        'support@licitatii-insolventa.ro', 'comunicare@unpir.ro',
    }
    # Reversed CF-decoded local parts to detect (yahoo→oohay, gmail→liamg, etc.)
    REVERSED_LOCALS = {'oohay', 'liamg', 'moc', 'or', 'ue'}
    cleaned_emails = []
    for e in all_emails:
        e_lower = e.lower()
        if e_lower in SKIP_EMAILS:
            continue
        local = e_lower.split('@')[0] if '@' in e_lower else ''
        domain = e_lower.split('@')[-1] if '@' in e_lower else ''
        tld = domain.split('.')[-1] if '.' in domain else ''
        # Skip reversed CF emails (local part starts with reversed provider)
        if any(domain.startswith(rl + '.') or local == rl for rl in REVERSED_LOCALS):
            continue
        # Skip emails where local part looks like reversed domain (e.g. eciffo, tsevnitnoc)
        if local.endswith(('eciffo', 'iraznav', 'tairatercespidofni')):
            continue
        # Skip if TLD not valid
        if tld not in ('ro', 'com', 'eu', 'net', 'org', 'info', 'io', 'biz', 'online'):
            continue
        cleaned_emails.append(e)

    if cleaned_emails:
        data['email'] = '; '.join(cleaned_emails)

    # Deduplicate phones
    phones_found = list(set(phones_found))
    if phones_found:
        data['phone'] = '; '.join(phones_found[:3])

    # Publisher name - look for profile links
    for a in soup.find_all('a', href=True):
        if '/user/profil/' in a['href']:
            data['publisher_name'] = a.get_text(strip=True)
            data['publisher_profile'] = urljoin(BASE_URL, a['href'])
            break

    # Price
    price_text = page_text
    m = re.search(r'([\d.,]+)\s*(LEI|EUR|RON)', price_text)
    if m:
        data['price'] = m.group(1)
        data['currency'] = m.group(2)

    # Location - look for county/city patterns
    loc_match = re.search(r'jud(?:ețul|etul|\.)\s*([A-ZĂÂÎȘȚa-zăâîșț\s\-]+)', page_text)
    if loc_match:
        data['county'] = loc_match.group(1).strip()

    # Extract location from common patterns
    loc_patterns = [
        r'(?:Localitate|Oraș|Oras|Loc\.):\s*([^\n,]+)',
        r'(?:mun\.|municipiul|orașul|orasul|loc\.)\s+([A-ZĂÂÎȘȚa-zăâîșț\s\-]+)',
    ]
    for lp in loc_patterns:
        lm = re.search(lp, page_text, re.IGNORECASE)
        if lm:
            data['location'] = lm.group(1).strip()
            break

    # Description excerpt (first 300 chars)
    desc_div = soup.find('div', class_=re.compile(r'description|content|details', re.I))
    if desc_div:
        data['description_excerpt'] = desc_div.get_text(' ', strip=True)[:300]
    elif data['title']:
        # Fallback: get text after title
        all_text = page_text
        idx = all_text.find(data['title'])
        if idx > -1:
            data['description_excerpt'] = all_text[idx+len(data['title']):idx+len(data['title'])+300].strip()

    # Dates
    date_patterns = [
        (r'(?:Publicat|Postat)\s*(?:la|pe|:)\s*(\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4})', 'publish_date'),
        (r'(?:Licitatie|Licitație|Data licitatie|Auction)\s*(?:la|pe|:)\s*(\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4})', 'auction_date'),
    ]
    for dp, field in date_patterns:
        dm = re.search(dp, page_text, re.IGNORECASE)
        if dm:
            data[field] = dm.group(1)

    return data

def scrape_category(category, test_mode=False):
    """Scrape all listings from a category."""
    print(f"\n{'='*60}")
    print(f"Category: {category.upper()}")
    print(f"{'='*60}")

    url = f"{BASE_URL}/{category}"
    soup, _ = get_page(url)
    if not soup:
        print(f"  Failed to load {url}")
        return []

    pages, total = get_total_pages(soup)
    print(f"  Total: {total} listings across {pages} pages")

    if test_mode:
        pages = 1
        print(f"  TEST MODE: scraping page 1 only")

    all_listings = []

    for page in range(1, pages + 1):
        if page == 1:
            page_url = url
        else:
            page_url = f"{url}/{page}"

        print(f"\n  Page {page}/{pages}: {page_url}")

        if page > 1:
            soup, _ = get_page(page_url)
            if not soup:
                print(f"    Failed to load page {page}")
                continue

        listing_urls = get_listing_urls_from_page(soup)
        print(f"    Found {len(listing_urls)} listings")

        for i, lurl in enumerate(listing_urls):
            lid = re.search(r'_i(\d+)$', lurl)
            lid_str = lid.group(1) if lid else '?'
            print(f"    [{i+1}/{len(listing_urls)}] ID {lid_str}...", end='', flush=True)

            data = scrape_detail_page(lurl)
            if data:
                data['category'] = category
                all_listings.append(data)
                contact = []
                if data.get('email'):
                    contact.append(f"email={data['email']}")
                if data.get('phone'):
                    contact.append(f"phone={data['phone']}")
                if contact:
                    print(f" OK ({', '.join(contact)})")
                else:
                    print(f" OK (no contact)")
            else:
                print(f" FAILED")

    return all_listings

def save_to_csv(data, output_file):
    """Save data to a CSV file."""
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

def main():
    test_mode = '--test' in sys.argv

    timestamp = datetime.now().strftime('%Y%m%d')
    output_file = os.path.join(OUTPUT_DIR, f'licitatii_insolventa_{timestamp}.csv')

    print(f"licitatii-insolventa.ro Scraper")
    print(f"{'='*60}")
    print(f"Mode: {'TEST (1 page/category)' if test_mode else 'FULL'}")
    print(f"Output: {output_file}")
    print(f"Delay: {REQUEST_DELAY}s between requests")

    all_data = []
    for cat in CATEGORIES:
        listings = scrape_category(cat, test_mode)
        all_data.extend(listings)
        print(f"\n  >> {cat}: {len(listings)} listings scraped")

    # Write CSV
    fields = [
        'listing_id', 'category', 'subcategory', 'title', 'price', 'currency',
        'location', 'county', 'publisher_name', 'publisher_profile',
        'phone', 'email', 'auction_date', 'publish_date',
        'description_excerpt', 'url',
    ]

    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(all_data)

    # Stats
    print(f"\n{'='*60}")
    print(f"DONE — {len(all_data)} listings saved to {output_file}")
    with_email = sum(1 for d in all_data if d.get('email'))
    with_phone = sum(1 for d in all_data if d.get('phone'))
    print(f"  With email: {with_email}")
    print(f"  With phone: {with_phone}")
    print(f"  With either: {sum(1 for d in all_data if d.get('email') or d.get('phone'))}")

    # Category breakdown
    print(f"\nBy category:")
    for cat in CATEGORIES:
        count = sum(1 for d in all_data if d.get('category') == cat)
        emails = sum(1 for d in all_data if d.get('category') == cat and d.get('email'))
        phones = sum(1 for d in all_data if d.get('category') == cat and d.get('phone'))
        print(f"  {cat}: {count} listings ({emails} emails, {phones} phones)")

if __name__ == '__main__':
    main()
