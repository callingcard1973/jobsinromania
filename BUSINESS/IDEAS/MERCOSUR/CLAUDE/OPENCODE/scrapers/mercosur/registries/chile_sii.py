#!/usr/bin/env python3
"""Chile SII (Tax Service) RUT Registry Scraper"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_registries/chile")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json"
}

def search_sii(rut: str) -> dict:
    """Query SII for RUT information"""

    # Clean RUT
    rut = rut.replace(".", "").replace("-", "")

    # SII public verification
    url = f"https://www.sii.cl/cgi_iol/cgi_tcon/tcon_consulta.cgi?rut={rut}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            data = {
                "rut": rut,
                "name": "",
                "activity": "",
                "region": "",
                "status": "",
                "source": "SII"
            }

            # Parse response
            for row in soup.select('tr'):
                cells = row.select('td')
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    if 'razon' in label or 'nombre' in label:
                        data["name"] = value
                    elif 'actividad' in label:
                        data["activity"] = value

            return data

    except Exception as e:
        print(f"SII error: {e}")

    return {}

def scrape_exporters_directory() -> list:
    """Scrape ProChile exporter directory with RUT"""
    companies = []

    try:
        # ProChile often includes RUT in directory
        url = "https://www.prochile.gob.cl/exportadores-chilenos/"
        resp = requests.get(url, headers=HEADERS, timeout=30)

        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.exporter, .empresa'):
                company = {
                    "name": item.select_one('h3, .name').get_text(strip=True) if item.select_one('h3, .name') else "",
                    "rut": item.get('data-rut', ''),
                    "sector": item.select_one('.sector').get_text(strip=True) if item.select_one('.sector') else "",
                    "region": item.select_one('.region').get_text(strip=True) if item.select_one('.region') else "",
                    "country": "Chile",
                    "source": "ProChile"
                }
                if company["name"]:
                    companies.append(company)

    except Exception as e:
        print(f"Error: {e}")

    return companies

def scrape_mining_registry() -> list:
    """Scrape SERNAGEOMIN mining company registry"""
    companies = []

    try:
        url = "https://www.sernageomin.cl/empresas-mineras/"
        resp = requests.get(url, headers=HEADERS, timeout=30)

        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.empresa, tr.mining-company'):
                company = {
                    "name": item.select_one('td:first-child, .name').get_text(strip=True) if item.select_one('td:first-child, .name') else "",
                    "rut": item.get('data-rut', ''),
                    "sector": "Mining",
                    "mineral": item.select_one('.mineral').get_text(strip=True) if item.select_one('.mineral') else "",
                    "region": item.select_one('.region').get_text(strip=True) if item.select_one('.region') else "",
                    "country": "Chile",
                    "source": "SERNAGEOMIN"
                }
                if company["name"]:
                    companies.append(company)

    except Exception as e:
        print(f"Mining registry error: {e}")

    return companies

def main():
    print("=== Chile SII Registry Scraper ===")

    companies = []

    # Get exporter directory
    print("Scraping exporter directory...")
    companies.extend(scrape_exporters_directory())

    # Get mining registry
    print("Scraping mining registry...")
    companies.extend(scrape_mining_registry())

    # Deduplicate
    seen = set()
    unique = []
    for c in companies:
        key = c.get("rut") or c.get("name", "").lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(c)

    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"chile_sii_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(unique)} companies to {output_file}")
    return unique

if __name__ == "__main__":
    main()
