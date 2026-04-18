#!/usr/bin/env python3
import re, sys
sys.stdout.reconfigure(encoding='utf-8')

files = [
    (r'D:\MEMORY\DELECROIX\greengarden.html', 'GREEN GARDEN'),
    (r'D:\MEMORY\DELECROIX\agrialianta.html', 'AGRIALIANTA'),
    (r'D:\MEMORY\DELECROIX\eqinto.html', 'EQUINTO'),
]

for filepath, label in files:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            html = f.read()
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', '\n', text)
        lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 2]
        print(f'\n=== {label} ({len(lines)} lines, {len(html)} bytes) ===')
        # Look for price-related lines
        for line in lines[:150]:
            lower = line.lower()
            if any(kw in lower for kw in ['recolt', 'harvest', 'tapis', 'remorc', 'banda', 'convey', 'trailer', 'sort', 'legum', 'price', 'pret', 'lei', 'eur', '€', 'ron']):
                print(f'  >> {line}')
        # Print first 20 lines anyway
        print('  --- General content ---')
        for line in lines[:30]:
            print(f'  {line}')
    except Exception as e:
        print(f'{label}: ERROR {e}')
