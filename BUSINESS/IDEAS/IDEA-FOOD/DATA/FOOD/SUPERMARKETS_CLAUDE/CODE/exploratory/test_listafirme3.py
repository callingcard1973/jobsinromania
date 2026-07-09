#!/usr/bin/env python3
"""Test listafirme.ro search by CUI."""
import re
import requests

headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0"}

cui = "15779023"

# Try search
url = f"https://www.listafirme.ro/{cui}"
print(f"Try 1: {url}")
r = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
print(f"  HTTP {r.status_code}, {len(r.text)} bytes, final URL: {r.url}")

# Try search page
url2 = f"https://www.listafirme.ro/cautare?query={cui}"
print(f"\nTry 2: {url2}")
r2 = requests.get(url2, headers=headers, timeout=20, allow_redirects=True)
print(f"  HTTP {r2.status_code}, {len(r2.text)} bytes")
# Find company links
links = re.findall(r'href="(/[^"]+' + cui + r'[^"]*)"', r2.text)
print(f"  Links with CUI: {links[:5]}")

# Also try with firma prefix
url3 = f"https://www.listafirme.ro/firma/{cui}"
print(f"\nTry 3: {url3}")
r3 = requests.get(url3, headers=headers, timeout=20, allow_redirects=True)
print(f"  HTTP {r3.status_code}, {len(r3.text)} bytes, final URL: {r3.url}")

# Try Google-like search within listafirme
url4 = f"https://www.listafirme.ro/search.asp?q={cui}"
print(f"\nTry 4: {url4}")
r4 = requests.get(url4, headers=headers, timeout=20, allow_redirects=True)
print(f"  HTTP {r4.status_code}, {len(r4.text)} bytes, final URL: {r4.url}")

# If any of them worked, look for contact info
for label, resp in [("try2", r2), ("try3", r3)]:
    if resp.status_code == 200 and len(resp.text) > 1000:
        emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}', resp.text)
        emails = [e for e in emails if "listafirme" not in e]
        phones = re.findall(r'(?:0[237]\d{8}|\+40\d{9})', resp.text)
        title = re.search(r'<title>([^<]+)', resp.text)
        print(f"\n{label} content:")
        print(f"  title: {title.group(1)[:80] if title else 'none'}")
        print(f"  emails: {emails[:5]}")
        print(f"  phones: {phones[:5]}")
        # Find the actual company page link
        firm_links = re.findall(r'href="(/[^"]*-\d{6,10})"', resp.text)
        print(f"  firm links: {firm_links[:5]}")
