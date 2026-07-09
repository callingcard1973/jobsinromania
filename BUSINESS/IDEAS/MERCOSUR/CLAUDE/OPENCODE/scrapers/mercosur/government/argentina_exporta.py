#!/usr/bin/env python3
"""Argentina Exporta - Official Export Directory Scraper"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_argentina")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/html"
}

SECTORS = [
    "alimentos", "bebidas", "maquinaria", "quimicos",
    "minerales", "textiles", "automotriz", "servicios",
    "tecnologia", "agroindustria"
]

def scrape_argentina_exporta() -> list:
    """Scrape Argentina government export directory"""
    companies = []

    # Argentina Exporta API endpoint
    api_url = "https://www.argentina.gob.ar/api/produccion/exportadores"

    try:
        for sector in SECTORS:
            print(f"Scraping sector: {sector}")
            params = {"sector": sector, "limit": 100, "offset": 0}

            while True:
                resp = requests.get(api_url, params=params, headers=HEADERS, timeout=30)
                if resp.status_code != 200:
                    break

                data = resp.json()
                results = data.get("results", data.get("data", []))

                if not results:
                    break

                for item in results:
                    company = {
                        "name": item.get("razon_social", item.get("nombre", "")),
                        "cuit": item.get("cuit", ""),
                        "sector": sector,
                        "province": item.get("provincia", ""),
                        "city": item.get("localidad", ""),
                        "email": item.get("email", ""),
                        "phone": item.get("telefono", ""),
                        "website": item.get("web", ""),
                        "products": item.get("productos", []),
                        "country": "Argentina",
                        "source": "Argentina Exporta"
                    }
                    companies.append(company)

                params["offset"] += 100
                time.sleep(0.5)

                if len(results) < 100:
                    break

    except Exception as e:
        print(f"API error: {e}, trying alternative...")
        companies = scrape_exporters_website()

    return companies

def scrape_exporters_website() -> list:
    """Fallback: scrape from public website"""
    companies = []
    url = "https://www.argentina.gob.ar/produccion/comercio-exterior/exportadores"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.exporter-item, .company-row, tr[data-cuit]'):
                company = {
                    "name": item.select_one('.name, td:first-child').get_text(strip=True) if item.select_one('.name, td:first-child') else "",
                    "cuit": item.get('data-cuit', ''),
                    "country": "Argentina",
                    "source": "Argentina Exporta Website"
                }
                if company["name"]:
                    companies.append(company)
    except Exception as e:
        print(f"Website error: {e}")

    return companies

def main():
    print("=== Argentina Exporta Scraper ===")
    companies = scrape_argentina_exporta()

    # Deduplicate by CUIT or name
    seen = set()
    unique = []
    for c in companies:
        key = c.get("cuit") or c.get("name", "").lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(c)

    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"argentina_exporta_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(unique)} companies to {output_file}")
    return unique

if __name__ == "__main__":
    main()
