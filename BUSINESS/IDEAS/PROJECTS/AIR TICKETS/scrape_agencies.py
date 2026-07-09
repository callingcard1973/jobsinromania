#!/usr/bin/env python3
"""
Scrape 2,968 Romanian travel agencies from SITUR list.
Extracts: services offered, booking capability, API/affiliate/B2B,
RSS feeds, sitemaps, tech stack, social media.

No tokens needed — pure HTTP scraping.
Run: python3 scrape_agencies.py
Output: agentii_scraped.csv

Max 250 lines (project rule).
"""

import csv
import re
import sys
import time
import random
import logging
import requests
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

SRC = 'D:/MEMORY/AIR TICKETS/agentii_turistice_clean.csv'
DST = 'D:/MEMORY/AIR TICKETS/agentii_scraped.csv'
LOG = 'D:/MEMORY/AIR TICKETS/scrape_log.txt'
TIMEOUT = 10
MAX_WORKERS = 10
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 Chrome/125.0 Safari/537.36',
    'Accept-Language': 'ro-RO,ro;q=0.9,en;q=0.8',
}

logging.basicConfig(filename=LOG, level=logging.INFO,
                    format='%(asctime)s %(message)s')

# Keywords to detect in page content
KW_FLIGHTS = r'bilete?\s*(?:de\s*)?avion|flight|airline|zbor|charter'
KW_VACATION = r'vacan[tț][aă]|sejur|all\s*inclusive|litoral|exotic'
KW_CORPORATE = r'corporate|business\s*travel|mice|teambuilding'
KW_BOOKING = r'rezer[vw]|book(?:ing)?|cump[aă]r[aă]|add.to.cart|checkout'
KW_API = r'\bapi\b|affiliate|afiliere|partener|partner|b2b|reseller'
KW_GDS = r'amadeus|sabre|galileo|travelport|worldspan|gds|iata'
KW_TOURS = r'circuit|excursie|tour|ghid|guide|city.?break'
KW_TRANSFER = r'transfer|airport|shuttle|transport'
KW_INSURANCE = r'asigur[aă]r|insurance|travel.protect'
KW_CARRENTAL = r'rent.?a.?car|[iî]nchiri|car.?rental|auto'


def normalize_url(url):
    if not url or not url.strip():
        return None
    url = url.strip().rstrip('/')
    if not url.startswith('http'):
        url = 'https://' + url
    return url


def find_patterns(html, url):
    """Extract structured data from HTML without parsing libraries."""
    low = html.lower()
    result = {}

    # Services detected
    for name, pattern in [
        ('flights', KW_FLIGHTS), ('vacations', KW_VACATION),
        ('corporate', KW_CORPORATE), ('tours', KW_TOURS),
        ('transfers', KW_TRANSFER), ('insurance', KW_INSURANCE),
        ('car_rental', KW_CARRENTAL),
    ]:
        result[name] = bool(re.search(pattern, low))

    # Booking capability
    result['has_booking'] = bool(re.search(KW_BOOKING, low))

    # API / B2B / Affiliate
    result['has_api_b2b'] = bool(re.search(KW_API, low))
    result['has_gds'] = bool(re.search(KW_GDS, low))

    # RSS feeds
    rss = re.findall(
        r'(?:href|src)=["\']([^"\']*(?:rss|feed|atom)[^"\']*)["\']', low)
    result['rss_feeds'] = '; '.join(set(rss[:3]))

    # Sitemap
    result['has_sitemap'] = '/sitemap' in low or 'sitemap.xml' in low

    # Social media
    socials = []
    for platform in ['facebook.com', 'instagram.com', 'linkedin.com',
                     'youtube.com', 'tiktok.com', 'twitter.com', 'x.com']:
        matches = re.findall(
            rf'href=["\']([^"\']*{platform}[^"\']*)["\']', html)
        if matches:
            socials.append(matches[0])
    result['social_media'] = '; '.join(socials[:5])

    # Tech stack hints
    techs = []
    if 'wordpress' in low or 'wp-content' in low:
        techs.append('WordPress')
    if 'woocommerce' in low:
        techs.append('WooCommerce')
    if 'shopify' in low:
        techs.append('Shopify')
    if 'wix.com' in low:
        techs.append('Wix')
    if 'squarespace' in low:
        techs.append('Squarespace')
    if 'joomla' in low:
        techs.append('Joomla')
    if 'prestashop' in low:
        techs.append('PrestaShop')
    if 'travelport' in low or 'amadeus' in low:
        techs.append('GDS-integrated')
    result['tech_stack'] = ', '.join(techs)

    # Phone numbers (Romanian format)
    phones = re.findall(r'(?:0|\+40)\s*[237]\d[\d\s\-.]{6,12}', html)
    result['phones'] = '; '.join(set(p.strip() for p in phones[:3]))

    # Extra emails beyond the SITUR one
    emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.]+', html)
    result['extra_emails'] = '; '.join(
        set(e for e in emails[:5] if 'wixpress' not in e and 'sentry' not in e))

    # Page title
    title = re.search(r'<title[^>]*>([^<]+)</title>', html, re.I)
    result['page_title'] = title.group(1).strip()[:120] if title else ''

    return result


def check_robots_sitemap(base_url):
    """Check robots.txt for sitemap references."""
    try:
        r = requests.get(f"{base_url}/robots.txt",
                         headers=HEADERS, timeout=5)
        if r.ok:
            sitemaps = re.findall(r'Sitemap:\s*(\S+)', r.text, re.I)
            return '; '.join(sitemaps[:3])
    except Exception:
        pass
    return ''


def scrape_one(row):
    """Scrape a single agency website."""
    url = normalize_url(row.get('site_web', ''))
    info = {
        'nr_licenta': row.get('nr_licenta', ''),
        'operator': row.get('operator_economic', ''),
        'agentie': row.get('denumire_agentie', ''),
        'email': row.get('email', ''),
        'judet': row.get('judet', ''),
        'tip': row.get('tip_agentie', ''),
        'site_web': url or '',
        'status': 'no_url', 'http_code': '',
    }
    if not url:
        return info

    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT,
                         allow_redirects=True)
        info['http_code'] = r.status_code
        info['final_url'] = r.url
        info['status'] = 'ok' if r.ok else f'http_{r.status_code}'

        if r.ok and len(r.text) > 500:
            patterns = find_patterns(r.text, url)
            info.update(patterns)
            # Check robots.txt for sitemaps
            base = f"{urlparse(r.url).scheme}://{urlparse(r.url).netloc}"
            info['robots_sitemaps'] = check_robots_sitemap(base)
        else:
            info['status'] = 'empty_or_error'
    except requests.exceptions.Timeout:
        info['status'] = 'timeout'
    except requests.exceptions.SSLError:
        info['status'] = 'ssl_error'
        try:
            r = requests.get(url.replace('https:', 'http:'),
                             headers=HEADERS, timeout=TIMEOUT)
            if r.ok:
                info['status'] = 'ok_http'
                info['http_code'] = r.status_code
                info.update(find_patterns(r.text, url))
        except Exception:
            pass
    except Exception as e:
        info['status'] = f'error_{type(e).__name__}'

    time.sleep(random.uniform(0.3, 0.8))
    return info


def main():
    with open(SRC, encoding='utf-8') as f:
        agencies = list(csv.DictReader(f))
    print(f"Loaded {len(agencies)} agencies, starting scrape...")

    fields = [
        'nr_licenta', 'operator', 'agentie', 'email', 'judet', 'tip',
        'site_web', 'status', 'http_code', 'final_url', 'page_title',
        'flights', 'vacations', 'corporate', 'tours', 'transfers',
        'insurance', 'car_rental', 'has_booking', 'has_api_b2b',
        'has_gds', 'tech_stack', 'rss_feeds', 'has_sitemap',
        'robots_sitemaps', 'social_media', 'phones', 'extra_emails',
    ]

    done = 0
    with open(DST, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(scrape_one, row): row for row in agencies}
            for future in as_completed(futures):
                result = future.result()
                w.writerow(result)
                done += 1
                if done % 50 == 0:
                    f.flush()
                    ok = sum(1 for _ in open(DST, encoding='utf-8')) - 1
                    print(f"  [{done}/{len(agencies)}] scraped, {ok} saved")
                    logging.info(f"Progress: {done}/{len(agencies)}")

    print(f"\nDone! {done} agencies scraped -> {DST}")
    # Quick stats
    with open(DST, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    ok = sum(1 for r in rows if r.get('status', '').startswith('ok'))
    api = sum(1 for r in rows if r.get('has_api_b2b') == 'True')
    gds = sum(1 for r in rows if r.get('has_gds') == 'True')
    bk = sum(1 for r in rows if r.get('has_booking') == 'True')
    fl = sum(1 for r in rows if r.get('flights') == 'True')
    print(f"Reachable: {ok} | Flights: {fl} | Booking: {bk} | "
          f"API/B2B: {api} | GDS: {gds}")


if __name__ == '__main__':
    main()
