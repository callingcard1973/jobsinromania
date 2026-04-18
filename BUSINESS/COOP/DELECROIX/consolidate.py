#!/usr/bin/env python3
import re, sys, os, glob
sys.stdout.reconfigure(encoding='utf-8')

def extract(filepath, label, maxlines=80):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            html = f.read()
        if len(html) < 100:
            print(f'\n=== {label}: EMPTY or TINY ({len(html)} bytes) ===')
            return
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', '\n', text)
        lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 2]
        print(f'\n=== {label} ({len(lines)} lines, {len(html)} bytes) ===')
        for line in lines[:maxlines]:
            print(f'  {line}')
    except Exception as e:
        print(f'{label}: ERROR {e}')

# Green Garden pages
for f in ['greengarden_home.html', 'greengarden_despre.html', 'greengarden_categorii.html', 'greengarden_utilaje.html']:
    extract(os.path.join(r'D:\MEMORY\DELECROIX', f), f.upper())

# Domasz
extract(r'D:\MEMORY\DELECROIX\domasz.html', 'DOMASZ Poland')

# Allround VP
for f in glob.glob(r'D:\MEMORY\DELECROIX\allround*'):
    extract(f, os.path.basename(f).upper())

# Grimme
for f in glob.glob(r'D:\MEMORY\DELECROIX\grimme*'):
    extract(f, os.path.basename(f).upper())

# Jansen
for f in glob.glob(r'D:\MEMORY\DELECROIX\jansen*'):
    extract(f, os.path.basename(f).upper())
