#!/usr/bin/env python3
import requests, sys, re
sys.stdout.reconfigure(encoding='utf-8')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# Check MARCOSER
try:
    r = requests.get('https://www.marcoser.ro/', headers=headers, timeout=15)
    text = re.sub(r'<script[^>]*>.*?</script>', '', r.text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+]', '\n', text)
    lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 2]
    print(f'MARCOSER: {r.status_code}, {len(lines)} lines')
    for l in lines[:50]:
        print(f'  {l}')
except Exception as e:
    print(f'MARCOSER ERROR: {e}')

# Check Agrialianta
try:
    r = requests.get('https://www.agrialianta.com/', headers=headers, timeout=15)
    text = re.sub(r'<script[^>]*>.*?</script>', '', r.text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '\n', text)
    lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 2]
    print(f'\nAGRIALIANTA: {r.status_code}, {len(lines)} lines')
    for l in lines[:50]:
        print(f'  {l}')
except Exception as e:
    print(f'AGRIALIANTA ERROR: {e}')
