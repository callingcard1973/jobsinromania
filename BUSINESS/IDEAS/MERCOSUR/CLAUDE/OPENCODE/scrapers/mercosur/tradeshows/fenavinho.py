#!/usr/bin/env python3
"""Fenavinho - Brazil Wine Festival Exhibitors Scraper"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_tradeshows")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml"
}

def scrape_fenavinho() -> list:
    """Scrape Fenavinho exhibitors"""
    companies = []

    url = "https://www.fenavinho.com.br/expositores"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.expositor, .vinicola, .winery'):
                company = {
                    "name": "",
                    "region": "",
                    "products": [],
                    "website": "",
                    "email": "",
                    "country": "Brazil",
                    "sector": "Wine",
                    "event": "Fenavinho",
                    "source": "Fenavinho 2026"
                }

                name_el = item.select_one('h3, h4, .name')
                if name_el:
                    company["name"] = name_el.get_text(strip=True)

                region = item.select_one('.region, .cidade')
                if region:
                    company["region"] = region.get_text(strip=True)

                products = item.select('.product, .vinho, .wine')
                company["products"] = [p.get_text(strip=True) for p in products]

                website = item.select_one('a[href*="http"]:not([href*="fenavinho"])')
                if website:
                    company["website"] = website.get('href', '')

                if company["name"]:
                    companies.append(company)

    except Exception as e:
        print(f"Error: {e}")

    return companies

def scrape_ibravin_wineries() -> list:
    """Scrape IBRAVIN (Brazilian Wine Institute) member wineries"""
    companies = []

    try:
        url = "https://www.ibravin.org.br/vinicolas"
        resp = requests.get(url, headers=HEADERS, timeout=30)

        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.vinicola, .winery'):
                company = {
                    "name": item.select_one('h3, .name').get_text(strip=True) if item.select_one('h3, .name') else "",
                    "region": item.select_one('.region').get_text(strip=True) if item.select_one('.region') else "",
                    "country": "Brazil",
                    "sector": "Wine",
                    "source": "IBRAVIN"
                }
                if company["name"]:
                    companies.append(company)

    except Exception as e:
        print(f"IBRAVIN error: {e}")

    return companies

def main():
    print("=== Fenavinho Wine Exhibitors Scraper ===")

    companies = scrape_fenavinho()
    companies.extend(scrape_ibravin_wineries())

    # Deduplicate
    seen = set()
    unique = []
    for c in companies:
        key = c.get("name", "").lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(c)

    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"fenavinho_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(unique)} wineries to {output_file}")
    return unique

if __name__ == "__main__":
    main()
