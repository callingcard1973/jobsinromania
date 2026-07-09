#!/usr/bin/env python3
"""Chile Producer Scraper - Mining, Wine, Seafood"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_chile_producers")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0"}

# Known Chilean exporters
KNOWN_EXPORTERS = {
    "copper": [
        "Codelco", "BHP Escondida", "Collahuasi", "Antofagasta Minerals",
        "Anglo American Chile", "Teck Carmen de Andacollo", "Freeport McMoRan",
        "Centinela", "Candelaria", "Los Pelambres"
    ],
    "lithium": [
        "SQM (Sociedad Quimica y Minera)", "Albemarle Chile",
        "Livent Chile", "BYD Chile"
    ],
    "wine": [
        "Concha y Toro", "Santa Rita", "Undurraga", "San Pedro",
        "Errazuriz", "Montes", "Cono Sur", "Casillero del Diablo",
        "Carmen", "Tarapaca", "Ventisquero", "De Martino"
    ],
    "salmon": [
        "Mowi Chile", "Cermaq Chile", "AquaChile", "Blumar",
        "Multiexport Foods", "Camanchaca", "Salmones Aysen",
        "Invertec Pesquera", "Australis Seafoods"
    ],
    "fruits": [
        "Unifrutti Chile", "Dole Chile", "Del Monte Chile",
        "Hortifrut", "Subsole", "David del Curto",
        "Copefrut", "Frusan", "San Clemente"
    ],
    "forestry": [
        "CMPC", "Arauco", "Masisa", "Volterra"
    ]
}

def scrape_prochile_directory():
    """Scrape ProChile exporter directory"""
    companies = []

    try:
        url = "https://www.prochile.gob.cl/difusion/directorio-exportadores"
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.exporter, .empresa, .company'):
                name = item.select_one('h3, .name, .title')
                if name:
                    companies.append({
                        "name": name.get_text(strip=True),
                        "country": "Chile",
                        "source": "ProChile"
                    })
    except Exception as e:
        print(f"ProChile error: {e}")

    return companies

def scrape_sofofa():
    """Scrape SOFOFA (Industry Federation) members"""
    companies = []

    try:
        url = "https://www.sofofa.cl/empresas-asociadas"
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.empresa, .member, .company'):
                name = item.select_one('h3, h4, .name')
                if name:
                    companies.append({
                        "name": name.get_text(strip=True),
                        "country": "Chile",
                        "source": "SOFOFA"
                    })
    except Exception as e:
        print(f"SOFOFA error: {e}")

    return companies

def build_from_known():
    """Build list from known exporters"""
    companies = []

    for sector, names in KNOWN_EXPORTERS.items():
        for name in names:
            companies.append({
                "name": name,
                "country": "Chile",
                "sector": sector,
                "source": "Known Exporter"
            })

    return companies

def main():
    print("=== Chile Producer Scraper ===")

    all_companies = []

    # Add known exporters
    print("1. Adding known exporters...")
    known = build_from_known()
    all_companies.extend(known)
    print(f"   Added {len(known)} known exporters")

    # Try ProChile
    print("2. Scraping ProChile...")
    prochile = scrape_prochile_directory()
    all_companies.extend(prochile)
    print(f"   Found {len(prochile)} from ProChile")

    # Try SOFOFA
    print("3. Scraping SOFOFA...")
    sofofa = scrape_sofofa()
    all_companies.extend(sofofa)
    print(f"   Found {len(sofofa)} from SOFOFA")

    # Deduplicate
    seen = set()
    unique = []
    for c in all_companies:
        key = c["name"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(c)

    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"chile_producers_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print(f"\nTotal unique: {len(unique)}")
    print(f"Saved to {output_file}")

    return unique

if __name__ == "__main__":
    main()
