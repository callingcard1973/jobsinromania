#!/usr/bin/env python3
"""APEX Brasil Exporter Directory Scraper"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_apex")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/html",
    "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8"
}

SECTORS = [
    "agribusiness", "food-beverages", "machinery-equipment",
    "chemicals", "minerals", "textiles", "automotive",
    "electronics", "construction", "services"
]

def scrape_apex_search(sector: str, page: int = 1) -> list:
    """Search APEX Brasil exporter directory"""
    url = "https://portal.apexbrasil.com.br/api/v1/exporters"
    params = {
        "sector": sector,
        "page": page,
        "per_page": 50
    }
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("results", [])
    except Exception as e:
        print(f"Error: {e}")
    return []

def scrape_apex_website() -> list:
    """Scrape from public website if API unavailable"""
    url = "https://www.apexbrasil.com.br/en/explore-brazil/brazilian-exporters"
    companies = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            # Parse HTML for company listings
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')
            for card in soup.select('.company-card, .exporter-item, [data-company]'):
                company = {
                    "name": card.select_one('.name, h3, h4').get_text(strip=True) if card.select_one('.name, h3, h4') else "",
                    "sector": card.select_one('.sector, .category').get_text(strip=True) if card.select_one('.sector, .category') else "",
                    "website": card.select_one('a[href*="http"]')['href'] if card.select_one('a[href*="http"]') else "",
                    "country": "Brazil",
                    "source": "APEX Brasil"
                }
                if company["name"]:
                    companies.append(company)
    except Exception as e:
        print(f"Website scrape error: {e}")
    return companies

def main():
    print("=== APEX Brasil Exporter Scraper ===")
    all_companies = []

    # Try API first
    for sector in SECTORS:
        print(f"Scraping sector: {sector}")
        for page in range(1, 20):
            results = scrape_apex_search(sector, page)
            if not results:
                break
            all_companies.extend(results)
            time.sleep(1)

    # Fallback to website
    if not all_companies:
        print("API unavailable, trying website...")
        all_companies = scrape_apex_website()

    # Deduplicate
    seen = set()
    unique = []
    for c in all_companies:
        key = c.get("name", "").lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(c)

    # Save
    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"apex_brasil_{timestamp}.json"
    with open(output_file, 'w') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(unique)} companies to {output_file}")
    return unique

if __name__ == "__main__":
    main()
