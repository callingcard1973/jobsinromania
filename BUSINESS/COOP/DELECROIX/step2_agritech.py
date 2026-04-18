#!/usr/bin/env python3
import re, sys
sys.stdout.reconfigure(encoding='utf-8')

for filepath, label in [
    (r'D:\MEMORY\DELECROIX\agritech_recoltat.html', 'AGRITECH RECOLTARE'),
    (r'D:\MEMORY\DELECROIX\agritech_sortare.html', 'AGRITECH SORTARE'),
]:
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
