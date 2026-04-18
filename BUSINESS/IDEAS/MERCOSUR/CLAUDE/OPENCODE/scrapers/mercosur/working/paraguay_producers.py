#!/usr/bin/env python3
"""Paraguay Producer Scraper - Major Exporters"""

import json
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_paraguay_producers")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Known Paraguayan exporters by sector
KNOWN_EXPORTERS = {
    "beef": [
        "Frigorifico Concepcion", "JBS Paraguay", "Minerva Paraguay",
        "Frigorifico San Antonio", "Frigorifico Guarani",
        "Frigorifico Norte", "Frigomerc", "Cencoprod"
    ],
    "soy": [
        "ADM Paraguay", "Cargill Paraguay", "Bunge Paraguay",
        "Louis Dreyfus Paraguay", "COFCO Paraguay", "Vicentin Paraguay",
        "Noble Paraguay", "Sodrugestvo", "CHS Paraguay"
    ],
    "corn_grains": [
        "Dekalpar", "Agrofertil", "Grupo Favero", "Agrotec",
        "Desarrollo Agricola", "Agropeco", "Ganadera Corina"
    ],
    "sugar": [
        "Azucarera Paraguaya (AZPA)", "Azucarera Iturbe",
        "Azucarera Friedmann", "Censi & Pirotta"
    ],
    "wood_charcoal": [
        "Industria Forestal", "Forestal Apepu", "Unique Wood",
        "Parquet Los Pinos", "Itaipu Maderas", "Copetbol"
    ],
    "leather": [
        "Friasa", "Curtiembre Corina", "Curtiembre Paraguay",
        "Cueros del Paraguay"
    ],
    "stevia": [
        "Stevia Paraguay", "Steviapar", "Pure Circle Paraguay",
        "Granular", "Ka'a He'e Paraguaya"
    ],
    "yerba_mate": [
        "Selecta", "Kurupi", "Pajarito", "La Rubia",
        "Campesino", "Colonia Independencia"
    ],
    "sesame": [
        "Shirosawa", "Sesamo del Paraguay", "Agrosam",
        "Compania Paraguaya de Granos"
    ],
    "chia": [
        "Terrasol", "Chia Paraguay", "Natural Seed"
    ]
}

def build_from_known():
    """Build list from known exporters"""
    companies = []

    for sector, names in KNOWN_EXPORTERS.items():
        for name in names:
            companies.append({
                "name": name,
                "country": "Paraguay",
                "sector": sector,
                "source": "Known Exporter"
            })

    return companies

def main():
    print("=== Paraguay Producer Scraper ===")

    all_companies = build_from_known()

    # Deduplicate
    seen = set()
    unique = []
    for c in all_companies:
        key = c["name"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(c)

    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"paraguay_producers_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print(f"\nTotal unique: {len(unique)}")
    print(f"Saved to {output_file}")

    return unique

if __name__ == "__main__":
    main()
