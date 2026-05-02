#!/usr/bin/env python3
"""
European Government Auctions Downloader

Downloads judicial and government auction data from:
- EU e-Justice Portal (judicial auctions)
- Germany: justiz-auktion.de, zvg-portal.de
- Spain: subastas.boe.es
- Italy: astegiudiziarie.it
- Sweden: Kronofogden
- France: licitor.com
- Netherlands: RVV/Domeinen

Output: /opt/ACTIVE/OPENDATA/DATA/EU_AUCTIONS/
"""

import csv
import json
import os
import requests
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from bs4 import BeautifulSoup

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
try:
    from skills_common import to_ascii
except:
    def to_ascii(text):
        if not text:
            return ""
        return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii').strip()

OUTPUT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/EU_AUCTIONS")

# Auction sources by country
AUCTION_SOURCES = {
    "EU": {
        "name": "EU e-Justice Portal",
        "url": "https://e-justice.europa.eu/473/EN/judicial_auctions",
        "type": "portal",
    },
    "DE": [
        {
            "name": "Justiz Auktion",
            "url": "https://www.justiz-auktion.de",
            "feed": "https://www.justiz-auktion.de/rss/",  # Updated RSS URL
            "type": "rss",
        },
        {
            "name": "ZVG Portal",
            "url": "https://www.zvg-portal.de",
            "search": "https://www.zvg-portal.de/index.php?button=Suchen",
            "type": "scrape",
        },
        {
            "name": "Zoll Auktion",
            "url": "https://www.zoll-auktion.de",
            "type": "scrape",
        },
    ],
    "ES": [
        {
            "name": "Subastas BOE",
            "url": "https://subastas.boe.es",
            "api": "https://subastas.boe.es/subastas_ava.php?accion=Mas",
            "type": "api",
        },
    ],
    "IT": [
        {
            "name": "Aste Giudiziarie",
            "url": "https://www.astegiudiziarie.it",
            "type": "scrape",
        },
        {
            "name": "IVASS Aste",
            "url": "https://www.ivass.it/pubblicazioni-e-statistiche/pubblicazioni/aste/",
            "type": "portal",
        },
    ],
    "SE": [
        {
            "name": "Kronofogden Auktionstorget",
            "url": "https://auktionstorget.kronofogden.se/Auktionstorget.html",
            "type": "scrape",
        },
    ],
    "FR": [
        {
            "name": "Licitor",
            "url": "https://www.licitor.com",
            "type": "scrape",
        },
        {
            "name": "Encheres Publiques",
            "url": "https://www.encheres-publiques.com",
            "type": "scrape",
        },
    ],
    "NL": [
        {
            "name": "Domeinen RVV",
            "url": "https://www.domeinenrvr.nl/aanbod",
            "type": "scrape",
        },
    ],
    "PL": [
        {
            "name": "Licytacje Komornicze",
            "url": "https://licytacje.komornik.pl",
            "type": "scrape",
        },
    ],
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def download_file(url, output_path, chunk_size=8192):
    """Download a file with progress."""
    try:
        print(f"  Downloading: {url[:80]}...")
        response = requests.get(url, stream=True, timeout=300, headers=HEADERS)
        response.raise_for_status()

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)

        print(f"    Saved: {output_path}")
        return True
    except Exception as e:
        print(f"    Error: {e}")
        return False


def fetch_rss(url):
    """Fetch and parse RSS feed."""
    try:
        response = requests.get(url, timeout=60, headers=HEADERS)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        items = []

        for item in root.findall('.//item'):
            entry = {
                'title': to_ascii(item.findtext('title', ''))[:300],
                'link': item.findtext('link', ''),
                'description': to_ascii(item.findtext('description', ''))[:500],
                'date': item.findtext('pubDate', ''),
            }
            items.append(entry)

        return items
    except Exception as e:
        print(f"    RSS Error: {e}")
        return []


def scrape_page(url):
    """Generic page scraper."""
    try:
        response = requests.get(url, timeout=60, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        return soup
    except Exception as e:
        print(f"    Scrape Error: {e}")
        return None


def download_germany_auctions():
    """Download German auction data."""
    de_dir = OUTPUT_DIR / "DE"
    de_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" GERMANY AUCTIONS")
    print("="*60)

    auctions = []

    # 1. Justiz Auktion (scrape beliebte-auktionen page)
    print("\n  Justiz Auktion (beliebte-auktionen)...")
    soup = scrape_page("https://www.justiz-auktion.de/beliebte-auktionen")
    if soup:
        # Find auction links with title="Zur Auktion"
        auction_links = soup.find_all('a', title='Zur Auktion')
        seen = set()
        for link in auction_links:
            href = link.get('href', '')
            if href and href not in seen and not href.startswith('http'):
                seen.add(href)
                title = href.replace('-', ' ').rsplit(' ', 1)[0]  # Remove ID from end
                auctions.append({
                    'source': 'justiz-auktion.de',
                    'country': 'DE',
                    'title': to_ascii(title)[:200],
                    'url': f"https://www.justiz-auktion.de/{href}",
                    'description': '',
                    'date': datetime.now().strftime('%Y-%m-%d'),
                })
        print(f"    Found: {len(auctions)} auctions")

    # 2. ZVG Portal (foreclosure auctions)
    print("\n  ZVG Portal (scraping)...")
    soup = scrape_page("https://www.zvg-portal.de")
    if soup:
        # Extract auction count/links
        links = soup.find_all('a', href=lambda h: h and 'index.php' in h)
        print(f"    Found: {len(links)} links")

    # 3. Zoll Auktion (customs)
    print("\n  Zoll Auktion (scraping)...")
    soup = scrape_page("https://www.zoll-auktion.de/auktion/index.php")
    if soup:
        articles = soup.find_all('article') or soup.find_all('div', class_='auction')
        print(f"    Found: {len(articles)} items")

    # Save German auctions
    if auctions:
        output_file = de_dir / f"auctions_{datetime.now().strftime('%Y%m%d')}.csv"
        fieldnames = ['source', 'country', 'title', 'url', 'description', 'date']

        with open(output_file, 'w', newline='', encoding='ascii', errors='ignore') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(auctions)

        print(f"\n  Saved: {output_file}")

    return auctions


def download_spain_auctions():
    """Download Spanish auction data from subastas.boe.es."""
    es_dir = OUTPUT_DIR / "ES"
    es_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" SPAIN AUCTIONS (subastas.boe.es)")
    print("="*60)

    auctions = []

    # BOE Subastas has an API
    try:
        # Search for active auctions
        url = "https://subastas.boe.es/subastas_ava.php"
        params = {
            "accion": "Mas",
            "campo[0]": "SUBASTA.ESTADO",
            "dato[0]": "EJ",  # En ejecucion (active)
        }

        response = requests.get(url, params=params, timeout=60, headers=HEADERS)
        if response.ok:
            soup = BeautifulSoup(response.content, 'html.parser')
            rows = soup.find_all('tr', class_='rowClass')

            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 4:
                    auctions.append({
                        'source': 'subastas.boe.es',
                        'country': 'ES',
                        'id': to_ascii(cols[0].get_text(strip=True)),
                        'type': to_ascii(cols[1].get_text(strip=True)),
                        'value': to_ascii(cols[2].get_text(strip=True)),
                        'deadline': to_ascii(cols[3].get_text(strip=True)),
                    })

            print(f"  Found: {len(auctions)} auctions")

    except Exception as e:
        print(f"  Error: {e}")

    # Save
    if auctions:
        output_file = es_dir / f"auctions_{datetime.now().strftime('%Y%m%d')}.csv"
        fieldnames = ['source', 'country', 'id', 'type', 'value', 'deadline']

        with open(output_file, 'w', newline='', encoding='ascii', errors='ignore') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(auctions)

        print(f"  Saved: {output_file}")

    return auctions


def download_sweden_auctions():
    """Download Swedish Kronofogden auctions."""
    se_dir = OUTPUT_DIR / "SE"
    se_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" SWEDEN AUCTIONS (Kronofogden Auktionstorget)")
    print("="*60)

    auctions = []

    # Scrape the auction site
    soup = scrape_page("https://auktionstorget.kronofogden.se/Auktionstorget.html")
    if soup:
        # Look for auction links
        links = soup.find_all('a', href=lambda h: h and 'auction' in h.lower())
        items = soup.find_all('div', class_='auction') or soup.find_all('tr')
        print(f"  Found: {len(links)} links, {len(items)} items")

        # Extract auction info from table rows
        for item in items:
            text = item.get_text(strip=True)
            if 'Auktion' in text or '2026' in text:
                auctions.append({
                    'source': 'auktionstorget.kronofogden.se',
                    'country': 'SE',
                    'title': to_ascii(text[:200]),
                    'date': '',
                })
    else:
        print("  Could not access Auktionstorget")

    # Save
    if auctions:
        output_file = se_dir / f"auctions_{datetime.now().strftime('%Y%m%d')}.csv"
        fieldnames = ['source', 'country', 'id', 'title', 'type', 'location', 'value', 'deadline', 'url']

        with open(output_file, 'w', newline='', encoding='ascii', errors='ignore') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(auctions)

        print(f"  Saved: {output_file}")

    return auctions


def download_france_auctions():
    """Download French auction data."""
    fr_dir = OUTPUT_DIR / "FR"
    fr_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" FRANCE AUCTIONS")
    print("="*60)

    auctions = []

    # 1. Encheres Domaines (government property)
    print("\n  Encheres Domaines...")
    soup = scrape_page("https://encheres-domaines.gouv.fr")
    if soup:
        items = soup.find_all('div', class_='vente') or soup.find_all('article')
        print(f"    Found: {len(items)} items")

    # 2. Licitor (judicial auctions)
    print("\n  Licitor...")
    soup = scrape_page("https://www.licitor.com/ventes")
    if soup:
        items = soup.find_all('div', class_='vente-item') or soup.find_all('article')
        print(f"    Found: {len(items)} items")

    print(f"\n  Total: {len(auctions)} auctions")
    return auctions


def download_italy_auctions():
    """Download Italian auction data."""
    it_dir = OUTPUT_DIR / "IT"
    it_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" ITALY AUCTIONS")
    print("="*60)

    auctions = []

    # Aste Giudiziarie
    print("\n  Aste Giudiziarie...")
    soup = scrape_page("https://www.astegiudiziarie.it")
    if soup:
        items = soup.find_all('div', class_='asta') or soup.find_all('article')
        print(f"    Found: {len(items)} items")

    print(f"\n  Total: {len(auctions)} auctions")
    return auctions


def download_all():
    """Download all European auction data."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    log_file = OUTPUT_DIR / "download.log"
    with open(log_file, "w") as f:
        f.write(f"Auctions Download Started: {datetime.now()}\n\n")

    # Download by country
    download_germany_auctions()
    download_spain_auctions()
    download_sweden_auctions()
    download_france_auctions()
    download_italy_auctions()

    with open(log_file, "a") as f:
        f.write(f"\nDownload Completed: {datetime.now()}\n")

    print("\n" + "="*60)
    print(" DOWNLOAD COMPLETE")
    print("="*60)
    print(f"\n  Output: {OUTPUT_DIR}")

    return True


def status():
    """Check download status."""
    print("\n" + "="*60)
    print(" AUCTIONS DOWNLOAD STATUS")
    print("="*60)

    if OUTPUT_DIR.exists():
        for country_dir in sorted(OUTPUT_DIR.iterdir()):
            if country_dir.is_dir():
                files = list(country_dir.glob("*.csv"))
                total_rows = 0
                for f in files:
                    try:
                        with open(f, 'r') as csv_file:
                            total_rows += sum(1 for _ in csv_file) - 1
                    except:
                        pass
                print(f"\n  {country_dir.name}: {len(files)} files, ~{total_rows} auctions")
    else:
        print(f"\n  Directory not found: {OUTPUT_DIR}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="European Auctions Downloader")
    parser.add_argument("--all", action="store_true", help="Download all sources")
    parser.add_argument("--de", action="store_true", help="Download Germany auctions")
    parser.add_argument("--es", action="store_true", help="Download Spain auctions")
    parser.add_argument("--se", action="store_true", help="Download Sweden auctions")
    parser.add_argument("--fr", action="store_true", help="Download France auctions")
    parser.add_argument("--it", action="store_true", help="Download Italy auctions")
    parser.add_argument("--status", action="store_true", help="Check download status")
    args = parser.parse_args()

    if args.status:
        status()
    elif args.all:
        download_all()
    elif args.de:
        download_germany_auctions()
    elif args.es:
        download_spain_auctions()
    elif args.se:
        download_sweden_auctions()
    elif args.fr:
        download_france_auctions()
    elif args.it:
        download_italy_auctions()
    else:
        parser.print_help()
