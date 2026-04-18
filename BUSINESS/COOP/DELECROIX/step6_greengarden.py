#!/usr/bin/env python3
"""Download Green Garden full site to understand their business"""
import requests, sys
sys.stdout.reconfigure(encoding='utf-8')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

urls = [
    ("https://www.greengarden.ro/", "greengarden_home.html"),
    ("https://www.greengarden.ro/despre-noi/", "greengarden_despre.html"),
    ("https://www.greengarden.ro/categorii-produse/", "greengarden_categorii.html"),
    ("https://www.greengarden.ro/utilaje-agricole/", "greengarden_utilaje.html"),
]

for url, fname in urls:
    try:
        r = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        with open(r'D:\MEMORY\DELECROIX\\' + fname, 'w', encoding='utf-8') as f:
            f.write(r.text)
        print(f'OK {fname}: {len(r.text)} bytes, status {r.status_code}')
    except Exception as e:
        print(f'FAIL {fname}: {e}')
