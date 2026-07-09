#!/usr/bin/env python3
"""Enrich known Brazil exporters - 219 companies"""
import subprocess
import json
import time
import csv
import os
from datetime import datetime

OUTPUT = "/opt/ACTIVE/IDEAS/MERCOSUR/TOTAL_SCRAPER/data/brazil/brazil_exporters_enriched.csv"
DATA_DIR = "/opt/ACTIVE/IDEAS/MERCOSUR/TOTAL_SCRAPER/data/brazil"

# Known major exporters with their CNPJs (manually verified)
KNOWN_CNPJS = {
    "JBS S.A.": "02916265000160",
    "BRF S.A.": "01838723000227",
    "Marfrig Global Foods": "03853896000169",
    "Minerva Foods": "67620377000174",
    "Vale S.A.": "33592510000154",
    "Petrobras": "33000167000101",
    "Suzano": "16404287000155",
    "Klabin": "89637490000145",
    "Embraer": "07689002000189",
    "WEG": "84429695000111",
    "Gerdau": "33611500000119",
    "Usiminas": "60894730000105",
    "CSN": "33042730000104",
    "Braskem": "42150391000170",
    "Ambev": "07526557000100",
    "Cargill Brasil": "60498706000114",
    "Bunge Brasil": "84046101000357",
    "ADM Brasil": "02003402000140",
    "Louis Dreyfus": "47067525000160",
    "Amaggi": "77294254000300",
    "Citrosuco": "55555792000107",
    "Cutrale": "55115507000120",
    "Raizen": "08070508001570",
    "Copersucar": "11742455000107",
    "Tereos": "01685326000137",
    "Illy Brasil": "61099008000170",
    "Ipanema Coffees": "17174549000160",
    "Cooxupe": "20696418000181",
    "Aurora Alimentos": "83310441000117",
    "Friboi": "02916265000160",  # Same as JBS
    "Sadia": "01838723000308",
    "Perdigao": "01838723000308",
    "Seara": "02916265004207",
    "3tentos": "94813102000108",
    "Jalles Machado": "01536594000166",
    "Cocamar": "79114450000163",
    "Coamo": "75904383000128",
    "Caramuru": "00080671000111",
    "Fibria": "60643228000121",
    "Eldorado Brasil": "07401436000164",
    "CMPC": "92823068000163",
}

def fetch_cnpj(cnpj):
    """Fetch from ReceitaWS API"""
    url = f"https://receitaws.com.br/v1/cnpj/{cnpj}"
    try:
        result = subprocess.run(
            f'curl -sL --max-time 25 "{url}"',
            shell=True, capture_output=True, text=True, timeout=30
        )
        if result.stdout:
            if "Too many requests" in result.stdout:
                return "RATE_LIMITED"
            data = json.loads(result.stdout)
            if data.get('status') == 'OK':
                return data
    except:
        pass
    return None

def to_ascii(text):
    if not text:
        return ""
    import unicodedata
    return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii')

def main():
    print("=" * 60)
    print("BRAZIL EXPORTERS ENRICHMENT")
    print(f"Output: {OUTPUT}")
    print("=" * 60)

    # Load exporters from JSON files
    exporters = {}

    # From brazil_producers
    try:
        with open(f"{DATA_DIR}/brazil_producers_20260322.json") as f:
            for c in json.load(f):
                name = c.get('name', '')
                if name:
                    exporters[name] = {'sector': c.get('sector', ''), 'source': 'producers'}
    except: pass

    # From brazil_exporters
    try:
        with open(f"{DATA_DIR}/brazil_exporters_20260321.json") as f:
            for c in json.load(f):
                name = c.get('name', '')
                if name and name not in exporters:
                    exporters[name] = {
                        'sector': c.get('sector', ''),
                        'website': c.get('website', ''),
                        'city': c.get('city', ''),
                        'source': 'exporters'
                    }
    except: pass

    print(f"Loaded {len(exporters)} unique exporters")
    print(f"Known CNPJs: {len(KNOWN_CNPJS)}")
    print("-" * 60)

    rows = []
    enriched = 0
    failed = 0

    # Process exporters with known CNPJs first
    for name, cnpj in KNOWN_CNPJS.items():
        print(f"[{enriched+failed+1:3d}] {name[:45]}...", end=" ", flush=True)

        data = fetch_cnpj(cnpj)

        if data == "RATE_LIMITED":
            print("RATE LIMITED - waiting 60s")
            time.sleep(60)
            data = fetch_cnpj(cnpj)

        if data and data != "RATE_LIMITED":
            email = data.get('email', '')
            phone = data.get('telefone', '')
            domain = email.split('@')[1] if '@' in email else ''

            info = exporters.get(name, {})
            row = {
                'name': to_ascii(data.get('nome', name)),
                'cnpj': data.get('cnpj', cnpj),
                'email': email.lower() if email else '',
                'phone': phone,
                'domain': domain,
                'city': to_ascii(data.get('municipio', info.get('city', ''))),
                'state': data.get('uf', ''),
                'sector': info.get('sector', ''),
                'website': info.get('website', ''),
                'status': data.get('situacao', ''),
                'activity': to_ascii(data.get('atividade_principal', [{}])[0].get('text', ''))[:80],
                'capital': data.get('capital_social', ''),
            }
            rows.append(row)
            enriched += 1
            print(f"OK - {email or 'no email'}")
        else:
            failed += 1
            print("FAILED")

        time.sleep(21)

    # Save CSV
    if rows:
        with open(OUTPUT, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

        print("=" * 60)
        print(f"COMPLETE")
        print(f"Enriched: {enriched}")
        print(f"Failed: {failed}")
        print(f"Output: {OUTPUT}")

        # Domain stats
        domains = {}
        for r in rows:
            d = r.get('domain', '')
            if d:
                domains[d] = domains.get(d, 0) + 1

        print("\nDOMAINS:")
        for d, c in sorted(domains.items(), key=lambda x: -x[1])[:20]:
            print(f"  {d}: {c}")

        # With email count
        with_email = sum(1 for r in rows if r.get('email'))
        print(f"\nWith email: {with_email}/{len(rows)}")

if __name__ == "__main__":
    main()
