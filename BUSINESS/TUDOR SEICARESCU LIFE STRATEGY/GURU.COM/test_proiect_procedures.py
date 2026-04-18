#!/usr/bin/env python3
"""Test extracting procedure list from proiect page."""
import requests, re
from bs4 import BeautifulSoup
requests.packages.urllib3.disable_warnings()

r = requests.get("https://beneficiar.fonduri-ue.ro:8080/proiecte/details/1/15006/", verify=False, timeout=30)
soup = BeautifulSoup(r.text, "html.parser")

# Find the procedures section
print("=== Looking for procedure links ===")
for a in soup.find_all("a", href=True):
    if "anunturi/details" in a["href"]:
        print(f"  Link: {a.get_text(strip=True)[:80]} -> {a['href']}")

# Find procedure blocks with status
print("\n=== Full text around procedures ===")
text = soup.get_text()
idx = text.find("Proceduri de achizi")
if idx >= 0:
    print(text[idx:idx+2000])
else:
    # Try finding by structure
    for div in soup.find_all(["div", "ul", "li", "table"]):
        t = div.get_text(strip=True)
        if "ofertare" in t.lower() or "inchisa" in t.lower():
            if len(t) > 20 and len(t) < 3000:
                print(f"Found block ({div.name}): {t[:200]}")
                print()
