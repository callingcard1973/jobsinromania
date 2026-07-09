#!/usr/bin/env python3
"""Scrape produsmontan.ro — all producers with contact details.

Iterates all listing pages, clicks each detail link, extracts producer
info (name, contact, address, county, ODM), groups products by producer.
Resumes from last completed page via scrape_state.txt.
"""
import csv
import json
import os
import re
import sys
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

BASE = "https://produsmontan.ro/produse_montane/"
DELAY = 2.5
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) RNPM-Scraper/1.0"
HEADERS = {"User-Agent": UA}
TODAY = datetime.now().strftime("%Y-%m-%d")
OUTFILE = f"rnpm_producers_{TODAY}.csv"
STATEFILE = "scrape_state.json"

FIELDS = [
    "producer_name", "products", "county", "odm",
    "address_punct_lucru", "address_sediu", "phone", "email",
    "product_urls", "scraped_at",
]

session = requests.Session()
session.headers.update(HEADERS)


def get_soup(url):
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


# -- Listing pages --
def get_total_pages():
    soup = get_soup(BASE)
    max_page = 1
    for a in soup.find_all("a", href=True):
        m = re.search(r"/page/(\d+)", a["href"])
        if m:
            max_page = max(max_page, int(m.group(1)))
    return max_page


def get_listing_items(page_num):
    """Extract product cards from a listing page."""
    url = BASE if page_num == 1 else f"{BASE}page/{page_num}/"
    soup = get_soup(url)
    items = []
    for div in soup.find_all("div", class_="ct-div-block"):
        text = div.get_text(" ", strip=True)
        if "Detalii" not in text:
            continue
        link = county = odm = title = None
        for a in div.find_all("a", href=True):
            href = a["href"]
            atxt = a.get_text(strip=True)
            if "/judet/" in href:
                county = atxt
            elif "/odm/" in href:
                odm = atxt
            elif "/produse_montane/" in href and "/page/" not in href:
                if not link:
                    link = href
                    title = atxt
        if link:
            items.append({
                "url": link, "title": title or "",
                "county": county or "", "odm": odm or "",
            })
    return items


# -- Detail page --
def scrape_detail(url):
    """Extract producer details from a product detail page."""
    soup = get_soup(url)

    h1s = soup.find_all("h1")
    title = h1s[1].get_text(strip=True) if len(h1s) > 1 else ""

    product_name, producer = title, ""
    for sep in [" - ", " – ", " — "]:
        if sep in title:
            product_name, producer = title.split(sep, 1)
            break

    fields = {}
    for strong in soup.find_all("strong"):
        label = strong.get_text(strip=True).rstrip(":")
        parent = strong.parent
        if parent:
            full = parent.get_text(strip=True)
            value = re.sub(rf"^{re.escape(label)}\s*:?\s*", "", full).strip()
            fields[label.lower()] = value

    producer2 = fields.get("producător", fields.get("producator", ""))
    if producer2:
        producer = producer2

    contact = fields.get("contact", "")
    addr_pl = fields.get("punct de lucru", "")
    addr_sed = fields.get("sediu social", "")

    phone = ""
    phone_m = re.search(r"(0\d{2,3}[\s.\-]?\d{3}[\s.\-]?\d{3,4})", contact)
    if phone_m:
        phone = phone_m.group(1).strip()

    email = ""
    email_m = re.search(r"[\w.\-+]+@[\w.\-]+\.\w{2,}", contact)
    if email_m:
        email = email_m.group(0)

    county = odm = ""
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/judet/" in href:
            county = a.get_text(strip=True)
        elif "/odm/" in href:
            odm = a.get_text(strip=True)

    return {
        "product_name": product_name.strip(),
        "producer_name": producer.strip(),
        "county": county, "odm": odm,
        "address_punct_lucru": addr_pl, "address_sediu": addr_sed,
        "phone": phone, "email": email,
    }


# -- State management --
def load_state():
    """Load producers dict + last page from JSON state."""
    try:
        with open(STATEFILE, encoding="utf-8") as f:
            state = json.load(f)
        return state.get("last_page", 0), state.get("producers", {}), set(state.get("seen_urls", []))
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        return 0, {}, set()


def save_state(page, producers, seen_urls):
    with open(STATEFILE, "w", encoding="utf-8") as f:
        json.dump({
            "last_page": page,
            "producers": producers,
            "seen_urls": list(seen_urls),
        }, f, ensure_ascii=False)


def write_csv(producers):
    """Write all producers to CSV (overwrites)."""
    with open(OUTFILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        ts = datetime.now().isoformat()
        for p in sorted(producers.values(), key=lambda x: x["producer_name"]):
            writer.writerow({
                "producer_name": p["producer_name"],
                "products": " | ".join(p.get("products", [])),
                "county": p.get("county", ""),
                "odm": p.get("odm", ""),
                "address_punct_lucru": p.get("address_punct_lucru", ""),
                "address_sediu": p.get("address_sediu", ""),
                "phone": p.get("phone", ""),
                "email": p.get("email", ""),
                "product_urls": " | ".join(p.get("product_urls", [])[:5]),
                "scraped_at": ts,
            })


def main():
    last_done, producers, seen_urls = load_state()
    start_page = int(sys.argv[1]) if len(sys.argv) > 1 else last_done + 1
    total = get_total_pages()
    print(f"{total} pages. Start: {start_page}. Resumed: {len(producers)} producers.")

    errors = 0
    details_fetched = 0
    for page in range(start_page, total + 1):
        print(f"P{page}/{total}", end=" ", flush=True)
        try:
            items = get_listing_items(page)
        except Exception as e:
            print(f"ERR listing: {e}")
            errors += 1
            time.sleep(DELAY * 2)
            continue

        new_on_page = 0
        for item in items:
            url = item["url"]
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # Parse producer name from listing title "PRODUCT - PRODUCER"
            title = item["title"]
            product_from_title, producer_from_title = title, ""
            for sep in [" - ", " – ", " — "]:
                if sep in title:
                    product_from_title, producer_from_title = title.split(sep, 1)
                    break

            # Known producer? Just add the product, skip detail page
            if producer_from_title and producer_from_title in producers:
                prod = producers[producer_from_title]
                if product_from_title and product_from_title not in prod["products"]:
                    prod["products"].append(product_from_title)
                if url not in prod["product_urls"]:
                    prod["product_urls"].append(url)
                continue

            # New producer — fetch detail page for contact info
            try:
                detail = scrape_detail(url)
                details_fetched += 1
            except Exception as e:
                print(f"\n  ERR {url}: {e}")
                errors += 1
                time.sleep(DELAY)
                continue

            name = detail["producer_name"] or producer_from_title or title
            if name not in producers:
                producers[name] = {
                    "producer_name": name, "products": [],
                    "county": detail["county"] or item["county"],
                    "odm": detail["odm"] or item["odm"],
                    "address_punct_lucru": detail["address_punct_lucru"],
                    "address_sediu": detail["address_sediu"],
                    "phone": detail["phone"], "email": detail["email"],
                    "product_urls": [],
                }
                new_on_page += 1

            prod = producers[name]
            pname = detail["product_name"]
            if pname and pname not in prod["products"]:
                prod["products"].append(pname)
            if url not in prod["product_urls"]:
                prod["product_urls"].append(url)

            time.sleep(DELAY)

        # Save state + CSV after each page
        save_state(page, producers, seen_urls)
        write_csv(producers)
        print(f"{len(items)}items +{new_on_page}new = {len(producers)} prod ({details_fetched} fetched)")
        time.sleep(DELAY)

    print(f"\nDone. {len(producers)} producers, {len(seen_urls)} products, {details_fetched} detail pages fetched, {errors} errors.")
    print(f"Output: {OUTFILE}")


if __name__ == "__main__":
    main()
