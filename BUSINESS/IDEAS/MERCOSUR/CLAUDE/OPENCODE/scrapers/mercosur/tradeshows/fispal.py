#!/usr/bin/env python3
"""Fispal Food Service & Fispal Tecnologia Exhibitors Scraper"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_tradeshows")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml"
}

FISPAL_EVENTS = [
    ("https://www.fispal.com.br/fispal-food-service/expositores", "Fispal Food Service"),
    ("https://www.fispal.com.br/fispal-tecnologia/expositores", "Fispal Tecnologia"),
]

def scrape_fispal_exhibitors(url: str, event_name: str) -> list:
    """Scrape Fispal exhibitor list"""
    companies = []

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.expositor, .exhibitor, .empresa'):
                company = {
                    "name": "",
                    "booth": "",
                    "sector": "",
                    "products": [],
                    "website": "",
                    "email": "",
                    "country": "Brazil",
                    "event": event_name,
                    "source": "Fispal 2026"
                }

                name_el = item.select_one('h3, h4, .name')
                if name_el:
                    company["name"] = name_el.get_text(strip=True)

                booth = item.select_one('.booth, .stand')
                if booth:
                    company["booth"] = booth.get_text(strip=True)

                sector = item.select_one('.sector, .segmento')
                if sector:
                    company["sector"] = sector.get_text(strip=True)

                website = item.select_one('a[href*="http"]:not([href*="fispal"])')
                if website:
                    company["website"] = website.get('href', '')

                email = item.select_one('a[href^="mailto:"]')
                if email:
                    company["email"] = email['href'].replace('mailto:', '')

                if company["name"]:
                    companies.append(company)

    except Exception as e:
        print(f"Error scraping {event_name}: {e}")

    return companies

def main():
    print("=== Fispal Exhibitors Scraper ===")

    all_companies = []

    for url, event_name in FISPAL_EVENTS:
        print(f"Scraping {event_name}...")
        companies = scrape_fispal_exhibitors(url, event_name)
        all_companies.extend(companies)
        time.sleep(1)

    # Deduplicate
    seen = set()
    unique = []
    for c in all_companies:
        key = c.get("name", "").lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(c)

    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"fispal_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(unique)} exhibitors to {output_file}")
    return unique

if __name__ == "__main__":
    main()
