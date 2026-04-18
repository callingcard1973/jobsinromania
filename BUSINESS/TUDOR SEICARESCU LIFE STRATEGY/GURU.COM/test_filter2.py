#!/usr/bin/env python3
import requests, re
from bs4 import BeautifulSoup
requests.packages.urllib3.disable_warnings()
BASE = "https://beneficiar.fonduri-ue.ro:8080"

r = requests.get(f"{BASE}/anunturi/2/entry?search_form_id=2", verify=False, timeout=30)
soup = BeautifulSoup(r.text, "html.parser")

# Find ALL selects on the page
for s in soup.find_all("select"):
    name = s.get("name", "")
    opts = [(o.get("value", ""), o.get_text(strip=True)) for o in s.find_all("option")]
    # Only show selects with interesting options
    if len(opts) > 1 and len(opts) < 50:
        print(f"SELECT name={name}: {opts}")
    elif len(opts) >= 50:
        print(f"SELECT name={name}: {len(opts)} options (first 3: {opts[:3]})")
    print()

# Find all hidden inputs
print("=== Hidden inputs ===")
for inp in soup.find_all("input", type="hidden"):
    name = inp.get("name", "")
    val = inp.get("value", "")
    if name:
        print(f"  {name} = {val}")
