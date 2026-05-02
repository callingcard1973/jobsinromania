#!/usr/bin/env python3
"""Europages - EU Staffing Agencies Scraper"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
import requests, re, csv, time
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from skills_common import to_ascii
from alerting import send_telegram

OUTPUT = Path('/opt/ACTIVE/OPENDATA/DATA/GERMANY_AGENCIES')
OUTPUT.mkdir(exist_ok=True)
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

COUNTRIES = {'de': 'Germany', 'nl': 'Netherlands', 'be': 'Belgium', 'at': 'Austria', 'fr': 'France', 'pl': 'Poland'}
TERMS = ['temporary-work-agencies', 'recruitment-agencies', 'staffing-agencies', 'employment-agencies']

def scrape_europages(country='de', term='temporary-work-agencies', max_pages=10):
    agencies = []
    base = "https://www.europages.co.uk"
    
    for page in range(1, max_pages+1):
        url = f"{base}/companies/{country}/{term}.html" + (f"?page={page}" if page > 1 else "")
        print(f"[{country}] {term} p{page}", end=" ")
        
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            soup = BeautifulSoup(resp.text, 'html.parser')
            cards = soup.select('.company-card, .company-item, article[class*="company"]')
            
            if not cards:
                cards = soup.select('[data-company], .search-result')
            
            if not cards:
                print("- 0")
                break
            print(f"- {len(cards)}")
            
            for c in cards:
                a = {'country': COUNTRIES.get(country, country), 'category': term, 'source': 'europages'}
                
                name = c.select_one('h2, h3, .company-name, [class*="name"]')
                if name: a['company_name'] = to_ascii(name.get_text(strip=True))
                
                loc = c.select_one('.location, .city, [class*="location"]')
                if loc: a['city'] = to_ascii(loc.get_text(strip=True))
                
                web = c.select_one('a[href*="http"]:not([href*="europages"])')
                if web: a['website'] = web.get('href')
                
                email = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', c.get_text())
                if email: a['email'] = email.group()
                
                phone = c.select_one('a[href^="tel:"], .phone')
                if phone: a['phone'] = re.sub(r'[^\d\+]', '', phone.get_text())
                
                if a.get('company_name'): agencies.append(a)
            
            time.sleep(1)
        except Exception as e:
            print(f"Error: {e}")
            break
    return agencies

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--countries', default='de,nl,be,at')
    parser.add_argument('--pages', type=int, default=10)
    parser.add_argument('--notify', action='store_true')
    args = parser.parse_args()
    
    all_agencies = []
    for country in args.countries.split(','):
        for term in TERMS:
            agencies = scrape_europages(country.strip(), term, args.pages)
            all_agencies.extend(agencies)
    
    # Dedupe
    seen = set()
    unique = [a for a in all_agencies if (k:=a.get('company_name','').lower()) not in seen and not seen.add(k)]
    
    out = OUTPUT / f'europages_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
    keys = ['company_name','phone','email','website','city','country','category','source']
    with open(out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
        w.writeheader()
        w.writerows(unique)
    
    stats = f"Total: {len(unique)}\nPhone: {sum(1 for a in unique if a.get('phone'))}\nEmail: {sum(1 for a in unique if a.get('email'))}\nWebsite: {sum(1 for a in unique if a.get('website'))}"
    print(f"\n{stats}\nSaved: {out}")
    if args.notify: send_telegram(f"<b>Europages Agencies</b>\n{stats}")

if __name__ == "__main__":
    main()
