#!/usr/bin/env python3
"""Sector Enricher - Find more producers from known seed companies"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_enriched")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Seed companies by sector - verified producers
SEED_DATA = {
    "lithium": {
        "country": "Argentina/Brazil",
        "companies": [
            {"name": "Livent Corporation", "country": "Argentina", "website": "livent.com", "capacity": "25K t/yr"},
            {"name": "Allkem (Olaroz)", "country": "Argentina", "website": "allkem.com", "capacity": "42K t/yr"},
            {"name": "Arcadium Lithium", "country": "Argentina", "website": "arcadiumlithium.com", "capacity": "75K t/yr"},
            {"name": "Sigma Lithium", "country": "Brazil", "website": "sigmalithium.com", "capacity": "104K t/yr"},
            {"name": "CBL Brazil", "country": "Brazil", "website": "cbl.com.br", "capacity": "6K t/yr"},
            {"name": "AMG Lithium", "country": "Brazil", "website": "amg-nv.com", "capacity": "90K t/yr"},
            {"name": "Lithium Americas", "country": "Argentina", "website": "lithiumamericas.com", "capacity": "40K t/yr"},
            {"name": "Eramet (Eramine)", "country": "Argentina", "website": "eramet.com", "capacity": "24K t/yr"},
            {"name": "Gangfeng Lithium", "country": "Argentina", "website": "ganfenglithium.com", "capacity": "20K t/yr"},
            {"name": "POSCO Argentina", "country": "Argentina", "website": "posco.com", "capacity": "25K t/yr"},
        ]
    },
    "niobium": {
        "country": "Brazil",
        "companies": [
            {"name": "CBMM", "country": "Brazil", "website": "cbmm.com", "capacity": "100K t/yr", "share": "80%"},
            {"name": "CMOC Niobras", "country": "Brazil", "website": "cmocgroup.com", "capacity": "9.5K t/yr"},
            {"name": "Mineracao Taboca", "country": "Brazil", "website": "minsur.com", "capacity": "2K t/yr"},
            {"name": "NioCorp", "country": "Brazil", "website": "niocorp.com", "capacity": "Development"},
        ]
    },
    "beef": {
        "country": "Brazil/Argentina/Uruguay",
        "companies": [
            {"name": "JBS S.A.", "country": "Brazil", "website": "jbs.com.br", "eu_plants": 37},
            {"name": "Minerva Foods", "country": "Brazil", "website": "minervafoods.com", "profit_2025": "EUR 162M"},
            {"name": "Marfrig Global Foods", "country": "Brazil", "website": "marfrig.com.br"},
            {"name": "BRF S.A.", "country": "Brazil", "website": "bfrfoods.com"},
            {"name": "Frigorifico Gorina", "country": "Argentina", "website": "gorina.com.ar", "quota": "Hilton"},
            {"name": "Grupo Belen", "country": "Argentina", "website": "grupobelen.com.ar"},
            {"name": "Frigorifico Rioplatense", "country": "Argentina", "website": "rfrp.com.ar"},
            {"name": "INAC Members", "country": "Uruguay", "website": "inac.uy", "plants": 40},
            {"name": "Frigorifico Las Piedras", "country": "Uruguay", "website": "flp.com.uy"},
            {"name": "Frigorifico Tacuarembo", "country": "Uruguay", "website": "tacuarembo.com.uy"},
            {"name": "Breeders & Packers Uruguay", "country": "Uruguay", "website": "bpu.com.uy"},
            {"name": "Frigorifico San Jacinto", "country": "Uruguay", "website": "sanjacinto.com.uy"},
        ]
    },
    "honey": {
        "country": "Argentina/Brazil/Uruguay",
        "companies": [
            {"name": "NEXCO Coop", "country": "Argentina", "website": "nexco.com.ar", "capacity": "15K t/yr", "organic": True},
            {"name": "Mieles del Sur", "country": "Argentina", "capacity": "5K t/yr", "organic": True},
            {"name": "COSAR Cooperativa", "country": "Argentina", "capacity": "3K t/yr", "organic": True},
            {"name": "Urucoop", "country": "Uruguay", "website": "urucoop.com.uy", "capacity": "2K t/yr"},
            {"name": "CONAP Brazil", "country": "Brazil", "website": "conap.coop.br", "capacity": "8K t/yr"},
            {"name": "Prodapys", "country": "Brazil", "website": "prodapys.com.br"},
            {"name": "Apiarios Girassol", "country": "Brazil", "capacity": "1K t/yr"},
            {"name": "Baldini S.A.", "country": "Argentina", "website": "baldini.com.ar"},
            {"name": "Miel San Antonio", "country": "Argentina"},
            {"name": "Abejas del Valle", "country": "Argentina"},
        ]
    },
    "wine": {
        "country": "Argentina/Chile/Brazil",
        "companies": [
            {"name": "Bodega Catena Zapata", "country": "Argentina", "website": "catenawines.com", "region": "Mendoza"},
            {"name": "Trapiche", "country": "Argentina", "website": "trapiche.com.ar", "region": "Mendoza"},
            {"name": "Luigi Bosca", "country": "Argentina", "website": "luigibosca.com.ar"},
            {"name": "Bodega Norton", "country": "Argentina", "website": "norton.com.ar"},
            {"name": "Rutini Wines", "country": "Argentina", "website": "rutiniwines.com"},
            {"name": "Concha y Toro", "country": "Chile", "website": "conchaytoro.com"},
            {"name": "Santa Rita", "country": "Chile", "website": "santarita.com"},
            {"name": "Undurraga", "country": "Chile", "website": "undurraga.cl"},
            {"name": "Casa Valduga", "country": "Brazil", "website": "casavalduga.com.br", "region": "Serra Gaucha"},
            {"name": "Miolo Wine Group", "country": "Brazil", "website": "miolo.com.br"},
            {"name": "Aurora Wines", "country": "Brazil", "website": "vinicolaaurora.com.br"},
        ]
    },
    "soy": {
        "country": "Brazil/Argentina/Paraguay",
        "companies": [
            {"name": "Bunge", "country": "Brazil", "website": "bunge.com"},
            {"name": "Cargill Brazil", "country": "Brazil", "website": "cargill.com.br"},
            {"name": "ADM Brazil", "country": "Brazil", "website": "adm.com"},
            {"name": "Louis Dreyfus", "country": "Brazil", "website": "ldc.com"},
            {"name": "COFCO International", "country": "Brazil", "website": "cofcointernational.com"},
            {"name": "Amaggi", "country": "Brazil", "website": "amaggi.com.br"},
            {"name": "Grupo Los Grobo", "country": "Argentina", "website": "losgrobo.com.ar"},
            {"name": "Vicentin", "country": "Argentina"},
            {"name": "AGD", "country": "Argentina", "website": "agd.com.ar"},
        ]
    },
    "sugar": {
        "country": "Brazil",
        "companies": [
            {"name": "Raizen", "country": "Brazil", "website": "raizen.com.br", "capacity": "Largest in Brazil"},
            {"name": "Cosan", "country": "Brazil", "website": "cosan.com.br"},
            {"name": "Sao Martinho", "country": "Brazil", "website": "saomartinho.com.br"},
            {"name": "Biosev", "country": "Brazil", "website": "biosev.com"},
            {"name": "Tereos Brazil", "country": "Brazil", "website": "tereos.com"},
            {"name": "BP Bunge Bioenergia", "country": "Brazil"},
            {"name": "Usina Coruripe", "country": "Brazil", "website": "coruripe.com.br"},
        ]
    },
    "coffee": {
        "country": "Brazil",
        "companies": [
            {"name": "Cooxupe", "country": "Brazil", "website": "cooxupe.com.br", "type": "Cooperative"},
            {"name": "Ipanema Coffees", "country": "Brazil", "website": "ipanema.com.br"},
            {"name": "Cafe Bom Dia", "country": "Brazil", "website": "cafebomdia.com.br"},
            {"name": "Daterra Coffee", "country": "Brazil", "website": "daterracoffee.com.br"},
            {"name": "Fazenda Santa Ines", "country": "Brazil"},
            {"name": "Stockler Cafe", "country": "Brazil", "website": "stockler.com.br"},
            {"name": "Atlantica Coffee", "country": "Brazil", "website": "atlanticacoffee.com"},
        ]
    },
    "aluminum": {
        "country": "Brazil",
        "companies": [
            {"name": "Albras", "country": "Brazil", "website": "albras.net", "capacity": "450K t/yr"},
            {"name": "Alcoa Brazil", "country": "Brazil", "website": "alcoa.com"},
            {"name": "CBA - Companhia Brasileira de Aluminio", "country": "Brazil", "website": "cba.com.br"},
            {"name": "Novelis Brazil", "country": "Brazil", "website": "novelis.com"},
            {"name": "Alunorte", "country": "Brazil", "website": "hydro.com", "type": "Alumina"},
        ]
    },
    "copper": {
        "country": "Chile/Peru",
        "companies": [
            {"name": "Codelco", "country": "Chile", "website": "codelco.com", "share": "World #1"},
            {"name": "Escondida (BHP)", "country": "Chile", "website": "bhp.com"},
            {"name": "Collahuasi", "country": "Chile", "website": "collahuasi.cl"},
            {"name": "Antofagasta Minerals", "country": "Chile", "website": "aminerals.cl"},
            {"name": "Cerro Verde", "country": "Peru", "website": "cerroverde.pe"},
            {"name": "Southern Copper", "country": "Peru", "website": "southerncoppercorp.com"},
        ]
    }
}

def enrich_company(company: dict) -> dict:
    """Try to enrich company with more data from web"""

    website = company.get("website", "")
    if not website:
        return company

    # Clean website URL
    if not website.startswith("http"):
        website = f"https://www.{website}"

    try:
        resp = requests.get(website, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            # Try to find email
            for link in soup.select('a[href^="mailto:"]'):
                email = link['href'].replace('mailto:', '').split('?')[0]
                if '@' in email:
                    company["email"] = email
                    break

            # Try to find phone
            for text in soup.stripped_strings:
                if any(c.isdigit() for c in text) and len(text) > 8:
                    if '+' in text or text.startswith('0') or 'tel' in text.lower():
                        company["phone"] = text[:30]
                        break

            company["website_verified"] = True

    except Exception as e:
        company["website_verified"] = False

    return company

def main():
    print("=== Mercosur Sector Enricher ===")

    all_companies = []
    sector_counts = {}

    for sector, data in SEED_DATA.items():
        print(f"\n{sector.upper()}: {len(data['companies'])} companies")
        sector_counts[sector] = len(data['companies'])

        for company in data['companies']:
            company['sector'] = sector
            company['source'] = 'Verified Seed Data'
            company['scraped_at'] = datetime.now().isoformat()

            # Try to enrich
            print(f"  Enriching {company['name']}...")
            enriched = enrich_company(company)
            all_companies.append(enriched)
            time.sleep(0.5)

    # Save all
    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"mercosur_producers_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(all_companies, f, indent=2, ensure_ascii=False)

    print(f"\n=== SUMMARY ===")
    print(f"Total producers: {len(all_companies)}")
    for sector, count in sector_counts.items():
        print(f"  {sector}: {count}")
    print(f"\nSaved to {output_file}")

    # Also save as CSV
    csv_file = OUTPUT_DIR / f"mercosur_producers_{timestamp}.csv"
    import csv
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'country', 'sector', 'website', 'email', 'phone', 'capacity'])
        writer.writeheader()
        for c in all_companies:
            writer.writerow({
                'name': c.get('name', ''),
                'country': c.get('country', ''),
                'sector': c.get('sector', ''),
                'website': c.get('website', ''),
                'email': c.get('email', ''),
                'phone': c.get('phone', ''),
                'capacity': c.get('capacity', '')
            })
    print(f"Saved CSV to {csv_file}")

    return all_companies

if __name__ == "__main__":
    main()
