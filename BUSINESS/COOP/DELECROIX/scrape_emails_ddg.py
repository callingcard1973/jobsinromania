#!/usr/bin/env python3
"""
DDG Email Scraper for CAEN 4661/2830 Distributors
Searches DuckDuckGo for each company, finds website, scrapes contact page for email.
Resumable with checkpoint. Rate-limited.
"""

import csv
import json
import time
import re
import random
import os
from datetime import datetime

# ============================================
# CONFIG
# ============================================
INPUT_CSV = r'D:\MEMORY\DELECROIX\ddg_search_targets.csv'
ENRICHED_CSV = r'D:\MEMORY\DELECROIX\distribuitori_utilaje_ENRICHED.csv'
CHECKPOINT_FILE = r'D:\MEMORY\DELECROIX\ddg_email_checkpoint.json'
OUTPUT_CSV = r'D:\MEMORY\DELECROIX\ddg_email_results.csv'
LOG_FILE = r'D:\MEMORY\DELECROIX\ddg_email_scraper.log'

DELAY_MIN = 2.0  # seconds between requests
DELAY_MAX = 5.0
MAX_RESULTS_PER_QUERY = 5
TIMEOUT = 15  # seconds for HTTP requests

# ============================================
# SETUP
# ============================================
import urllib.request
import urllib.parse
import urllib.error

def log(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line, flush=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'completed': {}, 'failed': []}

def save_checkpoint(cp):
    with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
        json.dump(cp, f, ensure_ascii=False, indent=2)

def load_results():
    results = []
    if os.path.exists(OUTPUT_CSV):
        with open(OUTPUT_CSV, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                results.append(row)
    return results

def save_results(results):
    fields = ['cui', 'denumire', 'email', 'website', 'search_query', 'source', 'found_at']
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)

# ============================================
# SCRAPING FUNCTIONS
# ============================================

def ddg_search(query):
    """Search DuckDuckGo HTML version, return list of (title, url)"""
    results = []
    try:
        url = 'https://html.duckduckgo.com/html/?' + urllib.parse.urlencode({'q': query})
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7',
        })
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        
        # Parse DDG HTML results
        # Pattern: <a rel="nofollow" class="result__a" href="URL">TITLE</a>
        links = re.findall(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
        for url_match, title_match in links[:MAX_RESULTS_PER_QUERY]:
            # DDG uses redirect URLs, extract actual URL
            actual_url = urllib.parse.unquote(url_match)
            if 'uddg=' in actual_url:
                actual_url = actual_url.split('uddg=')[-1].split('&')[0]
                actual_url = urllib.parse.unquote(actual_url)
            title = re.sub(r'<[^>]+>', '', title_match).strip()
            results.append((title, actual_url))
    except Exception as e:
        log(f'  DDG search error: {e}')
    
    return results

def fetch_page(url):
    """Fetch a webpage and return text content"""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
        })
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except:
        return ''

def extract_emails(text):
    """Extract all email addresses from text"""
    # Standard email regex
    emails = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', text)
    
    # Filter out common junk
    blocked = ['example.com', 'test.com', 'domain.com', 'email.com', 'yoursite.com',
               'sentry.io', 'googleapis.com', 'wixpress.com', 'wordpress.com',
               'cloudflare.com', 'gravatar.com', 'schema.org', 'w3.org',
               'facebook.com', 'instagram.com', 'youtube.com', 'twitter.com',
               'linkedin.com', '.png', '.jpg', '.gif', '.svg', '.css', '.js']
    
    clean = []
    for e in emails:
        e = e.lower().strip()
        if any(b in e for b in blocked):
            continue
        if e.endswith(('.png', '.jpg', '.gif', '.svg')):
            continue
        if len(e) > 50:
            continue
        clean.append(e)
    
    return list(set(clean))

def find_email_for_company(name, judet='', localitate=''):
    """Search for company and find email"""
    queries = [
        f'"{name}" {judet} contact email',
        f'{name} {localitate} site',
    ]
    
    for query in queries:
        log(f'  Query: {query[:80]}')
        results = ddg_search(query)
        
        for title, url in results:
            # Skip irrelevant results
            skip_domains = ['facebook.com', 'instagram.com', 'youtube.com', 'twitter.com',
                          'linkedin.com', 'wikipedia.org', 'olx.ro', 'publio.ro',
                          'bizpedia.ro', 'firme.biz', 'companii.biz', 'lista-firme.ro',
                          'termene.ro', 'totalfirme.ro', 'infocui.ro']
            if any(d in url.lower() for d in skip_domains):
                continue
            
            log(f'    Checking: {url[:70]}')
            html = fetch_page(url)
            if not html:
                continue
            
            emails = extract_emails(html)
            if emails:
                # Prefer contact@, office@, info@ emails
                contact_emails = [e for e in emails if any(p in e for p in ['contact', 'office', 'info', 'sales', 'comercial', 'vanzari'])]
                if contact_emails:
                    return contact_emails[0], url
                return emails[0], url
    
    return '', ''

# ============================================
# MAIN
# ============================================
def main():
    log('=' * 60)
    log('DDG EMAIL SCRAPER - Start')
    log('=' * 60)
    
    # Load targets
    targets = []
    with open(INPUT_CSV, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            targets.append(row)
    log(f'Targets: {len(targets)}')
    
    # Load checkpoint
    cp = load_checkpoint()
    completed = cp.get('completed', {})
    log(f'Already completed: {len(completed)}')
    
    # Load existing results
    results = load_results()
    log(f'Existing results: {len(results)}')
    
    # Process
    remaining = [t for t in targets if t['cui'] not in completed]
    log(f'Remaining: {len(remaining)}')
    
    for i, target in enumerate(remaining):
        cui = target['cui']
        name = target['denumire']
        judet = target.get('sediu_judet', '')
        localitate = target.get('sediu_localitate', '')
        
        log(f'[{i+1}/{len(remaining)}] {name}')
        
        email, website = find_email_for_company(name, judet, localitate)
        
        if email:
            log(f'  FOUND: {email}')
            results.append({
                'cui': cui,
                'denumire': name,
                'email': email,
                'website': website,
                'search_query': f'{name} {judet}',
                'source': 'ddg_email_scraper',
                'found_at': datetime.now().isoformat()
            })
            completed[cui] = {'email': email, 'website': website, 'status': 'found'}
        else:
            log(f'  NOT FOUND')
            completed[cui] = {'email': '', 'website': '', 'status': 'not_found'}
        
        # Save checkpoint every 10 results
        if (i + 1) % 10 == 0:
            save_checkpoint({'completed': completed, 'failed': []})
            save_results(results)
            log(f'  Checkpoint saved ({len(completed)} done, {len(results)} emails found)')
        
        # Rate limit
        delay = random.uniform(DELAY_MIN, DELAY_MAX)
        time.sleep(delay)
    
    # Final save
    save_checkpoint({'completed': completed, 'failed': []})
    save_results(results)
    
    found = sum(1 for v in completed.values() if v.get('status') == 'found')
    not_found = sum(1 for v in completed.values() if v.get('status') == 'not_found')
    
    log('=' * 60)
    log(f'DONE! Found: {found}, Not found: {not_found}, Total: {len(completed)}')
    log(f'Results: {OUTPUT_CSV}')
    log('=' * 60)

if __name__ == '__main__':
    main()
