#!/usr/bin/env python3
"""Mass scraper - hit all known exporter directories and extract companies"""

import json
import re
import time
import requests
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_mass")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

# URLs to scrape - directories, associations, government portals
TARGETS = {
    # BRAZIL
    "abiec_beef": "https://www.abiec.com.br/en/associated-companies/",
    "abiove_soy": "https://abiove.org.br/en/associated-companies/",
    "abpa_poultry": "https://abpa-br.org/associados/",
    "abiquim_chemicals": "https://abiquim.org.br/associados",
    "abal_aluminum": "https://abal.org.br/associados/",
    "ibram_mining": "https://ibram.org.br/associados/",
    "abrafrigo_meat": "https://abrafrigo.com.br/associados/",
    "abras_retail": "https://www.abras.com.br/associados",
    "apex_brasil": "https://portal.apexbrasil.com.br/empresas-exportadoras/",
    "brazil_wine": "https://www.ibravin.org.br/Vinícolas",
    "cecafe_coffee": "https://www.cecafe.com.br/en/about-us/associates/",
    "citrusbr_orange": "https://www.citrusbr.com/en/about-citrusbr/",
    "unica_sugar": "https://unica.com.br/en/about-unica/",

    # ARGENTINA
    "wines_argentina": "https://www.winesofargentina.org/en/wineries/",
    "wines_arg_alt": "https://www.argentina.gob.ar/economia/comercioexterior",
    "ipcva_beef": "https://www.ipcva.com.ar/frigorifico/",
    "camara_comercio": "https://www.cac.com.ar/socios",
    "came_pymes": "https://www.redcame.org.ar/afiliados",
    "uia_industry": "https://www.uia.org.ar/empresas-asociadas/",

    # CHILE
    "prochile": "https://www.prochile.gob.cl/difusion/directorio-exportadores/",
    "wines_chile": "https://www.winesofchile.org/en/wineries/",
    "sofofa": "https://www.sofofa.cl/empresas-asociadas/",
    "salmon_chile": "https://www.salmonchile.cl/en/associated-companies/",
    "fedefruta": "https://fedefruta.cl/socios/",
    "asoex_fruit": "https://www.asoex.cl/empresas-asociadas.html",
    "chilealimentos": "https://www.chilealimentos.com/empresas/",

    # URUGUAY
    "uruguay_xxi": "https://www.uruguayxxi.gub.uy/es/exportar/directorio-de-exportadores/",
    "ciu_industry": "https://www.ciu.com.uy/empresas/",
    "inac_meat": "https://www.inac.uy/plantas-habilitadas/",
    "conaprole": "https://www.conaprole.com.uy/empresas/",

    # PARAGUAY
    "rediex": "https://www.rediex.gov.py/directorio-de-exportadores/",
    "uip_industry": "https://www.uip.org.py/asociados/",
    "capeco_grains": "https://capeco.org.py/socios/",
}

def extract_companies(url, name):
    """Extract company names and emails from a page"""
    companies = []

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        if resp.status_code != 200:
            return companies, f"HTTP {resp.status_code}"

        soup = BeautifulSoup(resp.text, 'html.parser')
        text = soup.get_text()

        # Extract emails
        emails = EMAIL_RE.findall(text)
        emails = [e for e in emails if not any(x in e.lower() for x in ['example', 'test', '.png', '.jpg'])]

        # Try to find company containers
        selectors = [
            '.company', '.empresa', '.associado', '.member', '.partner',
            '.winery', '.bodega', '.exportador', '.socio', '.afiliado',
            'article', '.card', '.item', '.list-item', '[class*="company"]',
            '[class*="member"]', '[class*="partner"]', 'li.item'
        ]

        for sel in selectors:
            items = soup.select(sel)
            if items and len(items) < 500:  # Reasonable number
                for item in items:
                    # Get company name
                    name_el = item.select_one('h2, h3, h4, .name, .title, .company-name, strong, a')
                    if name_el:
                        company_name = name_el.get_text(strip=True)
                        if len(company_name) > 2 and len(company_name) < 100:
                            company = {"name": company_name, "source": name}

                            # Try to get email from item
                            item_text = item.get_text()
                            item_emails = EMAIL_RE.findall(item_text)
                            if item_emails:
                                company["email"] = item_emails[0]

                            # Try to get website
                            link = item.select_one('a[href*="http"]')
                            if link and 'mailto' not in link.get('href', ''):
                                href = link.get('href')
                                if href and not any(x in href for x in ['facebook', 'twitter', 'linkedin', 'instagram']):
                                    company["website"] = href

                            companies.append(company)

                if companies:
                    break

        # If no companies found but we have emails, create entries
        if not companies and emails:
            for email in emails[:20]:
                domain = email.split('@')[1]
                companies.append({
                    "name": domain.replace('.com', '').replace('.br', '').replace('.ar', '').title(),
                    "email": email,
                    "source": name
                })

        return companies, "OK"

    except Exception as e:
        return companies, str(e)[:50]

def main():
    print("=== MASS SCRAPER ===\n")

    all_companies = []
    results = {}

    print(f"Scraping {len(TARGETS)} targets...\n")

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(extract_companies, url, name): name for name, url in TARGETS.items()}

        for future in as_completed(futures):
            name = futures[future]
            companies, status = future.result()
            results[name] = {"count": len(companies), "status": status}
            all_companies.extend(companies)

            print(f"{name:25} | {len(companies):4} companies | {status}")

    # Deduplicate
    seen = set()
    unique = []
    for c in all_companies:
        key = c.get("name", "").lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(c)

    print(f"\n=== RESULTS ===")
    print(f"Total raw: {len(all_companies)}")
    print(f"Unique: {len(unique)}")
    print(f"With email: {sum(1 for c in unique if c.get('email'))}")

    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    output_file = OUTPUT_DIR / f"mass_scraped_{timestamp}.json"
    with open(output_file, 'w') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {output_file}")

    # Save CSV
    import csv
    csv_file = OUTPUT_DIR / f"mass_scraped_{timestamp}.csv"
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'email', 'website', 'source'], extrasaction='ignore')
        writer.writeheader()
        writer.writerows(unique)
    print(f"Saved: {csv_file}")

    return unique

if __name__ == "__main__":
    main()
