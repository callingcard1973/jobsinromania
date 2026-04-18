#!/usr/bin/env python3
"""Search for actual prices of harvest belts and vegetable trailers"""
import requests, sys, re
sys.stdout.reconfigure(encoding='utf-8')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# Try to find prices on Agralia / agricultural forums / marketplace sites
sites = [
    ("https://www.agriaffaires.ro/utilaj/second-hand/1/banda-de-sortare.html", "agriaffaires_banda_ro.html"),
    ("https://www.agriaffaires.com/used/1/harvesting-belt.html", "agriaffaires_belt_en.html"),
    ("https://www.tractorpool.ro/utilaje-second-hand/banda-de-recoltare/", "tractorpool_banda.html"),
    ("https://www.mascus.ro/Agricultura-%C5%9Fi-foresterie/Benzi-de-sortare/", "macus_banda.html"),
    # Check Delecroix YouTube channel for product videos that might have prices
    ("https://www.youtube.com/@DelecroixHarvesting/videos", "delecroix_youtube.html"),
    # Domasz Poland - sorting belt manufacturer  
    ("https://www.domasz.eu/en/sorting-lines/", "domasz_sorting.html"),
]

for url, fname in sites:
    try:
        r = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        with open(r'D:\MEMORY\DELECROIX\\' + fname, 'w', encoding='utf-8') as f:
            f.write(r.text)
        print(f'OK {fname}: {len(r.text)} bytes, status {r.status_code}')
    except Exception as e:
        print(f'FAIL {fname}: {e}')
