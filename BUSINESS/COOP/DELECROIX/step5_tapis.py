#!/usr/bin/env python3
import re, sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'D:\MEMORY\DELECROIX\delecroix_tapis.html', 'r', encoding='utf-8') as f:
    html = f.read()

text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
text = re.sub(r'<[^>]+>', '\n', text)
lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 2]

keywords = ['€','eur','price','prix','pret','banda','belt','tapis','remorc','trailer',
            'convey','long','large','mate','dimension','mesh','pvc','mate','maille',
            'config','simulat','budget','specif','model','length','width','height']

print(f'Total: {len(lines)} lines')
printed = 0
for line in lines:
    lower = line.lower()
    if any(kw in lower for kw in keywords):
        print(f'  >> {line}')
        printed += 1

if printed == 0:
    for line in lines[:60]:
        print(f'  {line}')
