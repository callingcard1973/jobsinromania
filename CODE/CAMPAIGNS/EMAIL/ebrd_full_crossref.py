#!/usr/bin/env python3
"""Full cross-reference: ALL sectors in EBRD cities, not just construction."""
import psycopg2, csv

DB = dict(user="tudor", password="tudor", host="localhost")

EBRD_PROJECTS = {
    # Energie — solar/eolian
    "Buzau": {"project": "Vifor Wind 461MW", "sectors": ["energie", "eolian", "wind", "turbine", "electric", "retea", "cablu", "sudur", "macara", "transport"]},
    "Dambovita": {"project": "Muntenia Solar 282MW Corbii Mari", "sectors": ["solar", "fotovoltaic", "panouri", "electric", "energie", "montaj"]},
    "Giurgiu": {"project": "Muntenia Solar (Iepuresti+Ghimpati+Slobozia)", "sectors": ["solar", "fotovoltaic", "panouri", "electric", "energie", "montaj"]},
    "Dolj": {"project": "Dobrun-Sadova Solar 190MW", "sectors": ["solar", "fotovoltaic", "electric", "energie", "construct", "montaj"]},
    "Olt": {"project": "Scornicesti BESS 127MW + CAO Water", "sectors": ["electric", "energie", "baterie", "construct", "instal", "apa", "canal"]},
    # Infrastructura
    "Timisoara": {"project": "DH 30M + Urban Regeneration", "sectors": ["construct", "termi", "instal", "drum", "urban", "reabilit", "izolat", "sudur", "conducte"]},
    "Brasov": {"project": "Energy Efficiency 30M cladiri publice", "sectors": ["construct", "instal", "izolat", "tamplari", "zugrav", "termi", "reabilit", "fatad"]},
    "Craiova": {"project": "Urban Rehabilitation 24.2M", "sectors": ["construct", "instal", "izolat", "zugrav", "reabilit", "drum", "iluminat"]},
    "Iasi": {"project": "Green Buildings 50.4M + RIVUS pipeline", "sectors": ["construct", "instal", "izolat", "reabilit", "beton", "cofraj", "structur"]},
    "Cluj": {"project": "RIVUS 550M + Transport 20M", "sectors": ["construct", "instal", "beton", "cofraj", "structur", "electric", "fatad", "montaj", "zugrav"]},
    "Alba Iulia": {"project": "Transport Rehabilitation 15M", "sectors": ["construct", "drum", "asfalt", "transport", "semnalisti"]},
    "Constanta": {"project": "RAJA Water 45M + DP World Port 25M", "sectors": ["construct", "instal", "apa", "canal", "hidro", "electric", "portuar", "naval"]},
    "Bacau": {"project": "CRAB Water 22M", "sectors": ["construct", "instal", "apa", "canal", "hidro", "electric"]},
    "Braila": {"project": "CUP Water 14.2M + Urleasca Wind", "sectors": ["construct", "instal", "apa", "canal", "electric", "eolian"]},
    "Hunedoara": {"project": "Apa Prod Water 14M", "sectors": ["construct", "instal", "apa", "canal", "hidro"]},
    # Real estate / food / manufacturing
    "Stefanestii de Jos": {"project": "NewCold depozit frigorific -28C", "sectors": ["construct", "structur", "metal", "frigori", "depozit", "logistic", "sudur", "izolat"]},
    "Slatina": {"project": "Vimetco Power 250MW CCPP", "sectors": ["construct", "energie", "electric", "sudur", "montaj", "industrial"]},
    # Food
    "Lantmannen": {"project": "Lantmannen Brutarie Noua 90M", "sectors": ["alimentar", "panificati", "brutari", "productie", "ambalaj", "echipament"]},
    # National
    "CNAIR": {"project": "Drumuri Nationale 63M", "sectors": ["drum", "asfalt", "construct", "utilaj", "transport", "agregate"]},
}

conn_master = psycopg2.connect(dbname="interjob_master", **DB)
cur_master = conn_master.cursor()

conn_anofm = psycopg2.connect(dbname="anofm", **DB)
cur_anofm = conn_anofm.cursor()

all_results = []
seen_emails = set()

print("=" * 80)
print("FULL CROSS-REFERENCE: TOATE SECTOARELE IN ORASELE EBRD")
print("=" * 80)

for city, info in EBRD_PROJECTS.items():
    # Build search conditions
    name_conditions = " OR ".join([f"name ILIKE '%%{s}%%'" for s in info["sectors"]])
    sector_conditions = " OR ".join([f"sector_name ILIKE '%%{s}%%'" for s in info["sectors"]])

    # interjob_master
    if city == "CNAIR":
        # National search for road companies
        query = f"""
            SELECT DISTINCT name, email, phone, city FROM companies
            WHERE country='RO' AND email IS NOT NULL AND email != ''
            AND ({name_conditions} OR {sector_conditions})
            ORDER BY name LIMIT 50
        """
        cur_master.execute(query)
    elif city == "Lantmannen":
        query = f"""
            SELECT DISTINCT name, email, phone, city FROM companies
            WHERE country='RO' AND email IS NOT NULL AND email != ''
            AND ({name_conditions} OR {sector_conditions})
            ORDER BY name LIMIT 30
        """
        cur_master.execute(query)
    else:
        city_search = city.split()[0]
        query = f"""
            SELECT DISTINCT name, email, phone, city FROM companies
            WHERE country='RO' AND email IS NOT NULL AND email != ''
            AND (city ILIKE '%%{city_search}%%')
            AND ({name_conditions} OR {sector_conditions})
            ORDER BY name LIMIT 50
        """
        cur_master.execute(query)

    rows = cur_master.fetchall()

    # ANOFM
    if city not in ("CNAIR", "Lantmannen"):
        city_search = city.split()[0]
        cur_anofm.execute("""
            SELECT DISTINCT company_name, email, region FROM jobs
            WHERE email IS NOT NULL AND email != ''
            AND (region ILIKE %s OR city ILIKE %s OR company_city ILIKE %s)
            LIMIT 30
        """, (f"%{city_search}%", f"%{city}%", f"%{city}%"))
        anofm_rows = cur_anofm.fetchall()
    else:
        anofm_rows = []

    count = 0
    for r in rows:
        if r[1] not in seen_emails:
            all_results.append({
                "company": r[0], "email": r[1], "phone": r[2] or "",
                "city": r[3] or city, "ebrd_project": info["project"], "ebrd_city": city,
                "source": "interjob_master"
            })
            seen_emails.add(r[1])
            count += 1

    for r in anofm_rows:
        if r[1] not in seen_emails:
            all_results.append({
                "company": r[0], "email": r[1], "phone": "",
                "city": r[2] or city, "ebrd_project": info["project"], "ebrd_city": city,
                "source": "anofm"
            })
            seen_emails.add(r[1])
            count += 1

    if count > 0:
        print(f"  {city:25s}: {count:4d} companii | {info['project']}")

cur_master.close()
conn_master.close()
cur_anofm.close()
conn_anofm.close()

# Export
outfile = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/ebrd_all_sectors.csv"
with open(outfile, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["company","email","phone","city","ebrd_project","ebrd_city","source"])
    w.writeheader()
    for r in all_results:
        w.writerow(r)

print(f"\n{'='*80}")
print(f"TOTAL: {len(all_results)} companii unice cu email")
print(f"Saved: {outfile}")

# Stats by EBRD city
from collections import Counter
by_city = Counter(r["ebrd_city"] for r in all_results)
print(f"\nPer oras EBRD:")
for city, count in by_city.most_common():
    print(f"  {city:25s}: {count}")
