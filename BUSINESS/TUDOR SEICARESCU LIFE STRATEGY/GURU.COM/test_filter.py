#!/usr/bin/env python3
"""Find the correct POST form to filter open anunturi."""
import requests
import re
from bs4 import BeautifulSoup

requests.packages.urllib3.disable_warnings()
BASE = "https://beneficiar.fonduri-ue.ro:8080"

r = requests.get(f"{BASE}/anunturi/2/entry?search_form_id=2", verify=False, timeout=30)
soup = BeautifulSoup(r.text, "html.parser")

# Find the search form
for form in soup.find_all("form"):
    fields = form.find_all(["input", "select"])
    names = [f.get("name", "") for f in fields]
    if any("inchis" in n.lower() or "closed" in n.lower() for n in names):
        print(f"Found search form: method={form.get('method')} action={form.get('action')}")
        for f in fields:
            name = f.get("name", "")
            if not name:
                continue
            if f.name == "select":
                opts = [(o.get("value", ""), o.get_text(strip=True)) for o in f.find_all("option")]
                print(f"  SELECT {name}: {opts}")
            else:
                print(f"  {f.get('type','')} {name} = {f.get('value','')}")

# Try POST with procedura_inchisa = Nu
print("\n=== Testing POST ===")
# Collect all form data
form_data = {}
for f in fields:
    name = f.get("name", "")
    if not name:
        continue
    if f.name == "select":
        # Find the "Nu" option for inchisa
        for o in f.find_all("option"):
            if "nu" in o.get_text(strip=True).lower() and "inchis" in name.lower():
                form_data[name] = o.get("value", "")
    elif f.get("type") == "hidden":
        form_data[name] = f.get("value", "")

print(f"Form data: {form_data}")

r2 = requests.post(f"{BASE}/anunturi/2/entry?search_form_id=2", data=form_data, verify=False, timeout=30)
pages = re.findall(r"start=(\d+)", r2.text)
max_p = max(int(p) for p in pages) if pages else 0
m = re.search(r"Pagina \d+ din (\d+)", r2.text)
total_pages = m.group(1) if m else "?"
items = re.findall(r"details/2/(\d+)", r2.text)
print(f"Result: {total_pages} pages, {len(items)} items, max_start={max_p}")
print(f"Estimated total: {max_p + len(items)}")
