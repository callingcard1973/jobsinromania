#!/usr/bin/env python3
"""Gelbe Seiten - Playwright version for JS pagination"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
import csv, time, re
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright
from skills_common import to_ascii
from alerting import send_telegram

OUTPUT = Path('/opt/ACTIVE/OPENDATA/DATA/GERMANY_AGENCIES')
OUTPUT.mkdir(exist_ok=True)
CATEGORIES = ['zeitarbeit', 'personalvermittlung', 'personaldienstleistungen']

def scrape_all(max_pages=30):
    agencies = []
    
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        page = browser.new_page()
        
        for cat in CATEGORIES:
            print(f"\n=== {cat.upper()} ===")
            url = f"https://www.gelbeseiten.de/suche/{cat}/bundesweit"
            page.goto(url, timeout=30000)
            time.sleep(2)
            
            for pg in range(1, max_pages+1):
                print(f"Page {pg}", end=" ")
                
                # Get entries
                entries = page.query_selector_all('article.mod-Treffer')
                if not entries:
                    print("- no results")
                    break
                print(f"- {len(entries)} entries")
                
                for e in entries:
                    a = {'category': cat, 'source': 'gelbeseiten'}
                    
                    # Name
                    name = e.query_selector('h2')
                    if name: a['company_name'] = to_ascii(name.inner_text())
                    
                    # Click to get details
                    detail_link = e.query_selector('a[href*="/gsbiz/"]')
                    if detail_link:
                        href = detail_link.get_attribute('href')
                        a['detail_url'] = href
                    
                    if a.get('company_name'):
                        agencies.append(a)
                
                # Next page
                next_btn = page.query_selector('a.mod-Pagination__list__item--next, a[aria-label*="chste"]')
                if not next_btn:
                    print("No next button")
                    break
                
                next_btn.click()
                time.sleep(2)
        
        # Get details for each agency
        print(f"\n=== Fetching details for {len(agencies)} agencies ===")
        for i, a in enumerate(agencies):
            if i % 50 == 0: print(f"{i}/{len(agencies)}")
            url = a.get('detail_url')
            if not url: continue
            
            try:
                page.goto(url, timeout=15000)
                time.sleep(1)
                
                # Phone
                tel = page.query_selector('a[href^="tel:"]')
                if tel: a['phone'] = re.sub(r'[^\d\+]', '', tel.get_attribute('href'))
                
                # Email
                mail = page.query_selector('a[href^="mailto:"]')
                if mail: a['email'] = mail.get_attribute('href').replace('mailto:','').split('?')[0]
                
                # Website
                web = page.query_selector('a[data-click*="website"], a.mod-WebseitenLink')
                if web: a['website'] = web.get_attribute('href')
                
                # Address
                addr = page.query_selector('.mod-Geschaeftsdaten__adress')
                if addr:
                    txt = addr.inner_text()
                    a['address'] = to_ascii(txt)
                    m = re.search(r'(\d{5})\s+(\S+)', txt)
                    if m: a['postal_code'], a['city'] = m.group(1), to_ascii(m.group(2))
            except:
                pass
        
        browser.close()
    
    return agencies

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--pages', type=int, default=30)
    parser.add_argument('--notify', action='store_true')
    args = parser.parse_args()
    
    agencies = scrape_all(args.pages)
    
    # Dedupe
    seen = set()
    unique = [a for a in agencies if (k:=a.get('company_name','').lower()) not in seen and not seen.add(k)]
    
    out = OUTPUT / f'gelbe_seiten_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
    keys = ['company_name','phone','email','website','address','city','postal_code','category','source']
    with open(out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
        w.writeheader()
        w.writerows(unique)
    
    stats = f"Total: {len(unique)}\nPhone: {sum(1 for a in unique if a.get('phone'))}\nEmail: {sum(1 for a in unique if a.get('email'))}\nWebsite: {sum(1 for a in unique if a.get('website'))}"
    print(f"\n{stats}\nSaved: {out}")
    if args.notify: send_telegram(f"<b>Gelbe Seiten</b>\n{stats}")

if __name__ == "__main__":
    main()
