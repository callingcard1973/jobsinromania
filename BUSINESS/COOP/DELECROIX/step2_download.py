#!/usr/bin/env python3
"""Download competitor websites using requests"""
import requests, sys, os
sys.stdout.reconfigure(encoding='utf-8')

sites = [
    ("https://www.simon-gewinnemann.de/en/", "simon.html"),
    ("https://asa-lift.dk/en/", "asalift.html"),
    ("https://www.allan-eng.com/", "allan.html"),
    ("https://www.imacimac.it/en/", "imac.html"),
    ("https://www.hortech.it/en/", "hortech.html"),
    ("https://www.standen.co.uk/", "standen.html"),
    ("https://www.dewulf.com/en/products", "dewulf_products.html"),
]

base = r'D:\MEMORY\DELECROIX'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

for url, fname in sites:
    fpath = os.path.join(base, fname)
    try:
        r = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(r.text)
        print(f'OK {fname}: {len(r.text)} bytes, status {r.status_code}')
    except Exception as e:
        print(f'FAIL {fname}: {e}')
