#!/usr/bin/env python3
"""Uruguay Producer Scraper - Beef, Dairy, Rice"""

import json
import requests
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_uruguay_producers")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0"}

# Known Uruguayan exporters
KNOWN_EXPORTERS = {
    "beef": [
        "Frigorifico Las Piedras", "Frigorifico Tacuarembo",
        "Breeders & Packers Uruguay (BPU)", "Frigorifico San Jacinto",
        "Frigorifico Canelones", "Frigorifico Carrasco",
        "Frigorifico Colonia", "Frigorifico Pando",
        "Frigorifico Rosario", "Frigorifico Florida",
        "Marfrig Uruguay", "Minerva Uruguay", "JBS Uruguay"
    ],
    "dairy": [
        "Conaprole", "Lactalis Uruguay", "Estancias del Lago",
        "Pili", "Calcar", "Indulacsa"
    ],
    "rice": [
        "SAMAN", "Coopar", "Casarone", "Arroceros del Uruguay",
        "Glencore Arroz"
    ],
    "wool": [
        "Lanas Trinidad", "Central Lanera", "Tops Fray Marcos",
        "Engraw", "Lanas Sur"
    ],
    "citrus": [
        "Citricultura San Francisco", "Milagro Citrus",
        "Caputto", "Citrus Uruguay"
    ],
    "wood": [
        "UPM Uruguay", "Montes del Plata", "Weyerhaeuser Uruguay",
        "Forestal Oriental"
    ]
}

def build_from_known():
    """Build list from known exporters"""
    companies = []

    for sector, names in KNOWN_EXPORTERS.items():
        for name in names:
            companies.append({
                "name": name,
                "country": "Uruguay",
                "sector": sector,
                "source": "Known Exporter"
            })

    return companies

def scrape_uruguay_xxi():
    """Scrape Uruguay XXI directory"""
    companies = []

    try:
        url = "https://www.uruguayxxi.gub.uy/es/exportar/directorio"
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.exporter, .empresa, .company'):
                name = item.select_one('h3, .name')
                if name:
                    companies.append({
                        "name": name.get_text(strip=True),
                        "country": "Uruguay",
                        "source": "Uruguay XXI"
                    })
    except Exception as e:
        print(f"Uruguay XXI error: {e}")

    return companies

def main():
    print("=== Uruguay Producer Scraper ===")

    all_companies = []

    # Add known exporters
    print("1. Adding known exporters...")
    known = build_from_known()
    all_companies.extend(known)
    print(f"   Added {len(known)} known exporters")

    # Try Uruguay XXI
    print("2. Scraping Uruguay XXI...")
    uxxii = scrape_uruguay_xxi()
    all_companies.extend(uxxii)
    print(f"   Found {len(uxxii)} from Uruguay XXI")

    # Deduplicate
    seen = set()
    unique = []
    for c in all_companies:
        key = c["name"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(c)

    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"uruguay_producers_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print(f"\nTotal unique: {len(unique)}")
    print(f"Saved to {output_file}")

    return unique

if __name__ == "__main__":
    main()
