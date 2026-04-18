#!/usr/bin/env python3
"""Deep cross-reference: search interjob_master for construction companies in EBRD cities."""
import psycopg2, csv

DB = dict(user="tudor", password="tudor", host="localhost")

EBRD_CITIES = {
    "Buzau": "Vifor Wind 461MW + Urleasca Wind 102MW",
    "Dambovita": "Muntenia Solar (Corbii Mari 282MW)",
    "Giurgiu": "Muntenia Solar (Iepuresti + Ghimpati + Slobozia)",
    "Dolj": "Dobrun-Sadova Solar 190MW",
    "Olt": "Scornicesti BESS 127MW + CAO Water 14.5M",
    "Timisoara": "DH + Urban 30M",
    "Brasov": "Energy Efficiency 30M + Transport",
    "Craiova": "Urban Rehabilitation 24.2M",
    "Iasi": "Green Buildings 50.4M + RIVUS indirect",
    "Cluj": "RIVUS 550M + Transport 20M",
    "Alba Iulia": "Transport Rehabilitation 15M",
    "Constanta": "RAJA Water 45M + DP World Port 25M",
    "Bacau": "CRAB Water 22M + Mario Resort (Moinesti)",
    "Braila": "CUP Water 14.2M + Urleasca Wind",
    "Hunedoara": "Apa Prod Water 14M",
    "Stefanestii de Jos": "NewCold depozit frigorific",
}

conn = psycopg2.connect(dbname="interjob_master", **DB)
cur = conn.cursor()

print("=" * 80)
print("INTERJOB_MASTER — CONSTRUCTORI IN ORASELE EBRD")
print("=" * 80)

all_results = []

for city, project in EBRD_CITIES.items():
    # Search for construction-related companies in this city
    cur.execute("""
        SELECT name, email, phone, city
        FROM companies
        WHERE country = 'RO'
        AND email IS NOT NULL AND email != ''
        AND (city ILIKE %s OR city ILIKE %s)
        AND (
            name ILIKE '%%construct%%'
            OR name ILIKE '%%instal%%'
            OR name ILIKE '%%drum%%'
            OR name ILIKE '%%beton%%'
            OR name ILIKE '%%electric%%'
            OR name ILIKE '%%hidro%%'
            OR name ILIKE '%%izol%%'
            OR name ILIKE '%%montaj%%'
            OR name ILIKE '%%sudur%%'
            OR name ILIKE '%%proiect%%'
            OR name ILIKE '%%infrastruct%%'
            OR sector_name ILIKE '%%construct%%'
            OR sector_name ILIKE '%%build%%'
        )
        ORDER BY name
        LIMIT 50
    """, (f"%{city}%", f"%{city.split()[0]}%"))

    rows = cur.fetchall()
    if rows:
        print(f"\n--- {city} — {project} ({len(rows)} constructori) ---")
        for r in rows[:15]:
            print(f"  {r[0][:45]:45s} | {r[1][:35]:35s} | {r[2] or '':15s} | {r[3] or ''}")
            all_results.append({
                "company": r[0],
                "email": r[1],
                "phone": r[2] or "",
                "city": r[3] or city,
                "ebrd_project": project,
                "ebrd_city": city,
            })
        if len(rows) > 15:
            print(f"  ... +{len(rows)-15} more")

cur.close()
conn.close()

# Also search ANOFM for construction companies in EBRD cities
print(f"\n{'='*80}")
print("ANOFM — CONSTRUCTORI CU JOBURI ACTIVE IN ORASELE EBRD")
print(f"{'='*80}")

conn = psycopg2.connect(dbname="anofm", **DB)
cur = conn.cursor()

for city, project in EBRD_CITIES.items():
    cur.execute("""
        SELECT DISTINCT company_name, email, region
        FROM jobs
        WHERE sector IN ('Constructii / Instalatii', 'Productie / Logistica')
        AND email IS NOT NULL AND email != ''
        AND (region ILIKE %s OR city ILIKE %s OR company_city ILIKE %s)
        LIMIT 20
    """, (f"%{city.split()[0]}%", f"%{city}%", f"%{city}%"))

    rows = cur.fetchall()
    if rows:
        print(f"\n--- {city} — {project} ({len(rows)} companii cu joburi) ---")
        for r in rows[:10]:
            print(f"  {r[0][:45]:45s} | {r[1][:35]:35s} | {r[2] or ''}")
            # Check if already in results
            if not any(x["email"] == r[1] for x in all_results):
                all_results.append({
                    "company": r[0],
                    "email": r[1],
                    "phone": "",
                    "city": r[2] or city,
                    "ebrd_project": project,
                    "ebrd_city": city,
                })

cur.close()
conn.close()

# Export combined CSV
outfile = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/ebrd_constructori_extended.csv"
with open(outfile, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["company","email","phone","city","ebrd_project","ebrd_city"])
    w.writeheader()
    seen = set()
    count = 0
    for r in all_results:
        if r["email"] not in seen:
            w.writerow(r)
            seen.add(r["email"])
            count += 1

print(f"\n{'='*80}")
print(f"TOTAL UNIC: {count} constructori cu email in orasele EBRD")
print(f"Saved: {outfile}")
print(f"{'='*80}")
