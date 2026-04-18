#!/usr/bin/env python3
"""D&B Hoovers Latin America Company Search Scraper"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_dnb")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/html"
}

COUNTRIES = ["Brazil", "Argentina", "Chile", "Uruguay", "Paraguay"]

INDUSTRIES = [
    "Agriculture", "Mining", "Food Processing", "Beverages",
    "Chemicals", "Machinery", "Textiles", "Metal Products"
]

def search_dnb(country: str, industry: str) -> list:
    """Search D&B free company search"""
    companies = []

    # D&B public search endpoint
    search_url = "https://www.dnb.com/business-directory/company-search.html"

    params = {
        "country": country,
        "industry": industry,
        "page": 1
    }

    try:
        # Note: Full D&B data requires subscription
        # This scrapes the free search results
        resp = requests.get(search_url, params=params, headers=HEADERS, timeout=30)

        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.company-result, .search-result, .business-card'):
                company = {
                    "name": "",
                    "country": country,
                    "industry": industry,
                    "city": "",
                    "duns": "",
                    "employees": "",
                    "revenue": "",
                    "website": "",
                    "source": "D&B Hoovers"
                }

                name_el = item.select_one('h3, h4, .company-name')
                if name_el:
                    company["name"] = name_el.get_text(strip=True)

                city_el = item.select_one('.location, .city')
                if city_el:
                    company["city"] = city_el.get_text(strip=True)

                duns_el = item.select_one('[data-duns], .duns')
                if duns_el:
                    company["duns"] = duns_el.get('data-duns', duns_el.get_text(strip=True))

                emp_el = item.select_one('.employees, .emp-count')
                if emp_el:
                    company["employees"] = emp_el.get_text(strip=True)

                if company["name"]:
                    companies.append(company)

    except Exception as e:
        print(f"Error searching D&B: {e}")

    return companies

def scrape_dnb_directory() -> list:
    """Scrape D&B business directory listings"""
    companies = []

    for country in COUNTRIES:
        print(f"Searching {country}...")
        for industry in INDUSTRIES:
            results = search_dnb(country, industry)
            companies.extend(results)
            print(f"  {industry}: {len(results)} companies")
            time.sleep(1)

    return companies

def main():
    print("=== D&B Hoovers Latin America Scraper ===")
    companies = scrape_dnb_directory()

    # Deduplicate
    seen = set()
    unique = []
    for c in companies:
        key = c.get("duns") or (c.get("name", "").lower() + c.get("country", ""))
        if key and key not in seen:
            seen.add(key)
            unique.append(c)

    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"dnb_latam_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(unique)} companies to {output_file}")
    return unique

if __name__ == "__main__":
    main()
