#!/usr/bin/env python3
"""
CNPJ corectate pentru companiile mari braziliene
Surse: web search + CNPJA API verification
"""

import requests
import csv
import time
import sys
from pathlib import Path

API_URL = "https://open.cnpja.com/office/{cnpj}"
OUTPUT_DIR = Path('/opt/ACTIVE/IDEAS/MERCOSUR/VENTAS_EN_EUROPA')

# CNPJ-uri CORECTE (matrice/sede, nu filiale)
# Format: 'company': ('cnpj_clean', 'website')
COMPANIES = {
    # Carne
    'JBS S.A.': ('02916265000160', 'jbs.com.br'),
    'BRF S.A.': ('01838723000127', 'brf.com'),  # CORECT: 0001-27, nu 0002-27
    'Marfrig Global Foods': ('03853896000140', 'marfrig.com.br'),  # CORECT: 0001-40
    'Minerva Foods': ('67620377000114', 'minervafoods.com'),
    'Frigol': ('52289700000170', 'frigol.com.br'),
    'Masterboi': ('07273193000145', 'masterboi.com.br'),

    # Mining
    'Vale S.A.': ('33592510000154', 'vale.com'),
    'CBMM': ('33131541000108', 'cbmm.com'),  # CORECT: alt CNPJ
    'CSN': ('33042730000104', 'csn.com.br'),
    'Samarco': ('16628281000161', 'samarco.com'),

    # Petroleo
    'Petrobras': ('33000167000101', 'petrobras.com.br'),
    'Raizen': ('33453598000123', 'raizen.com.br'),

    # Siderurgia
    'Gerdau S.A.': ('33611500000119', 'gerdau.com'),
    'Usiminas': ('60894730000105', 'usiminas.com'),
    'ArcelorMittal Brasil': ('17469701000177', 'arcelormittal.com.br'),

    # Celulose/Papel
    'Suzano': ('16404287000155', 'suzano.com.br'),
    'Klabin': ('89637490000145', 'klabin.com.br'),
    'Eldorado Brasil': ('07401436000114', 'eldoradobrasil.com.br'),

    # Agronegocio
    'Cargill Brasil': ('60498706000157', 'cargill.com.br'),  # CORECT: 0001-57
    'Bunge Brasil': ('84046101000193', 'bunge.com.br'),  # CORECT: 0001-93
    'ADM do Brasil': ('02003402000175', 'adm.com'),  # CORECT: 0001-75
    'Citrosuco': ('33010786000187', 'citrosuco.com.br'),  # CORECT
    'Cooxupe': ('20770566000100', 'cooxupe.com.br'),  # CORECT
    'Louis Dreyfus Brasil': ('47067525000102', 'ldc.com'),
    'Amaggi': ('77294254000300', 'amaggi.com.br'),
    'SLC Agricola': ('89096457000155', 'slcagricola.com.br'),

    # Quimice
    'Braskem': ('42150391000170', 'braskem.com.br'),
    'Unipar': ('33958695000178', 'unipar.com'),

    # Aerospace/Auto
    'Embraer': ('07689002000189', 'embraer.com'),
    'WEG S.A.': ('84429695000111', 'weg.net'),
    'Randon': ('89086144000116', 'randon.com.br'),
    'Tupy S.A.': ('84683374000194', 'tupy.com.br'),

    # Aluminio
    'CBA': ('61409892000173', 'cba.com.br'),
    'Alcoa Brasil': ('23637697000101', 'alcoa.com'),  # CORECT: 0001-01

    # Niobio
    'CMOC Brasil (Niobras)': ('17469625000164', 'cmocgroup.com'),
    'Mineracao Taboca': ('04223072000146', 'mineracaotaboca.com.br'),

    # Acucar/Etanol
    'Copersucar': ('13720936000161', 'copersucar.com.br'),
    'Sao Martinho': ('51466860000156', 'saomartinho.com.br'),
    'Tereos Brasil': ('60843514000130', 'tereos.com'),
    'Biosev': ('23010756000178', 'biosev.com'),
}

def fetch_cnpj(cnpj):
    """Fetch company data from CNPJA API"""
    url = API_URL.format(cnpj=cnpj)
    try:
        resp = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        if resp.status_code == 200:
            data = resp.json()
            emails = data.get('emails', [])
            phones = data.get('phones', [])
            return {
                'status': 'OK',
                'razao_social': data.get('company', {}).get('name', ''),
                'email': emails[0].get('address', '') if emails else '',
                'phone': f"+55{phones[0].get('area', '')}{phones[0].get('number', '')}" if phones else '',
                'city': data.get('address', {}).get('city', ''),
                'state': data.get('address', {}).get('state', ''),
                'situacao': data.get('status', {}).get('text', ''),
            }
        elif resp.status_code == 429:
            print("  Rate limited, waiting 60s...")
            time.sleep(60)
            return fetch_cnpj(cnpj)
        else:
            return {'status': f'HTTP {resp.status_code}'}
    except Exception as e:
        return {'status': str(e)}

def main():
    print("=== CNPJA ENRICHMENT - COMPANIILE MARI BRAZILIENE ===\n")
    print(f"Total companii: {len(COMPANIES)}\n")

    results = []
    batch_count = 0

    for i, (company, (cnpj, website)) in enumerate(COMPANIES.items()):
        print(f"[{i+1}/{len(COMPANIES)}] {company}...", end=" ", flush=True)

        data = fetch_cnpj(cnpj)

        result = {
            'company': company,
            'cnpj': cnpj,
            'website': website,
            'razao_social': data.get('razao_social', ''),
            'email': data.get('email', ''),
            'phone': data.get('phone', ''),
            'city': data.get('city', ''),
            'state': data.get('state', ''),
            'situacao': data.get('situacao', ''),
            'status': data.get('status', 'OK'),
        }
        results.append(result)

        if data.get('email'):
            print(f"OK {data['email']}")
        else:
            print(data.get('status', 'no email'))

        batch_count += 1
        # Rate limit: 5 requests/minute
        if batch_count < 5:
            time.sleep(2)  # 2s between requests
        else:
            batch_count = 0
            if i + 1 < len(COMPANIES):
                print("  [Waiting 60s for rate limit...]")
                time.sleep(60)

    # Save results
    output = OUTPUT_DIR / 'brazil_major_companies_enriched.csv'
    fieldnames = ['company', 'cnpj', 'website', 'razao_social', 'email', 'phone', 'city', 'state', 'situacao', 'status']

    with open(output, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    # Stats
    with_email = sum(1 for r in results if r.get('email'))
    with_phone = sum(1 for r in results if r.get('phone'))
    ok_status = sum(1 for r in results if r.get('status') == 'OK')

    print(f"\n=== REZULTAT ===")
    print(f"Total: {len(results)}")
    print(f"Cu email: {with_email}")
    print(f"Cu telefon: {with_phone}")
    print(f"Status OK: {ok_status}")
    print(f"Fisier: {output}")

if __name__ == '__main__':
    main()
