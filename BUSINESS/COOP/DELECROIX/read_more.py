#!/usr/bin/env python3
import re, sys
sys.stdout.reconfigure(encoding='utf-8')

def extract(filepath, label, maxlines=150):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            html = f.read()
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', '\n', text)
        lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 2]
        print(f'\n{"="*60}')
        print(f'  {label} ({len(lines)} lines)')
        print(f'{"="*60}')
        for line in lines[:maxlines]:
            print(f'  {line}')
    except Exception as e:
        print(f'{label}: ERROR {e}')

extract(r'D:\MEMORY\DELECROIX\standen_harvesters.html', 'STANDEN (UK) - Harvesters')
extract(r'D:\MEMORY\DELECROIX\eqinto_recoltat.html', 'EQUINTO (Romania) - Recoltat')
