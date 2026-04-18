#!/usr/bin/env python3
"""Cross-reference EBRD Romania beneficiaries with SEAP winners to find contractors.
Also cross-ref with interjob_master, ANOFM, and european_funds."""
import psycopg2, csv, re, json

DB = dict(user="tudor", password="tudor", host="localhost")

# EBRD beneficiaries to search for in SEAP
EBRD_BENEFICIARIES = {
    # Primarii
    "Timisoara": {"ebrd": "56078", "eur": "30M", "project": "DH + Urban Regeneration", "keywords": ["timisoara", "municipiul timisoara"]},
    "Brasov": {"ebrd": "56281", "eur": "30M", "project": "Energy Efficiency", "keywords": ["brasov", "municipiul brasov"]},
    "Craiova": {"ebrd": "50083", "eur": "24.2M", "project": "Urban Rehabilitation", "keywords": ["craiova", "municipiul craiova"]},
    "Iasi": {"ebrd": "51703", "eur": "50.4M", "project": "Green Buildings", "keywords": ["iasi", "municipiul iasi"]},
    "Alba-Iulia": {"ebrd": "53901", "eur": "15M", "project": "Transport Rehabilitation", "keywords": ["alba iulia", "alba-iulia", "municipiul alba"]},
    "Cluj": {"ebrd": "47857", "eur": "20M", "project": "Urban Transport", "keywords": ["cluj", "municipiul cluj"]},
    "Bucuresti": {"ebrd": "53476", "eur": "RON 27.75M", "project": "Bond + GCAP", "keywords": ["bucuresti", "municipiul bucuresti", "primaria municipiului bucuresti"]},
    # Companii de stat / utilitati
    "CNAIR": {"ebrd": "52472", "eur": "63M", "project": "Road Maintenance", "keywords": ["cnair", "compania nationala de administr"]},
    "RAJA Constanta": {"ebrd": "49600", "eur": "45M", "project": "Water SWIFT", "keywords": ["raja", "regia autonoma judeteana de apa"]},
    "CRAB Bacau": {"ebrd": "52511", "eur": "22M", "project": "Water SWIFT", "keywords": ["crab", "compania regionala de apa bacau"]},
    "CUP Braila": {"ebrd": "53047", "eur": "14.2M", "project": "Water SWIFT", "keywords": ["cup dunarea", "braila"]},
    "CATD Targoviste": {"ebrd": "53405", "eur": "18M", "project": "Water SWIFT", "keywords": ["compania de apa targoviste", "catd"]},
    "Aquatim Timis": {"ebrd": "53923", "eur": "14.4M", "project": "Water SWIFT", "keywords": ["aquatim"]},
    "CAO Olt": {"ebrd": "54536", "eur": "14.5M", "project": "Water SWIFT", "keywords": ["compania de apa olt", "cao"]},
    "Apa Prod Hunedoara": {"ebrd": "56261", "eur": "14M", "project": "Water SWIFT", "keywords": ["apa prod"]},
    # CSCT / DP World
    "DP World Constanta": {"ebrd": "54712", "eur": "25M", "project": "Port Electrification", "keywords": ["csct", "dp world", "constanta south"]},
}

print("=" * 80)
print("EBRD × SEAP CROSS-REFERENCE")
print("=" * 80)

# Load SEAP winners
seap_file = "/opt/ACTIVE/SCRAPERS/ROMANIA/SCRAPERS/LISTAFIRME/DATA/output/closed_procedures_winners.fuzzy_enriched.csv"
seap = []
with open(seap_file, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        seap.append(row)

print(f"SEAP winners loaded: {len(seap)}")

# Cross-reference
results = {}
for name, info in EBRD_BENEFICIARIES.items():
    contractors = []
    for row in seap:
        ben = (row.get("beneficiar_name", "") or "").lower()
        title = (row.get("titlu", "") or "").lower()
        if any(kw in ben for kw in info["keywords"]):
            # Filter for construction-related
            if any(t in title for t in ["construc", "reabilit", "moderni", "drum", "apa", "canal",
                "termi", "instal", "repara", "execut", "lucrar", "rehab", "eficien",
                "energie", "strad", "iluminat", "retea", "cladiri"]):
                email = row.get("fuzzy_email", "").strip()
                contractor = row.get("contractor_name", "").strip()
                value = row.get("contract_value", "").strip()
                if contractor and contractor not in [c["contractor"] for c in contractors]:
                    contractors.append({
                        "contractor": contractor,
                        "email": email,
                        "title": row.get("titlu", "")[:80],
                        "value": value,
                        "phone": row.get("fuzzy_phone", "").strip(),
                    })
    results[name] = {"info": info, "contractors": contractors}
    if contractors:
        print(f"\n{'='*60}")
        print(f"EBRD: {name} — {info['project']} (EUR {info['eur']})")
        print(f"{'='*60}")
        for c in sorted(contractors, key=lambda x: -1 if x["email"] else 0):
            tag = "✓" if c["email"] else "✗"
            print(f"  {tag} {c['contractor'][:50]:50s} | {c['email'][:35]:35s} | {c['phone'][:15]:15s} | {c['value'][:12]}")

# Summary
print(f"\n{'='*80}")
print("REZUMAT")
print(f"{'='*80}")
total_contractors = 0
total_with_email = 0
for name, data in results.items():
    n = len(data["contractors"])
    e = len([c for c in data["contractors"] if c["email"]])
    total_contractors += n
    total_with_email += e
    if n > 0:
        print(f"  {name:25s}: {n:3d} contractori ({e} cu email)")

print(f"\nTOTAL: {total_contractors} contractori unici, {total_with_email} cu email")

# Cross-reference with interjob_master for missing emails
print(f"\n{'='*80}")
print("ENRICHMENT DIN INTERJOB_MASTER")
print(f"{'='*80}")

conn = psycopg2.connect(dbname="interjob_master", **DB)
cur = conn.cursor()
enriched = 0
for name, data in results.items():
    for c in data["contractors"]:
        if c["email"]:
            continue
        # Search by company name
        cname = c["contractor"].replace("'", "''")
        cur.execute(f"""
            SELECT email, phone FROM companies
            WHERE country='RO' AND email IS NOT NULL AND email != ''
            AND (name ILIKE '%{cname[:30]}%' OR name ILIKE '%{cname.split()[0] if cname.split() else cname}%')
            LIMIT 3
        """)
        rows = cur.fetchall()
        if rows:
            c["email"] = rows[0][0]
            c["phone"] = c["phone"] or (rows[0][1] or "")
            enriched += 1
            print(f"  ENRICHED: {c['contractor'][:40]} → {c['email']}")

cur.close()
conn.close()
print(f"Enriched: {enriched} contractors")

# Also check ANOFM for construction companies
print(f"\n{'='*80}")
print("ANOFM CONSTRUCTII — TOP COMPANII CU JOBURI ACTIVE")
print(f"{'='*80}")
conn = psycopg2.connect(dbname="anofm", **DB)
cur = conn.cursor()
cur.execute("""
    SELECT company_name, email, COUNT(*) jobs
    FROM jobs
    WHERE sector IN ('Constructii / Instalatii', 'Productie / Logistica')
    AND email IS NOT NULL AND email != ''
    GROUP BY company_name, email
    HAVING COUNT(*) >= 3
    ORDER BY COUNT(*) DESC
    LIMIT 30
""")
print(f"{'Company':50s} | {'Email':35s} | Jobs")
for row in cur.fetchall():
    print(f"  {row[0][:48]:48s} | {row[1][:35]:35s} | {row[2]}")
cur.close()
conn.close()

# Export campaign-ready CSV
print(f"\n{'='*80}")
print("EXPORT CSV")
print(f"{'='*80}")

outfile = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/ebrd_constructori.csv"
with open(outfile, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["contractor","email","phone","ebrd_project","ebrd_eur","ebrd_city","seap_title"])
    w.writeheader()
    for name, data in results.items():
        for c in data["contractors"]:
            if c["email"]:
                w.writerow({
                    "contractor": c["contractor"],
                    "email": c["email"],
                    "phone": c["phone"],
                    "ebrd_project": data["info"]["project"],
                    "ebrd_eur": data["info"]["eur"],
                    "ebrd_city": name,
                    "seap_title": c["title"],
                })

# Count output
with open(outfile) as f:
    lines = len(f.readlines()) - 1
print(f"Saved: {outfile}")
print(f"Total: {lines} contractors with email, ready for campaign")
