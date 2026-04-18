#!/usr/bin/env python3
"""Download specific product pages from competitors"""
import requests, sys, os
sys.stdout.reconfigure(encoding='utf-8')

sites = [
    # Hortech harvest machines
    ("https://www.hortech.it/en/slide-eco/", "hortech_slide_eco.html"),
    ("https://www.hortech.it/en/rapid/", "hortech_rapid.html"),
    # Asa-Lift (now part of Grimme group)
    ("https://www.asa-lift.dk/en/products/", "asalift_products.html"),
    # Standen
    ("https://www.standen.co.uk/harvesters/", "standen_harvesters.html"),
    ("https://www.standen.co.uk/imports/", "standen_imports.html"),
    # Delecroix own site for prices
    ("https://www.delecroix-harvesting.com/en/simulateur", "delecroix_simulateur.html"),
    # Domasz (Polish - making sorting belts)
    ("https://www.domasz.eu/en", "domasz_eu.html"),
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
