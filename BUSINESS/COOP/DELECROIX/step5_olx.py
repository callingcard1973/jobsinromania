#!/usr/bin/env python3
"""Search for harvest belt / sorting conveyor prices on marketplaces"""
import requests, sys, re, json
sys.stdout.reconfigure(encoding='utf-8')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# Try olx.ro for Romanian second-hand market
urls = [
    ("https://www.olx.ro/q/banda-sortare/?search%5Border%5D=relevance", "olx_banda_sortare.html"),
    ("https://www.olx.ro/q/banda-recoltare/?search%5Border%5D=relevance", "olx_banda_recoltare.html"),
    ("https://www.olx.ro/q/tapis-recolte/?search%5Border%5D=relevance", "olx_tapis.html"),
    # Try delecroix products page  
    ("https://www.delecroix-harvesting.com/en/tapis-convoyeurs", "delecroix_tapis.html"),
    ("https://www.delecroix-harvesting.com/en/remorques", "delecroix_remorques.html"),
]

for url, fname in urls:
    try:
        r = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        with open(r'D:\MEMORY\DELECROIX\\' + fname, 'w', encoding='utf-8') as f:
            f.write(r.text)
        print(f'OK {fname}: {len(r.text)} bytes, status {r.status_code}, url: {r.url}')
    except Exception as e:
        print(f'FAIL {fname}: {e}')
