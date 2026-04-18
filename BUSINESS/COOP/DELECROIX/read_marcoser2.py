#!/usr/bin/env python3
import requests, sys, re
sys.stdout.reconfigure(encoding='utf-8')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# Download fresh
r = requests.get('https://www.marcoser.ro/', headers=headers, timeout=15, allow_redirects=True)
with open(r'D:\MEMORY\DELECROIX\marcoser_fresh.html', 'w', encoding='utf-8') as f:
    f.write(r.text)
print(f'Status: {r.status_code}, Size: {len(r.text)} bytes, URL: {r.url}')

# Extract text
text = re.sub(r'<script[^>]*>.*?</script>', '', r.text, flags=re.DOTALL)
text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
text = re.sub(r'<[^>]+>', '\n', text)
lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 2]
print(f'Text lines: {len(lines)}')
for i, line in enumerate(lines):
    print(f'{i:3d}: {line}')

# Also try to find WooCommerce/product links
links = re.findall(r'href="([^"]*)"', r.text)
prod_links = [l for l in links if any(kw in l.lower() for kw in ['product', 'produs', 'magazin', 'shop', 'categorie', 'utilaj'])]
print(f'\nProduct-related links ({len(prod_links)}):')
for l in sorted(set(prod_links)):
    print(f'  {l}')

# Find menu items
menu_items = re.findall(r'<a[^>]*class="[^"]*menu[^"]*"[^>]*>(.*?)</a>', r.text, re.DOTALL)
if not menu_items:
    menu_items = re.findall(r'<li[^>]*class="[^"]*menu[^"]*"[^>]*>.*?<a[^>]*>(.*?)</a>', r.text, re.DOTALL)
print(f'\nMenu items ({len(menu_items)}):')
for m in menu_items:
    clean = re.sub(r'<[^>]+>', '', m).strip()
    if clean:
        print(f'  {clean}')
