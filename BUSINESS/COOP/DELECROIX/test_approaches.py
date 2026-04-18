import urllib.request, urllib.parse, re, json, time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ro-RO,ro;q=0.9,en-US;q=0.8',
}

def fetch(url, headers=None):
    try:
        req = urllib.request.Request(url, headers=headers or HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return ''

def extract_emails(text):
    blocked = ['example.com', 'wixpress.com', 'cloudflare.com', 'facebook.com',
               'instagram.com', 'youtube.com', 'schema.org', 'sentry.io',
               'gravatar.com', 'googleapis.com', 'w3.org', 'mozilla.org',
               'linkedin.com', 'twitter.com', '.png', '.jpg', '.gif', '.svg']
    emails = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', text)
    clean = []
    for e in emails:
        e = e.lower().strip()
        if any(b in e for b in blocked): continue
        if e.endswith(('.png','.jpg','.gif','.svg','.css','.js')): continue
        if len(e) > 50: continue
        clean.append(e)
    return list(set(clean))

# Test companies
tests = [
    ('AGROMEC DRAGASANI S.R.L.', 'VALCEA', '250810450'),
    ('EQUINTO SERVICE SRL', 'GALATI', '36665117'),
    ('AGRITECH S.R.L.', 'IALOMITA', '15967408'),
]

for name, judet, cui in tests:
    print(f'\n{"="*60}')
    print(f'{name} ({judet}) - CUI: {cui}')
    
    # 1. Listafirme.ro by CUI
    print('\n  1. Listafirme.ro/CUI...')
    url1 = f'https://www.listafirme.ro/c/{cui}'
    html1 = fetch(url1)
    print(f'     Size: {len(html1)}, Emails: {extract_emails(html1)}')
    # Find website links
    sites = re.findall(r'href="(https?://[^"]+)"', html1)
    sites = [s for s in sites if not any(d in s for d in ['listafirme', 'facebook', 'google', 'javascript'])]
    print(f'     Links: {sites[:3]}')
    time.sleep(1)
    
    # 2. OpenJustice.ro by CUI  
    print('  2. Openjustice.ro...')
    url2 = f'https://openjustice.ro/companies/{cui}'
    html2 = fetch(url2)
    print(f'     Size: {len(html2)}, Emails: {extract_emails(html2)}')
    sites2 = re.findall(r'href="(https?://[^"]+)"', html2)
    sites2 = [s for s in sites2 if not any(d in s for d in ['openjustice', 'facebook', 'google'])]
    print(f'     Links: {sites2[:3]}')
    time.sleep(1)
    
    # 3. Termene.ro by CUI
    print('  3. Termene.ro...')
    slug = name.lower().replace(' ', '-').replace('.','').replace(',','').replace('/','-')
    url3 = f'https://termene.ro/firma/{slug}-{cui}'
    html3 = fetch(url3)
    print(f'     Size: {len(html3)}, Emails: {extract_emails(html3)}')
    time.sleep(1)
    
    # 4. Direct website guess
    print('  4. Direct website guess...')
    # Try common patterns
    short_name = name.replace(' S.R.L.', '').replace(' SRL', '').replace(' S.A.', '').replace(' SA', '').strip()
    domain_guesses = [
        f'https://{short_name.lower().replace(" ", "")}.ro',
        f'https://www.{short_name.lower().replace(" ", "")}.ro',
        f'https://{short_name.lower().replace(" ", "-")}.ro',
    ]
    for dg in domain_guesses:
        html4 = fetch(dg)
        if html4 and len(html4) > 500:
            emails4 = extract_emails(html4)
            print(f'     {dg} -> {len(html4)} chars, Emails: {emails4}')
            if emails4:
                break
        time.sleep(0.5)
    
    # 5. Google search (try)
    print('  5. Google search...')
    q = f'{name} {judet} contact email site:.ro'
    url5 = 'https://www.google.com/search?' + urllib.parse.urlencode({'q': q, 'num': 5})
    html5 = fetch(url5, headers={**HEADERS, 'Accept-Language': 'ro-RO'})
    print(f'     Size: {len(html5)}, Emails: {extract_emails(html5)}')
    # Extract redirected URLs from Google
    glinks = re.findall(r'href="/url\?q=(https?://[^&]+)', html5)
    glinks += re.findall(r'href="(https?://[^"]*\.ro[^"]*)"', html5)
    glinks = [l for l in glinks if not any(d in l for d in ['google', 'facebook'])]
    print(f'     Google links: {glinks[:3]}')
    # Visit those links
    for gl in glinks[:2]:
        html_g = fetch(gl)
        if html_g:
            emails_g = extract_emails(html_g)
            print(f'       {gl[:50]} -> emails: {emails_g}')
            if emails_g:
                break
        time.sleep(1)
    
    time.sleep(2)
