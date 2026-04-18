#!/usr/bin/env python3
"""Lookup 2,186 SEAP food winners on listafirme.ro by CUI.

Run ON raspibig: python3 /tmp/listafirme_cui_lookup.py
Resumes from state file. Safe to interrupt and restart.

Rate: ~2.5s between requests = ~1,400/hour = finishes in ~1.5h
"""

import csv
import json
import os
import random
import re
import time
from pathlib import Path

try:
    import requests
except ImportError:
    import sys
    sys.exit("pip install requests")

ENRICHED = "/opt/ACTIVE/OPENDATA/DATA/SEAP_ENRICHED/seap_food_winners_enriched.csv"
COLS = ["winner_name", "cui", "email", "phone", "website",
        "city", "address", "sector", "wins", "total_value_ron", "match_source"]
STATE_FILE = "/opt/ACTIVE/OPENDATA/DATA/SEAP_ENRICHED/listafirme_state.json"
DELAY = 2.5

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
]


def fetch(url):
    headers = {
        "User-Agent": random.choice(UA_LIST),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "ro-RO,ro;q=0.9,en;q=0.8",
    }
    try:
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code == 200:
            return r.text
        if r.status_code == 429:
            print("  Rate limited, sleeping 120s...")
            time.sleep(120)
    except Exception as ex:
        print(f"  Fetch error: {ex}")
    return None


def extract_from_page(html):
    """Extract email, phone, website from listafirme company page."""
    data = {}
    # Email - mailto links
    em = re.search(r'mailto:([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,})', html)
    if em:
        data["email"] = em.group(1).lower()
    # Email - text pattern (backup)
    if "email" not in data:
        em2 = re.search(r'["\s>]([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.(?:ro|com|eu|net|org))', html)
        if em2:
            e = em2.group(1).lower()
            if "listafirme" not in e and "example" not in e:
                data["email"] = e
    # Phone
    ph = re.search(r'tel:(\+?[\d\s.-]{8,})', html)
    if ph:
        data["phone"] = re.sub(r'[\s.-]', '', ph.group(1))
    if "phone" not in data:
        ph2 = re.search(r'(?:Telefon|Tel)[:\s]*(\+?4?0\d[\d\s.-]{7,})', html, re.I)
        if ph2:
            data["phone"] = re.sub(r'[\s.-]', '', ph2.group(1))
    # Website
    ws = re.search(r'href="(https?://(?!(?:www\.)?listafirme|(?:www\.)?facebook|(?:www\.)?google)[^"]{5,})"[^>]*target="_blank"', html)
    if ws:
        data["website"] = ws.group(1)
    # Address
    addr = re.search(r'itemprop="address"[^>]*>([^<]+)', html)
    if addr:
        data["address"] = addr.group(1).strip()
    return data


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"done": [], "found": 0}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def main():
    # Load enriched
    enriched = {}
    with open(ENRICHED, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            enriched[row["cui"]] = row

    need = {c: r for c, r in enriched.items() if not r.get("email") and c}
    print(f"Total: {len(enriched)}, need email: {len(need)}")

    state = load_state()
    done_set = set(state.get("done", []))
    todo = [c for c in need if c not in done_set]
    print(f"Already checked: {len(done_set)}, remaining: {len(todo)}")

    hit = 0
    for i, cui in enumerate(todo):
        url = f"https://www.listafirme.ro/{cui}/"
        html = fetch(url)
        if html:
            data = extract_from_page(html)
            if data.get("email"):
                enriched[cui]["email"] = data["email"]
                enriched[cui]["match_source"] = "listafirme"
                hit += 1
            if data.get("phone") and not enriched[cui].get("phone"):
                enriched[cui]["phone"] = data["phone"]
            if data.get("website") and not enriched[cui].get("website"):
                enriched[cui]["website"] = data["website"]
            if data.get("address") and not enriched[cui].get("address"):
                enriched[cui]["address"] = data["address"]

        done_set.add(cui)

        # Progress + save every 50
        if (i + 1) % 50 == 0:
            state["done"] = list(done_set)
            state["found"] = hit
            save_state(state)
            we = sum(1 for r in enriched.values() if r.get("email"))
            print(f"  [{i+1}/{len(todo)}] listafirme: {hit} new emails, total: {we}")

        # Rate limit
        time.sleep(DELAY + random.uniform(0, 0.5))

        # Save enriched every 200
        if (i + 1) % 200 == 0:
            rows = sorted(enriched.values(), key=lambda x: -int(x.get("wins", 0)))
            with open(ENRICHED, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=COLS)
                w.writeheader()
                for r in rows:
                    w.writerow({c: r.get(c, "") for c in COLS})

    # Final save
    state["done"] = list(done_set)
    state["found"] = hit
    save_state(state)

    rows = sorted(enriched.values(), key=lambda x: -int(x.get("wins", 0)))
    with open(ENRICHED, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLS})

    total = len(enriched)
    we = sum(1 for r in enriched.values() if r.get("email"))
    wp = sum(1 for r in enriched.values() if r.get("phone"))
    print(f"\nListafirme: {hit} new emails")
    print(f"FINAL: {total} total, email: {we} ({100*we//total}%), phone: {wp} ({100*wp//total}%)")
    print(f"Saved: {ENRICHED}")


if __name__ == "__main__":
    main()
