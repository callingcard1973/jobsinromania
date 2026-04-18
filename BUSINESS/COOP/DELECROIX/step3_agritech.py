#!/usr/bin/env python3
import requests, sys, os
sys.stdout.reconfigure(encoding='utf-8')

base = r'D:\MEMORY\DELECROIX'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

sites = [
    ("https://www.agritech.com.ro/category/recoltare-si-ambalare/masini-de-recoltat-legume/", "agritech_recoltat_legume.html"),
    ("https://www.agritech.com.ro/category/recoltare-si-ambalare/sortare-si-conditionare/", "agritech_sortare.html"),
    ("https://www.agritech.com.ro/category/recoltare-si-ambalare/cantarire-si-ambalare/", "agritech_cantarire.html"),
]

for url, fname in sites:
    fpath = os.path.join(base, fname)
    try:
        r = requests.get(url, headers=headers, timeout=15)
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(r.text)
        print(f'OK {fname}: {len(r.text)} bytes')
    except Exception as e:
        print(f'FAIL {fname}: {e}')
