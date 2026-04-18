#!/usr/bin/env python3
"""Uruguay DGI RUC Registry Scraper"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_registries/uruguay")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json"
}

def search_dgi(rut: str) -> dict:
    """Query DGI for RUT information"""

    url = f"https://www.dgi.gub.uy/consulta-rut/api/buscar/{rut}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"DGI error: {e}")

    return {}

def scrape_exporters() -> list:
    """Scrape Uruguay exporter directories"""
    companies = []

    # Uruguay XXI directory with RUT
    try:
        url = "https://www.uruguayxxi.gub.uy/es/exportar/directorio/"
        resp = requests.get(url, headers=HEADERS, timeout=30)

        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.exporter, .empresa'):
                company = {
                    "name": item.select_one('h3, .name').get_text(strip=True) if item.select_one('h3, .name') else "",
                    "rut": item.get('data-rut', ''),
                    "sector": item.select_one('.sector').get_text(strip=True) if item.select_one('.sector') else "",
                    "department": item.select_one('.department').get_text(strip=True) if item.select_one('.department') else "",
                    "website": item.select_one('a[href*="http"]')['href'] if item.select_one('a[href*="http"]') else "",
                    "country": "Uruguay",
                    "source": "Uruguay XXI"
                }
                if company["name"]:
                    companies.append(company)

    except Exception as e:
        print(f"Error: {e}")

    return companies

def scrape_meat_exporters() -> list:
    """Scrape INAC meat exporter registry"""
    companies = []

    try:
        url = "https://www.inac.uy/innovaportal/v/13574/10/innova.front/empresas-habilitadas"
        resp = requests.get(url, headers=HEADERS, timeout=30)

        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for row in soup.select('table tr'):
                cells = row.select('td')
                if len(cells) >= 3:
                    company = {
                        "name": cells[0].get_text(strip=True),
                        "inac_number": cells[1].get_text(strip=True) if len(cells) > 1 else "",
                        "department": cells[2].get_text(strip=True) if len(cells) > 2 else "",
                        "sector": "Meat",
                        "eu_approved": True,
                        "country": "Uruguay",
                        "source": "INAC"
                    }
                    if company["name"]:
                        companies.append(company)

    except Exception as e:
        print(f"INAC error: {e}")

    return companies

def main():
    print("=== Uruguay DGI Registry Scraper ===")

    companies = []

    print("Scraping exporter directory...")
    companies.extend(scrape_exporters())

    print("Scraping meat exporters...")
    companies.extend(scrape_meat_exporters())

    # Deduplicate
    seen = set()
    unique = []
    for c in companies:
        key = c.get("rut") or c.get("name", "").lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(c)

    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"uruguay_dgi_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(unique)} companies to {output_file}")
    return unique

if __name__ == "__main__":
    main()
