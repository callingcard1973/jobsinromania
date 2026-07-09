#!/usr/bin/env python3
"""DB connection, safe_query, ANAF API, bilant import for bankruptcy scanner."""

import csv
import json
import socket
import sys
from datetime import datetime
from pathlib import Path

import psycopg2
import psycopg2.extras
import requests

# -- Config
RASPIBIG = '192.168.100.21'
DB_NAME = 'interjob_master'
DB_USER = 'tudor'
DB_PASS = 'tudor'
ANAF_API = 'https://webservicesp.anaf.ro/api/PlatitorTvaRest/v9/tva'
BILANT_DIR = Path('/opt/DATA/ROMANIA/BILANT')

# -- Connection
def get_conn(dbname=DB_NAME):
    """Connect to PostgreSQL. Localhost if on raspibig, TCP otherwise."""
    try:
        socket.create_connection(('localhost', 5432), timeout=1).close()
        return psycopg2.connect(dbname=dbname, user=DB_USER, password=DB_PASS)
    except Exception:
        return psycopg2.connect(
            host=RASPIBIG, port=5432, dbname=dbname,
            user=DB_USER, password=DB_PASS
        )

# -- Safe query
def safe_query(conn, sql, params=None):
    """Execute query, return rows. Rollback on error."""
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params or ())
        if cur.description:
            return cur.fetchall()
        conn.commit()
        return []
    except Exception as e:
        conn.rollback()
        print(f"Query error: {e}", file=sys.stderr)
        return []

# -- ANAF API
def anaf_lookup(cui):
    """Single CUI lookup via ANAF v9 API."""
    cui = safe_cui(cui)
    if not cui:
        return {}
    payload = [{'cui': int(cui), 'data': datetime.now().strftime('%Y-%m-%d')}]
    try:
        resp = requests.post(ANAF_API, json=payload, timeout=15,
                             headers={'Content-Type': 'application/json'})
        resp.raise_for_status()
        found = resp.json().get('found', [])
        if not found:
            return {}
        dg = found[0].get('date_generale', {})
        return {
            'denumire': dg.get('denumire', ''),
            'adresa': dg.get('adresa', ''),
            'telefon': dg.get('telefon', ''),
            'cod_postal': dg.get('codPostal', ''),
            'stare': dg.get('statusRO', ''),
            'platitor_tva': dg.get('scpTVA', False),
            'cod_caen': str(dg.get('cod_CAEN', '')),
        }
    except Exception as e:
        print(f"ANAF API error: {e}", file=sys.stderr)
        return {}

# -- Helpers
def safe_cui(val):
    """Strip RO prefix, validate CUI is numeric."""
    if not val:
        return ''
    s = str(val).strip().upper()
    if s.startswith('RO'):
        s = s[2:]
    return s if s.isdigit() else ''

# -- Bilant config (local files + download URLs)
BILANT_URLS = {
    2022: {
        'bl': 'https://data.gov.ro/dataset/aa2567a4-e7d7-4e6e-ab19-d08d39f99996/resource/b35fab04-f101-42d7-a765-8f41728b373a/download/web_bl_bs_sl_an2022.txt',
        'uu': 'https://data.gov.ro/dataset/aa2567a4-e7d7-4e6e-ab19-d08d39f99996/resource/7f31544a-1f85-4700-8fe6-9cd19fcf8515/download/web_uu_an2022.txt',
        'ong': 'https://data.gov.ro/dataset/aa2567a4-e7d7-4e6e-ab19-d08d39f99996/resource/43b16cb9-3312-494a-bc1b-4a1a9974e017/download/web_ong_an2022.txt',
    },
    2023: {
        'bl': 'https://data.gov.ro/dataset/7861a98f-4d5c-4faa-90d4-8e934ebd1782/resource/8c914899-cf2a-494c-9d3b-7f9f7faa47a3/download/web_bl_bs_sl_an2023.txt',
        'uu': 'https://data.gov.ro/dataset/7861a98f-4d5c-4faa-90d4-8e934ebd1782/resource/ee5b6665-c096-4582-ada7-cc51a62c3c40/download/web_uu_an2023.txt',
        'ong': 'https://data.gov.ro/dataset/7861a98f-4d5c-4faa-90d4-8e934ebd1782/resource/137f73ef-e1e4-466e-b1ab-1912c9be7c83/download/web_ong_an2023.txt',
    },
    2024: {
        'bl': 'https://data.gov.ro/dataset/d3caacb6-2c08-445e-94e6-8d36d00ab250/resource/f89140dc-20dd-494f-912a-d1a482188885/download/web_bl_bs_sl_an2024.txt',
        'uu': 'https://data.gov.ro/dataset/d3caacb6-2c08-445e-94e6-8d36d00ab250/resource/25098618-f6a5-4610-8c7f-c0bdb801635f/download/web_uu_an2024.txt',
        'ong': 'https://data.gov.ro/dataset/d3caacb6-2c08-445e-94e6-8d36d00ab250/resource/d6eb54bb-9d94-4b64-814b-26a6b4a9064a/download/web_ong_an2024.txt',
    },
}
BILANT_FILES = {
    2022: ['raw_bl_2022.txt', 'raw_uu_2022.txt', 'raw_ong_2022.txt'],
    2023: ['raw_bl_2023.txt', 'raw_uu_2023.txt', 'raw_ong_2023.txt'],
    2024: ['raw_bl_2024.txt', 'raw_uu_2024.txt', 'raw_ong_2024.txt'],
}

def download_bilant(year):
    """Download bilant files for a year from data.gov.ro."""
    if year not in BILANT_URLS:
        print(f"No URLs for year {year}")
        return
    BILANT_DIR.mkdir(parents=True, exist_ok=True)
    fnames = BILANT_FILES[year]
    url_keys = ['bl', 'uu', 'ong']
    for fname, key in zip(fnames, url_keys):
        fpath = BILANT_DIR / fname
        if fpath.exists():
            print(f"  Already exists: {fname}")
            continue
        url = BILANT_URLS[year].get(key)
        if not url:
            continue
        print(f"  Downloading {fname}...")
        resp = requests.get(url, stream=True, timeout=120)
        resp.raise_for_status()
        with open(fpath, 'wb') as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        print(f"  Saved {fname} ({fpath.stat().st_size:,} bytes)")

def parse_bilant_file(filepath):
    """Parse bilant TXT, yield {cui, caen, cifra_afaceri, ...}."""
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            if len(row) < 22:
                continue
            try:
                cui = row[0].strip()
                if not cui.isdigit():
                    continue
                profit = int(row[19]) if row[19].strip() else 0
                loss = int(row[20]) if row[20].strip() else 0
                yield {
                    'cui': int(cui),
                    'caen': row[1].strip(),
                    'cifra_afaceri': int(row[14]) if row[14].strip() else 0,
                    'nr_angajati': int(row[21]) if row[21].strip() else 0,
                    'profit_net': profit - loss,
                    'active_imobilizate': int(row[2]) if row[2].strip() else 0,
                    'active_circulante': int(row[3]) if row[3].strip() else 0,
                }
            except (ValueError, IndexError):
                continue

def import_bilant():
    """Import bilant data into bilant_years table."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('DROP TABLE IF EXISTS bilant_years')
    cur.execute('''CREATE TABLE bilant_years (
        cui BIGINT NOT NULL, year INT NOT NULL,
        cifra_afaceri BIGINT, profit_net BIGINT, nr_angajati BIGINT,
        active_imobilizate BIGINT, active_circulante BIGINT,
        caen VARCHAR(10),
        UNIQUE(cui, year)
    )''')
    conn.commit()
    for year, files in BILANT_FILES.items():
        rows = {}
        for fname in files:
            fpath = BILANT_DIR / fname
            if not fpath.exists():
                print(f"  SKIP {fname} (not found)")
                continue
            for r in parse_bilant_file(fpath):
                c = r['cui']
                if c not in rows or r['cifra_afaceri'] > rows[c]['cifra_afaceri']:
                    rows[c] = r
            print(f"  Parsed {fname}")
        if not rows:
            continue
        batch = [(r['cui'], year, r['cifra_afaceri'], r['profit_net'],
                  r['nr_angajati'], r['active_imobilizate'],
                  r['active_circulante'], r['caen']) for r in rows.values()]
        psycopg2.extras.execute_values(cur, '''
            INSERT INTO bilant_years (cui,year,cifra_afaceri,profit_net,
                nr_angajati,active_imobilizate,active_circulante,caen)
            VALUES %s ON CONFLICT (cui,year) DO UPDATE SET
                cifra_afaceri=EXCLUDED.cifra_afaceri,
                profit_net=EXCLUDED.profit_net,
                nr_angajati=EXCLUDED.nr_angajati,
                active_imobilizate=EXCLUDED.active_imobilizate,
                active_circulante=EXCLUDED.active_circulante,
                caen=EXCLUDED.caen
        ''', batch, page_size=5000)
        conn.commit()
        print(f"  Year {year}: {len(batch):,} companies imported")
    cur.execute('SELECT year, COUNT(*) FROM bilant_years GROUP BY year ORDER BY year')
    for row in cur.fetchall():
        print(f"  bilant_years {row[0]}: {row[1]:,} records")
    conn.close()
    print("Done.")

if __name__ == '__main__':
    if '--download-bilant' in sys.argv:
        for y in BILANT_URLS:
            print(f"Year {y}:")
            download_bilant(y)
        print("Download complete.")
    elif '--import-bilant' in sys.argv:
        import_bilant()
    else:
        print("Usage: python db_helper.py --download-bilant | --import-bilant")
