#!/usr/bin/env python3
"""Scrape company websites for contact info"""

import json
import re
import time
import requests
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

INPUT_FILE = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_master/mercosur_all_producers_20260322.json")
OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_master")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"
}

EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PHONE_REGEX = re.compile(r'[\+]?[(]?[0-9]{1,4}[)]?[-\s\./0-9]{7,}')

def clean_url(website):
    """Clean and format URL"""
    if not website:
        return None
    website = website.strip().lower()
    if not website.startswith('http'):
        website = f"https://www.{website}"
    return website

def extract_emails(text, soup):
    """Extract emails from text and mailto links"""
    emails = set()

    # From mailto links
    for link in soup.select('a[href^="mailto:"]'):
        href = link.get('href', '')
        email = href.replace('mailto:', '').split('?')[0].strip()
        if '@' in email and '.' in email:
            emails.add(email.lower())

    # From text
    for match in EMAIL_REGEX.findall(text):
        if not any(x in match.lower() for x in ['example', 'test', 'domain', '.png', '.jpg', '.gif']):
            emails.add(match.lower())

    return list(emails)

def extract_phones(text, soup):
    """Extract phone numbers"""
    phones = set()

    # From tel links
    for link in soup.select('a[href^="tel:"]'):
        href = link.get('href', '')
        phone = href.replace('tel:', '').strip()
        if len(phone) > 7:
            phones.add(phone)

    # From text - look for patterns
    for match in PHONE_REGEX.findall(text):
        clean = re.sub(r'[^\d+]', '', match)
        if 8 <= len(clean) <= 15:
            phones.add(match.strip())

    return list(phones)[:3]  # Limit to 3

def scrape_website(company):
    """Scrape a single company website"""
    website = company.get('website')
    if not website:
        return company

    url = clean_url(website)
    if not url:
        return company

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        if resp.status_code != 200:
            # Try without www
            alt_url = url.replace('://www.', '://')
            resp = requests.get(alt_url, headers=HEADERS, timeout=10, allow_redirects=True)

        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            text = soup.get_text()

            # Extract emails
            emails = extract_emails(text, soup)
            if emails and not company.get('email'):
                # Prefer contact/info emails
                for e in emails:
                    if any(x in e for x in ['contact', 'info', 'ventas', 'comercial', 'export']):
                        company['email'] = e
                        break
                if not company.get('email'):
                    company['email'] = emails[0]

            # Extract phones
            phones = extract_phones(text, soup)
            if phones and not company.get('phone'):
                company['phone'] = phones[0]

            # Try contact page
            if not company.get('email'):
                for link in soup.select('a'):
                    href = link.get('href', '').lower()
                    if any(x in href for x in ['contact', 'contato', 'contacto', 'fale']):
                        contact_url = href if href.startswith('http') else url.rstrip('/') + '/' + href.lstrip('/')
                        try:
                            contact_resp = requests.get(contact_url, headers=HEADERS, timeout=8)
                            if contact_resp.status_code == 200:
                                contact_soup = BeautifulSoup(contact_resp.text, 'html.parser')
                                contact_emails = extract_emails(contact_soup.get_text(), contact_soup)
                                if contact_emails:
                                    company['email'] = contact_emails[0]
                                    break
                        except:
                            pass

            company['website_scraped'] = True

    except Exception as e:
        company['scrape_error'] = str(e)[:50]

    return company

def main():
    print("=== Website Scraper ===\n")

    with open(INPUT_FILE) as f:
        producers = json.load(f)

    # Filter to those with websites
    with_website = [p for p in producers if p.get('website')]
    print(f"Total producers: {len(producers)}")
    print(f"With website: {len(with_website)}")

    # Count before
    before_email = sum(1 for p in producers if p.get('email'))
    before_phone = sum(1 for p in producers if p.get('phone'))
    print(f"Before - emails: {before_email}, phones: {before_phone}")

    print(f"\nScraping {len(with_website)} websites...\n")

    scraped = 0
    errors = 0

    # Scrape with thread pool
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(scrape_website, p): p for p in with_website}

        for future in as_completed(futures):
            scraped += 1
            result = future.result()
            name = result.get('name', '')[:30]
            email = result.get('email', '')

            if result.get('scrape_error'):
                errors += 1
                status = f"ERR: {result['scrape_error'][:20]}"
            elif email:
                status = f"OK: {email}"
            else:
                status = "OK: no email found"

            print(f"[{scraped}/{len(with_website)}] {name:30} | {status}")

    # Count after
    after_email = sum(1 for p in producers if p.get('email'))
    after_phone = sum(1 for p in producers if p.get('phone'))

    print(f"\n=== RESULTS ===")
    print(f"Scraped: {scraped}")
    print(f"Errors: {errors}")
    print(f"Emails: {before_email} -> {after_email} (+{after_email - before_email})")
    print(f"Phones: {before_phone} -> {after_phone} (+{after_phone - before_phone})")

    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_file = OUTPUT_DIR / f"mercosur_scraped_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(producers, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {output_file}")

    # CSV too
    import csv
    csv_file = OUTPUT_DIR / f"mercosur_scraped_{timestamp}.csv"
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['name','country','sector','website','email','phone','source'], extrasaction='ignore')
        writer.writeheader()
        writer.writerows(producers)
    print(f"Saved: {csv_file}")

if __name__ == "__main__":
    main()
