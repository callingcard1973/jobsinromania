#!/usr/bin/env python3
"""Brazil ComexStat - Official Export Statistics & Companies"""

import json
import requests
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_brazil_exporters")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

# Key NCM codes for target products
NCM_CODES = {
    "28369100": "Lithium carbonate",
    "72029300": "Ferroniobium",
    "02011000": "Beef carcasses",
    "02013000": "Beef boneless",
    "04090000": "Honey",
    "22042100": "Wine",
    "12019000": "Soybeans",
    "17011400": "Raw sugar",
    "09011100": "Coffee",
    "76011000": "Aluminum unwrought"
}

def get_comex_exporters(ncm: str, year: int = 2024) -> list:
    """Get exporters for a specific NCM code from ComexStat"""

    # ComexStat API
    url = "https://api-comexstat.mdic.gov.br/general"

    params = {
        "filter": json.dumps({
            "yearStart": year,
            "yearEnd": year,
            "typeFlow": 2,  # Exports
            "typeOrder": 1,
            "filterList": [{"id": "ncm", "values": [ncm]}],
            "details": ["country", "state", "ncm"],
            "metrics": ["metricFOB", "metricKG"]
        })
    }

    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=60, verify=False)
        if resp.status_code == 200:
            return resp.json().get("data", [])
    except Exception as e:
        print(f"ComexStat error for {ncm}: {e}")

    return []

def get_brazil_exporters_csv() -> list:
    """Download Brazil exporter list from MDIC open data"""

    companies = []

    # MDIC open data portal
    urls = [
        "https://www.gov.br/produtividade-e-comercio-exterior/pt-br/assuntos/comercio-exterior/estatisticas/base-de-dados-bruta",
        "https://balanca.economia.gov.br/balanca/bd/comexstat-bd/ncm/EXP_COMPLETA.zip"
    ]

    # Try to get exporter names from transparency portal
    try:
        url = "https://portaldatransparencia.gov.br/api-de-dados/notas-fiscais"
        # This would need authentication
    except:
        pass

    return companies

def scrape_brazil_exporters_directory() -> list:
    """Scrape from Invest & Export Brasil"""

    companies = []

    url = "https://www.investexportbrasil.gov.br/ExportadoresBrasileiros"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.empresa, .company, .exporter, tr'):
                name_el = item.select_one('td:first-child, .name, h3')
                if name_el:
                    text = name_el.get_text(strip=True)
                    if len(text) > 3 and not text.startswith(('NCM', 'Código', 'Nome')):
                        companies.append({
                            "name": text,
                            "country": "Brazil",
                            "source": "Invest Export Brasil"
                        })
    except Exception as e:
        print(f"Directory error: {e}")

    return companies

def get_sector_data() -> dict:
    """Get export statistics by sector"""

    results = {}

    for ncm, product in NCM_CODES.items():
        print(f"Getting data for {product} (NCM {ncm})...")
        data = get_comex_exporters(ncm)

        if data:
            results[product] = {
                "ncm": ncm,
                "records": len(data),
                "top_states": [],
                "top_destinations": [],
                "total_fob": 0,
                "total_kg": 0
            }

            # Aggregate
            states = {}
            countries = {}

            for row in data:
                state = row.get("noUf", "Unknown")
                country = row.get("noPaisDestino", "Unknown")
                fob = row.get("metricFOB", 0)
                kg = row.get("metricKG", 0)

                states[state] = states.get(state, 0) + fob
                countries[country] = countries.get(country, 0) + fob
                results[product]["total_fob"] += fob
                results[product]["total_kg"] += kg

            results[product]["top_states"] = sorted(states.items(), key=lambda x: -x[1])[:5]
            results[product]["top_destinations"] = sorted(countries.items(), key=lambda x: -x[1])[:10]

    return results

def main():
    print("=== Brazil ComexStat Exporter Scraper ===")

    # Get sector statistics
    print("\n1. Getting export statistics by sector...")
    sector_data = get_sector_data()

    # Get exporter directory
    print("\n2. Scraping exporter directory...")
    exporters = scrape_brazil_exporters_directory()
    print(f"   Found {len(exporters)} exporters")

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d")

    # Save sector data
    sector_file = OUTPUT_DIR / f"brazil_export_stats_{timestamp}.json"
    with open(sector_file, 'w') as f:
        json.dump(sector_data, f, indent=2, ensure_ascii=False)
    print(f"\nSaved sector data to {sector_file}")

    # Save exporters
    if exporters:
        exporter_file = OUTPUT_DIR / f"brazil_exporters_{timestamp}.json"
        with open(exporter_file, 'w') as f:
            json.dump(exporters, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(exporters)} exporters to {exporter_file}")

    # Print summary
    print("\n=== EXPORT SUMMARY ===")
    for product, data in sector_data.items():
        fob = data.get("total_fob", 0)
        print(f"{product}: USD {fob:,.0f}")
        if data.get("top_states"):
            print(f"  Top state: {data['top_states'][0][0]}")
        if data.get("top_destinations"):
            top_dest = [d[0] for d in data["top_destinations"][:3]]
            print(f"  Top destinations: {', '.join(top_dest)}")

    return sector_data

if __name__ == "__main__":
    main()
