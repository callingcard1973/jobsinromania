#!/usr/bin/env python3
"""REDIEX Paraguay Exporter Directory Scraper"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_paraguay")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/html"
}

def scrape_rediex() -> list:
    """Scrape REDIEX Paraguay exporter directory"""
    companies = []

    # REDIEX directory page
    url = "https://www.rediex.gov.py/exportadores"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for card in soup.select('.exporter-card, .company-item, .directory-row'):
                company = {
                    "name": card.select_one('h3, h4, .name, td:first-child').get_text(strip=True) if card.select_one('h3, h4, .name, td:first-child') else "",
                    "ruc": card.get('data-ruc', ''),
                    "sector": card.select_one('.sector, .category').get_text(strip=True) if card.select_one('.sector, .category') else "",
                    "city": card.select_one('.city, .location').get_text(strip=True) if card.select_one('.city, .location') else "",
                    "email": "",
                    "phone": "",
                    "website": card.select_one('a[href*="http"]')['href'] if card.select_one('a[href*="http"]') else "",
                    "country": "Paraguay",
                    "source": "REDIEX"
                }

                # Extract email if present
                email_el = card.select_one('a[href^="mailto:"]')
                if email_el:
                    company["email"] = email_el['href'].replace('mailto:', '')

                if company["name"]:
                    companies.append(company)

    except Exception as e:
        print(f"Error: {e}")

    # Also try REDIEX API if available
    try:
        api_url = "https://www.rediex.gov.py/api/exportadores"
        resp = requests.get(api_url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("exportadores", []):
                company = {
                    "name": item.get("nombre", ""),
                    "ruc": item.get("ruc", ""),
                    "sector": item.get("sector", ""),
                    "email": item.get("email", ""),
                    "phone": item.get("telefono", ""),
                    "website": item.get("web", ""),
                    "country": "Paraguay",
                    "source": "REDIEX API"
                }
                companies.append(company)
    except:
        pass

    return companies

def main():
    print("=== REDIEX Paraguay Exporter Scraper ===")
    companies = scrape_rediex()

    seen = set()
    unique = []
    for c in companies:
        key = c.get("ruc") or c.get("name", "").lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(c)

    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"rediex_paraguay_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(unique)} companies to {output_file}")
    return unique

if __name__ == "__main__":
    main()
