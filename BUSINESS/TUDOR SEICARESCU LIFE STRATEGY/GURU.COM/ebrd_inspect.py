#!/usr/bin/env python3
"""Inspect EBRD project pages to understand structure."""
import requests
from bs4 import BeautifulSoup

# Test a PSD page
for pid in [56433, 56000, 55000, 54000, 53000]:
    url = f"https://www.ebrd.com/home/work-with-us/projects/psd/{pid}.html"
    r = requests.get(url, timeout=30)
    if r.status_code != 200:
        print(f"{pid}: {r.status_code}")
        continue
    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text()
    # Find key fields
    print(f"\n=== PSD {pid} ===")
    for keyword in ["Company", "Client", "Sponsor", "Country", "Sector", "Amount",
                     "Contact", "Phone", "Email", "Status", "Signing", "Board"]:
        idx = text.find(keyword)
        if idx >= 0:
            snippet = text[idx:idx+100].replace("\n", " ").strip()
            print(f"  {snippet[:80]}")
    # Also check for structured data
    for div in soup.find_all(["div", "dd", "dt", "span", "p"]):
        t = div.get_text(strip=True)
        if any(k in t for k in ["client", "sponsor", "company", "€", "$", "EUR", "USD"]):
            if 10 < len(t) < 200:
                print(f"  [{div.name}] {t[:100]}")
