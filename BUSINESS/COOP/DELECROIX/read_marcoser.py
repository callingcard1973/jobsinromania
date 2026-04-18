#!/usr/bin/env python3
import re, sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'D:\MEMORY\DELECROIX\marcoser.html', 'r', encoding='utf-8') as f:
    html = f.read()

text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
text = re.sub(r'<[^>]+>', '\n', text)
lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 2]

print(f'Total: {len(lines)} lines, {len(html)} bytes\n')
for i, line in enumerate(lines):
    print(f'{i:3d}: {line}')
