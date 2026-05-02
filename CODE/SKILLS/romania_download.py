#!/usr/bin/env python3
"""
Download ALL free Romanian company data.

Sources:
1. data.gov.ro (ONRC, Bilant, ONG, Datorii, Achizitii)
2. ANAF API cache refresh
3. European funds beneficiaries

Usage:
    python3 download_romania_all.py          # Download all
    python3 download_romania_all.py --status # Show what's downloaded
    nohup python3 download_romania_all.py &  # Background
"""

import os
import sys
import csv
import json
import requests
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

# === CONFIG ===
BASE = Path('/opt/ACTIVE/OPENDATA/DATA/ROMANIA')
DOWNLOADS = BASE / 'DOWNLOADS'
DOWNLOADS.mkdir(parents=True, exist_ok=True)

SOURCES = {
    # === BILANT (Financial Data) ===
    'bilant_2024_uu': ('BILANT/raw_uu_2024.txt',
        'https://data.gov.ro/dataset/d3caacb6-2c08-445e-94e6-8d36d00ab250/resource/25098618-f6a5-4610-8c7f-c0bdb801635f/download/web_uu_an2024.txt'),
    'bilant_2024_bl': ('BILANT/raw_bl_2024.txt',
        'https://data.gov.ro/dataset/d3caacb6-2c08-445e-94e6-8d36d00ab250/resource/f89140dc-20dd-494f-912a-d1a482188885/download/web_bl_bs_sl_an2024.txt'),
    'bilant_2023_uu': ('BILANT/raw_uu_2023.txt',
        'https://data.gov.ro/dataset/7861a98f-4d5c-4faa-90d4-8e934ebd1782/resource/ee5b6665-c096-4582-ada7-cc51a62c3c40/download/web_uu_an2023.txt'),
    'bilant_2023_bl': ('BILANT/raw_bl_2023.txt',
        'https://data.gov.ro/dataset/7861a98f-4d5c-4faa-90d4-8e934ebd1782/resource/8c914899-cf2a-494c-9d3b-7f9f7faa47a3/download/web_bl_bs_sl_an2023.txt'),

    # === DATORII BUGET (Tax Debts) ===
    'datorii_mari': ('DATORII_BUGET/contribuabili_mari.csv',
        'https://data.gov.ro/dataset/238727a2-ffd4-4aa9-9655-814a86721c97/resource/125297c1-78df-4c82-a437-0f6f52aeda86/download/mari.csv'),
    'datorii_mijlocii': ('DATORII_BUGET/contribuabili_mijlocii.csv',
        'https://data.gov.ro/dataset/238727a2-ffd4-4aa9-9655-814a86721c97/resource/bb24c535-83d8-469b-bf5c-b345d8619ad0/download/mijlocii.csv'),
    'datorii_mici': ('DATORII_BUGET/contribuabili_mici.csv',
        'https://data.gov.ro/dataset/238727a2-ffd4-4aa9-9655-814a86721c97/resource/1a23968b-de59-4e42-88e0-d78155c6706a/download/micijuridice.csv'),

    # === ONG (NGOs - Asociatii & Fundatii) ===
    'ong_asociatii': ('ONG/asociatii.xls',
        'https://data.gov.ro/dataset/ong-uri-inscrise-in-registrul-national-ong/resource/9a7c9b9a-4c4b-4b4a-9c9a-7c9b9a4c4b4a/download/asociatii.xls'),
    'ong_fundatii': ('ONG/fundatii.xlsx',
        'https://data.gov.ro/dataset/ong-uri-inscrise-in-registrul-national-ong/resource/fundatii.xlsx'),

    # === EU FUNDS BENEFICIARIES ===
    'eu_beneficiari': ('EU_FUNDS/beneficiari.xlsx',
        'https://data.gov.ro/dataset/beneficiari-fonduri-europene/resource/download/beneficiari.xlsx'),
    'sponsorizari': ('EU_FUNDS/sponsorizari.xlsx',
        'https://data.gov.ro/dataset/sponsorizari-ong/resource/download/sponsorizari.xlsx'),
}

def download_file(name, rel_path, url, force=False):
    """Download single file."""
    path = BASE / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists() and not force:
        age = (datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)).days
        if age < 30:
            return 'CACHED', path.stat().st_size

    try:
        r = requests.get(url, timeout=300, stream=True,
                        headers={'User-Agent': 'Mozilla/5.0'})
        if r.status_code == 200:
            path.write_bytes(r.content)
            return 'OK', len(r.content)
        return f'HTTP_{r.status_code}', 0
    except Exception as e:
        return f'ERR', 0

def download_datagov_search():
    """Search and download from data.gov.ro API."""
    queries = ['ong asociatii', 'fundatii', 'beneficiari fonduri', 'firme registru']
    downloaded = []

    for q in queries:
        try:
            r = requests.get(f'https://data.gov.ro/api/3/action/package_search?q={q}&rows=5', timeout=30)
            data = r.json()
            for pkg in data.get('result', {}).get('results', []):
                for res in pkg.get('resources', []):
                    url = res.get('url', '')
                    fmt = res.get('format', '').lower()
                    if fmt in ['csv', 'xlsx', 'xls'] and url and 'download' in url:
                        name = pkg.get('name', 'unknown')[:30]
                        safe = ''.join(c if c.isalnum() else '_' for c in name)
                        path = DOWNLOADS / f'{safe}.{fmt}'
                        if not path.exists():
                            try:
                                resp = requests.get(url, timeout=120)
                                if resp.status_code == 200 and len(resp.content) > 5000:
                                    path.write_bytes(resp.content)
                                    downloaded.append((safe, len(resp.content)))
                            except:
                                pass
        except:
            pass

    return downloaded

def show_status():
    """Show download status."""
    print("=" * 60)
    print("ROMANIA DATA STATUS")
    print("=" * 60)

    total = 0
    for name, (rel_path, url) in SOURCES.items():
        path = BASE / rel_path
        if path.exists():
            size = path.stat().st_size
            age = (datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)).days
            print(f"[OK] {name}: {size:,} bytes ({age}d ago)")
            total += size
        else:
            print(f"[--] {name}: NOT DOWNLOADED")

    print(f"\nTotal: {total:,} bytes ({total/1024/1024:.1f} MB)")

    # Extra downloads
    extras = list(DOWNLOADS.glob('*'))
    if extras:
        print(f"\nExtra downloads: {len(extras)} files")
        for f in extras[:10]:
            print(f"  {f.name}: {f.stat().st_size:,}")

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    print("=" * 60)
    print("DOWNLOADING ALL ROMANIA DATA")
    print("=" * 60)

    ok, fail = 0, 0
    for name, (rel_path, url) in SOURCES.items():
        print(f"{name}...", end=' ')
        status, size = download_file(name, rel_path, url, args.force)
        print(f"{status} ({size:,})" if size else status)
        if status in ['OK', 'CACHED']:
            ok += 1
        else:
            fail += 1

    print(f"\nSearching data.gov.ro for extras...")
    extras = download_datagov_search()
    for name, size in extras:
        print(f"  + {name}: {size:,}")

    print(f"\n{'='*60}")
    print(f"Complete: {ok} OK, {fail} failed, {len(extras)} extras")
    print(f"Output: {BASE}")

if __name__ == '__main__':
    main()
