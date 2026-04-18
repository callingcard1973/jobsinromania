#!/usr/bin/env python3
import re, sys
sys.stdout.reconfigure(encoding='utf-8')

def extract_text(filepath, label, maxlines=200):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            html = f.read()
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', '\n', text)
        lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 2]
        # filter for relevant keywords
        keywords = ['€','euro','eur','lei','price','prix','pret','banda','belt','tapis','remorc',
                     'trailer','sort','convey','harvest','recolt','delecroix','domasz','krukowiak',
                     'simon','simulat','config','dimension','long','large','mate','matériau',
                     'techni','specif','model','remorq']
        print(f'\n{"="*60}')
        print(f'  {label} ({len(lines)} lines)')
        print(f'{"="*60}')
        printed = 0
        for line in lines:
            lower = line.lower()
            if any(kw in lower for kw in keywords):
                print(f'  >> {line}')
                printed += 1
        if printed == 0:
            for line in lines[:40]:
                print(f'  {line}')
    except Exception as e:
        print(f'{label}: ERROR {e}')

# Delecroix site - find products and maybe prices
extract_text(r'D:\MEMORY\DELECROIX\delecroix_site.html', 'DELECROIX - Full Site')
