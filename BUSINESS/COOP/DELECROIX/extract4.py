#!/usr/bin/env python3
import re, sys
sys.stdout.reconfigure(encoding='utf-8')

files = [
    (r'D:\MEMORY\DELECROIX\eqinto_remorci.html', 'EQUINTO REMORCI'),
    (r'D:\MEMORY\DELECROIX\eqinto_recoltat.html', 'EQUINTO RECOLTAT'),
]

for filepath, label in files:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            html = f.read()
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', '\n', text)
        lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 2]
        print(f'\n=== {label} ({len(lines)} lines) ===')
        for line in lines[:200]:
            print(f'  {line}')
    except Exception as e:
        print(f'{label}: ERROR {e}')
