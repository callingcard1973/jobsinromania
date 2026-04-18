#!/usr/bin/env python3
"""Scrape last 2 weeks directly by browsing recent pages."""
import requests
import re
import psycopg2
import csv
from bs4 import BeautifulSoup
from parsers import parse_anunt, decode_email, normalize_phone, to_ascii

requests.packages.urllib3.disable_warnings()
BASE = "https://beneficiar.fonduri-ue.ro:8080"
DB = {"dbname": "european_funds", "user": "tudor", "host": "/var/run/postgresql", "port": 5432}
OUT = "/opt/ACTIVE/INFRA/SKILLS/eu_funding_anunturi_2w.csv"

conn = psycopg2.connect(**DB)
cur = conn.cursor()
rows_saved = []

# Scrape first 30 pages (most recent 300 entries)
for page in range(30):
    url = f"{BASE}/anunturi?start={page * 10}"
    r = requests.get(url, verify=False, timeout=30)
    ids = [int(m) for m in re.findall(r"details/2/(\d+)", r.text)]
    if not ids:
        break
    # Extract dates from listing
    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table")
    listing_dates = {}
    if table:
        for row in table.find_all("tr")[1:]:
            cells = row.find_all("td")
            if len(cells) >= 4:
                link = cells[0].find("a", href=True)
                if link and "details/2/" in link["href"]:
                    eid = link["href"].split("/")[-2]
                    listing_dates[eid] = {
                        "data_publicare": cells[3].get_text(strip=True) if len(cells) > 3 else "",
                        "data_limita": cells[4].get_text(strip=True) if len(cells) > 4 else "",
                    }

    for eid in ids:
        detail_url = f"{BASE}/anunturi/details/2/{eid}/"
        dr = requests.get(detail_url, verify=False, timeout=30)
        d = parse_anunt(dr.text, eid, listing_dates.get(str(eid)))
        if d.get("email"):
            print(f"  {eid}: {d['email']} | {d['beneficiar'][:30]} | {d['data_publicare']}")
        rows_saved.append(d)
        # Upsert to DB
        cols = list(d.keys())
        try:
            cur.execute(
                f"INSERT INTO beneficiari_privati ({','.join(cols)}) VALUES ({','.join(['%s']*len(cols))}) "
                f"ON CONFLICT (id) DO UPDATE SET {','.join(f'{c}=EXCLUDED.{c}' for c in cols[1:])}",
                [d.get(c, "") for c in cols])
        except Exception as e:
            print(f"  DB error {eid}: {e}")
            conn.rollback()

    conn.commit()
    print(f"Page {page+1}: {len(ids)} scraped")

# Export to CSV
with_email = [r for r in rows_saved if "@" in (r.get("email") or "")]
with open(OUT, "w", newline="", encoding="ascii", errors="replace") as f:
    if with_email:
        w = csv.DictWriter(f, fieldnames=with_email[0].keys())
        w.writeheader()
        w.writerows(with_email)

conn.close()
print(f"\nTotal: {len(rows_saved)} scraped, {len(with_email)} with email -> {OUT}")
