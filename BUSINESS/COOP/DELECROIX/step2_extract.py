#!/usr/bin/env python3
import re, sys
sys.stdout.reconfigure(encoding='utf-8')

for filepath, label in [
    (r'D:\MEMORY\DELECROIX\asalift.html', 'ASA-LIFT (Denmark)'),
    (r'D:\MEMORY\DELECROIX\hortech.html', 'HORTECH (Italy)'),
    (r'D:\MEMORY\DELECROIX\standen.html', 'STANDEN (UK)'),
]:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            html = f.read()
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', '\n', text)
        lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 2]
        print(f'\n=== {label} ({len(lines)} lines) ===')
        # Filter for relevant keywords
        keywords = ['harvest', 'belt', 'convey', 'trailer', 'sort', 'price', '€', 'EUR', 'euro', 'vegetable', 'recolt', 'tapis', 'remorc', 'banda']
        printed = 0
        for line in lines:
            lower = line.lower()
            if any(kw in lower for kw in keywords):
                print(f'  >> {line}')
                printed += 1
        if printed == 0:
            print('  (no matching keywords, showing first 30 lines)')
            for line in lines[:30]:
                print(f'  {line}')
    except Exception as e:
        print(f'{label}: ERROR {e}')
