#!/usr/bin/env python3
"""Scrape ALL websites for contact info"""

import json
import re
import requests
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

INPUT = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_final/mercosur_all_20260322.json")
OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_final")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

def clean_url(url):
    if not url:
        return None
    url = str(url).strip()
    if not url.startswith('http'):
        url = f"https://{url}"
    return url

def scrape_one(company):
    """Scrape single company website"""
    website = company.get('website')
    if not website:
        return company

    url = clean_url(website)
    if not url:
        return company

    try:
        resp = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True, verify=False)
        if resp.status_code != 200:
            return company

        soup = BeautifulSoup(resp.text, 'html.parser')
        text = soup.get_text()

        # Get emails from mailto
        for link in soup.select('a[href^="mailto:"]'):
            email = link.get('href', '').replace('mailto:', '').split('?')[0].strip().lower()
            if '@' in email and '.' in email:
                if not any(x in email for x in ['example', 'test', '.png', '.jpg', 'sentry']):
                    company['email'] = email
                    break

        # Get emails from text
        if not company.get('email'):
            emails = EMAIL_RE.findall(text)
            for email in emails:
                email = email.lower()
                if not any(x in email for x in ['example', 'test', '.png', '.jpg', 'sentry', 'webpack']):
                    # Prefer contact/info emails
                    if any(x in email for x in ['contact', 'info', 'ventas', 'export', 'comercial']):
                        company['email'] = email
                        break
            if not company.get('email') and emails:
                company['email'] = emails[0].lower()

        # Try contact page
        if not company.get('email'):
            for link in soup.select('a'):
                href = str(link.get('href', '')).lower()
                if any(x in href for x in ['contact', 'contato', 'contacto']):
                    try:
                        if href.startswith('http'):
                            contact_url = href
                        else:
                            contact_url = url.rstrip('/') + '/' + href.lstrip('/')

                        cresp = requests.get(contact_url, headers=HEADERS, timeout=8, verify=False)
                        if cresp.status_code == 200:
                            csoup = BeautifulSoup(cresp.text, 'html.parser')
                            for clink in csoup.select('a[href^="mailto:"]'):
                                email = clink.get('href', '').replace('mailto:', '').split('?')[0].strip().lower()
                                if '@' in email:
                                    company['email'] = email
                                    break
                            if not company.get('email'):
                                cemails = EMAIL_RE.findall(csoup.get_text())
                                if cemails:
                                    company['email'] = cemails[0].lower()
                    except:
                        pass
                    break

        # Get phone from tel links
        if not company.get('phone'):
            for link in soup.select('a[href^="tel:"]'):
                phone = link.get('href', '').replace('tel:', '').strip()
                if len(phone) > 7:
                    company['phone'] = phone
                    break

        company['scraped'] = True

    except Exception as e:
        company['error'] = str(e)[:30]

    return company

def main():
    print("=== WEBSITE SCRAPER ===\n")

    # Suppress SSL warnings
    import urllib3
    urllib3.disable_warnings()

    with open(INPUT) as f:
        companies = json.load(f)

    with_website = [c for c in companies if c.get('website')]
    need_email = [c for c in with_website if not c.get('email')]

    print(f"Total: {len(companies)}")
    print(f"With website: {len(with_website)}")
    print(f"Need email: {len(need_email)}")

    before_email = sum(1 for c in companies if c.get('email'))

    print(f"\nScraping {len(need_email)} sites...\n")

    done = 0
    found = 0

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(scrape_one, c): c for c in need_email}

        for future in as_completed(futures):
            done += 1
            result = future.result()
            name = result.get('name', '')[:25]
            email = result.get('email', '')

            if email and not futures[future].get('email'):
                found += 1
                print(f"[{done}/{len(need_email)}] {name:25} -> {email}")
            elif done % 20 == 0:
                print(f"[{done}/{len(need_email)}] processed...")

    after_email = sum(1 for c in companies if c.get('email'))

    print(f"\n=== RESULTS ===")
    print(f"Scraped: {done}")
    print(f"New emails found: {found}")
    print(f"Total emails: {before_email} -> {after_email}")

    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    json_file = OUTPUT_DIR / f"mercosur_enriched_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump(companies, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {json_file}")

    # CSV
    import csv
    csv_file = OUTPUT_DIR / f"mercosur_enriched_{timestamp}.csv"
    fields = ['name', 'country', 'sector', 'website', 'email', 'phone', 'source']
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(companies)
    print(f"Saved: {csv_file}")

    # Contacts only
    contacts = [c for c in companies if c.get('email')]
    contacts_file = OUTPUT_DIR / f"mercosur_contacts_{timestamp}.csv"
    with open(contacts_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(contacts)
    print(f"Saved: {contacts_file} ({len(contacts)} contacts)")

if __name__ == "__main__":
    main()
