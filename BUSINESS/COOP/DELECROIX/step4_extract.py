#!/usr/bin/env python3
import re, sys
sys.stdout.reconfigure(encoding='utf-8')

def extract(filepath, label, maxlines=100):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            html = f.read()
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', '\n', text)
        lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 2]
        # filter for price/product related
        keywords = ['€','eur','lei','price','pret','€','banda','belt','sort','recolt','harvest',
                     'trailer','remorc','tapis','convey','delecroix','domasz','krukowiak',
                     'simon','¥','$','£','RON','ft','€','dot','used','occasion','second']
        print(f'\n=== {label} ({len(lines)} lines) ===')
        printed = 0
        for line in lines:
            lower = line.lower()
            if any(kw in lower for kw in keywords):
                print(f'  >> {line}')
                printed += 1
        if printed == 0:
            for line in lines[:30]:
                print(f'  {line}')
    except Exception as e:
        print(f'{label}: ERROR {e}')

extract(r'D:\MEMORY\DELECROIX\macus_banda.html', 'MASCUS Romania - Benzi de sortare')
extract(r'D:\MEMORY\DELECROIX\delecroix_youtube.html', 'DELECROIX YouTube')
