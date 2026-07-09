#!/usr/bin/env python3
"""APAS Show - Brazil Supermarket & Food Expo Exhibitors Scraper"""

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

def scrape_apas_exhibitors() -> list:
    """Scrape APAS Show exhibitor list"""
    companies = []

    # APAS Show exhibitors page
    url = "https://www.apasshow.com.br/expositores"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.expositor, .exhibitor, .company-card'):
                company = {
                    "name": "",
                    "booth": "",
                    "sector": "",
                    "products": [],
                    "website": "",
                    "email": "",
                    "phone": "",
                    "country": "Brazil",
                    "event": "APAS Show",
                    "source": "APAS Show 2026"
                }

                name_el = item.select_one('h3, h4, .name, .company-name')
                if name_el:
                    company["name"] = name_el.get_text(strip=True)

                booth = item.select_one('.booth, .stand, .estande')
                if booth:
                    company["booth"] = booth.get_text(strip=True)

                sector = item.select_one('.sector, .category, .segmento')
                if sector:
                    company["sector"] = sector.get_text(strip=True)

                products = item.select('.product, .produto')
                company["products"] = [p.get_text(strip=True) for p in products]

                website = item.select_one('a[href*="http"]:not([href*="apas"])')
                if website:
                    company["website"] = website.get('href', '')

                email = item.select_one('a[href^="mailto:"]')
                if email:
                    company["email"] = email['href'].replace('mailto:', '')

                if company["name"]:
                    companies.append(company)

    except Exception as e:
        print(f"Error scraping APAS: {e}")

    return companies

def scrape_apas_api() -> list:
    """Try APAS API if available"""
    companies = []

    try:
        url = "https://www.apasshow.com.br/api/exhibitors"
        resp = requests.get(url, headers=HEADERS, timeout=30)

        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("exhibitors", []):
                company = {
                    "name": item.get("name", ""),
                    "booth": item.get("booth", ""),
                    "sector": item.get("sector", ""),
                    "products": item.get("products", []),
                    "website": item.get("website", ""),
                    "email": item.get("email", ""),
                    "country": item.get("country", "Brazil"),
                    "event": "APAS Show",
                    "source": "APAS API"
                }
                if company["name"]:
                    companies.append(company)

    except:
        pass

    return companies

def main():
    print("=== APAS Show Exhibitors Scraper ===")

    companies = scrape_apas_exhibitors()
    if not companies:
        companies = scrape_apas_api()

    # Deduplicate
    seen = set()
    unique = []
    for c in companies:
        key = c.get("name", "").lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(c)

    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"apas_show_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(unique)} exhibitors to {output_file}")
    return unique

if __name__ == "__main__":
    main()
