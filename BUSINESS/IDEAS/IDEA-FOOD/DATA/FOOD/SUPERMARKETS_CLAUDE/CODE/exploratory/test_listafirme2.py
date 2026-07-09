#!/usr/bin/env python3
"""Test listafirme.ro - check HTML patterns for contact data."""
import re
import requests

headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0"}

# Strip RO prefix, use numeric CUI only
cui = "15779023"
url = f"https://www.listafirme.ro/{cui}/"
r = requests.get(url, headers=headers, timeout=20)
html = r.text
print(f"CUI {cui}: HTTP {r.status_code}, {len(html)} bytes")

# Search for any email-like patterns
emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}', html)
emails = [e for e in emails if "listafirme" not in e and "example" not in e]
print(f"Email patterns: {emails[:5]}")

# Search for phone patterns
phones = re.findall(r'(?:0[237]\d{8}|\+40\d{9})', html)
print(f"Phone patterns: {phones[:5]}")

# Look for "contact" or "telefon" sections
for pat in ["contact", "telefon", "email", "website", "site", "www\\."]:
    matches = re.findall(rf'.{{0,80}}{pat}.{{0,80}}', html, re.I)
    if matches:
        print(f"\n'{pat}' context ({len(matches)} hits):")
        for m in matches[:3]:
            clean = re.sub(r'<[^>]+>', ' ', m).strip()
            if clean:
                print(f"  {clean[:120]}")

# Also try risco.ro
print("\n--- RISCO.RO ---")
url2 = f"https://www.risco.ro/{cui}/"
r2 = requests.get(url2, headers=headers, timeout=20, allow_redirects=True)
print(f"risco: HTTP {r2.status_code}, {len(r2.text)} bytes")
if r2.status_code == 200:
    emails2 = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}', r2.text)
    emails2 = [e for e in emails2 if "risco" not in e]
    print(f"Emails: {emails2[:5]}")
    phones2 = re.findall(r'(?:0[237]\d{8}|\+40\d{9})', r2.text)
    print(f"Phones: {phones2[:5]}")
