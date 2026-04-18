#!/usr/bin/env python3
"""Quick test of DDG email scraper on 3 companies"""
import csv
import re
import time
import random
import urllib.request
import urllib.parse

def ddg_search(query):
    results = []
    try:
        url = 'https://html.duckduckgo.com/html/?' + urllib.parse.urlencode({'q': query})
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html',
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        
        links = re.findall(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
        for url_match, title_match in links[:5]:
            actual_url = urllib.parse.unquote(url_match)
            if 'uddg=' in actual_url:
                actual_url = actual_url.split('uddg=')[-1].split('&')[0]
                actual_url = urllib.parse.unquote(actual_url)
            title = re.sub(r'<[^>]+>', '', title_match).strip()
            results.append((title, actual_url))
    except Exception as e:
        print(f'  Error: {e}')
    return results

def fetch_page(url):
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except:
        return ''

def extract_emails(text):
    blocked = ['example.com', 'wixpress.com', 'cloudflare.com', 'facebook.com', 
               'instagram.com', 'youtube.com', 'schema.org', 'sentry.io', '.png', '.jpg']
    emails = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', text)
    clean = []
    for e in emails:
        e = e.lower().strip()
        if any(b in e for b in blocked): continue
        if e.endswith(('.png','.jpg','.gif','.svg','.css','.js')): continue
        if len(e) > 50: continue
        clean.append(e)
    return list(set(clean))

# Test with 3 companies from targets
test_companies = [
    ('36316846', 'A&TAM AGRIUTILMASINI IMPORT SRL', 'MURES'),
    ('42854556', 'A50 PREMIUM SERVICE UTILAJE S.R.L.', 'BUCURESTI'),
    ('34769867', 'ACF SPEDITION SRL', 'BIHOR'),
]

for cui, name, judet in test_companies:
    print(f'\n{"="*60}')
    print(f'Testing: {name} ({judet})')
    
    query = f'"{name}" {judet} contact email'
    print(f'Query: {query}')
    
    results = ddg_search(query)
    print(f'DDG results: {len(results)}')
    
    for title, url in results:
        skip = ['facebook.com', 'instagram.com', 'youtube.com', 'linkedin.com',
                'wikipedia.org', 'olx.ro', 'lista-firme.ro', 'termene.ro']
        if any(d in url.lower() for d in skip):
            print(f'  SKIP: {url[:60]}')
            continue
        
        print(f'  Checking: {url[:70]}')
        html = fetch_page(url)
        if html:
            emails = extract_emails(html)
            if emails:
                print(f'  FOUND EMAILS: {emails}')
            else:
                print(f'  No emails found (page: {len(html)} chars)')
        else:
            print(f'  Could not fetch')
    
    time.sleep(random.uniform(2, 4))
