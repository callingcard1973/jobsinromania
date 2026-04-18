#!/usr/bin/env python3
"""Download Agrialianta website - multiple pages"""
import requests, sys, re
sys.stdout.reconfigure(encoding='utf-8')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

urls = [
    ("https://agrialianta.com/", "agrialianta_home.html"),
    ("https://agrialianta.com/despre-noi/", "agrialianta_despre.html"),
    ("https://agrialianta.com/magazin/", "agrialianta_magazin.html"),
    ("https://agrialianta.com/utilaje-agricole/", "agrialianta_utilaje.html"),
    ("https://agrialianta.com/categorie-produs/utilaje-agricole/", "agrialianta_utilaje2.html"),
    ("https://agrialianta.com/product-category/utilaje-agricole/", "agrialianta_utilaje3.html"),
    ("https://agrialianta.com/legumicultura/", "agrialianta_legumicultura.html"),
    ("https://agrialianta.com/contact/", "agrialianta_contact.html"),
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
        print(f'\n=== {fname}: {r.status_code}, {len(lines)} lines, {len(r.text)} bytes ===')
        print(f'  Final URL: {r.url}')
        for l in lines[:50]:
            print(f'  {l}')
        if len(lines) > 50:
            print(f'  ... ({len(lines)-50} more)')
    except Exception as e:
        print(f'FAIL {fname}: {e}')
