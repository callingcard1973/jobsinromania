#!/usr/bin/env python3
"""
CNPJA Enrichment Skill
Îmbogățire companii braziliene cu date de la CNPJA API
Suport pentru multiple IP-uri prin proxy

Utilizare:
  python3 cnpja_enrich.py --cnpj 33000167000101
  python3 cnpja_enrich.py --file companii.csv --cnpj-col cui
  python3 cnpja_enrich.py --search "JBS"
"""

import argparse
import csv
import json
import os
import random
import requests
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# API
API_BASE = "https://open.cnpja.com"
API_OFFICE = f"{API_BASE}/office/{{cnpj}}"

# Proxy list - adaugă proxy-uri aici
PROXIES = [
    None,  # Direct connection
    # 'http://proxy1:port',
    # 'http://proxy2:port',
    # 'socks5://proxy3:port',
]

# Rate limiting
RATE_LIMIT = 5  # requests per minute
DELAY = 60 / RATE_LIMIT + 1  # ~13 seconds

# Output
OUTPUT_DIR = Path('/opt/ACTIVE/IDEAS/MERCOSUR/VENTAS_EN_EUROPA')

def get_session(proxy=None):
    """Create session with optional proxy"""
    session = requests.Session()
    session.headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
    }
    if proxy:
        session.proxies = {'http': proxy, 'https': proxy}
    return session

def fetch_cnpj(cnpj, proxy=None):
    """Fetch company data by CNPJ"""
    cnpj_clean = ''.join(filter(str.isdigit, str(cnpj)))
    if len(cnpj_clean) != 14:
        return {'error': f'Invalid CNPJ: {cnpj}'}
    
    url = API_OFFICE.format(cnpj=cnpj_clean)
    session = get_session(proxy)
    
    try:
        resp = session.get(url, timeout=30)
        
        if resp.status_code == 200:
            data = resp.json()
            return {
                'cnpj': cnpj_clean,
                'razao_social': data.get('company', {}).get('name', ''),
                'nome_fantasia': data.get('alias', ''),
                'email': data.get('emails', [{}])[0].get('address', '') if data.get('emails') else '',
                'telefone': format_phone(data.get('phones', [])),
                'cidade': data.get('address', {}).get('city', ''),
                'uf': data.get('address', {}).get('state', ''),
                'cep': data.get('address', {}).get('zip', ''),
                'endereco': format_address(data.get('address', {})),
                'situacao': data.get('status', {}).get('text', ''),
                'cnae_principal': data.get('mainActivity', {}).get('text', ''),
                'data_abertura': data.get('founded', ''),
                'raw': data,
            }
        elif resp.status_code == 429:
            return {'error': 'Rate limited', 'retry': True}
        else:
            return {'error': f'HTTP {resp.status_code}'}
            
    except requests.exceptions.RequestException as e:
        return {'error': str(e)}

def format_phone(phones):
    """Format phone numbers"""
    if not phones:
        return ''
    phone = phones[0]
    return f"+55{phone.get('area', '')}{phone.get('number', '')}"

def format_address(addr):
    """Format address"""
    if not addr:
        return ''
    parts = [
        addr.get('street', ''),
        addr.get('number', ''),
        addr.get('details', ''),
        addr.get('district', ''),
    ]
    return ', '.join(p for p in parts if p)

def enrich_file(input_file, cnpj_col='cnpj', output_file=None):
    """Enrich CSV file with CNPJA data"""
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"Error: File not found: {input_file}")
        return
    
    output_path = output_file or OUTPUT_DIR / f"{input_path.stem}_enriched.csv"
    
    # Read input
    with open(input_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames
    
    # Add new fields
    new_fields = ['cnpja_email', 'cnpja_telefone', 'cnpja_cidade', 'cnpja_uf', 'cnpja_situacao']
    all_fields = fieldnames + new_fields
    
    print(f"Processing {len(rows)} rows...")
    
    results = []
    for i, row in enumerate(rows):
        cnpj = row.get(cnpj_col, '')
        if not cnpj:
            results.append(row)
            continue
        
        print(f"  [{i+1}/{len(rows)}] {cnpj}...", end=" ", flush=True)
        
        # Rotate proxies
        proxy = random.choice(PROXIES)
        data = fetch_cnpj(cnpj, proxy)
        
        if data.get('retry'):
            print("Rate limited, waiting 60s...")
            time.sleep(60)
            data = fetch_cnpj(cnpj, proxy)
        
        if 'error' not in data:
            row['cnpja_email'] = data.get('email', '')
            row['cnpja_telefone'] = data.get('telefone', '')
            row['cnpja_cidade'] = data.get('cidade', '')
            row['cnpja_uf'] = data.get('uf', '')
            row['cnpja_situacao'] = data.get('situacao', '')
            print(f"✓ {data.get('email', 'no email')}")
        else:
            print(f"✗ {data['error']}")
        
        results.append(row)
        time.sleep(DELAY)
    
    # Write output
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=all_fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(results)
    
    print(f"\nSaved to: {output_path}")

def single_lookup(cnpj):
    """Single CNPJ lookup"""
    print(f"Looking up CNPJ: {cnpj}")
    data = fetch_cnpj(cnpj)
    
    if 'error' in data:
        print(f"Error: {data['error']}")
        return
    
    print(f"\n{'='*50}")
    print(f"CNPJ: {data['cnpj']}")
    print(f"Razão Social: {data['razao_social']}")
    print(f"Nome Fantasia: {data['nome_fantasia']}")
    print(f"Email: {data['email']}")
    print(f"Telefone: {data['telefone']}")
    print(f"Cidade/UF: {data['cidade']}/{data['uf']}")
    print(f"Situação: {data['situacao']}")
    print(f"CNAE: {data['cnae_principal']}")
    print(f"{'='*50}")

def main():
    parser = argparse.ArgumentParser(description='CNPJA Enrichment Skill')
    parser.add_argument('--cnpj', help='Single CNPJ lookup')
    parser.add_argument('--file', help='CSV file to enrich')
    parser.add_argument('--cnpj-col', default='cnpj', help='Column name for CNPJ')
    parser.add_argument('--output', help='Output file')
    parser.add_argument('--proxy', help='Proxy to use (http://host:port)')
    
    args = parser.parse_args()
    
    if args.proxy:
        PROXIES.append(args.proxy)
    
    if args.cnpj:
        single_lookup(args.cnpj)
    elif args.file:
        enrich_file(args.file, args.cnpj_col, args.output)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
