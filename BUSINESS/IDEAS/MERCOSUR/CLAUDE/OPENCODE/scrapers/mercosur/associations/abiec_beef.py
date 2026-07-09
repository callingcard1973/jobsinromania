#!/usr/bin/env python3
"""ABIEC - Brazilian Beef Exporters Association Scraper"""

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

def scrape_abiec() -> list:
    """Scrape ABIEC member companies"""
    companies = []

    # ABIEC members page
    url = "https://www.abiec.com.br/associados"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.associado, .member-card, .company-item'):
                company = {
                    "name": "",
                    "country": "Brazil",
                    "sector": "Beef",
                    "type": "Exporter",
                    "city": "",
                    "state": "",
                    "website": "",
                    "email": "",
                    "phone": "",
                    "certifications": [],
                    "eu_approved": False,
                    "source": "ABIEC"
                }

                name_el = item.select_one('h3, h4, .name, .company-name')
                if name_el:
                    company["name"] = name_el.get_text(strip=True)

                # Check for EU approval badge
                if item.select_one('.eu-approved, .sif-eu, [data-eu="true"]'):
                    company["eu_approved"] = True

                location = item.select_one('.location, .city, .address')
                if location:
                    loc_text = location.get_text(strip=True)
                    parts = loc_text.split(',')
                    if len(parts) >= 2:
                        company["city"] = parts[0].strip()
                        company["state"] = parts[-1].strip()

                website = item.select_one('a[href*="http"]:not([href*="abiec"])')
                if website:
                    company["website"] = website.get('href', '')

                email = item.select_one('a[href^="mailto:"]')
                if email:
                    company["email"] = email['href'].replace('mailto:', '')

                certs = item.select('.certification, .cert-badge')
                company["certifications"] = [c.get_text(strip=True) for c in certs]

                if company["name"]:
                    companies.append(company)

    except Exception as e:
        print(f"Error scraping ABIEC: {e}")

    return companies

def scrape_abiec_statistics() -> dict:
    """Get ABIEC export statistics"""
    stats = {}

    try:
        url = "https://www.abiec.com.br/estatisticas"
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            # Extract key stats
            for stat in soup.select('.stat-item, .statistic'):
                label = stat.select_one('.label, .stat-label')
                value = stat.select_one('.value, .stat-value')
                if label and value:
                    stats[label.get_text(strip=True)] = value.get_text(strip=True)

    except Exception as e:
        print(f"Error getting stats: {e}")

    return stats

def main():
    print("=== ABIEC Beef Exporters Scraper ===")

    companies = scrape_abiec()
    stats = scrape_abiec_statistics()

    output = {
        "association": "ABIEC - Brazilian Beef Exporters Association",
        "website": "https://www.abiec.com.br",
        "members": companies,
        "statistics": stats,
        "scraped_at": datetime.now().isoformat()
    }

    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"abiec_members_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(companies)} companies to {output_file}")
    return companies

if __name__ == "__main__":
    main()
