#!/usr/bin/env python3
import requests, re
from bs4 import BeautifulSoup
requests.packages.urllib3.disable_warnings()

for eid in [44949, 44951, 51376, 50962]:
    r = requests.get(f"https://beneficiar.fonduri-ue.ro:8080/anunturi/details/2/{eid}/", verify=False, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text()
    contractors = re.findall(r"Denumire contractor:\s*([^\n]+)", text)
    print(f"{eid}: {contractors}")
