#!/usr/bin/env python3
"""ABEMEL - Brazilian Honey Exporters Association Scraper"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_honey_associations")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml"
}

def scrape_abemel() -> list:
    """Scrape ABEMEL member companies"""
    companies = []

    url = "https://www.abemel.com.br/associados"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.associado, .member, .company'):
                company = {
                    "name": "",
                    "country": "Brazil",
                    "sector": "Honey",
                    "type": "Exporter",
                    "state": "",
                    "city": "",
                    "website": "",
                    "email": "",
                    "phone": "",
                    "products": [],
                    "certifications": [],
                    "organic": False,
                    "source": "ABEMEL"
                }

                name_el = item.select_one('h3, h4, .name')
                if name_el:
                    company["name"] = name_el.get_text(strip=True)

                # Check organic certification
                if item.select_one('.organic, .organico') or 'organic' in item.get_text().lower():
                    company["organic"] = True

                location = item.select_one('.location, .address')
                if location:
                    company["city"] = location.get_text(strip=True)

                state = item.select_one('.state, .uf')
                if state:
                    company["state"] = state.get_text(strip=True)

                website = item.select_one('a[href*="http"]:not([href*="abemel"])')
                if website:
                    company["website"] = website.get('href', '')

                email = item.select_one('a[href^="mailto:"]')
                if email:
                    company["email"] = email['href'].replace('mailto:', '')

                # Products
                products = item.select('.product, .produto')
                company["products"] = [p.get_text(strip=True) for p in products]

                if company["name"]:
                    companies.append(company)

    except Exception as e:
        print(f"Error scraping ABEMEL: {e}")

    return companies

def scrape_conap() -> list:
    """Scrape CONAP (Beekeeping Confederation) members"""
    companies = []

    try:
        url = "https://www.conap.coop.br/cooperativas"
        resp = requests.get(url, headers=HEADERS, timeout=30)

        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.cooperativa, .member'):
                company = {
                    "name": item.select_one('h3, .name').get_text(strip=True) if item.select_one('h3, .name') else "",
                    "country": "Brazil",
                    "sector": "Honey",
                    "type": "Cooperative",
                    "source": "CONAP"
                }
                if company["name"]:
                    companies.append(company)

    except Exception as e:
        print(f"CONAP error: {e}")

    return companies

def main():
    print("=== ABEMEL Honey Exporters Scraper ===")

    companies = scrape_abemel()
    companies.extend(scrape_conap())

    # Deduplicate
    seen = set()
    unique = []
    for c in companies:
        key = c.get("name", "").lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(c)

    output = {
        "association": "ABEMEL - Brazilian Honey Exporters",
        "website": "https://www.abemel.com.br",
        "members": unique,
        "scraped_at": datetime.now().isoformat()
    }

    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"abemel_members_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(unique)} companies to {output_file}")
    return unique

if __name__ == "__main__":
    main()
