#!/usr/bin/env python3
"""Extract visible text from Delecroix website HTML"""
import re, sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'D:\MEMORY\DELECROIX\delecroix_site.html', 'r', encoding='utf-8') as f:
    html = f.read()

text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
text = re.sub(r'<[^>]+>', '\n', text)
lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 2]
print(f'Total lines: {len(lines)}')
for line in lines:
    print(line)
