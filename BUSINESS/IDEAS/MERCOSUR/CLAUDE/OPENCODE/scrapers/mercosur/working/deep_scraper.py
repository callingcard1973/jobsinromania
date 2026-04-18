#!/usr/bin/env python3
"""Deep scraper - scrape working sites thoroughly"""

import json
import re
import time
import requests
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_deep")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

def scrape_abpa():
    """ABPA - Brazilian Poultry Association"""
    print("\n=== ABPA Poultry ===")
    companies = []
    url = "https://abpa-br.org/associados/"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')

        for item in soup.select('.associado, .member, article, .card'):
            name = item.select_one('h2, h3, h4, .title, strong')
            if name:
                company = {"name": name.get_text(strip=True), "sector": "poultry", "country": "Brazil"}
                link = item.select_one('a[href*="http"]')
                if link:
                    company["website"] = link.get('href')
                companies.append(company)

        # Also get from main text
        for text in soup.stripped_strings:
            if any(x in text.lower() for x in ['s.a.', 'ltda', 'foods', 'alimentos']):
                if 3 < len(text) < 80:
                    companies.append({"name": text, "sector": "poultry", "country": "Brazil"})

    except Exception as e:
        print(f"Error: {e}")

    print(f"Found: {len(companies)}")
    return companies

def scrape_capeco():
    """CAPECO - Paraguay Grain Chamber"""
    print("\n=== CAPECO Grains ===")
    companies = []
    url = "https://capeco.org.py/socios/"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')

        for item in soup.select('.socio, .member, .card, article, li'):
            name = item.select_one('h2, h3, h4, .name, strong, a')
            if name:
                text = name.get_text(strip=True)
                if 3 < len(text) < 80:
                    company = {"name": text, "sector": "grains", "country": "Paraguay"}
                    companies.append(company)

        # Extract from page text
        text = soup.get_text()
        for line in text.split('\n'):
            line = line.strip()
            if any(x in line.lower() for x in ['s.a.', 's.r.l.', 'cargill', 'bunge', 'adm', 'louis dreyfus']):
                if 5 < len(line) < 60:
                    companies.append({"name": line, "sector": "grains", "country": "Paraguay"})

    except Exception as e:
        print(f"Error: {e}")

    print(f"Found: {len(companies)}")
    return companies

def scrape_uruguay_xxi():
    """Uruguay XXI - Investment Agency"""
    print("\n=== Uruguay XXI ===")
    companies = []

    urls = [
        "https://www.uruguayxxi.gub.uy/es/exportar/directorio-de-exportadores/",
        "https://www.uruguayxxi.gub.uy/es/quiero-exportar/",
        "https://www.uruguayxxi.gub.uy/es/casos-de-exito/"
    ]

    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.empresa, .company, .card, article'):
                name = item.select_one('h2, h3, h4, .name, .title')
                if name:
                    text = name.get_text(strip=True)
                    if 3 < len(text) < 80:
                        company = {"name": text, "country": "Uruguay"}
                        link = item.select_one('a[href*="http"]')
                        if link:
                            company["website"] = link.get('href')
                        companies.append(company)

        except Exception as e:
            print(f"Error {url}: {e}")

    print(f"Found: {len(companies)}")
    return companies

def scrape_argentina_export():
    """Argentina export directories"""
    print("\n=== Argentina Export ===")
    companies = []

    urls = [
        "https://www.argentina.gob.ar/produccion/industria/exportar",
        "https://www.exportargentina.org.ar/empresas/",
        "https://www.argentina.gob.ar/desarrolloproductivo/trade"
    ]

    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.empresa, .company, article, .item'):
                name = item.select_one('h2, h3, h4, .name, .title, a')
                if name:
                    text = name.get_text(strip=True)
                    if 3 < len(text) < 80 and not text.startswith('http'):
                        company = {"name": text, "country": "Argentina"}
                        companies.append(company)

        except Exception as e:
            print(f"Error {url}: {e}")

    print(f"Found: {len(companies)}")
    return companies

def scrape_chile_export():
    """Chile ProChile directory"""
    print("\n=== Chile ProChile ===")
    companies = []

    urls = [
        "https://www.prochile.gob.cl/landing/directorio-exportadores/",
        "https://www.direcon.gob.cl/exportadores/",
        "https://www.subrei.gob.cl/exportadores"
    ]

    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.empresa, .exportador, .company, article'):
                name = item.select_one('h2, h3, h4, .name, .title')
                if name:
                    text = name.get_text(strip=True)
                    if 3 < len(text) < 80:
                        company = {"name": text, "country": "Chile"}
                        companies.append(company)

        except Exception as e:
            print(f"Error {url}: {e}")

    print(f"Found: {len(companies)}")
    return companies

def scrape_brazil_apex():
    """APEX Brasil - Export Agency"""
    print("\n=== APEX Brasil ===")
    companies = []

    urls = [
        "https://portal.apexbrasil.com.br/",
        "https://www.apexbrasil.com.br/cases-de-sucesso",
        "https://www.investexportbrasil.gov.br/empresas"
    ]

    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, 'html.parser')
            text = soup.get_text()

            # Extract company names from text
            for line in text.split('\n'):
                line = line.strip()
                if any(x in line for x in ['S.A.', 'S/A', 'LTDA', 'Ltda']):
                    if 5 < len(line) < 60:
                        companies.append({"name": line, "country": "Brazil"})

            # From cards/items
            for item in soup.select('.case, .empresa, article, .card'):
                name = item.select_one('h2, h3, h4, .title')
                if name:
                    text = name.get_text(strip=True)
                    if 3 < len(text) < 80:
                        companies.append({"name": text, "country": "Brazil"})

        except Exception as e:
            print(f"Error {url}: {e}")

    print(f"Found: {len(companies)}")
    return companies

def scrape_beef_associations():
    """Beef industry associations"""
    print("\n=== Beef Associations ===")
    companies = []

    # ABIEC members page (if working)
    urls = [
        ("https://www.abiec.com.br/associados/", "Brazil"),
        ("https://www.ipcva.com.ar/exportadores/", "Argentina"),
        ("https://www.inac.uy/innovaportal/v/19929/13/innova.front/plantas-de-faena-habilitadas", "Uruguay"),
    ]

    for url, country in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, 'html.parser')

            for item in soup.select('.member, .associado, .empresa, .planta, tr, article'):
                name = item.select_one('h2, h3, h4, td, .name, strong')
                if name:
                    text = name.get_text(strip=True)
                    if 3 < len(text) < 80 and any(x in text.lower() for x in ['frigo', 'meat', 'beef', 'carne', 'brf', 'jbs', 'marfrig']):
                        companies.append({"name": text, "sector": "beef", "country": country})

        except Exception as e:
            print(f"Error {url}: {e}")

    print(f"Found: {len(companies)}")
    return companies

def main():
    print("=== DEEP SCRAPER ===")

    all_companies = []

    # Run all scrapers
    all_companies.extend(scrape_abpa())
    all_companies.extend(scrape_capeco())
    all_companies.extend(scrape_uruguay_xxi())
    all_companies.extend(scrape_argentina_export())
    all_companies.extend(scrape_chile_export())
    all_companies.extend(scrape_brazil_apex())
    all_companies.extend(scrape_beef_associations())

    # Deduplicate
    seen = set()
    unique = []
    for c in all_companies:
        key = c.get("name", "").lower().strip()
        if key and len(key) > 3 and key not in seen:
            seen.add(key)
            unique.append(c)

    print(f"\n=== TOTAL ===")
    print(f"Raw: {len(all_companies)}")
    print(f"Unique: {len(unique)}")

    # By country
    countries = {}
    for c in unique:
        country = c.get("country", "Unknown")
        countries[country] = countries.get(country, 0) + 1
    for country, count in sorted(countries.items(), key=lambda x: -x[1]):
        print(f"  {country}: {count}")

    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_file = OUTPUT_DIR / f"deep_scraped_{timestamp}.json"
    with open(output_file, 'w') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {output_file}")

    return unique

if __name__ == "__main__":
    main()
