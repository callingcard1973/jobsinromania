#!/usr/bin/env python3
"""IBRAM - Brazilian Mining Association Scraper"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_mining_associations")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml"
}

def scrape_ibram() -> list:
    """Scrape IBRAM member companies"""
    companies = []

    url = "https://ibram.org.br/associados"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.associado, .member-card, .company'):
                company = {
                    "name": "",
                    "country": "Brazil",
                    "sector": "Mining",
                    "subsector": "",
                    "minerals": [],
                    "state": "",
                    "website": "",
                    "email": "",
                    "source": "IBRAM"
                }

                name_el = item.select_one('h3, h4, .name, .company-name')
                if name_el:
                    company["name"] = name_el.get_text(strip=True)

                subsector = item.select_one('.subsector, .segment')
                if subsector:
                    company["subsector"] = subsector.get_text(strip=True)

                minerals = item.select('.mineral, .product')
                company["minerals"] = [m.get_text(strip=True) for m in minerals]

                website = item.select_one('a[href*="http"]:not([href*="ibram"])')
                if website:
                    company["website"] = website.get('href', '')

                if company["name"]:
                    companies.append(company)

    except Exception as e:
        print(f"Error scraping IBRAM: {e}")

    return companies

def scrape_adimb() -> list:
    """Scrape ADIMB (Mining Development Association) members"""
    companies = []

    try:
        url = "https://www.adimb.com.br/associados"
        resp = requests.get(url, headers=HEADERS, timeout=30)

        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.associado, .company'):
                company = {
                    "name": item.select_one('h3, .name').get_text(strip=True) if item.select_one('h3, .name') else "",
                    "country": "Brazil",
                    "sector": "Mining",
                    "source": "ADIMB"
                }
                if company["name"]:
                    companies.append(company)

    except Exception as e:
        print(f"ADIMB error: {e}")

    return companies

def main():
    print("=== IBRAM Mining Association Scraper ===")

    companies = scrape_ibram()
    companies.extend(scrape_adimb())

    # Deduplicate
    seen = set()
    unique = []
    for c in companies:
        key = c.get("name", "").lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(c)

    output = {
        "association": "IBRAM - Brazilian Mining Association",
        "website": "https://ibram.org.br",
        "members": unique,
        "scraped_at": datetime.now().isoformat()
    }

    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"ibram_members_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(unique)} companies to {output_file}")
    return unique

if __name__ == "__main__":
    main()
