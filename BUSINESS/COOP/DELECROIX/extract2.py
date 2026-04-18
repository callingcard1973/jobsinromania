#!/usr/bin/env python3
import re, sys
sys.stdout.reconfigure(encoding='utf-8')

def extract_text(filepath, label, maxchars=6000):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            html = f.read()
    except:
        print(f'{label}: FILE NOT FOUND')
        return
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '\n', text)
    lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 2]
    print(f'\n=== {label} ({len(lines)} lines) ===')
    for line in lines[:200]:
        print(line)

extract_text(r'D:\MEMORY\DELECROIX\agritech_products.html', 'AGRITECH PRODUCTS')
