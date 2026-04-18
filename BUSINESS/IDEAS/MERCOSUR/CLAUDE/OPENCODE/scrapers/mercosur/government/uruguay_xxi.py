#!/usr/bin/env python3
"""Uruguay XXI Exporter Directory Scraper"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_uruguay")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/html"
}

SECTORS = [
    "alimentos", "bebidas", "agroindustria", "tecnologia",
    "servicios", "manufactura", "quimicos", "textiles"
]

def scrape_uruguay_xxi() -> list:
    """Scrape Uruguay XXI exporter directory"""
    companies = []

    # Uruguay XXI directory
    api_url = "https://www.uruguayxxi.gub.uy/api/exporters"

    try:
        for sector in SECTORS:
            print(f"Scraping sector: {sector}")
            params = {"sector": sector, "page": 1}

            while True:
                resp = requests.get(api_url, params=params, headers=HEADERS, timeout=30)
                if resp.status_code != 200:
                    break

                data = resp.json()
                results = data.get("exporters", data.get("data", []))

                if not results:
                    break

                for item in results:
                    company = {
                        "name": item.get("company_name", item.get("nombre", "")),
                        "rut": item.get("rut", ""),
                        "sector": sector,
                        "department": item.get("departamento", ""),
                        "email": item.get("email", ""),
                        "phone": item.get("phone", item.get("telefono", "")),
                        "website": item.get("website", item.get("web", "")),
                        "products": item.get("products", []),
                        "country": "Uruguay",
                        "source": "Uruguay XXI"
                    }
                    companies.append(company)

                params["page"] += 1
                time.sleep(0.5)

                if len(results) < 20:
                    break

    except Exception as e:
        print(f"API error: {e}, trying website...")
        companies = scrape_website()

    return companies

def scrape_website() -> list:
    """Fallback website scraper"""
    companies = []
    url = "https://www.uruguayxxi.gub.uy/es/exportar/directorio-exportadores/"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.exporter, .company-card, tr.company'):
                company = {
                    "name": item.select_one('.name, h3, td:first-child').get_text(strip=True) if item.select_one('.name, h3, td:first-child') else "",
                    "country": "Uruguay",
                    "source": "Uruguay XXI Website"
                }
                if company["name"]:
                    companies.append(company)
    except Exception as e:
        print(f"Website error: {e}")

    return companies

def main():
    print("=== Uruguay XXI Exporter Scraper ===")
    companies = scrape_uruguay_xxi()

    seen = set()
    unique = []
    for c in companies:
        key = c.get("rut") or c.get("name", "").lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(c)

    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"uruguay_xxi_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(unique)} companies to {output_file}")
    return unique

if __name__ == "__main__":
    main()
