#!/usr/bin/env python3
"""Search DuckDuckGo for remaining SEAP winner emails.

Run ON raspibig: python3 /tmp/ddg_email_search.py
Resumes from state. Safe to interrupt.

Rate: ~3s/query. For 2,090 companies = ~1.7 hours.
"""

import csv
import json
import os
import re
import time
import random
import unicodedata

try:
    import requests
except ImportError:
    import sys
    sys.exit("pip install requests")

ENRICHED = "/opt/ACTIVE/OPENDATA/DATA/SEAP_ENRICHED/seap_food_winners_enriched.csv"
COLS = ["winner_name", "cui", "email", "phone", "website",
        "city", "address", "sector", "wins", "total_value_ron", "match_source"]
STATE_FILE = "/opt/ACTIVE/OPENDATA/DATA/SEAP_ENRICHED/ddg_search_state.json"
DELAY = 3.0

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119.0.0.0",
]

# Domains to skip in email results
SKIP_DOMAINS = {
    "example.com", "listafirme.ro", "risco.ro", "firme.info",
    "termene.ro", "einformatii.ro", "srl.ro", "google.com",
    "facebook.com", "linkedin.com", "twitter.com", "youtube.com",
}


def clean_name(name):
    """Clean company name for search."""
    if not name:
        return ""
    name = unicodedata.normalize("NFKD", str(name))
    name = name.encode("ascii", "ignore").decode("ascii").strip()
    for s in [" S.R.L.", " SRL", " S.A.", " SA", " S.C.", " SC",
              " II", " PFA", " IF"]:
        if name.upper().endswith(s):
            name = name[:-len(s)].strip()
    if name.upper().startswith("SC "):
        name = name[3:]
    if name.upper().startswith("S.C. "):
        name = name[5:]
    return name.strip()


def ddg_search(query):
    """Search DuckDuckGo HTML and extract emails from snippets."""
    url = "https://html.duckduckgo.com/html/"
    headers = {
        "User-Agent": random.choice(UA_LIST),
        "Accept": "text/html",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    try:
        r = requests.post(url, data={"q": query}, headers=headers, timeout=20)
        if r.status_code == 200:
            # Extract emails from results
            emails = re.findall(
                r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}', r.text)
            valid = []
            for e in emails:
                e = e.lower()
                domain = e.split("@")[1]
                if domain not in SKIP_DOMAINS and len(e) < 60:
                    valid.append(e)
            # Extract phone numbers from snippets
            phones = re.findall(r'(?:0[237]\d{8}|\+40\d{9})', r.text)
            return list(set(valid)), list(set(phones))
        if r.status_code == 429 or r.status_code == 202:
            print("  DDG rate limited, sleeping 60s...")
            time.sleep(60)
    except Exception as ex:
        print(f"  DDG error: {ex}")
    return [], []


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
    enriched = {}
    with open(ENRICHED, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            enriched[row["cui"]] = row

    need = [(c, r) for c, r in enriched.items() if not r.get("email") and c]
    print(f"Total: {len(enriched)}, need email: {len(need)}")

    state = load_state()
    done_set = set(state.get("done", []))
    todo = [(c, r) for c, r in need if c not in done_set]
    print(f"Already searched: {len(done_set)}, remaining: {len(todo)}")

    hit = 0
    for i, (cui, r) in enumerate(todo):
        name = clean_name(r.get("winner_name", ""))
        if not name or len(name) < 3:
            done_set.add(cui)
            continue

        query = f'"{name}" email Romania'
        emails, phones = ddg_search(query)

        if emails:
            enriched[cui]["email"] = emails[0]
            enriched[cui]["match_source"] = "ddg_search"
            hit += 1
        if phones and not enriched[cui].get("phone"):
            enriched[cui]["phone"] = phones[0]

        done_set.add(cui)

        if (i + 1) % 50 == 0:
            state["done"] = list(done_set)
            state["found"] = hit
            save_state(state)
            we = sum(1 for r in enriched.values() if r.get("email"))
            print(f"  [{i+1}/{len(todo)}] DDG: {hit} new, total: {we}")

        if (i + 1) % 200 == 0:
            rows = sorted(enriched.values(), key=lambda x: -int(x.get("wins", 0)))
            with open(ENRICHED, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=COLS)
                w.writeheader()
                for r in rows:
                    w.writerow({c: r.get(c, "") for c in COLS})

        time.sleep(DELAY + random.uniform(0, 1))

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
    print(f"\nDDG search: {hit} new emails")
    print(f"FINAL: {total} total, email: {we} ({100*we//total}%), phone: {wp}")
    print(f"Saved: {ENRICHED}")


if __name__ == "__main__":
    main()
