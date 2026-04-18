#!/usr/bin/env python3
"""Debug overview extraction from EBRD pages."""
import requests, re
from bs4 import BeautifulSoup

sess = requests.Session()
sess.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0'

for pid in [55644, 56000, 40004, 40008]:
    r = sess.get(f"https://www.ebrd.com/home/work-with-us/projects/psd/{pid}.html", timeout=30)
    if r.status_code != 200:
        print(f"{pid}: HTTP {r.status_code}")
        continue
    soup = BeautifulSoup(r.text, "html.parser")

    print(f"\n=== PSD {pid} ===")

    # Find all h2 headings
    for h2 in soup.find_all("h2"):
        print(f"  H2: {h2.get_text(strip=True)[:60]}")

    # Find the Overview section specifically
    overview_h2 = soup.find("h2", string=re.compile(r"Overview"))
    if overview_h2:
        print(f"  Found Overview h2")
        # Get all next siblings until next h2
        for sib in overview_h2.find_next_siblings():
            if sib.name == "h2":
                break
            t = sib.get_text(strip=True)
            if t and len(t) > 20:
                print(f"  [{sib.name}] {t[:150]}")
    else:
        print("  NO Overview h2 found")
        # Try finding description in article-content or similar
        for cls in ["text-block", "article-content", "project-description", "content"]:
            divs = soup.find_all(["div", "section"], class_=re.compile(cls, re.I))
            for div in divs:
                t = div.get_text(strip=True)
                if 50 < len(t) < 2000 and "cookie" not in t.lower():
                    print(f"  [{cls}] {t[:200]}")

    import time; time.sleep(3)
