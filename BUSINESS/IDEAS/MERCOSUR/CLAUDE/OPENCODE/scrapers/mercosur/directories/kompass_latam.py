#!/usr/bin/env python3
"""Kompass Latin America B2B Directory Scraper"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_kompass")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml"
}

COUNTRIES = {
    "br": "Brazil",
    "ar": "Argentina",
    "cl": "Chile",
    "uy": "Uruguay",
    "py": "Paraguay",
    "pe": "Peru",
    "co": "Colombia"
}

SECTORS = [
    "food-products", "beverages", "mining", "chemicals",
    "machinery", "agriculture", "textiles", "metals"
]

def scrape_kompass_country(country_code: str, sector: str) -> list:
    """Scrape Kompass directory for a country and sector"""
    companies = []

    base_url = f"https://{country_code}.kompass.com"
    search_url = f"{base_url}/searchCompanies/ss/{sector}/cid/0/page/1"

    try:
        page = 1
        while page <= 50:  # Max 50 pages
            url = f"{base_url}/searchCompanies/ss/{sector}/cid/0/page/{page}"
            resp = requests.get(url, headers=HEADERS, timeout=30)

            if resp.status_code != 200:
                break

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            items = soup.select('.company-item, .search-result-item, .companyCard')
            if not items:
                break

            for item in items:
                company = {
                    "name": "",
                    "country": COUNTRIES.get(country_code, country_code),
                    "city": "",
                    "sector": sector,
                    "activities": [],
                    "website": "",
                    "phone": "",
                    "employees": "",
                    "source": "Kompass"
                }

                # Extract name
                name_el = item.select_one('h2, h3, .company-name, .companyName')
                if name_el:
                    company["name"] = name_el.get_text(strip=True)

                # Extract city
                city_el = item.select_one('.city, .location, .address')
                if city_el:
                    company["city"] = city_el.get_text(strip=True)

                # Extract activities
                activities = item.select('.activity, .sector-tag, .nace')
                company["activities"] = [a.get_text(strip=True) for a in activities]

                # Extract website
                web_el = item.select_one('a[href*="http"]:not([href*="kompass"])')
                if web_el:
                    company["website"] = web_el.get('href', '')

                # Extract phone
                phone_el = item.select_one('.phone, [data-phone]')
                if phone_el:
                    company["phone"] = phone_el.get('data-phone', phone_el.get_text(strip=True))

                if company["name"]:
                    companies.append(company)

            page += 1
            time.sleep(1)

    except Exception as e:
        print(f"Error scraping {country_code}/{sector}: {e}")

    return companies

def main():
    print("=== Kompass Latin America Scraper ===")
    all_companies = []

    for country_code in COUNTRIES.keys():
        print(f"Scraping {COUNTRIES[country_code]}...")
        for sector in SECTORS:
            results = scrape_kompass_country(country_code, sector)
            all_companies.extend(results)
            print(f"  {sector}: {len(results)} companies")

    # Deduplicate
    seen = set()
    unique = []
    for c in all_companies:
        key = c.get("name", "").lower() + c.get("country", "")
        if key and key not in seen:
            seen.add(key)
            unique.append(c)

    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"kompass_latam_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(unique)} companies to {output_file}")
    return unique

if __name__ == "__main__":
    main()
