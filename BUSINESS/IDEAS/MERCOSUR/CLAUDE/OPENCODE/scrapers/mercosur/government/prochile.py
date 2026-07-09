#!/usr/bin/env python3
"""ProChile Exporter Directory Scraper"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_chile")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/html"
}

SECTORS = [
    "agroindustria", "alimentos", "vinos", "frutas",
    "salmon", "mineria", "forestal", "manufactura",
    "servicios", "tecnologia"
]

def scrape_prochile_api() -> list:
    """Scrape ProChile exporter API"""
    companies = []
    api_url = "https://www.prochile.gob.cl/api/exportadores"

    try:
        for sector in SECTORS:
            print(f"Scraping sector: {sector}")
            params = {"sector": sector, "page": 1, "per_page": 50}

            while True:
                resp = requests.get(api_url, params=params, headers=HEADERS, timeout=30)
                if resp.status_code != 200:
                    break

                data = resp.json()
                results = data.get("data", [])

                if not results:
                    break

                for item in results:
                    company = {
                        "name": item.get("nombre", ""),
                        "rut": item.get("rut", ""),
                        "sector": sector,
                        "region": item.get("region", ""),
                        "comuna": item.get("comuna", ""),
                        "email": item.get("email", ""),
                        "phone": item.get("telefono", ""),
                        "website": item.get("web", ""),
                        "products": item.get("productos", []),
                        "export_countries": item.get("paises_destino", []),
                        "country": "Chile",
                        "source": "ProChile"
                    }
                    companies.append(company)

                params["page"] += 1
                time.sleep(0.5)

                if len(results) < 50:
                    break

    except Exception as e:
        print(f"API error: {e}")

    return companies

def scrape_prochile_directory() -> list:
    """Scrape ProChile directory website"""
    companies = []
    base_url = "https://www.prochile.gob.cl/difusion/directorio-exportadores"

    try:
        resp = requests.get(base_url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for card in soup.select('.exporter-card, .company-item, .directory-item'):
                company = {
                    "name": card.select_one('h3, h4, .name').get_text(strip=True) if card.select_one('h3, h4, .name') else "",
                    "sector": card.select_one('.sector, .category').get_text(strip=True) if card.select_one('.sector, .category') else "",
                    "website": card.select_one('a[href*="http"]')['href'] if card.select_one('a[href*="http"]') else "",
                    "country": "Chile",
                    "source": "ProChile Directory"
                }
                if company["name"]:
                    companies.append(company)
    except Exception as e:
        print(f"Website error: {e}")

    return companies

def main():
    print("=== ProChile Exporter Scraper ===")

    companies = scrape_prochile_api()
    if not companies:
        print("API unavailable, trying website...")
        companies = scrape_prochile_directory()

    # Deduplicate
    seen = set()
    unique = []
    for c in companies:
        key = c.get("rut") or c.get("name", "").lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(c)

    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"prochile_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(unique)} companies to {output_file}")
    return unique

if __name__ == "__main__":
    main()
