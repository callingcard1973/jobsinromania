#!/usr/bin/env python3
import requests, sys, re
sys.stdout.reconfigure(encoding='utf-8')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# Try multiple pages to understand Green Garden
urls = [
    ("https://greengarden.ro/produse/", "gg_produse.html"),
    ("https://greengarden.ro/magazin/", "gg_magazin.html"),
    ("https://greengarden.ro/despre-noi/", "gg_despre.html"),
    ("https://greengarden.ro/categorie-produs/utilaje/", "gg_utilaje.html"),
    ("https://greengarden.ro/product-category/utilaje/", "gg_utilaje2.html"),
]

for url, fname in urls:
    try:
        r = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        with open(r'D:\MEMORY\DELECROIX\\' + fname, 'w', encoding='utf-8') as f:
            f.write(r.text)
        # quick check content
        text = re.sub(r'<script[^>]*>.*?</script>', '', r.text, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', '\n', text)
        lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 2]
        print(f'{fname}: {r.status_code}, {len(r.text)} bytes, {len(lines)} text lines, URL: {r.url}')
        if len(lines) > 3 and len(lines) < 50:
            for l in lines[:20]:
                print(f'  {l}')
    except Exception as e:
        print(f'FAIL {fname}: {e}')
