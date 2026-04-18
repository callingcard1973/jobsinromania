#!/usr/bin/env python3
"""
Email Enrichment - Domain Guess + Contact Page Scraper
For CAEN 4661/2830 Romanian agricultural machinery distributors.

Strategy:
1. Generate domain guesses from company name
2. Try to fetch homepage
3. If homepage exists, look for contact page
4. Extract emails from both

Rate-limited, resumable, with checkpoint.
"""

import csv
import re
import json
import time
import os
from datetime import datetime
import urllib.request
import urllib.parse

# ============================================
# CONFIG
# ============================================
ENRICHED_CSV = r'D:\MEMORY\DELECROIX\distribuitori_utilaje_ENRICHED.csv'
CHECKPOINT_FILE = r'D:\MEMORY\DELECROIX\email_enrich_checkpoint.json'
OUTPUT_CSV = r'D:\MEMORY\DELECROIX\email_enrich_results.csv'
LOG_FILE = r'D:\MEMORY\DELECROIX\email_enrich.log'

DELAY_BETWEEN_DOMAINS = 0.5  # seconds
DELAY_BETWEEN_COMPANIES = 1.5
TIMEOUT = 10
BATCH_SIZE = 50  # save checkpoint every N companies

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

# ============================================
# UTILS
# ============================================

def log(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    line = f'[{ts}] {msg}'
    try:
        print(line, flush=True)
    except UnicodeEncodeError:
        print(line.encode('ascii', 'replace').decode(), flush=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

def fetch(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            ct = resp.headers.get('Content-Type', '')
            if 'text/html' in ct or 'text/plain' in ct or 'application/xhtml' in ct:
                return resp.read().decode('utf-8', errors='ignore')
            return ''
    except:
        return ''

def extract_emails(text):
    blocked = ['example.com', 'wixpress.com', 'cloudflare.com', 'facebook.com',
               'instagram.com', 'youtube.com', 'schema.org', 'sentry.io',
               'gravatar.com', 'googleapis.com', 'w3.org', 'mozilla.org',
               'linkedin.com', 'twitter.com', 'pinterest.com', 'tiktok.com',
               '.png', '.jpg', '.gif', '.svg', '.css', '.js', '.ico',
               'politicadecookies', 'wordpress.com', 'googletagmanager',
               'hotjar.com', 'analytics', 'maps.googleapis']
    emails = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', text)
    clean = []
    for e in emails:
        e = e.lower().strip()
        if any(b in e for b in blocked): continue
        if e.endswith(('.png','.jpg','.gif','.svg','.css','.js')): continue
        if len(e) > 50: continue
        if '..' in e: continue
        clean.append(e)
    return list(set(clean))

def generate_domain_guesses(name):
    """Generate possible .ro domains from company name"""
    # Remove suffixes
    n = name.strip()
    for suffix in [' S.R.L.', ' S.R.L', ' SRL', ' S.A.', ' S.A', ' SA',
                   ' S.C.', ' S.C', ' SC', ' S.N.', ' S.N', ' SN',
                   ' SOCIETATE CU RASPUNDERE LIMITATA',
                   ' SOCIETATE PE ACTIUNI',
                   ' INTREPRINDERE INDIVIDUALA',
                   ' PERSOANA FIZICA AUTORIZATA',
                   ' REGIA AUTONOMA']:
        n = n.replace(suffix, '')
    n = n.strip().rstrip('.')
    
    # Generate variations
    bases = set()
    # All lowercase, no spaces
    bases.add(n.lower().replace(' ', '').replace('-', '').replace('.', '').replace('&', 'and'))
    # With hyphens
    bases.add(n.lower().replace(' ', '-').replace('.', '-').replace('&', 'and'))
    # Remove common prefixes
    for prefix in ['SC ', 'S.C. ', 'SRL ', 'SA ']:
        if n.upper().startswith(prefix):
            clean = n[len(prefix):].strip()
            bases.add(clean.lower().replace(' ', '').replace('-', '').replace('.', ''))
            bases.add(clean.lower().replace(' ', '-').replace('.', '-'))
    
    # Remove common Romanian words
    for word in [' IMPEX', ' IMPORT', ' EXPORT', ' COM', ' COMERC', ' TRADING',
                 ' SERVICE', ' GROUP', ' INTERNATIONAL', ' ROMANIA', ' ROM',
                 ' INVEST', ' PROD', ' PRODUC', ' INDUSTRIAL', ' GENERAL',
                 ' AGRICOL', ' AGRO', ' FARM', ' TECH', ' UTILAJE', ' MASINI']:
        if word in n.upper():
            short = re.sub(re.escape(word), '', n, flags=re.IGNORECASE).strip()
            if len(short) > 3:
                bases.add(short.lower().replace(' ', '').replace('-', '').replace('.', ''))
                bases.add(short.lower().replace(' ', '-').replace('.', '-'))
    
    # Filter too short or too long
    domains = []
    for b in bases:
        b = b.strip('-').strip('.')
        if 3 <= len(b) <= 40:
            domains.append(f'https://{b}.ro')
            domains.append(f'https://www.{b}.ro')
    
    return list(dict.fromkeys(domains))  # unique, preserve order

# ============================================
# MAIN LOGIC
# ============================================

def find_email_for_company(name):
    """Try domain guesses, find website, scrape for email"""
    guesses = generate_domain_guesses(name)
    
    for url in guesses:
        html = fetch(url)
        if not html or len(html) < 300:
            continue
        
        # We found a live site!
        emails = extract_emails(html)
        
        # Also try /contact and /contacte pages
        contact_paths = ['/contact', '/contacte', '/despre-noi', '/about', 
                        '/contact-us', '/despre']
        for path in contact_paths:
            contact_html = fetch(url.rstrip('/') + path)
            if contact_html:
                emails += extract_emails(contact_html)
            time.sleep(0.3)
        
        if emails:
            # Prefer contact@, office@, info@ emails
            preferred = [e for e in emails if any(p in e for p in 
                        ['contact', 'office', 'info', 'sales', 'comercial', 
                         'vanzari', 'admin', 'manager', 'director'])]
            if preferred:
                return preferred[0], url
            # Otherwise return first non-noreply
            non_noreply = [e for e in emails if 'noreply' not in e and 'no-reply' not in e]
            if non_noreply:
                return non_noreply[0], url
            return emails[0], url
        
        # Site exists but no email found
        return '', url
    
    return '', ''

# ============================================
# MAIN
# ============================================

def main():
    log('=' * 60)
    log('EMAIL ENRICHMENT - Domain Guess Strategy')
    log('=' * 60)
    
    # Load enriched CSV
    companies = []
    with open(ENRICHED_CSV, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            companies.append(row)
    
    # Filter: only those WITHOUT email
    need_email = [c for c in companies if not c.get('email')]
    log(f'Total: {len(companies)}, Need email: {len(need_email)}')
    
    # Load checkpoint
    cp = {}
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
            cp = json.load(f)
        log(f'Checkpoint: {len(cp)} already processed')
    
    # Load existing results
    results = []
    if os.path.exists(OUTPUT_CSV):
        with open(OUTPUT_CSV, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                results.append(row)
        log(f'Existing results: {len(results)}')
    
    # Process
    remaining = [c for c in need_email if c['cui'] not in cp]
    log(f'Remaining to process: {len(remaining)}')
    
    found_count = 0
    site_count = 0
    
    for i, company in enumerate(remaining):
        cui = company['cui']
        name = company['denumire']
        
        log(f'[{i+1}/{len(remaining)}] {name}')
        
        email, website = find_email_for_company(name)
        
        if email:
            found_count += 1
            log(f'  EMAIL: {email}')
            results.append({
                'cui': cui,
                'denumire': name,
                'email': email,
                'website': website,
                'found_at': datetime.now().isoformat(),
                'method': 'domain_guess'
            })
            cp[cui] = {'email': email, 'website': website, 'status': 'found'}
        elif website:
            site_count += 1
            log(f'  WEBSITE only: {website}')
            results.append({
                'cui': cui,
                'denumire': name,
                'email': '',
                'website': website,
                'found_at': datetime.now().isoformat(),
                'method': 'domain_guess'
            })
            cp[cui] = {'email': '', 'website': website, 'status': 'website_only'}
        else:
            cp[cui] = {'email': '', 'website': '', 'status': 'not_found'}
        
        # Save checkpoint periodically
        if (i + 1) % BATCH_SIZE == 0:
            with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
                json.dump(cp, f, ensure_ascii=False)
            with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['cui', 'denumire', 'email', 'website', 'found_at', 'method'])
                writer.writeheader()
                writer.writerows(results)
            log(f'  CHECKPOINT: {len(cp)} processed, {found_count} emails, {site_count} websites')
        
        time.sleep(DELAY_BETWEEN_COMPANIES)
    
    # Final save
    with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
        json.dump(cp, f, ensure_ascii=False)
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['cui', 'denumire', 'email', 'website', 'found_at', 'method'])
        writer.writeheader()
        writer.writerows(results)
    
    not_found = sum(1 for v in cp.values() if v.get('status') == 'not_found')
    log('=' * 60)
    log(f'DONE!')
    log(f'  Processed: {len(cp)}')
    log(f'  Emails found: {found_count}')
    log(f'  Websites found: {site_count}')
    log(f'  Not found: {not_found}')
    log(f'  Results: {OUTPUT_CSV}')
    log('=' * 60)

if __name__ == '__main__':
    main()
