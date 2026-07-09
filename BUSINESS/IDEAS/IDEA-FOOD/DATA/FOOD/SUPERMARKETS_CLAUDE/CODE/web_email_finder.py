#!/usr/bin/env python3
"""Find emails by scraping company websites found via DDG.

Step 1: DDG search -> find company website URL
Step 2: Fetch website contact/about page -> extract email

Run ON raspibig: python3 /tmp/web_email_finder.py
Resumes from state. Targets SRL companies only (best ROI).
"""

import csv
import json
import os
import re
import time
import random

try:
    import requests
except ImportError:
    import sys
    sys.exit("pip install requests")

ENRICHED = "/opt/ACTIVE/OPENDATA/DATA/SEAP_ENRICHED/seap_food_winners_enriched.csv"
COLS = ["winner_name", "cui", "email", "phone", "website",
        "city", "address", "sector", "wins", "total_value_ron", "match_source"]
STATE_FILE = "/opt/ACTIVE/OPENDATA/DATA/SEAP_ENRICHED/web_finder_state.json"
DELAY = 3.5

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0"

SKIP_DOMAINS = {
    "listafirme.ro", "risco.ro", "firme.info", "termene.ro",
    "einformatii.ro", "facebook.com", "linkedin.com", "twitter.com",
    "youtube.com", "google.com", "google.ro", "instagram.com",
    "tiktok.com", "wikipedia.org", "duckduckgo.com", "anaf.ro",
    "mfinante.gov.ro", "onrc.ro", "just.ro", "seap.ro",
}

CONTACT_PAGES = ["contact", "despre", "about", "contacte", "about-us"]


def ddg_find_website(company_name):
    """Search DDG for company website."""
    headers = {"User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded"}
    query = f"{company_name} site:.ro"
    try:
        r = requests.post("https://html.duckduckgo.com/html/",
                          data={"q": query}, headers=headers, timeout=20)
        if r.status_code != 200:
            return None
        # Extract URLs from results
        urls = re.findall(r'href="(https?://[^"]+)"', r.text)
        for url in urls:
            domain = re.search(r'https?://(?:www\.)?([^/]+)', url)
            if domain:
                d = domain.group(1).lower()
                if d not in SKIP_DOMAINS and ".ro" in d:
                    return url
    except Exception:
        pass
    return None


def extract_emails_from_page(url):
    """Fetch a page and extract email addresses."""
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=15,
                         allow_redirects=True)
        if r.status_code != 200:
            return [], None
        html = r.text
        emails = re.findall(
            r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}', html)
        # Decode Cloudflare email protection
        cf_matches = re.findall(
            r'data-cfemail="([0-9a-f]+)"', html)
        for cf in cf_matches:
            try:
                key = int(cf[:2], 16)
                decoded = ""
                for i in range(2, len(cf), 2):
                    decoded += chr(int(cf[i:i+2], 16) ^ key)
                if "@" in decoded:
                    emails.append(decoded)
            except Exception:
                pass
        # Filter
        valid = []
        for e in set(emails):
            e = e.lower().strip()
            domain = e.split("@")[1] if "@" in e else ""
            if (domain and domain not in SKIP_DOMAINS
                    and len(e) < 60 and "example" not in e
                    and not e.startswith("wixpress")):
                valid.append(e)
        # Extract phone
        phones = re.findall(r'(?:0[237]\d{8}|\+40\s?\d{9})', html)
        phone = re.sub(r'\s', '', phones[0]) if phones else None
        return valid, phone
    except Exception:
        return [], None


def scrape_contact_page(base_url):
    """Try to find and scrape contact page."""
    from urllib.parse import urljoin
    # First try base URL
    emails, phone = extract_emails_from_page(base_url)
    if emails:
        return emails, phone, base_url
    # Try contact pages
    for page in CONTACT_PAGES:
        contact_url = urljoin(base_url + "/", page)
        emails, phone = extract_emails_from_page(contact_url)
        if emails:
            return emails, phone, contact_url
        time.sleep(0.5)
    return [], phone, base_url


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"done": [], "found": 0, "websites": 0}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def main():
    enriched = {}
    with open(ENRICHED, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            enriched[row["cui"]] = row

    # Target SRL companies without email, sorted by wins (highest first)
    need = [(c, r) for c, r in enriched.items()
            if not r.get("email") and c
            and ("SRL" in r.get("winner_name", "").upper()
                 or "S.R.L" in r.get("winner_name", "").upper())]
    need.sort(key=lambda x: -int(x[1].get("wins", 0)))
    print(f"SRL companies without email: {len(need)}")

    state = load_state()
    done_set = set(state.get("done", []))
    todo = [(c, r) for c, r in need if c not in done_set]
    print(f"Already done: {len(done_set)}, remaining: {len(todo)}")

    hit = 0
    websites_found = 0

    for i, (cui, r) in enumerate(todo):
        name = r.get("winner_name", "").strip()
        if not name:
            done_set.add(cui)
            continue

        # Step 1: Find website via DDG
        website_url = ddg_find_website(name)
        time.sleep(1)

        if website_url:
            websites_found += 1
            # Step 2: Scrape website for email
            emails, phone, src = scrape_contact_page(website_url)
            if emails:
                enriched[cui]["email"] = emails[0]
                enriched[cui]["match_source"] = "web_scrape"
                hit += 1
            if not enriched[cui].get("website"):
                domain = re.search(r'https?://(?:www\.)?([^/]+)', website_url)
                if domain:
                    enriched[cui]["website"] = f"https://{domain.group(1)}"
            if phone and not enriched[cui].get("phone"):
                enriched[cui]["phone"] = phone

        done_set.add(cui)

        if (i + 1) % 25 == 0:
            state["done"] = list(done_set)
            state["found"] = state.get("found", 0) + hit
            state["websites"] = state.get("websites", 0) + websites_found
            save_state(state)
            we = sum(1 for r in enriched.values() if r.get("email"))
            print(f"  [{i+1}/{len(todo)}] sites={websites_found} emails={hit} total={we}")
            hit_reset, websites_found = hit, 0
            hit = 0

        if (i + 1) % 100 == 0:
            rows = sorted(enriched.values(), key=lambda x: -int(x.get("wins", 0)))
            with open(ENRICHED, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=COLS)
                w.writeheader()
                for rv in rows:
                    w.writerow({c: rv.get(c, "") for c in COLS})

        time.sleep(DELAY + random.uniform(0, 1))

    # Final save
    state["done"] = list(done_set)
    save_state(state)

    rows = sorted(enriched.values(), key=lambda x: -int(x.get("wins", 0)))
    with open(ENRICHED, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for rv in rows:
            w.writerow({c: rv.get(c, "") for c in COLS})

    total = len(enriched)
    we = sum(1 for r in enriched.values() if r.get("email"))
    wp = sum(1 for r in enriched.values() if r.get("phone"))
    print(f"\nFINAL: {total} total, email: {we} ({100*we//total}%), phone: {wp}")
    print(f"Saved: {ENRICHED}")


if __name__ == "__main__":
    main()
