#!/usr/bin/env python3
"""
German Staffing Agencies Scraper
Scrapes BAP and iGZ member directories for recruitment agencies.

Usage:
    python3 germany_agencies_scraper.py --source bap
    python3 germany_agencies_scraper.py --source igz
    python3 germany_agencies_scraper.py --source all
    python3 germany_agencies_scraper.py --enrich  # Add emails via impressum
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import requests
import re
import time
import json
import argparse
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from skills_common import to_ascii, fetch_url
from alerting import send_telegram

OUTPUT_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/GERMANY_AGENCIES')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}


def scrape_bap():
    """Scrape BAP (Bundesarbeitgeberverband der Personaldienstleister) members."""
    print("=== Scraping BAP Directory ===")
    base_url = "https://www.personaldienstleister.de"
    members_url = f"{base_url}/mitglieder"
    
    agencies = []
    page = 1
    
    while True:
        url = f"{members_url}?page={page}" if page > 1 else members_url
        print(f"Page {page}: {url}")
        
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Find member entries
            entries = soup.select('.member-item, .mitglied-item, article.member, .view-content .views-row')
            
            if not entries:
                # Try alternative selectors
                entries = soup.select('[class*="member"], [class*="mitglied"]')
            
            if not entries:
                print(f"  No entries found on page {page}")
                # Check if it's a search form page
                if soup.select('form[action*="mitglied"], input[name*="search"]'):
                    print("  Found search form, trying POST request...")
                    break
                break
            
            print(f"  Found {len(entries)} entries")
            
            for entry in entries:
                agency = {}
                
                # Extract company name
                name_el = entry.select_one('h2, h3, .title, .name, a')
                if name_el:
                    agency['company_name'] = to_ascii(name_el.get_text(strip=True))
                
                # Extract website
                link = entry.select_one('a[href*="http"]')
                if link and 'personaldienstleister.de' not in link.get('href', ''):
                    agency['website'] = link.get('href')
                
                # Extract location
                loc_el = entry.select_one('.location, .address, .city, .ort')
                if loc_el:
                    agency['city'] = to_ascii(loc_el.get_text(strip=True))
                
                # Extract contact info
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', entry.get_text())
                if email_match:
                    agency['email'] = email_match.group()
                
                phone_match = re.search(r'[\+\d\s\-\/]{10,}', entry.get_text())
                if phone_match:
                    agency['phone'] = phone_match.group().strip()
                
                if agency.get('company_name'):
                    agency['source'] = 'bap'
                    agency['scraped_date'] = datetime.now().isoformat()
                    agencies.append(agency)
            
            # Check for next page
            next_link = soup.select_one('a.next, a[rel="next"], .pager-next a')
            if not next_link:
                break
            
            page += 1
            time.sleep(2)
            
        except Exception as e:
            print(f"  Error: {e}")
            break
    
    # If no results from pagination, try API/search
    if len(agencies) < 10:
        print("\nTrying alternative extraction...")
        agencies = scrape_bap_search()
    
    return agencies


def scrape_bap_search():
    """Try BAP search/API approach."""
    agencies = []
    
    # Try the Mitgliedersuche
    search_url = "https://www.personaldienstleister.de/mitgliedersuche"
    
    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Look for embedded JSON data
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and ('members' in script.string.lower() or 'mitglied' in script.string.lower()):
                # Try to extract JSON
                json_match = re.search(r'\[[\s\S]*?\]', script.string)
                if json_match:
                    try:
                        data = json.loads(json_match.group())
                        for item in data:
                            if isinstance(item, dict):
                                agency = {
                                    'company_name': to_ascii(item.get('name', item.get('title', ''))),
                                    'website': item.get('url', item.get('website', '')),
                                    'city': to_ascii(item.get('city', item.get('ort', ''))),
                                    'source': 'bap',
                                    'scraped_date': datetime.now().isoformat()
                                }
                                if agency['company_name']:
                                    agencies.append(agency)
                    except:
                        pass
        
        # Also try to find a downloadable member list
        pdf_links = soup.select('a[href*=".pdf"], a[href*="download"]')
        for link in pdf_links:
            if 'mitglied' in link.get_text().lower():
                print(f"  Found member list PDF: {link.get('href')}")
                
    except Exception as e:
        print(f"  Search error: {e}")
    
    return agencies


def scrape_igz():
    """Scrape iGZ (Interessenverband Deutscher Zeitarbeitsunternehmen) members."""
    print("=== Scraping iGZ Directory ===")
    base_url = "https://www.ig-zeitarbeit.de"
    
    agencies = []
    
    # Try member search
    search_urls = [
        f"{base_url}/mitglieder",
        f"{base_url}/mitgliedersuche", 
        f"{base_url}/fuer-unternehmen/mitgliederverzeichnis"
    ]
    
    for url in search_urls:
        print(f"Trying: {url}")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Look for member entries
                entries = soup.select('.member, .mitglied, article, .company-item, .list-item')
                
                if not entries:
                    # Try finding any list of companies
                    entries = soup.select('li, tr, .row')
                
                for entry in entries:
                    text = entry.get_text()
                    
                    # Skip navigation/header items
                    if len(text) < 10 or len(text) > 500:
                        continue
                    
                    agency = {}
                    
                    # Extract company name (usually first text or in heading)
                    name_el = entry.select_one('h2, h3, h4, strong, b, .name, .title')
                    if name_el:
                        agency['company_name'] = to_ascii(name_el.get_text(strip=True))
                    elif entry.name in ['li', 'tr']:
                        # First significant text
                        first_text = entry.get_text(strip=True)[:100]
                        if first_text and not any(x in first_text.lower() for x in ['home', 'kontakt', 'suche', 'menu']):
                            agency['company_name'] = to_ascii(first_text.split('\n')[0])
                    
                    # Extract website
                    for link in entry.select('a[href]'):
                        href = link.get('href', '')
                        if href.startswith('http') and 'ig-zeitarbeit.de' not in href:
                            agency['website'] = href
                            break
                    
                    # Extract email
                    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
                    if email_match:
                        agency['email'] = email_match.group()
                    
                    # Extract city
                    city_match = re.search(r'\b\d{5}\s+([A-Za-z\-]+)', text)
                    if city_match:
                        agency['city'] = to_ascii(city_match.group(1))
                    
                    if agency.get('company_name') and len(agency['company_name']) > 3:
                        agency['source'] = 'igz'
                        agency['scraped_date'] = datetime.now().isoformat()
                        agencies.append(agency)
                
                if agencies:
                    print(f"  Found {len(agencies)} entries")
                    break
                    
        except Exception as e:
            print(f"  Error: {e}")
            continue
    
    # Try API endpoint if exists
    if len(agencies) < 10:
        print("\nTrying iGZ API...")
        try:
            api_url = f"{base_url}/api/members"
            resp = requests.get(api_url, headers=HEADERS, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                for item in data:
                    agency = {
                        'company_name': to_ascii(item.get('name', '')),
                        'website': item.get('website', ''),
                        'city': to_ascii(item.get('city', '')),
                        'email': item.get('email', ''),
                        'source': 'igz',
                        'scraped_date': datetime.now().isoformat()
                    }
                    if agency['company_name']:
                        agencies.append(agency)
        except:
            pass
    
    return agencies


def scrape_google_maps_agencies(cities=None):
    """Scrape German staffing agencies from Google Maps."""
    print("=== Scraping Google Maps ===")
    
    if cities is None:
        cities = ['Berlin', 'Hamburg', 'Munchen', 'Koln', 'Frankfurt', 'Stuttgart', 
                  'Dusseldorf', 'Leipzig', 'Dortmund', 'Essen', 'Bremen', 'Dresden',
                  'Hannover', 'Nurnberg', 'Duisburg']
    
    agencies = []
    search_terms = ['Zeitarbeit', 'Personalvermittlung', 'Personaldienstleistung']
    
    # Note: This would need a proper Google Maps API key or scraper
    # For now, just return placeholder
    print("  Google Maps scraping requires API key - skipping")
    print("  Use: python3 /opt/ACTIVE/SCRAPERS/EUROPE/GOOGLE/GOOGLE_MAPS_SCRAPER/gmaps_scraper.py")
    
    return agencies


def enrich_with_impressum(agencies):
    """Add emails by scraping company websites (impressum pages)."""
    print(f"\n=== Enriching {len(agencies)} agencies with emails ===")
    
    enriched = 0
    
    for i, agency in enumerate(agencies):
        if agency.get('email'):
            continue
        
        website = agency.get('website')
        if not website:
            continue
        
        print(f"[{i+1}/{len(agencies)}] {agency['company_name'][:40]}...", end=" ")
        
        try:
            # Try impressum page
            domain = urlparse(website).netloc
            impressum_urls = [
                f"https://{domain}/impressum",
                f"https://{domain}/kontakt",
                f"https://{domain}/contact",
                f"https://{domain}/about",
                website
            ]
            
            for url in impressum_urls:
                try:
                    resp = requests.get(url, headers=HEADERS, timeout=10)
                    if resp.status_code == 200:
                        # Find email
                        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', resp.text)
                        # Filter out common non-contact emails
                        emails = [e for e in emails if not any(x in e.lower() for x in 
                                  ['example', 'test', 'noreply', 'wordpress', 'google', 'facebook'])]
                        
                        if emails:
                            agency['email'] = emails[0]
                            enriched += 1
                            print(f"OK: {emails[0]}")
                            break
                except:
                    continue
            else:
                print("No email found")
                
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(1)  # Rate limit
    
    print(f"\nEnriched {enriched} agencies with emails")
    return agencies


def save_results(agencies, filename):
    """Save agencies to CSV."""
    import csv
    
    if not agencies:
        print("No agencies to save")
        return
    
    output_file = OUTPUT_DIR / filename
    
    # Get all keys
    keys = set()
    for a in agencies:
        keys.update(a.keys())
    keys = sorted(keys)
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(agencies)
    
    print(f"\nSaved {len(agencies)} agencies to {output_file}")
    return output_file


def main():
    parser = argparse.ArgumentParser(description='Scrape German staffing agencies')
    parser.add_argument('--source', choices=['bap', 'igz', 'gmaps', 'all'], default='all',
                        help='Source to scrape')
    parser.add_argument('--enrich', action='store_true', help='Enrich with emails via impressum')
    parser.add_argument('--notify', action='store_true', help='Send Telegram notification')
    args = parser.parse_args()
    
    all_agencies = []
    
    if args.source in ['bap', 'all']:
        agencies = scrape_bap()
        print(f"BAP: {len(agencies)} agencies")
        all_agencies.extend(agencies)
        if agencies:
            save_results(agencies, 'bap_agencies.csv')
    
    if args.source in ['igz', 'all']:
        agencies = scrape_igz()
        print(f"iGZ: {len(agencies)} agencies")
        all_agencies.extend(agencies)
        if agencies:
            save_results(agencies, 'igz_agencies.csv')
    
    if args.source in ['gmaps', 'all']:
        agencies = scrape_google_maps_agencies()
        print(f"Google Maps: {len(agencies)} agencies")
        all_agencies.extend(agencies)
    
    # Dedupe by company name
    seen = set()
    unique = []
    for a in all_agencies:
        name_key = a.get('company_name', '').lower().strip()
        if name_key and name_key not in seen:
            seen.add(name_key)
            unique.append(a)
    
    print(f"\nTotal unique agencies: {len(unique)}")
    
    if args.enrich and unique:
        unique = enrich_with_impressum(unique)
    
    if unique:
        save_results(unique, f'germany_agencies_{datetime.now().strftime("%Y%m%d")}.csv')
    
    # Summary
    with_email = sum(1 for a in unique if a.get('email'))
    with_website = sum(1 for a in unique if a.get('website'))
    
    summary = f"""German Agencies Scrape Complete
Total: {len(unique)}
With email: {with_email}
With website: {with_website}
Output: {OUTPUT_DIR}"""
    
    print(f"\n{summary}")
    
    if args.notify:
        send_telegram(f"<b>German Agencies Scraper</b>\n{summary}")


if __name__ == "__main__":
    main()
