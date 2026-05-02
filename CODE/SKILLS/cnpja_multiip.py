#!/usr/bin/env python3
"""
CNPJA Multi-IP Enrichment - Rate limit bypass cu proxy rotation
Foloseste proxy-uri gratuite sau Tor pentru IP-uri diferite

Usage:
  python3 cnpja_multiip.py --cnpj 33000167000101
  python3 cnpja_multiip.py --file companii.csv --cnpj-col cui
  python3 cnpja_multiip.py --test-proxies
"""

import argparse
import csv
import json
import os
import random
import requests
import sys
import time
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# API
API_URL = "https://open.cnpja.com/office/{cnpj}"

# Proxy sources - free rotating proxies
PROXY_SOURCES = [
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
]

# Proxy cache file
PROXY_CACHE = Path('/tmp/cnpja_proxies.json')
PROXY_CACHE_AGE = 3600  # 1 hour

# Output
OUTPUT_DIR = Path('/opt/ACTIVE/IDEAS/MERCOSUR/VENTAS_EN_EUROPA')


def get_proxies():
    """Get working proxies from cache or fetch new"""
    # Check cache
    if PROXY_CACHE.exists():
        cache_age = time.time() - PROXY_CACHE.stat().st_mtime
        if cache_age < PROXY_CACHE_AGE:
            with open(PROXY_CACHE) as f:
                data = json.load(f)
                if data.get('proxies'):
                    print(f"  Using {len(data['proxies'])} cached proxies")
                    return data['proxies']

    print("  Fetching fresh proxies...")
    proxies = set()

    for source in PROXY_SOURCES:
        try:
            resp = requests.get(source, timeout=10)
            if resp.status_code == 200:
                lines = resp.text.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if ':' in line and len(line) < 50:
                        proxies.add(f"http://{line}")
        except:
            continue

    proxies = list(proxies)
    print(f"  Found {len(proxies)} proxies")

    # Test and keep only working ones (sample)
    if len(proxies) > 50:
        sample = random.sample(proxies, 50)
        working = []
        print("  Testing proxies...")
        for p in sample[:20]:
            if test_proxy(p):
                working.append(p)
                if len(working) >= 5:
                    break

        if working:
            # Save to cache
            with open(PROXY_CACHE, 'w') as f:
                json.dump({'proxies': working, 'timestamp': time.time()}, f)
            print(f"  {len(working)} working proxies cached")
            return working

    return [None]  # Direct connection fallback


def test_proxy(proxy, timeout=5):
    """Test if proxy works"""
    try:
        resp = requests.get(
            "https://httpbin.org/ip",
            proxies={'http': proxy, 'https': proxy},
            timeout=timeout
        )
        return resp.status_code == 200
    except:
        return False


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


def fetch_cnpj(cnpj, proxy=None, retries=3):
    """Fetch company data by CNPJ with retry logic"""
    cnpj_clean = ''.join(filter(str.isdigit, str(cnpj)))
    if len(cnpj_clean) != 14:
        return {'error': f'Invalid CNPJ: {cnpj}'}

    url = API_URL.format(cnpj=cnpj_clean)

    for attempt in range(retries):
        try:
            session = get_session(proxy)
            resp = session.get(url, timeout=15)

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
                    'situacao': data.get('status', {}).get('text', ''),
                    'cnae_principal': data.get('mainActivity', {}).get('text', ''),
                }
            elif resp.status_code == 429:
                # Rate limited - switch proxy
                return {'error': 'Rate limited', 'retry': True}
            elif resp.status_code == 400:
                return {'error': 'Invalid CNPJ (400)'}
            else:
                return {'error': f'HTTP {resp.status_code}'}

        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            return {'error': str(e)}

    return {'error': 'Max retries'}


def format_phone(phones):
    """Format phone numbers"""
    if not phones:
        return ''
    phone = phones[0]
    return f"+55{phone.get('area', '')}{phone.get('number', '')}"


def enrich_parallel(companies, max_workers=5):
    """Enrich companies in parallel using multiple IPs"""
    print(f"\nEnriching {len(companies)} companies with multi-IP...")

    proxies = get_proxies()
    results = []
    rate_limited = []

    # First pass - parallel with proxies
    def fetch_with_proxy(item):
        company, cnpj, website = item
        proxy = random.choice(proxies) if proxies else None
        data = fetch_cnpj(cnpj, proxy)
        return (company, cnpj, website, data)

    items = [(c, d['cnpj'], d['website']) for c, d in companies.items()]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_with_proxy, item): item for item in items}

        for future in as_completed(futures):
            company, cnpj, website, data = future.result()

            if data.get('retry'):
                rate_limited.append((company, cnpj, website))
                print(f"  ! {company}: Rate limited")
            elif data.get('error'):
                print(f"  x {company}: {data['error']}")
                results.append({
                    'company': company,
                    'cnpj': cnpj,
                    'website': website,
                    'status': data['error']
                })
            else:
                email = data.get('email', '')
                print(f"  v {company}: {email if email else 'no email'}")
                results.append({
                    'company': company,
                    'cnpj': cnpj,
                    'website': website,
                    'razao_social': data.get('razao_social', ''),
                    'email': email,
                    'telefone': data.get('telefone', ''),
                    'cidade': data.get('cidade', ''),
                    'uf': data.get('uf', ''),
                    'situacao': data.get('situacao', ''),
                    'status': 'OK'
                })

            time.sleep(0.5)  # Small delay between requests

    # Retry rate-limited ones with different proxies
    if rate_limited:
        print(f"\nRetrying {len(rate_limited)} rate-limited companies...")
        time.sleep(60)  # Wait for rate limit reset

        # Refresh proxies
        if PROXY_CACHE.exists():
            PROXY_CACHE.unlink()
        proxies = get_proxies()

        for company, cnpj, website in rate_limited:
            proxy = random.choice(proxies) if proxies else None
            data = fetch_cnpj(cnpj, proxy)

            if data.get('error'):
                results.append({
                    'company': company,
                    'cnpj': cnpj,
                    'website': website,
                    'status': data.get('error', 'Failed')
                })
            else:
                results.append({
                    'company': company,
                    'cnpj': cnpj,
                    'website': website,
                    'razao_social': data.get('razao_social', ''),
                    'email': data.get('email', ''),
                    'telefone': data.get('telefone', ''),
                    'cidade': data.get('cidade', ''),
                    'uf': data.get('uf', ''),
                    'situacao': data.get('situacao', ''),
                    'status': 'OK'
                })

            time.sleep(2)

    return results


def single_lookup(cnpj):
    """Single CNPJ lookup"""
    proxies = get_proxies()
    proxy = random.choice(proxies) if proxies else None

    print(f"Looking up CNPJ: {cnpj}")
    print(f"Using proxy: {proxy or 'direct'}")

    data = fetch_cnpj(cnpj, proxy)

    if data.get('error'):
        print(f"Error: {data['error']}")
        return

    print(f"\n{'='*50}")
    print(f"CNPJ: {data['cnpj']}")
    print(f"Razao Social: {data['razao_social']}")
    print(f"Nome Fantasia: {data['nome_fantasia']}")
    print(f"Email: {data['email']}")
    print(f"Telefone: {data['telefone']}")
    print(f"Cidade/UF: {data['cidade']}/{data['uf']}")
    print(f"Situacao: {data['situacao']}")
    print(f"CNAE: {data['cnae_principal']}")
    print(f"{'='*50}")


def test_proxies_cmd():
    """Test proxy functionality"""
    print("Testing proxy acquisition and connectivity...\n")

    # Clear cache
    if PROXY_CACHE.exists():
        PROXY_CACHE.unlink()

    proxies = get_proxies()

    if not proxies or proxies == [None]:
        print("WARNING: No working proxies found, will use direct connection")
        return

    print(f"\nTesting {len(proxies)} proxies against CNPJA API...")

    for i, proxy in enumerate(proxies[:5]):
        print(f"\n[{i+1}] Testing {proxy}...")
        try:
            # Get our IP through proxy
            resp = requests.get(
                "https://httpbin.org/ip",
                proxies={'http': proxy, 'https': proxy},
                timeout=10
            )
            if resp.status_code == 200:
                ip = resp.json().get('origin', 'unknown')
                print(f"    IP: {ip}")

                # Test CNPJA
                test_cnpj = "33000167000101"  # Petrobras
                data = fetch_cnpj(test_cnpj, proxy)
                if data.get('error'):
                    print(f"    CNPJA: FAILED - {data['error']}")
                else:
                    print(f"    CNPJA: OK - {data.get('razao_social', '')[:40]}")
            else:
                print(f"    FAILED: HTTP {resp.status_code}")
        except Exception as e:
            print(f"    FAILED: {e}")


def main():
    parser = argparse.ArgumentParser(description='CNPJA Multi-IP Enrichment')
    parser.add_argument('--cnpj', help='Single CNPJ lookup')
    parser.add_argument('--file', help='CSV file to enrich')
    parser.add_argument('--cnpj-col', default='cnpj', help='Column name for CNPJ')
    parser.add_argument('--output', help='Output file')
    parser.add_argument('--test-proxies', action='store_true', help='Test proxy functionality')
    parser.add_argument('--workers', type=int, default=5, help='Parallel workers')

    args = parser.parse_args()

    if args.test_proxies:
        test_proxies_cmd()
    elif args.cnpj:
        single_lookup(args.cnpj)
    elif args.file:
        # TODO: implement file enrichment
        print("File enrichment not yet implemented")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
