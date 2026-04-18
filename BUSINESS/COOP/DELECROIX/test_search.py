#!/usr/bin/env python3
"""Test multiple search approaches for Romanian company emails"""
import urllib.request
import urllib.parse
import re
import json
import time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ro-RO,ro;q=0.9,en-US;q=0.8',
}

def fetch(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return ''

def extract_emails(text):
    blocked = ['example.com', 'wixpress.com', 'cloudflare.com', 'facebook.com',
               'instagram.com', 'youtube.com', 'schema.org', 'sentry.io',
               'gravatar.com', 'googleapis.com', 'w3.org', 'mozilla.org',
               '.png', '.jpg', '.gif', '.svg', '.css', '.js']
    emails = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', text)
    clean = []
    for e in emails:
        e = e.lower().strip()
        if any(b in e for b in blocked): continue
        if e.endswith(('.png','.jpg','.gif','.svg','.css','.js')): continue
        if len(e) > 50: continue
        clean.append(e)
    return list(set(clean))

test_name = 'AGROMEC DRAGASANI'
test_judet = 'VALCEA'

print(f'Testing: {test_name} ({test_judet})\n')

# ============================================
# APPROACH 1: DuckDuckGo with different format
# ============================================
print('1. DDG HTML...')
query = f'{test_name} {test_judet} email'
url = 'https://html.duckduckgo.com/html/?' + urllib.parse.urlencode({'q': query})
html = fetch(url)
print(f'   Page size: {len(html)} chars')
links = re.findall(r'href="(https?://[^"]+)"', html)
links = [l for l in links if not any(d in l for d in ['duckduckgo', 'javascript', 'facebook'])]
print(f'   Links found: {len(links[:10])}')
for l in links[:5]:
    print(f'     {l[:80]}')

time.sleep(2)

# ============================================
# APPROACH 2: Bing
# ============================================
print('\n2. Bing...')
query2 = f'{test_name} {test_judet} contact email'
url2 = 'https://www.bing.com/search?' + urllib.parse.urlencode({'q': query2})
html2 = fetch(url2)
print(f'   Page size: {len(html2)} chars')
emails_bing = extract_emails(html2)
print(f'   Emails found: {emails_bing}')
links2 = re.findall(r'href="(https?://[^"]+)"', html2)
links2 = [l for l in links2 if not any(d in l for d in ['bing.com', 'microsoft', 'javascript', 'facebook', 'go.microsoft'])]
print(f'   Links: {len(links2[:5])}')
for l in links2[:5]:
    print(f'     {l[:80]}')

time.sleep(2)

# ============================================
# APPROACH 3: Listafirme.ro
# ============================================
print('\n3. Listafirme.ro...')
slug = test_name.lower().replace(' ', '-').replace('.','')
url3 = f'https://www.listafirme.ro/{slug}-'
html3 = fetch(url3)
print(f'   Page size: {len(html3)} chars')
emails3 = extract_emails(html3)
print(f'   Emails found: {emails3}')

time.sleep(2)

# ============================================
# APPROACH 4: FirmenDB (German approach but works for RO)
# ============================================
print('\n4. Direct company name search via Google...')
# Try to find official website
query4 = f'site:{test_name.lower().replace(" ","")}.ro OR "{test_name}" site:*.ro contact'
url4 = 'https://html.duckduckgo.com/html/?' + urllib.parse.urlencode({'q': f'"{test_name}" site contact'})
html4 = fetch(url4)
print(f'   Page size: {len(html4)} chars')
# Look for .ro domains in results
ro_links = re.findall(r'href="(https?://[^"]*\.ro[^"]*)"', html4)
ro_links = [l for l in ro_links if 'duckduckgo' not in l]
print(f'   .ro links: {ro_links[:5]}')

time.sleep(2)

# ============================================
# APPROACH 5: Try specific known Romanian business directories
# ============================================
print('\n5. Romanian business directories...')
dirs = [
    f'https://www.rofin.ro/Cautare?cuvant={urllib.parse.quote(test_name)}',
    f'https://www.totalfirme.ro/search?q={urllib.parse.quote(test_name)}',
]
for durl in dirs:
    html5 = fetch(durl)
    emails5 = extract_emails(html5)
    print(f'   {durl[:50]}... -> {len(html5)} chars, emails: {emails5}')
    time.sleep(2)

# ============================================
# APPROACH 6: Firmzilla / Mate-info 
# ============================================
print('\n6. Firmzilla.ro...')
cui_test = '250810450'  # AGROMEC DRAGASANI
url6 = f'https://firmzilla.ro/firma/{cui_test}'
html6 = fetch(url6)
print(f'   Page size: {len(html6)} chars')
emails6 = extract_emails(html6)
print(f'   Emails found: {emails6}')
# Also try finding website link
websites = re.findall(r'href="(https?://[^"]+)"', html6)
websites = [w for w in websites if not any(d in w for d in ['firmzilla', 'facebook', 'google'])]
print(f'   Links: {websites[:5]}')
