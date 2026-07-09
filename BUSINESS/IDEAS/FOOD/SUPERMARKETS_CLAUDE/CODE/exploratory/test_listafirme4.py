#!/usr/bin/env python3
"""Find correct listafirme URL pattern and try other sources."""
import re
import requests

H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0"}

cui = "15779023"
name = "STEDYAN COM SRL"

# 1. listafirme search - check all href patterns
r = requests.get(f"https://www.listafirme.ro/cautare?query={cui}", headers=H, timeout=20)
print(f"listafirme search: {r.status_code}, {len(r.text)} bytes")
all_hrefs = re.findall(r'href="(/[^"]+)"', r.text)
firma_hrefs = [h for h in all_hrefs if "/firma/" in h or cui in h or "stedyan" in h.lower()]
print(f"  firma hrefs: {firma_hrefs[:10]}")
# Also get all hrefs containing digits
digit_hrefs = [h for h in all_hrefs if re.search(r'\d{6,}', h)]
print(f"  digit hrefs: {digit_hrefs[:10]}")

# 2. Try termene.ro
print("\n--- termene.ro ---")
r2 = requests.get(f"https://termene.ro/firma/{cui}", headers=H, timeout=20, allow_redirects=True)
print(f"  HTTP {r2.status_code}, {len(r2.text)} bytes, url: {r2.url}")
if r2.status_code == 200:
    emails = [e for e in re.findall(r'[\w.+-]+@[\w-]+\.[\w]{2,}', r2.text) if "termene" not in e]
    print(f"  emails: {emails[:5]}")

# 3. Try firme.info
print("\n--- firme.info ---")
r3 = requests.get(f"https://www.firme.info/firma/{cui}", headers=H, timeout=20, allow_redirects=True)
print(f"  HTTP {r3.status_code}, {len(r3.text)} bytes, url: {r3.url}")

# 4. Try einformatii.ro
print("\n--- einformatii.ro ---")
r4 = requests.get(f"https://www.einformatii.ro/cui/{cui}", headers=H, timeout=20, allow_redirects=True)
print(f"  HTTP {r4.status_code}, {len(r4.text)} bytes, url: {r4.url}")
if r4.status_code == 200 and len(r4.text) > 5000:
    emails = [e for e in re.findall(r'[\w.+-]+@[\w-]+\.[\w]{2,}', r4.text) if "einformatii" not in e]
    phones = re.findall(r'(?:0[237]\d{8}|\+40\d{9})', r4.text)
    print(f"  emails: {emails[:5]}")
    print(f"  phones: {phones[:5]}")

# 5. Try mfinante.gov.ro
print("\n--- mfinante.gov.ro ---")
r5 = requests.get(f"https://www.mfinante.gov.ro/domeniu_principal.html?cui={cui}", headers=H, timeout=20, allow_redirects=True)
print(f"  HTTP {r5.status_code}, {len(r5.text)} bytes")
