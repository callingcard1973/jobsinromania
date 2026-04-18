#!/usr/bin/env python3
"""Download MARCOSER website properly"""
import requests, sys, re
sys.stdout.reconfigure(encoding='utf-8')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

urls = [
    ("https://www.marcoser.ro/", "marcoser_home.html"),
    ("https://www.marcoser.ro/despre-noi/", "marcoser_despre.html"),
    ("https://www.marcoser.ro/magazin/", "marcoser_magazin.html"),
    ("https://www.marcoser.ro/categorie-produs/utilaje/", "marcoser_utilaje.html"),
    ("https://www.marcoser.ro/categorie-produs/masini-utilaje/", "marcoser_masini.html"),
    ("https://www.marcoser.ro/product-category/utilaje/", "marcoser_utilaje2.html"),
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
        for l in lines[:30]:
            print(f'  {l}')
        if len(lines) > 30:
            print(f'  ... ({len(lines)-30} more lines)')
    except Exception as e:
        print(f'FAIL {fname}: {e}')
