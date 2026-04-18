#!/usr/bin/env python3
"""Quick test: DDG search -> website -> email extraction."""
import csv
import re
import time
import requests

ENRICHED = "/opt/ACTIVE/OPENDATA/DATA/SEAP_ENRICHED/seap_food_winners_enriched.csv"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0"

SKIP = {"listafirme.ro", "risco.ro", "firme.info", "termene.ro",
        "facebook.com", "linkedin.com", "google.com", "google.ro",
        "einformatii.ro", "duckduckgo.com", "anaf.ro", "seap.ro",
        "onrc.ro", "just.ro", "youtube.com", "instagram.com",
        "twitter.com", "wikipedia.org", "mfinante.gov.ro"}

with open(ENRICHED) as f:
    need = [(r["cui"], r["winner_name"]) for r in csv.DictReader(f)
            if not r.get("email") and ("SRL" in r.get("winner_name","").upper()
               or "S.R.L" in r.get("winner_name","").upper())]
need.sort(key=lambda x: x[0])

print(f"Testing 10 of {len(need)} SRLs")
for cui, name in need[:10]:
    # DDG search
    r = requests.post("https://html.duckduckgo.com/html/",
                      data={"q": f"{name} site:.ro"},
                      headers={"User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded"},
                      timeout=20)
    urls = re.findall(r'href="(https?://[^"]+)"', r.text)
    site = None
    for u in urls:
        dm = re.search(r'https?://(?:www\.)?([^/]+)', u)
        if dm and dm.group(1).lower() not in SKIP and ".ro" in dm.group(1).lower():
            site = u
            break

    if site:
        # Fetch website
        try:
            r2 = requests.get(site, headers={"User-Agent": UA}, timeout=10, allow_redirects=True)
            emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w]{2,}', r2.text)
            emails = [e.lower() for e in set(emails) if e.split("@")[1] not in SKIP]
            # Cloudflare decode
            cf = re.findall(r'data-cfemail="([0-9a-f]+)"', r2.text)
            for c in cf:
                try:
                    key = int(c[:2], 16)
                    d = "".join(chr(int(c[i:i+2], 16) ^ key) for i in range(2, len(c), 2))
                    if "@" in d:
                        emails.append(d)
                except Exception:
                    pass
            print(f"  {name[:35]:35s} -> {site[:40]} -> emails: {emails[:2]}")
        except Exception as ex:
            print(f"  {name[:35]:35s} -> {site[:40]} -> ERROR: {ex}")
    else:
        print(f"  {name[:35]:35s} -> no website found")

    time.sleep(3)
