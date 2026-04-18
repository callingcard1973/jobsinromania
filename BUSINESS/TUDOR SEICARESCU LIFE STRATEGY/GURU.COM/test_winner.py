#!/usr/bin/env python3
"""Check if closed anunturi show winner/atribuire info."""
import requests, re
from bs4 import BeautifulSoup
requests.packages.urllib3.disable_warnings()

# Check a closed procedure from the project above
for eid in [51376, 50962, 44951]:  # closed anunturi
    r = requests.get(f"https://beneficiar.fonduri-ue.ro:8080/anunturi/details/2/{eid}/", verify=False, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text()
    # Look for winner/atribuire info
    for keyword in ["atribui", "castigat", "winner", "furnizor", "contractant", "adjudecat"]:
        idx = text.lower().find(keyword)
        if idx >= 0:
            print(f"{eid} [{keyword}]: ...{text[max(0,idx-20):idx+100]}...")
    # Check for any company name after "atribuire"
    m = re.search(r"[Aa]tribui[retă]*[^A-Z]*([A-Z][A-Z\s\-\.]+(?:SRL|SA|S\.R\.L))", text)
    if m:
        print(f"{eid} WINNER: {m.group(1)}")
    # Check all table rows for atribuire
    for td in soup.find_all("td"):
        t = td.get_text(strip=True)
        if "tribui" in t.lower() or "castig" in t.lower():
            nxt = td.find_next_sibling("td")
            if nxt:
                print(f"{eid} TD: {t} -> {nxt.get_text(strip=True)[:100]}")
    print()
