#!/usr/bin/env python3
import requests, re
from bs4 import BeautifulSoup
requests.packages.urllib3.disable_warnings()

# Test anunt page for SMIS code
r = requests.get("https://beneficiar.fonduri-ue.ro:8080/anunturi/details/2/51959/", verify=False, timeout=30)
m = re.search(r"Proiect\s*\[(\d+)\]", r.text)
print("SMIS:", m.group(1) if m else "not found")

soup = BeautifulSoup(r.text, "html.parser")
# Title
for div in soup.find_all("div", style=re.compile(r"background:#444")):
    full = div.get_text(strip=True)
    # Remove prefix like "Anunturi [proceduri de achizitie, beneficiari privati]"
    clean_title = re.sub(r"^Anun.*?privati\]?\s*", "", full, flags=re.I).strip()
    print("Raw title:", full[:100])
    print("Clean title:", clean_title[:100])

# Test proiect page for all fields
print("\n=== PROIECT ===")
r2 = requests.get("https://beneficiar.fonduri-ue.ro:8080/proiecte/details/1/17278/", verify=False, timeout=30)
soup2 = BeautifulSoup(r2.text, "html.parser")

# Find all key-value pairs
for li in soup2.find_all("li", class_="cat-list-row0"):
    strong = li.find("strong")
    div = li.find_next("div")
    if strong and div:
        key = strong.get_text(strip=True)
        val = div.get_text(strip=True)
        print(f"  {key}: {val[:80]}")

# Contact section
cdiv = soup2.find("div", {"id": "contact_benef"})
if cdiv:
    print("\nContact:")
    for li in cdiv.find_all("li"):
        print(f"  {li.get_text(strip=True)}")

# Title
t = soup2.find("title")
if t:
    title = t.get_text(strip=True)
    title = re.sub(r"^Proiecte\s*:?\s*", "", title)
    print(f"\nTitle: {title[:100]}")
