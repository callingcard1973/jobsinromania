#!/usr/bin/env python3
"""Wines of Argentina - Wine Exporters Association Scraper"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_wine_associations")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml"
}

def scrape_wines_argentina() -> list:
    """Scrape Wines of Argentina member wineries"""
    companies = []

    url = "https://www.winesofargentina.com/en/wineries"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.winery, .bodega, .company-card'):
                company = {
                    "name": "",
                    "country": "Argentina",
                    "sector": "Wine",
                    "region": "",
                    "province": "",
                    "varietals": [],
                    "website": "",
                    "email": "",
                    "phone": "",
                    "export_markets": [],
                    "certifications": [],
                    "organic": False,
                    "source": "Wines of Argentina"
                }

                name_el = item.select_one('h3, h4, .name, .winery-name')
                if name_el:
                    company["name"] = name_el.get_text(strip=True)

                region = item.select_one('.region')
                if region:
                    company["region"] = region.get_text(strip=True)

                province = item.select_one('.province, .provincia')
                if province:
                    company["province"] = province.get_text(strip=True)

                # Check organic
                if item.select_one('.organic') or 'organic' in item.get_text().lower():
                    company["organic"] = True

                varietals = item.select('.varietal, .grape')
                company["varietals"] = [v.get_text(strip=True) for v in varietals]

                website = item.select_one('a[href*="http"]:not([href*="winesofargentina"])')
                if website:
                    company["website"] = website.get('href', '')

                email = item.select_one('a[href^="mailto:"]')
                if email:
                    company["email"] = email['href'].replace('mailto:', '')

                if company["name"]:
                    companies.append(company)

    except Exception as e:
        print(f"Error scraping Wines of Argentina: {e}")

    return companies

def scrape_coviar() -> list:
    """Scrape COVIAR (Argentine Wine Corporation) data"""
    companies = []

    try:
        url = "https://www.argentina.gob.ar/agricultura/alimentos-y-bioeconomia/vitivinicultura"
        resp = requests.get(url, headers=HEADERS, timeout=30)

        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.bodega, .exporter'):
                company = {
                    "name": item.select_one('h3, .name').get_text(strip=True) if item.select_one('h3, .name') else "",
                    "country": "Argentina",
                    "sector": "Wine",
                    "source": "COVIAR"
                }
                if company["name"]:
                    companies.append(company)

    except Exception as e:
        print(f"COVIAR error: {e}")

    return companies

def main():
    print("=== Wines of Argentina Scraper ===")

    companies = scrape_wines_argentina()
    companies.extend(scrape_coviar())

    # Deduplicate
    seen = set()
    unique = []
    for c in companies:
        key = c.get("name", "").lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(c)

    output = {
        "association": "Wines of Argentina",
        "website": "https://www.winesofargentina.com",
        "members": unique,
        "scraped_at": datetime.now().isoformat()
    }

    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"wines_argentina_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(unique)} companies to {output_file}")
    return unique

if __name__ == "__main__":
    main()
