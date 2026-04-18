#!/usr/bin/env python3
import re, sys
sys.stdout.reconfigure(encoding='utf-8')

def extract_text(filepath, label):
    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    print(f'\n=== {label} ===')
    print(text[:4000])

extract_text(r'D:\MEMORY\DELECROIX\marcoser.html', 'MARCOSER')
extract_text(r'D:\MEMORY\DELECROIX\agritech.html', 'AGRITECH')
