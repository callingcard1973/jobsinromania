#!/usr/bin/env python3
"""
CNPJA Enrichment cu Tor pentru IP rotation
Schimba IP dupa fiecare 5 cereri pentru a evita rate limiting

Usage:
  python3 cnpja_tor.py --cnpj 33000167000101
  python3 cnpja_tor.py --companies  # Lista predefinita
  python3 cnpja_tor.py --test
"""

import argparse
import csv
import json
import os
import requests
import subprocess
import time
from pathlib import Path

# API
API_URL = "https://open.cnpja.com/office/{cnpj}"

# Tor SOCKS proxy (default port)
TOR_PROXY = "socks5h://127.0.0.1:9050"

# Output
OUTPUT_DIR = Path('/opt/ACTIVE/IDEAS/MERCOSUR/VENTAS_EN_EUROPA')

# Companiile mari braziliene cu CNPJ corect
COMPANIES = {
    'JBS S.A.': ('02916265000160', 'jbs.com.br'),
    'BRF S.A.': ('01838723000127', 'brf.com'),
    'Marfrig Global Foods': ('03853896000140', 'marfrig.com.br'),
    'Minerva Foods': ('67620377000114', 'minervafoods.com'),
    'Vale S.A.': ('33592510000154', 'vale.com'),
    'CBMM': ('33131541000108', 'cbmm.com'),
    'CSN': ('33042730000104', 'csn.com.br'),
    'Samarco': ('16628281000161', 'samarco.com'),
    'Petrobras': ('33000167000101', 'petrobras.com.br'),
    'Raizen': ('33453598000123', 'raizen.com.br'),
    'Gerdau S.A.': ('33611500000119', 'gerdau.com'),
    'Usiminas': ('60894730000105', 'usiminas.com'),
    'ArcelorMittal Brasil': ('17469701000177', 'arcelormittal.com.br'),
    'Suzano': ('16404287000155', 'suzano.com.br'),
    'Klabin': ('89637490000145', 'klabin.com.br'),
    'Cargill Brasil': ('60498706000157', 'cargill.com.br'),
    'Bunge Brasil': ('84046101000193', 'bunge.com.br'),
    'ADM do Brasil': ('02003402000175', 'adm.com'),
    'Citrosuco': ('33010786000187', 'citrosuco.com.br'),
    'Cooxupe': ('20770566000100', 'cooxupe.com.br'),
    'Louis Dreyfus Brasil': ('47067525000102', 'ldc.com'),
    'SLC Agricola': ('89096457000155', 'slcagricola.com.br'),
    'Braskem': ('42150391000170', 'braskem.com.br'),
    'Embraer': ('07689002000189', 'embraer.com'),
    'WEG S.A.': ('84429695000111', 'weg.net'),
    'Randon': ('89086144000116', 'randon.com.br'),
    'Tupy S.A.': ('84683374000194', 'tupy.com.br'),
    'CBA': ('61409892000173', 'cba.com.br'),
    'Alcoa Brasil': ('23637697000101', 'alcoa.com'),
    'Copersucar': ('13720936000161', 'copersucar.com.br'),
    'Sao Martinho': ('51466860000156', 'saomartinho.com.br'),
}


def renew_tor_ip():
    """Get new Tor circuit = new IP"""
    try:
        # Send NEWNYM signal to Tor control port
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(('127.0.0.1', 9051))
            s.send(b'AUTHENTICATE ""\r\n')
            response = s.recv(1024)
            if b'250' in response:
                s.send(b'SIGNAL NEWNYM\r\n')
                response = s.recv(1024)
                if b'250' in response:
                    print("    [New Tor IP]")
                    time.sleep(3)  # Wait for new circuit
                    return True
    except Exception as e:
        # Try alternative: restart tor service
        try:
            subprocess.run(['sudo', 'systemctl', 'reload', 'tor'],
                         capture_output=True, timeout=10)
            time.sleep(5)
            return True
        except:
            pass
    return False


def get_current_ip():
    """Check current IP through Tor"""
    try:
        resp = requests.get(
            'https://httpbin.org/ip',
            proxies={'http': TOR_PROXY, 'https': TOR_PROXY},
            timeout=15
        )
        if resp.status_code == 200:
            return resp.json().get('origin', 'unknown')
    except:
        pass
    return 'unknown'


def fetch_cnpj(cnpj, use_tor=True):
    """Fetch company data from CNPJA API"""
    cnpj_clean = ''.join(filter(str.isdigit, str(cnpj)))
    if len(cnpj_clean) != 14:
        return {'error': f'Invalid CNPJ: {cnpj}'}

    url = API_URL.format(cnpj=cnpj_clean)

    try:
        session = requests.Session()
        session.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
        }

        if use_tor:
            session.proxies = {'http': TOR_PROXY, 'https': TOR_PROXY}

        resp = session.get(url, timeout=30)

        if resp.status_code == 200:
            data = resp.json()
            emails = data.get('emails', [])
            phones = data.get('phones', [])
            return {
                'cnpj': cnpj_clean,
                'razao_social': data.get('company', {}).get('name', ''),
                'email': emails[0].get('address', '') if emails else '',
                'telefone': f"+55{phones[0].get('area', '')}{phones[0].get('number', '')}" if phones else '',
                'cidade': data.get('address', {}).get('city', ''),
                'uf': data.get('address', {}).get('state', ''),
                'situacao': data.get('status', {}).get('text', ''),
                'status': 'OK'
            }
        elif resp.status_code == 429:
            return {'error': 'Rate limited', 'retry': True}
        elif resp.status_code == 400:
            return {'error': 'Invalid CNPJ'}
        else:
            return {'error': f'HTTP {resp.status_code}'}

    except requests.exceptions.RequestException as e:
        return {'error': str(e)}


def enrich_companies():
    """Enrich all companies with Tor IP rotation"""
    print("=== CNPJA ENRICHMENT cu TOR ===\n")

    # Check Tor
    print("Verificare Tor...")
    ip = get_current_ip()
    print(f"  IP curent: {ip}\n")

    results = []
    request_count = 0

    for i, (company, (cnpj, website)) in enumerate(COMPANIES.items()):
        print(f"[{i+1}/{len(COMPANIES)}] {company}...", end=" ", flush=True)

        data = fetch_cnpj(cnpj, use_tor=True)

        if data.get('retry'):
            print("Rate limited, schimb IP...")
            renew_tor_ip()
            time.sleep(5)
            data = fetch_cnpj(cnpj, use_tor=True)

        result = {
            'company': company,
            'cnpj': cnpj,
            'website': website,
            'razao_social': data.get('razao_social', ''),
            'email': data.get('email', ''),
            'telefone': data.get('telefone', ''),
            'cidade': data.get('cidade', ''),
            'uf': data.get('uf', ''),
            'situacao': data.get('situacao', ''),
            'status': data.get('status', data.get('error', 'Failed'))
        }
        results.append(result)

        if data.get('email'):
            print(f"OK {data['email']}")
        elif data.get('error'):
            print(data['error'])
        else:
            print("no email")

        request_count += 1

        # Change IP every 5 requests
        if request_count >= 5:
            renew_tor_ip()
            request_count = 0
        else:
            time.sleep(2)

    # Save results
    output = OUTPUT_DIR / 'brazil_major_tor_enriched.csv'
    fieldnames = ['company', 'cnpj', 'website', 'razao_social', 'email',
                  'telefone', 'cidade', 'uf', 'situacao', 'status']

    with open(output, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    # Stats
    with_email = sum(1 for r in results if r.get('email'))
    ok_status = sum(1 for r in results if r.get('status') == 'OK')

    print(f"\n=== REZULTAT ===")
    print(f"Total: {len(results)}")
    print(f"Cu email: {with_email}")
    print(f"Status OK: {ok_status}")
    print(f"Fisier: {output}")

    return results


def test_tor():
    """Test Tor connectivity"""
    print("=== TEST TOR ===\n")

    print("1. Verificare Tor proxy...")
    ip1 = get_current_ip()
    print(f"   IP: {ip1}")

    print("\n2. Schimbare IP...")
    renew_tor_ip()
    ip2 = get_current_ip()
    print(f"   IP nou: {ip2}")

    if ip1 != ip2:
        print("\n   SUCCESS: IP-ul s-a schimbat!")
    else:
        print("\n   WARNING: IP-ul e acelasi (poate dura cateva secunde)")

    print("\n3. Test CNPJA API...")
    data = fetch_cnpj("33000167000101", use_tor=True)  # Petrobras
    if data.get('error'):
        print(f"   FAILED: {data['error']}")
    else:
        print(f"   OK: {data.get('razao_social', '')}")
        print(f"   Email: {data.get('email', 'N/A')}")


def main():
    parser = argparse.ArgumentParser(description='CNPJA Tor Enrichment')
    parser.add_argument('--cnpj', help='Single CNPJ lookup')
    parser.add_argument('--companies', action='store_true', help='Enrich all major companies')
    parser.add_argument('--test', action='store_true', help='Test Tor connectivity')

    args = parser.parse_args()

    if args.test:
        test_tor()
    elif args.companies:
        enrich_companies()
    elif args.cnpj:
        ip = get_current_ip()
        print(f"IP: {ip}")
        data = fetch_cnpj(args.cnpj, use_tor=True)
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
