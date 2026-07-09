#!/usr/bin/env python3
"""Argentina Producer Scraper - Multiple Sources"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_argentina_producers")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0"}

# Known Argentine exporters by sector
KNOWN_EXPORTERS = {
    "beef": [
        "Frigorifico Gorina", "Grupo Belen", "Frigorifico Rioplatense",
        "Quickfood", "Estancias del Sur", "Frigorifico Paladini",
        "Frigorifico Rio Platense", "Frigorifico Hughes", "Carnes Pampeanas",
        "La Anonima", "Mattievich", "Arre Beef", "Frigorifico General Pico"
    ],
    "wine": [
        "Catena Zapata", "Trapiche", "Luigi Bosca", "Norton", "Rutini",
        "Zuccardi", "Salentein", "Terrazas de los Andes", "Achaval Ferrer",
        "Susana Balbo", "Colomé", "Alta Vista", "Kaiken", "Pascual Toso"
    ],
    "honey": [
        "NEXCO", "Mieles del Sur", "COSAR", "Baldini", "Las Quinas",
        "Miel San Antonio", "Cooperativa Norte Grande", "Apiario del Sol",
        "Patagonia Bee", "Miel de Monte"
    ],
    "lithium": [
        "Livent Argentina", "Allkem Olaroz", "Arcadium Lithium",
        "Eramet Eramine", "Gangfeng Cauchari", "POSCO Sal de Oro",
        "Lithium Americas Argentina", "Rio Tinto Rincon"
    ],
    "soy": [
        "Grupo Los Grobo", "AGD", "Molinos Rio de la Plata", "Aceitera General Deheza",
        "Bunge Argentina", "Cargill Argentina", "Louis Dreyfus Argentina",
        "COFCO Argentina", "Vicentin", "Renova"
    ]
}

def scrape_argentina_trade_portal():
    """Scrape Argentina.gob.ar trade data"""
    companies = []

    try:
        url = "https://www.argentina.gob.ar/economia/comercio-exterior"
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for link in soup.select('a[href*="exportador"], a[href*="empresa"]'):
                text = link.get_text(strip=True)
                if len(text) > 3:
                    companies.append({
                        "name": text,
                        "country": "Argentina",
                        "source": "Argentina.gob.ar"
                    })
    except Exception as e:
        print(f"Portal error: {e}")

    return companies

def scrape_cira():
    """Scrape CIRA (Argentine Chamber of Commerce) members"""
    companies = []

    try:
        url = "https://www.cira.org.ar/empresas"
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.empresa, .member, .company'):
                name = item.select_one('h3, .name')
                if name:
                    companies.append({
                        "name": name.get_text(strip=True),
                        "country": "Argentina",
                        "source": "CIRA"
                    })
    except Exception as e:
        print(f"CIRA error: {e}")

    return companies

def build_from_known():
    """Build list from known exporters"""
    companies = []

    for sector, names in KNOWN_EXPORTERS.items():
        for name in names:
            companies.append({
                "name": name,
                "country": "Argentina",
                "sector": sector,
                "source": "Known Exporter"
            })

    return companies

def main():
    print("=== Argentina Producer Scraper ===")

    all_companies = []

    # Add known exporters
    print("1. Adding known exporters...")
    known = build_from_known()
    all_companies.extend(known)
    print(f"   Added {len(known)} known exporters")

    # Try portal scraping
    print("2. Scraping government portal...")
    portal = scrape_argentina_trade_portal()
    all_companies.extend(portal)
    print(f"   Found {len(portal)} from portal")

    # Try CIRA
    print("3. Scraping CIRA...")
    cira = scrape_cira()
    all_companies.extend(cira)
    print(f"   Found {len(cira)} from CIRA")

    # Deduplicate
    seen = set()
    unique = []
    for c in all_companies:
        key = c["name"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(c)

    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"argentina_producers_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print(f"\nTotal unique: {len(unique)}")
    print(f"Saved to {output_file}")

    return unique

if __name__ == "__main__":
    main()
