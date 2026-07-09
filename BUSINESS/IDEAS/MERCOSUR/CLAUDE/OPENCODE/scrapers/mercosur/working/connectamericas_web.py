#!/usr/bin/env python3
"""ConnectAmericas Web Scraper - Working Version"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_connectamericas")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}

def scrape_brazilian_catalog() -> list:
    """Scrape Brazilian Exporters Catalog from ConnectAmericas"""
    companies = []

    url = "https://connectamericas.com/content/brazilian-exporters-catalog"

    try:
        print(f"Fetching {url}...")
        resp = requests.get(url, headers=HEADERS, timeout=30)
        print(f"Status: {resp.status_code}")

        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            # Try multiple selectors
            selectors = [
                '.company-item', '.catalog-entry', '.exporter',
                'tr.exporter', '.card', '.list-item', 'article'
            ]

            for selector in selectors:
                items = soup.select(selector)
                if items:
                    print(f"Found {len(items)} items with selector: {selector}")
                    for item in items:
                        text = item.get_text(strip=True)
                        if len(text) > 10:  # Skip empty items
                            company = {
                                "name": text[:200],  # First 200 chars
                                "country": "Brazil",
                                "source": "ConnectAmericas Catalog"
                            }
                            companies.append(company)
                    break

            # If no items found, extract all links
            if not companies:
                print("Trying link extraction...")
                for link in soup.select('a[href*="company"], a[href*="empresa"]'):
                    company = {
                        "name": link.get_text(strip=True),
                        "url": link.get('href', ''),
                        "country": "Brazil",
                        "source": "ConnectAmericas Links"
                    }
                    if company["name"]:
                        companies.append(company)

    except Exception as e:
        print(f"Error: {e}")

    return companies

def scrape_search(query: str) -> list:
    """Search ConnectAmericas"""
    companies = []

    url = f"https://connectamericas.com/search?search={query}"

    try:
        print(f"Searching: {query}")
        resp = requests.get(url, headers=HEADERS, timeout=30)

        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.search-result, .result-item, .company, article'):
                name_el = item.select_one('h2, h3, h4, .title, .name')
                if name_el:
                    company = {
                        "name": name_el.get_text(strip=True),
                        "query": query,
                        "source": "ConnectAmericas Search"
                    }

                    # Try to get country
                    country_el = item.select_one('.country, .location')
                    if country_el:
                        company["country"] = country_el.get_text(strip=True)

                    companies.append(company)

        time.sleep(1)

    except Exception as e:
        print(f"Search error: {e}")

    return companies

def main():
    print("=== ConnectAmericas Web Scraper ===")

    all_companies = []

    # Scrape catalog
    print("\n1. Scraping Brazilian Catalog...")
    catalog = scrape_brazilian_catalog()
    all_companies.extend(catalog)
    print(f"   Found: {len(catalog)} companies")

    # Search by sector
    searches = [
        "lithium brazil", "niobium brazil", "honey argentina",
        "beef exporter brazil", "wine argentina", "mining chile"
    ]

    print("\n2. Running searches...")
    for query in searches:
        results = scrape_search(query)
        all_companies.extend(results)
        print(f"   {query}: {len(results)} results")

    # Deduplicate
    seen = set()
    unique = []
    for c in all_companies:
        key = c.get("name", "").lower()[:50]
        if key and key not in seen:
            seen.add(key)
            unique.append(c)

    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"connectamericas_web_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(unique)} companies to {output_file}")
    return unique

if __name__ == "__main__":
    main()
