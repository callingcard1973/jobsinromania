#!/usr/bin/env python3
"""
Company Status Checker - Romania
Verifica starea firmelor la Registrul Comertului dupa CUI

Surse gratuite:
- ANAF API (status TVA, denumire, adresa)
- Listafirme.ro (status ONRC: activa/radiata/dizolvata)

Usage:
    company_status_ro.py --cui 12345678              # Verifica un CUI
    company_status_ro.py --file input.csv            # Verifica lista (coloana: cui)
    company_status_ro.py --cui 12345678 --full       # Info complet (ANAF + Listafirme)
    company_status_ro.py --file input.csv --output results.csv
"""

import sys
import os
import argparse
import sqlite3
import csv
import json
import time
import re
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, fetch_url

# Cache database
DB_PATH = '/opt/ACTIVE/INFRA/SKILLS/data/company_status_cache.db'
CACHE_DAYS = 7  # Cache results for 7 days

# Rate limiting
REQUEST_DELAY = 1.0  # seconds between requests


def init_db():
    """Initialize SQLite cache database"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS company_cache (
            cui TEXT PRIMARY KEY,
            denumire TEXT,
            adresa TEXT,
            judet TEXT,
            localitate TEXT,
            cod_postal TEXT,
            tva_activ INTEGER,
            status_onrc TEXT,
            data_radiere TEXT,
            data_infiintare TEXT,
            cod_caen TEXT,
            nr_angajati TEXT,
            cifra_afaceri TEXT,
            source TEXT,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()


def get_cached(cui):
    """Get cached result if fresh"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cutoff = (datetime.now() - timedelta(days=CACHE_DAYS)).isoformat()
    cursor.execute('''
        SELECT * FROM company_cache
        WHERE cui = ? AND checked_at > ?
    ''', (str(cui), cutoff))

    row = cursor.fetchone()
    conn.close()

    if row:
        columns = ['cui', 'denumire', 'adresa', 'judet', 'localitate', 'cod_postal',
                   'tva_activ', 'status_onrc', 'data_radiere', 'data_infiintare',
                   'cod_caen', 'nr_angajati', 'cifra_afaceri', 'source', 'checked_at']
        return dict(zip(columns, row))
    return None


def save_cache(data):
    """Save result to cache"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO company_cache
        (cui, denumire, adresa, judet, localitate, cod_postal, tva_activ,
         status_onrc, data_radiere, data_infiintare, cod_caen, nr_angajati,
         cifra_afaceri, source, checked_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('cui'),
        data.get('denumire'),
        data.get('adresa'),
        data.get('judet'),
        data.get('localitate'),
        data.get('cod_postal'),
        data.get('tva_activ'),
        data.get('status_onrc'),
        data.get('data_radiere'),
        data.get('data_infiintare'),
        data.get('cod_caen'),
        data.get('nr_angajati'),
        data.get('cifra_afaceri'),
        data.get('source'),
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


def check_anaf(cui):
    """Check company via ANAF API"""
    import requests

    cui = str(cui).strip()
    if not cui.isdigit():
        return None

    url = "https://webservicesp.anaf.ro/api/PlatitorTvaRest/v9/tva"
    today = datetime.now().strftime("%Y-%m-%d")

    payload = [{"cui": int(cui), "data": today}]

    try:
        response = requests.post(url, json=payload, timeout=30)
        data = response.json()

        if data.get('found') and len(data['found']) > 0:
            item = data['found'][0]
            info = item.get('date_generale', {})
            tva_info = item.get('inregistrare_scop_Tva', {})
            stare_info = item.get('stare_inactiv', {})
            adresa_info = item.get('adresa_sediu_social', {})

            # Parse address
            adresa_full = info.get('adresa', '')
            judet = adresa_info.get('sdenumire_Judet', '')
            localitate = adresa_info.get('sdenumire_Localitate', '')
            cod_postal = info.get('codPostal', '') or adresa_info.get('scod_Postal', '')

            # Determine status
            status = 'ACTIVA'
            data_radiere = ''
            if stare_info.get('statusInactivi'):
                status = 'INACTIVA'
            if stare_info.get('dataRadiere'):
                status = 'RADIATA'
                data_radiere = stare_info.get('dataRadiere', '')

            # Check stare_inregistrare for more info
            stare_inreg = info.get('stare_inregistrare', '')
            if 'RADIAT' in stare_inreg.upper():
                status = 'RADIATA'
            elif 'INACTIV' in stare_inreg.upper():
                status = 'INACTIVA'

            return {
                'cui': cui,
                'denumire': to_ascii(info.get('denumire', '')),
                'adresa': to_ascii(adresa_full),
                'judet': to_ascii(judet),
                'localitate': to_ascii(localitate),
                'cod_postal': cod_postal,
                'tva_activ': 1 if tva_info.get('scpTVA', False) else 0,
                'status_onrc': status,
                'data_radiere': data_radiere,
                'data_infiintare': info.get('data_inregistrare', ''),
                'cod_caen': info.get('cod_CAEN', ''),
                'telefon': info.get('telefon', ''),
                'nr_reg_com': info.get('nrRegCom', ''),
                'source': 'ANAF'
            }
        elif data.get('notFound') and len(data['notFound']) > 0:
            return {
                'cui': cui,
                'denumire': '',
                'status_onrc': 'NEGASIT',
                'source': 'ANAF'
            }
    except Exception as e:
        print(f"  ANAF error for {cui}: {e}")

    return None


def check_listafirme(cui):
    """Scrape Listafirme.ro for ONRC status"""
    import requests
    from bs4 import BeautifulSoup

    cui = str(cui).strip()
    url = f"https://www.listafirme.ro/cauta.asp?cui={cui}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'ro-RO,ro;q=0.9,en;q=0.8',
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        result = {'cui': cui, 'source': 'LISTAFIRME'}

        # Find company link and follow it
        link = soup.find('a', href=re.compile(r'/[a-z0-9-]+-\d+/$', re.IGNORECASE))
        if link:
            detail_url = 'https://www.listafirme.ro' + link['href']
            time.sleep(0.5)

            detail_resp = requests.get(detail_url, headers=headers, timeout=30)
            detail_resp.encoding = 'utf-8'
            detail_soup = BeautifulSoup(detail_resp.text, 'html.parser')

            # Extract company name
            h1 = detail_soup.find('h1')
            if h1:
                result['denumire'] = to_ascii(h1.get_text(strip=True))

            # Find status in the page
            text = detail_soup.get_text()

            # Check for RADIATA
            if re.search(r'RADIATA|RADIERE|radiata', text, re.IGNORECASE):
                result['status_onrc'] = 'RADIATA'
                # Try to find radiere date
                date_match = re.search(r'(?:radiata?|radiere)[^\d]*(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4})', text, re.IGNORECASE)
                if date_match:
                    result['data_radiere'] = date_match.group(1)
            elif re.search(r'DIZOLVATA|DIZOLVARE|dizolvata', text, re.IGNORECASE):
                result['status_onrc'] = 'DIZOLVATA'
            elif re.search(r'SUSPENDATA|SUSPENDARE|suspendata', text, re.IGNORECASE):
                result['status_onrc'] = 'SUSPENDATA'
            elif re.search(r'INACTIVA|inactiva', text, re.IGNORECASE):
                result['status_onrc'] = 'INACTIVA'
            else:
                result['status_onrc'] = 'ACTIVA'

            # Try to extract more info from tables
            tables = detail_soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        label = cells[0].get_text(strip=True).lower()
                        value = cells[1].get_text(strip=True)

                        if 'adresa' in label or 'sediu' in label:
                            result['adresa'] = to_ascii(value)
                        elif 'judet' in label:
                            result['judet'] = to_ascii(value)
                        elif 'localitate' in label or 'oras' in label:
                            result['localitate'] = to_ascii(value)
                        elif 'caen' in label:
                            result['cod_caen'] = value[:4] if value else ''
                        elif 'angajat' in label:
                            result['nr_angajati'] = value
                        elif 'cifra' in label or 'afaceri' in label:
                            result['cifra_afaceri'] = value
                        elif 'infiintare' in label or 'inregistrare' in label:
                            result['data_infiintare'] = value

            return result
        else:
            return {
                'cui': cui,
                'status_onrc': 'NEGASIT',
                'source': 'LISTAFIRME'
            }

    except Exception as e:
        print(f"  Listafirme error for {cui}: {e}")

    return None


def check_company(cui, full=False, use_cache=True):
    """Check company status - combines sources"""
    cui = str(cui).strip().lstrip('0')

    if not cui or not cui.isdigit():
        return {'cui': cui, 'status_onrc': 'CUI_INVALID', 'error': 'CUI invalid'}

    # Check cache first
    if use_cache:
        cached = get_cached(cui)
        if cached:
            cached['from_cache'] = True
            return cached

    # Start with ANAF (always)
    result = check_anaf(cui)

    if not result:
        result = {'cui': cui, 'status_onrc': 'EROARE', 'source': 'NONE'}

    # If full mode or ANAF says not found, try Listafirme
    if full or result.get('status_onrc') in ['NEGASIT', 'NECUNOSCUT']:
        time.sleep(REQUEST_DELAY)
        lf_result = check_listafirme(cui)

        if lf_result:
            # Merge results, prefer Listafirme for ONRC status
            for key, value in lf_result.items():
                if value and (not result.get(key) or key == 'status_onrc'):
                    result[key] = value
            result['source'] = 'ANAF+LISTAFIRME'

    # Save to cache
    save_cache(result)
    result['from_cache'] = False

    return result


def batch_check(cui_list, full=False, progress=True):
    """Check multiple CUIs"""
    results = []
    total = len(cui_list)

    for i, cui in enumerate(cui_list):
        if progress:
            print(f"  [{i+1}/{total}] Checking CUI {cui}...", end=' ')

        result = check_company(cui, full=full)
        results.append(result)

        if progress:
            status = result.get('status_onrc', 'UNKNOWN')
            cached = ' (cached)' if result.get('from_cache') else ''
            print(f"{status}{cached}")

        # Rate limiting (skip if from cache)
        if not result.get('from_cache') and i < total - 1:
            time.sleep(REQUEST_DELAY)

    return results


def print_result(result):
    """Pretty print a single result"""
    print(f"\n{'='*60}")
    print(f"CUI: {result.get('cui')}")
    print(f"{'='*60}")
    print(f"Denumire:     {result.get('denumire', '-')}")
    print(f"Status ONRC:  {result.get('status_onrc', '-')}")
    print(f"TVA Activ:    {'DA' if result.get('tva_activ') else 'NU'}")
    print(f"J Number:     {result.get('nr_reg_com', '-')}")
    print(f"Telefon:      {result.get('telefon', '-')}")
    print(f"Adresa:       {result.get('adresa', '-')}")
    print(f"Judet:        {result.get('judet', '-')}")
    print(f"Localitate:   {result.get('localitate', '-')}")
    print(f"Cod Postal:   {result.get('cod_postal', '-')}")
    print(f"CAEN:         {result.get('cod_caen', '-')}")
    print(f"Infiintare:   {result.get('data_infiintare', '-')}")
    if result.get('data_radiere'):
        print(f"Data radiere: {result.get('data_radiere')}")
    print(f"Sursa:        {result.get('source', '-')}")
    if result.get('from_cache'):
        print(f"(din cache)")


def export_csv(results, output_path):
    """Export results to CSV"""
    if not results:
        return

    columns = ['cui', 'denumire', 'status_onrc', 'tva_activ', 'adresa', 'judet',
               'localitate', 'cod_postal', 'cod_caen', 'data_infiintare',
               'data_radiere', 'nr_angajati', 'cifra_afaceri', 'source']

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(results)

    print(f"\nExported {len(results)} results to {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Verifica starea firmelor la ONRC')
    parser.add_argument('--cui', type=str, help='CUI de verificat')
    parser.add_argument('--file', type=str, help='Fisier CSV cu CUI-uri (coloana: cui)')
    parser.add_argument('--output', type=str, help='Fisier CSV output')
    parser.add_argument('--full', action='store_true', help='Info complet (ANAF + Listafirme)')
    parser.add_argument('--no-cache', action='store_true', help='Ignora cache')
    parser.add_argument('--stats', action='store_true', help='Arata statistici cache')

    args = parser.parse_args()

    if args.stats:
        init_db()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM company_cache')
        total = cursor.fetchone()[0]
        cursor.execute("SELECT status_onrc, COUNT(*) FROM company_cache GROUP BY status_onrc")
        print(f"\nCache statistics ({total} total):")
        for row in cursor.fetchall():
            print(f"  {row[0] or 'UNKNOWN'}: {row[1]}")
        conn.close()
        return

    if args.cui:
        # Single CUI check
        print(f"Verificare CUI: {args.cui}")
        result = check_company(args.cui, full=args.full, use_cache=not args.no_cache)
        print_result(result)

    elif args.file:
        # Batch check from file
        if not os.path.exists(args.file):
            print(f"Fisier negasit: {args.file}")
            return

        cui_list = []
        with open(args.file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cui = row.get('cui') or row.get('CUI') or row.get('Cui')
                if cui:
                    cui_list.append(cui.strip())

        if not cui_list:
            print("Nu am gasit coloana 'cui' in fisier")
            return

        print(f"Verificare {len(cui_list)} CUI-uri din {args.file}")
        print(f"Mode: {'FULL (ANAF + Listafirme)' if args.full else 'RAPID (doar ANAF)'}")
        print()

        results = batch_check(cui_list, full=args.full)

        # Summary
        print(f"\n{'='*60}")
        print("SUMAR:")
        status_counts = {}
        for r in results:
            s = r.get('status_onrc', 'UNKNOWN')
            status_counts[s] = status_counts.get(s, 0) + 1
        for status, count in sorted(status_counts.items()):
            print(f"  {status}: {count}")

        # Export if output specified
        if args.output:
            export_csv(results, args.output)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
