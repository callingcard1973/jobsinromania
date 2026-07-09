#!/usr/bin/env python3
"""ConnectAmericas B2B Directory Scraper - IDB Platform"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_connectamericas")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json"
}

COUNTRIES = ["BR", "AR", "CL", "UY", "PY", "BO", "PE", "CO", "EC"]

SECTORS = [
    "Food & Beverages", "Agriculture", "Mining", "Manufacturing",
    "Chemicals", "Textiles", "Machinery", "Technology", "Services"
]

def scrape_connectamericas(country: str, sector: str = None) -> list:
    """Scrape ConnectAmericas company directory"""
    companies = []

    # ConnectAmericas API endpoints
    search_url = "https://connectamericas.com/api/v1/companies/search"

    try:
        params = {
            "country": country,
            "sector": sector,
            "page": 1,
            "per_page": 100,
            "type": "exporter"
        }

        while True:
            resp = requests.get(search_url, params=params, headers=HEADERS, timeout=30)
            if resp.status_code != 200:
                break

            data = resp.json()
            results = data.get("companies", data.get("results", []))

            if not results:
                break

            for item in results:
                company = {
                    "name": item.get("name", item.get("company_name", "")),
                    "country_code": country,
                    "country": item.get("country_name", ""),
                    "city": item.get("city", ""),
                    "sector": item.get("sector", sector),
                    "subsector": item.get("subsector", ""),
                    "description": item.get("description", ""),
                    "employees": item.get("employees", ""),
                    "year_founded": item.get("year_founded", ""),
                    "export_experience": item.get("export_experience", ""),
                    "products": item.get("products", []),
                    "certifications": item.get("certifications", []),
                    "website": item.get("website", ""),
                    "profile_url": f"https://connectamericas.com/company/{item.get('id', '')}",
                    "source": "ConnectAmericas"
                }
                companies.append(company)

            params["page"] += 1
            time.sleep(0.5)

            if len(results) < 100:
                break

    except Exception as e:
        print(f"API error for {country}/{sector}: {e}")

    return companies

def scrape_brazilian_catalog() -> list:
    """Scrape Brazilian Exporters Catalog specifically"""
    companies = []
    url = "https://connectamericas.com/content/brazilian-exporters-catalog"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.company-item, .catalog-entry, tr.exporter'):
                company = {
                    "name": item.select_one('.name, h3, td:first-child').get_text(strip=True) if item.select_one('.name, h3, td:first-child') else "",
                    "country": "Brazil",
                    "sector": item.select_one('.sector').get_text(strip=True) if item.select_one('.sector') else "",
                    "source": "ConnectAmericas Brazilian Catalog"
                }
                if company["name"]:
                    companies.append(company)
    except Exception as e:
        print(f"Catalog error: {e}")

    return companies

def main():
    print("=== ConnectAmericas Directory Scraper ===")
    all_companies = []

    # Scrape by country and sector
    for country in COUNTRIES:
        print(f"Scraping country: {country}")
        for sector in SECTORS:
            results = scrape_connectamericas(country, sector)
            all_companies.extend(results)
            print(f"  {sector}: {len(results)} companies")

    # Also get Brazilian catalog
    print("Scraping Brazilian Exporters Catalog...")
    catalog = scrape_brazilian_catalog()
    all_companies.extend(catalog)

    # Deduplicate
    seen = set()
    unique = []
    for c in all_companies:
        key = c.get("name", "").lower() + c.get("country_code", "")
        if key and key not in seen:
            seen.add(key)
            unique.append(c)

    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"connectamericas_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(unique)} companies to {output_file}")
    return unique

if __name__ == "__main__":
    main()
