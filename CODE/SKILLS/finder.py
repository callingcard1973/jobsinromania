#!/usr/bin/env python3
"""
Find company websites and extract contact info.
Uses DuckDuckGo search to find websites, then scrapes contact details.
"""

import asyncio
import aiohttp
import csv
import re
import logging
import random
import json
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

# Configure these paths
INPUT_FILE = Path("input.csv")
OUTPUT_FILE = Path(f"contacts_{datetime.now().strftime('%Y%m%d_%H%M')}.csv")
PROGRESS_FILE = Path("finder_progress.json")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
log = logging.getLogger('FINDER')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'ro-RO,ro;q=0.9,en;q=0.8',
}

PHONE_PATTERNS = [
    r'0[237]\d{2}[-.\\s]?\d{3}[-.\\s]?\d{3}',
    r'\+40[237]\d{2}[-.\\s]?\d{3}[-.\\s]?\d{3}',
    r'0[237]\d{8}',
]

EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'


def extract_contacts_from_html(html, url):
    """Extract phone, email, and other contacts from HTML."""
    if not html:
        return {}

    contacts = {}
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text(separator=' ')

    for pattern in PHONE_PATTERNS:
        phones = re.findall(pattern, text)
        if phones:
            clean_phones = []
            for p in phones:
                p = re.sub(r'[-.\\s]', '', p)
                if p.startswith('+40'):
                    p = '0' + p[3:]
                if len(p) == 10 and p not in clean_phones:
                    clean_phones.append(p)
            if clean_phones:
                contacts['phone'] = clean_phones[0]
                if len(clean_phones) > 1:
                    contacts['phone2'] = clean_phones[1]
                break

    emails = re.findall(EMAIL_PATTERN, text.lower())
    valid_emails = [e for e in emails if not any(x in e for x in
        ['example', 'test', 'domain', 'email', 'listafirme', 'facebook', 'google', 'jpg', 'png'])]
    if valid_emails:
        contacts['email'] = valid_emails[0]

    for link in soup.find_all('a', href=True):
        href = link.get('href', '').lower()
        if 'facebook.com' in href and 'facebook' not in contacts:
            contacts['facebook'] = href
        elif 'linkedin.com' in href and 'linkedin' not in contacts:
            contacts['linkedin'] = href

    contacts['website'] = url
    return contacts


async def search_duckduckgo(session, query):
    """Search DuckDuckGo for company website."""
    try:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        async with session.get(url, headers=HEADERS, timeout=15) as resp:
            if resp.status == 200:
                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')

                for result in soup.select('.result__a'):
                    href = result.get('href', '')
                    if any(x in href for x in ['listafirme', 'firme.info', 'termene.ro',
                            'facebook.com', 'linkedin.com', 'youtube.com', 'wikipedia']):
                        continue
                    if href.startswith('http'):
                        return href
    except Exception as e:
        log.debug(f"Search error: {e}")
    return None


async def fetch_website(session, url):
    """Fetch website content."""
    try:
        await asyncio.sleep(random.uniform(1, 2))
        async with session.get(url, headers=HEADERS, timeout=15, allow_redirects=True) as resp:
            if resp.status == 200:
                return await resp.text()
    except:
        pass
    return None


async def process_company(session, company, semaphore):
    """Find website and extract contacts for a company."""
    async with semaphore:
        name = company.get('name', '')
        if not name:
            return company

        query = f"{name} site:ro contact"
        website_url = await search_duckduckgo(session, query)

        if website_url:
            await asyncio.sleep(random.uniform(2, 4))
            html = await fetch_website(session, website_url)
            if html:
                contacts = extract_contacts_from_html(html, website_url)
                company.update(contacts)

        return company


async def main():
    companies = []
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        companies = list(csv.DictReader(f))

    log.info(f"Loaded {len(companies)} companies")

    start_idx = 0
    results = []
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r') as f:
            progress = json.load(f)
            start_idx = progress.get('last_idx', 0)
            results = progress.get('results', [])
            log.info(f"Resuming from {start_idx}")

    semaphore = asyncio.Semaphore(3)

    async with aiohttp.ClientSession() as session:
        for i, company in enumerate(companies[start_idx:], start=start_idx):
            enriched = await process_company(session, company.copy(), semaphore)
            results.append(enriched)

            if (i + 1) % 10 == 0:
                with_phone = sum(1 for r in results if r.get('phone'))
                with_email = sum(1 for r in results if r.get('email'))
                log.info(f"Processed {i+1}/{len(companies)} - {with_phone} phones, {with_email} emails")
                with open(PROGRESS_FILE, 'w') as f:
                    json.dump({'last_idx': i + 1, 'results': results}, f)

            await asyncio.sleep(random.uniform(3, 5))

    fieldnames = ['name', 'cui', 'phone', 'phone2', 'email', 'website', 'facebook', 'linkedin']
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(results)

    log.info(f"Saved to {OUTPUT_FILE}")
    if PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()


if __name__ == '__main__':
    asyncio.run(main())
