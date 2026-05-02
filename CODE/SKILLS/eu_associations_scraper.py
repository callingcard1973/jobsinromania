#!/usr/bin/env python3
"""EU Staffing Associations Member Scrapers"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
import requests, re, csv, time
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from skills_common import to_ascii
from alerting import send_telegram

OUTPUT = Path('/opt/ACTIVE/OPENDATA/DATA/GERMANY_AGENCIES')
HEADERS = {'User-Agent': 'Mozilla/5.0'}

def scrape_rec_uk():
    """REC UK - rec.uk.com members"""
    print("=== REC UK ===")
    agencies = []
    url = "https://www.rec.uk.com/membership/member-directory"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(resp.text, 'html.parser')
        for item in soup.select('.member-item, .directory-item, article'):
            a = {'country': 'UK', 'source': 'rec_uk'}
            name = item.select_one('h2, h3, .name')
            if name: a['company_name'] = to_ascii(name.get_text(strip=True))
            web = item.select_one('a[href*="http"]:not([href*="rec.uk"])')
            if web: a['website'] = web.get('href')
            if a.get('company_name'): agencies.append(a)
    except Exception as e:
        print(f"Error: {e}")
    print(f"Found: {len(agencies)}")
    return agencies

def scrape_abu_nl():
    """ABU Netherlands - abu.nl members"""
    print("=== ABU NL ===")
    agencies = []
    url = "https://www.abu.nl/leden"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(resp.text, 'html.parser')
        for item in soup.select('.member, .lid, article, li'):
            text = item.get_text(strip=True)
            if len(text) > 5 and len(text) < 200:
                a = {'country': 'Netherlands', 'source': 'abu_nl', 'company_name': to_ascii(text.split('\n')[0][:100])}
                web = item.select_one('a[href*="http"]:not([href*="abu.nl"])')
                if web: a['website'] = web.get('href')
                if a.get('company_name') and not any(x in a['company_name'].lower() for x in ['home','contact','menu','zoek']):
                    agencies.append(a)
    except Exception as e:
        print(f"Error: {e}")
    print(f"Found: {len(agencies)}")
    return agencies

def scrape_federgon_be():
    """Federgon Belgium members"""
    print("=== FEDERGON BE ===")
    agencies = []
    url = "https://www.federgon.be/nl/leden"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(resp.text, 'html.parser')
        for item in soup.select('.member, .lid, article'):
            a = {'country': 'Belgium', 'source': 'federgon_be'}
            name = item.select_one('h2, h3, .name')
            if name: a['company_name'] = to_ascii(name.get_text(strip=True))
            if a.get('company_name'): agencies.append(a)
    except Exception as e:
        print(f"Error: {e}")
    print(f"Found: {len(agencies)}")
    return agencies

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--notify', action='store_true')
    args = parser.parse_args()
    
    all_agencies = []
    all_agencies.extend(scrape_rec_uk())
    all_agencies.extend(scrape_abu_nl())
    all_agencies.extend(scrape_federgon_be())
    
    # Dedupe
    seen = set()
    unique = [a for a in all_agencies if (k:=a.get('company_name','').lower()) not in seen and not seen.add(k)]
    
    out = OUTPUT / f'eu_associations_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
    keys = ['company_name','website','city','country','source']
    with open(out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
        w.writeheader()
        w.writerows(unique)
    
    print(f"\nTotal: {len(unique)}\nSaved: {out}")
    if args.notify: send_telegram(f"<b>EU Associations</b>\nAgencies: {len(unique)}")

if __name__ == "__main__":
    main()
