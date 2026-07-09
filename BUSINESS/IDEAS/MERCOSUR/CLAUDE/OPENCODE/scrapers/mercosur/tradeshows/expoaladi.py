#!/usr/bin/env python3
"""ExpoALADI - Latin American Trade Exhibition Exhibitors Scraper"""

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

def scrape_expoaladi() -> list:
    """Scrape ExpoALADI exhibitors"""
    companies = []

    url = "https://www.expoaladi.com/expositores"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.expositor, .exhibitor, .empresa'):
                company = {
                    "name": "",
                    "country": "",
                    "booth": "",
                    "sector": "",
                    "products": [],
                    "website": "",
                    "email": "",
                    "event": "ExpoALADI",
                    "source": "ExpoALADI 2026"
                }

                name_el = item.select_one('h3, h4, .name')
                if name_el:
                    company["name"] = name_el.get_text(strip=True)

                country = item.select_one('.country, .pais')
                if country:
                    company["country"] = country.get_text(strip=True)

                booth = item.select_one('.booth, .stand')
                if booth:
                    company["booth"] = booth.get_text(strip=True)

                sector = item.select_one('.sector, .segmento')
                if sector:
                    company["sector"] = sector.get_text(strip=True)

                products = item.select('.product, .producto')
                company["products"] = [p.get_text(strip=True) for p in products]

                website = item.select_one('a[href*="http"]:not([href*="expoaladi"])')
                if website:
                    company["website"] = website.get('href', '')

                email = item.select_one('a[href^="mailto:"]')
                if email:
                    company["email"] = email['href'].replace('mailto:', '')

                if company["name"]:
                    companies.append(company)

    except Exception as e:
        print(f"Error: {e}")

    return companies

def scrape_aladi_directory() -> list:
    """Scrape ALADI member company directory"""
    companies = []

    try:
        url = "https://www.aladi.org/sitioaladi/empresas/"
        resp = requests.get(url, headers=HEADERS, timeout=30)

        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.empresa, .company'):
                company = {
                    "name": item.select_one('h3, .name').get_text(strip=True) if item.select_one('h3, .name') else "",
                    "country": item.select_one('.pais').get_text(strip=True) if item.select_one('.pais') else "",
                    "sector": item.select_one('.sector').get_text(strip=True) if item.select_one('.sector') else "",
                    "source": "ALADI Directory"
                }
                if company["name"]:
                    companies.append(company)

    except Exception as e:
        print(f"ALADI error: {e}")

    return companies

def main():
    print("=== ExpoALADI Exhibitors Scraper ===")

    companies = scrape_expoaladi()
    companies.extend(scrape_aladi_directory())

    # Deduplicate
    seen = set()
    unique = []
    for c in companies:
        key = c.get("name", "").lower() + c.get("country", "")
        if key and key not in seen:
            seen.add(key)
            unique.append(c)

    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"expoaladi_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(unique)} exhibitors to {output_file}")
    return unique

if __name__ == "__main__":
    main()
