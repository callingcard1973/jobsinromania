#!/usr/bin/env python3
"""Deep extract Eqinto - get all content from home and despre pages"""
import re, sys
sys.stdout.reconfigure(encoding='utf-8')

for fname, label in [
    (r'D:\MEMORY\DELECROIX\eqinto_home.html', 'HOME'),
    (r'D:\MEMORY\DELECROIX\eqinto_despre.html', 'DESPRE NOI'),
    (r'D:\MEMORY\DELECROIX\eqinto_recoltat.html', 'RECOLTAT (old)'),
    (r'D:\MEMORY\DELECROIX\eqinto_remorci.html', 'REMORCI (old)'),
]:
    with open(fname, 'r', encoding='utf-8') as f:
        html = f.read()
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '\n', text)
    lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 2]
    print(f'\n{"="*60}')
    print(f'{label}: {len(lines)} lines')
    print(f'{"="*60}')
    for i, line in enumerate(lines):
        print(f'{i:3d}: {line}')
