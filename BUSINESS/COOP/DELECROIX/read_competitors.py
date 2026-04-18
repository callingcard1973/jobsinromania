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

# Key competitors
extract(r'D:\MEMORY\DELECROIX\hortech_rapid.html', 'HORTECH RAPID (Italy) - harvester')
extract(r'D:\MEMORY\DELECROIX\hortech_slide_eco.html', 'HORTECH SLIDE ECO (Italy) - harvester')
