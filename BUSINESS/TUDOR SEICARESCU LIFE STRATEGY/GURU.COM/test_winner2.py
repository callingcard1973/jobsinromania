#!/usr/bin/env python3
import requests, re
from bs4 import BeautifulSoup
requests.packages.urllib3.disable_warnings()

r = requests.get("https://beneficiar.fonduri-ue.ro:8080/anunturi/details/2/51376/", verify=False, timeout=30)
soup = BeautifulSoup(r.text, "html.parser")

# Find all links
print("=== All links with atribui/lot/contract ===")
for a in soup.find_all("a", href=True):
    href = a["href"]
    text = a.get_text(strip=True)
    if any(k in href.lower() + text.lower() for k in ["atribu", "lot", "contract", "castig", "ofert"]):
        print(f"  {text[:50]} -> {href}")

# Find atribuire section
print("\n=== Text around Atribuire ===")
text = soup.get_text()
idx = text.find("Atribuire")
if idx >= 0:
    print(text[idx:idx+500])

# Check for lot-result or similar endpoints
print("\n=== All interesting links ===")
for a in soup.find_all("a", href=True):
    href = a["href"]
    if href.startswith("/") and "details" not in href and href != "/":
        print(f"  {a.get_text(strip=True)[:40]} -> {href}")
