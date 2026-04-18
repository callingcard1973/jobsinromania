#!/usr/bin/env python3
import requests, sys
sys.stdout.reconfigure(encoding='utf-8')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# Green Garden - check real URL
urls = [
    ("https://www.greengarden.ro/", "gg_home.html"),
    ("https://greengarden.ro/", "gg_home2.html"),
]

for url, fname in urls:
    try:
        r = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        with open(r'D:\MEMORY\DELECROIX\\' + fname, 'w', encoding='utf-8') as f:
            f.write(r.text)
        print(f'OK {fname}: {len(r.text)} bytes, status {r.status_code}, final URL: {r.url}')
    except Exception as e:
        print(f'FAIL {fname}: {e}')
