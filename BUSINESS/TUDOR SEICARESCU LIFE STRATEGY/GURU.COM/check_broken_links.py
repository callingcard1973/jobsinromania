#!/usr/bin/env python3
"""Check broken links on baneasa39.com"""
import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE = "https://baneasa39.com"
checked = set()
broken = []
ok = 0

def check_page(url, depth=0):
    global ok
    if url in checked or depth > 2:
        return
    checked.add(url)
    try:
        r = requests.get(url, timeout=15, allow_redirects=True)
        if r.status_code != 200:
            broken.append((url, r.status_code, "page"))
            print(f"  BROKEN {r.status_code}: {url}")
            return
        ok += 1
    except Exception as e:
        broken.append((url, str(e)[:50], "page"))
        print(f"  ERROR: {url} -> {e}")
        return

    if not url.startswith(BASE):
        return

    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup.find_all(["a", "img", "link", "script"]):
        href = tag.get("href") or tag.get("src")
        if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
            continue
        full = urljoin(url, href)
        if full in checked:
            continue
        # Only check internal links deeply, external just HEAD
        if full.startswith(BASE):
            check_page(full, depth + 1)
        else:
            checked.add(full)
            try:
                r2 = requests.head(full, timeout=10, allow_redirects=True)
                if r2.status_code >= 400:
                    broken.append((full, r2.status_code, f"linked from {url}"))
                    print(f"  BROKEN {r2.status_code}: {full} (from {url})")
                else:
                    ok += 1
            except Exception:
                pass

print(f"Checking {BASE}...")
check_page(BASE)
print(f"\nDone: {ok} OK, {len(broken)} broken, {len(checked)} checked")
if broken:
    print("\nBROKEN LINKS:")
    for url, status, source in broken:
        print(f"  {status}: {url} ({source})")
