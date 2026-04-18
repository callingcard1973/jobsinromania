#!/usr/bin/env python3
import re, sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'D:\MEMORY\DELECROIX\delecroix_site.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Extract visible text
text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
text = re.sub(r'<[^>]+>', ' ', text)
text = re.sub(r'\s+', ' ', text)

# Print chunks
chunks = [text[i:i+500] for i in range(0, min(len(text), 10000), 500)]
for c in chunks:
    print(c)
    print('---')
