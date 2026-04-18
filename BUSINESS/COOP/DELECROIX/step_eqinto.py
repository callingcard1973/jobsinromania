#!/usr/bin/env python3
"""Download Equinto website - multiple pages"""
import requests, sys, re
sys.stdout.reconfigure(encoding='utf-8')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

urls = [
    ("https://www.eqinto.eu/", "eqinto_home.html"),
    ("https://www.eqinto.eu/despre-noi/", "eqinto_despre.html"),
    ("https://www.eqinto.eu/categorie-produs/legume-fructe/", "eqinto_legume.html"),
    ("https://www.eqinto.eu/categorie-produs/utilaje-recoltat/", "eqinto_recoltat2.html"),
    ("https://www.eqinto.eu/product-category/legume-fructe/", "eqinto_legume2.html"),
    ("https://www.eqinto.eu/echipamente-industriale/industria-alimentara/legume-fructe/", "eqinto_legume3.html"),
]

for url, fname in urls:
    try:
        r = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        with open(r'D:\MEMORY\DELECROIX\\' + fname, 'w', encoding='utf-8') as f:
            f.write(r.text)
        text = re.sub(r'<script[^>]*>.*?</script>', '', r.text, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', '\n', text)
        lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 2]
        print(f'\n=== {fname}: {r.status_code}, {len(lines)} text lines, {len(r.text)} bytes ===')
        print(f'  URL: {r.url}')
        for l in lines[:40]:
            print(f'  {l}')
        if len(lines) > 40:
            print(f'  ... ({len(lines)-40} more)')
    except Exception as e:
        print(f'FAIL {fname}: {e}')
