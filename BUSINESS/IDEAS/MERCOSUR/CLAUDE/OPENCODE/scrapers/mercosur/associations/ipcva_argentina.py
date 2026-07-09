#!/usr/bin/env python3
"""IPCVA - Argentine Beef Promotion Institute Scraper"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_beef_associations")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml"
}

def scrape_ipcva() -> list:
    """Scrape IPCVA member/exporter companies"""
    companies = []

    # IPCVA exporters directory
    url = "https://www.ipcva.com.ar/exportadores"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.exporter, .company-card, .frigorifico'):
                company = {
                    "name": "",
                    "country": "Argentina",
                    "sector": "Beef",
                    "type": "Exporter",
                    "province": "",
                    "city": "",
                    "cuit": "",
                    "website": "",
                    "email": "",
                    "phone": "",
                    "certifications": [],
                    "hilton_quota": False,
                    "eu_approved": False,
                    "source": "IPCVA"
                }

                name_el = item.select_one('h3, h4, .name')
                if name_el:
                    company["name"] = name_el.get_text(strip=True)

                # Check for Hilton quota
                if item.select_one('.hilton, [data-hilton]') or 'hilton' in item.get_text().lower():
                    company["hilton_quota"] = True

                # Check EU approval
                if item.select_one('.eu, .ue, [data-eu]'):
                    company["eu_approved"] = True

                province = item.select_one('.province, .provincia')
                if province:
                    company["province"] = province.get_text(strip=True)

                city = item.select_one('.city, .localidad')
                if city:
                    company["city"] = city.get_text(strip=True)

                website = item.select_one('a[href*="http"]:not([href*="ipcva"])')
                if website:
                    company["website"] = website.get('href', '')

                email = item.select_one('a[href^="mailto:"]')
                if email:
                    company["email"] = email['href'].replace('mailto:', '')

                if company["name"]:
                    companies.append(company)

    except Exception as e:
        print(f"Error scraping IPCVA: {e}")

    # Also try getting from SENASA approved list
    companies.extend(scrape_senasa_approved())

    return companies

def scrape_senasa_approved() -> list:
    """Get SENASA EU-approved establishments"""
    companies = []

    try:
        url = "https://www.argentina.gob.ar/senasa/establecimientos-habilitados-ue"
        resp = requests.get(url, headers=HEADERS, timeout=30)

        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for row in soup.select('table tr'):
                cells = row.select('td')
                if len(cells) >= 3:
                    company = {
                        "name": cells[0].get_text(strip=True),
                        "senasa_number": cells[1].get_text(strip=True) if len(cells) > 1 else "",
                        "province": cells[2].get_text(strip=True) if len(cells) > 2 else "",
                        "country": "Argentina",
                        "sector": "Beef",
                        "eu_approved": True,
                        "source": "SENASA"
                    }
                    if company["name"]:
                        companies.append(company)

    except Exception as e:
        print(f"SENASA error: {e}")

    return companies

def main():
    print("=== IPCVA Argentina Beef Exporters Scraper ===")

    companies = scrape_ipcva()

    # Deduplicate
    seen = set()
    unique = []
    for c in companies:
        key = c.get("name", "").lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(c)

    output = {
        "association": "IPCVA - Instituto Promocion Carne Vacuna Argentina",
        "website": "https://www.ipcva.com.ar",
        "members": unique,
        "scraped_at": datetime.now().isoformat()
    }

    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"ipcva_members_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(unique)} companies to {output_file}")
    return unique

if __name__ == "__main__":
    main()
