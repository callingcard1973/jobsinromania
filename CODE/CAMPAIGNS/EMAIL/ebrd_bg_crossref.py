#!/usr/bin/env python3
"""Cross-reference EBRD Bulgaria projects with interjob_master companies."""
import psycopg2, csv

DB = dict(user="tudor", password="tudor", host="localhost")

EBRD_BG = {
    "София": {"project": "Sofia Public Transport + Airport SOF Connect", "keywords": ["construct", "transport", "electric", "instal", "metal", "montaj", "drum", "beton"]},
    "Пловдив": {"project": "Plovdiv Road Rehabilitation", "keywords": ["construct", "drum", "asfalt", "transport", "instal", "electric"]},
    "Sliven": {"project": "Sliven Water 12.6M", "keywords": ["construct", "instal", "apa", "water", "canal", "hidro"]},
    "Blagoevgrad": {"project": "Blagoevgrad Water Investment", "keywords": ["construct", "instal", "water", "hidro"]},
    # Energy
    "Solar_Vramis": {"project": "Solar Vramis 50M EUR", "keywords": ["solar", "electric", "energie", "energy", "construct", "montaj", "panel"]},
    "Asarel": {"project": "Asarel Medet Copper Mining 55M", "keywords": ["min", "metal", "copper", "construct", "industrial"]},
    "Sofia_Med": {"project": "Sofia Med Copper 20M", "keywords": ["metal", "copper", "fabricat", "industrial"]},
    "Stomana": {"project": "Stomana Industry Steel 35M", "keywords": ["metal", "steel", "industrial", "construct"]},
}

conn = psycopg2.connect(dbname="interjob_master", **DB)
cur = conn.cursor()

all_results = []
seen = set()

print("=" * 80)
print("EBRD BULGARIA CROSS-REFERENCE")
print("=" * 80)

for city, info in EBRD_BG.items():
    name_conds = " OR ".join([f"name ILIKE '%%{k}%%'" for k in info["keywords"]])
    sector_conds = " OR ".join([f"sector_name ILIKE '%%{k}%%'" for k in info["keywords"]])

    if city in ("Solar_Vramis", "Asarel", "Sofia_Med", "Stomana"):
        # National search for these sectors
        cur.execute(f"""
            SELECT DISTINCT name, email, phone, city FROM companies
            WHERE country='BG' AND email IS NOT NULL AND email != ''
            AND ({name_conds} OR {sector_conds})
            ORDER BY name LIMIT 50
        """)
    else:
        cur.execute(f"""
            SELECT DISTINCT name, email, phone, city FROM companies
            WHERE country='BG' AND email IS NOT NULL AND email != ''
            AND city ILIKE '%%{city}%%'
            AND ({name_conds} OR {sector_conds})
            ORDER BY name LIMIT 50
        """)

    rows = cur.fetchall()
    count = 0
    for r in rows:
        if r[1] not in seen:
            all_results.append({
                "company": r[0], "email": r[1], "phone": r[2] or "",
                "city": r[3] or city, "ebrd_project": info["project"], "ebrd_city": city,
            })
            seen.add(r[1])
            count += 1

    if count > 0:
        print(f"  {city:25s}: {count:4d} companii | {info['project']}")

cur.close()
conn.close()

# Export
outfile = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/ebrd_bulgaria_all.csv"
with open(outfile, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["company","email","phone","city","ebrd_project","ebrd_city"])
    w.writeheader()
    for r in all_results:
        w.writerow(r)

print(f"\nTOTAL: {len(all_results)} companii BG cu email")
print(f"Saved: {outfile}")
