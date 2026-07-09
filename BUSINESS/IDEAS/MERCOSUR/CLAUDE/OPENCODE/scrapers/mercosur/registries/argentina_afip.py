#!/usr/bin/env python3
"""Argentina AFIP CUIT Registry Scraper"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_registries/argentina")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json"
}

# Target activity codes
ACTIVITY_CODES = {
    "011111": "Soy cultivation",
    "011112": "Wheat cultivation",
    "011311": "Grape cultivation",
    "012110": "Cattle breeding",
    "031111": "Sea fishing",
    "071000": "Iron ore",
    "072900": "Other metal ores",
    "101011": "Slaughterhouses",
    "103010": "Fruit processing",
    "106100": "Grain milling",
    "107100": "Bakery products",
    "110100": "Spirits",
    "110211": "Wine production",
    "241000": "Steel production",
    "242000": "Non-ferrous metals"
}

def search_afip(cuit: str = None, name: str = None) -> dict:
    """Query AFIP CUIT database"""

    # AFIP public consultation
    if cuit:
        url = f"https://afip.gob.ar/genericos/cInscripcion/consultaConstancia.asp?cuit={cuit}"
    else:
        return {}

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            data = {
                "cuit": cuit,
                "name": "",
                "trade_name": "",
                "activity": "",
                "province": "",
                "status": "",
                "source": "AFIP"
            }

            # Parse response
            name_el = soup.select_one('.denominacion, .razon-social')
            if name_el:
                data["name"] = name_el.get_text(strip=True)

            return data

    except Exception as e:
        print(f"AFIP error: {e}")

    return {}

def scrape_padron_exportadores() -> list:
    """Scrape exporter registry from AFIP"""
    companies = []

    # Public exporter list
    url = "https://www.afip.gob.ar/exportadores/padron.asp"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for row in soup.select('table tr'):
                cells = row.select('td')
                if len(cells) >= 3:
                    company = {
                        "cuit": cells[0].get_text(strip=True),
                        "name": cells[1].get_text(strip=True),
                        "activity": cells[2].get_text(strip=True) if len(cells) > 2 else "",
                        "country": "Argentina",
                        "type": "Exporter",
                        "source": "AFIP Padron"
                    }
                    if company["name"]:
                        companies.append(company)

    except Exception as e:
        print(f"Error: {e}")

    return companies

def scrape_nosis_free(sector: str) -> list:
    """Use Nosis free search for company data"""
    companies = []

    try:
        url = f"https://www.nosis.com/es/buscar/{sector}/argentina"
        resp = requests.get(url, headers=HEADERS, timeout=30)

        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.company-result, .empresa'):
                company = {
                    "name": item.select_one('h3, .name').get_text(strip=True) if item.select_one('h3, .name') else "",
                    "cuit": item.get('data-cuit', ''),
                    "sector": sector,
                    "country": "Argentina",
                    "source": "Nosis"
                }
                if company["name"]:
                    companies.append(company)

    except Exception as e:
        print(f"Nosis error: {e}")

    return companies

def main():
    print("=== Argentina AFIP CUIT Registry Scraper ===")

    # Get exporter padron
    print("Scraping exporter registry...")
    companies = scrape_padron_exportadores()

    # Supplement with sector searches
    sectors = ["exportador carne", "exportador vinos", "exportador miel", "mineria"]
    for sector in sectors:
        print(f"Searching sector: {sector}")
        results = scrape_nosis_free(sector)
        companies.extend(results)
        time.sleep(1)

    # Deduplicate
    seen = set()
    unique = []
    for c in companies:
        key = c.get("cuit") or c.get("name", "").lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(c)

    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"argentina_afip_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(unique)} companies to {output_file}")
    return unique

if __name__ == "__main__":
    main()
