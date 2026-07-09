#!/usr/bin/env python3
"""Brazil CNPJ Registry - ReceitaNet Public Data"""

import json
import time
import requests
import zipfile
import csv
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_registries/brazil")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# CNAE codes for target sectors
CNAE_CODES = {
    "0111-3": "Cereals (soy, corn)",
    "0133-4": "Fruits",
    "0151-2": "Cattle raising",
    "0159-8": "Other animals",
    "0161-0": "Agriculture support",
    "0210-1": "Forestry",
    "0710-3": "Iron ore mining",
    "0723-5": "Other metal ores (niobium, lithium)",
    "1011-2": "Meat processing",
    "1012-1": "Poultry processing",
    "1033-3": "Fruit processing",
    "1052-0": "Dairy products",
    "1061-9": "Grain milling",
    "1071-6": "Sugar production",
    "1099-6": "Other food (honey)",
    "1111-9": "Spirits",
    "1112-7": "Wine",
    "2011-8": "Basic chemicals",
    "2419-9": "Non-ferrous metals",
    "2449-1": "Other non-ferrous (aluminum)"
}

def download_cnpj_data():
    """Download CNPJ bulk data from ReceitaNet"""

    # Public CNPJ data files
    base_url = "https://dadosabertos.rfb.gov.br/CNPJ/"

    files_to_download = [
        "Empresas0.zip",
        "Empresas1.zip",
        "Estabelecimentos0.zip",
        "Cnaes.zip"
    ]

    downloaded = []

    for filename in files_to_download:
        url = f"{base_url}{filename}"
        local_path = OUTPUT_DIR / filename

        if local_path.exists():
            print(f"Already have {filename}")
            downloaded.append(local_path)
            continue

        print(f"Downloading {filename}...")
        try:
            resp = requests.get(url, stream=True, timeout=300)
            if resp.status_code == 200:
                with open(local_path, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                downloaded.append(local_path)
                print(f"Downloaded {filename}")
        except Exception as e:
            print(f"Error downloading {filename}: {e}")

    return downloaded

def filter_by_cnae(cnae_filter: list = None) -> list:
    """Filter CNPJ data by CNAE codes"""

    if cnae_filter is None:
        cnae_filter = list(CNAE_CODES.keys())

    companies = []

    # Process downloaded files
    for zip_file in OUTPUT_DIR.glob("Estabelecimentos*.zip"):
        try:
            with zipfile.ZipFile(zip_file, 'r') as zf:
                for csv_name in zf.namelist():
                    with zf.open(csv_name) as f:
                        reader = csv.reader(f.read().decode('latin-1').splitlines(), delimiter=';')
                        for row in reader:
                            if len(row) >= 20:
                                cnae = row[11]  # CNAE fiscal
                                if any(cnae.startswith(code.replace("-", "")) for code in cnae_filter):
                                    company = {
                                        "cnpj_base": row[0],
                                        "cnpj_order": row[1],
                                        "cnpj_dv": row[2],
                                        "name": row[4],
                                        "trade_name": row[5],
                                        "cnae_main": cnae,
                                        "state": row[19],
                                        "city": row[20],
                                        "email": row[28] if len(row) > 28 else "",
                                        "phone": f"{row[16]}{row[17]}" if len(row) > 17 else "",
                                        "country": "Brazil",
                                        "source": "ReceitaNet CNPJ"
                                    }
                                    companies.append(company)

                                    if len(companies) % 10000 == 0:
                                        print(f"Found {len(companies)} companies...")

        except Exception as e:
            print(f"Error processing {zip_file}: {e}")

    return companies

def query_cnpj_api(cnpj: str) -> dict:
    """Query single CNPJ via public API"""

    # Clean CNPJ
    cnpj = cnpj.replace(".", "").replace("/", "").replace("-", "")

    url = f"https://receitaws.com.br/v1/cnpj/{cnpj}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"API error: {e}")

    return {}

def main():
    print("=== Brazil CNPJ Registry Scraper ===")

    # Option 1: Download bulk data
    print("Downloading bulk CNPJ data...")
    downloaded = download_cnpj_data()

    if downloaded:
        # Filter by target CNAEs
        print("Filtering by target sectors...")
        companies = filter_by_cnae()

        # Save filtered results
        timestamp = datetime.now().strftime("%Y%m%d")
        output_file = OUTPUT_DIR / f"brazil_exporters_cnpj_{timestamp}.json"

        with open(output_file, 'w') as f:
            json.dump(companies[:100000], f, indent=2, ensure_ascii=False)  # Limit size

        print(f"Saved {len(companies)} companies to {output_file}")
    else:
        print("No data downloaded. Use query_cnpj_api() for individual lookups.")

    return companies if downloaded else []

if __name__ == "__main__":
    main()
