#!/usr/bin/env python3
"""Cross-reference ALL EBRD countries with interjob_master companies.
Generates campaign CSV per country."""
import psycopg2, csv, os, re

DB = dict(user="tudor", password="tudor", host="localhost")
OUT_DIR = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/EBRD_COUNTRIES"
os.makedirs(OUT_DIR, exist_ok=True)

# Country code mapping (interjob_master uses ISO2, EBRD uses full names)
COUNTRY_MAP = {
    "Ukraine": "UA", "Kazakhstan": "KZ", "Poland": "PL", "Egypt": "EG",
    "Uzbekistan": "UZ", "Serbia": "RS", "Greece": "GR", "Russia": "RU",
    "Kyrgyz Republic": "KG", "Georgia": "GE", "Bosnia and Herzegovina": "BA",
    "Morocco": "MA", "Moldova": "MD", "Mongolia": "MN", "Montenegro": "ME",
    "Croatia": "HR", "Armenia": "AM", "Kosovo": "XK", "Bulgaria": "BG",
    "Jordan": "JO", "Tunisia": "TN", "Albania": "AL", "Tajikistan": "TJ",
    "North Macedonia": "MK", "Azerbaijan": "AZ", "Belarus": "BY",
    "Lithuania": "LT", "Slovak Republic": "SK", "Hungary": "HU",
    "Slovenia": "SI", "Estonia": "EE", "Turkmenistan": "TM",
    "Latvia": "LV", "Lebanon": "LB", "Czechia": "CZ",
    "Nigeria": "NG", "Benin": "BJ", "Turkey": "TR",
}

conn_ebrd = psycopg2.connect(dbname="interjob_master", **DB)
cur_ebrd = conn_ebrd.cursor()

# Get all EBRD countries with active projects (non-financial)
cur_ebrd.execute("""
    SELECT DISTINCT country FROM ebrd_projects
    WHERE status NOT IN ('Complete','Repaying')
    AND sector NOT IN ('Financial Institutions','Equity Funds')
    AND country IS NOT NULL AND country != ''
    AND country NOT LIKE 'Industry%%' AND country NOT LIKE 'Countries%%'
    AND country != 'Regional'
""")
ebrd_countries = [r[0] for r in cur_ebrd.fetchall()]

print(f"EBRD countries with actionable projects: {len(ebrd_countries)}")
print("=" * 80)

summary = []

for country in sorted(ebrd_countries):
    iso = COUNTRY_MAP.get(country)
    if not iso:
        continue

    # Get EBRD project titles for this country
    cur_ebrd.execute("""
        SELECT DISTINCT LEFT(REPLACE(title,' | We invest in changing lives',''), 60), sector
        FROM ebrd_projects
        WHERE country = %s AND status NOT IN ('Complete','Repaying')
        AND sector NOT IN ('Financial Institutions','Equity Funds')
        LIMIT 10
    """, (country,))
    projects = cur_ebrd.fetchall()
    project_summary = "; ".join([f"{r[0]} ({r[1]})" for r in projects[:5]])

    # Count companies in interjob_master for this country
    cur_ebrd.execute("""
        SELECT COUNT(*) FROM companies
        WHERE country = %s AND email IS NOT NULL AND email != ''
    """, (iso,))
    total = cur_ebrd.fetchone()[0]

    if total == 0:
        continue

    # Get relevant companies (construction, energy, manufacturing, transport, food)
    cur_ebrd.execute("""
        SELECT DISTINCT name, email, phone, city FROM companies
        WHERE country = %s AND email IS NOT NULL AND email != ''
        AND (
            name ILIKE '%%construct%%' OR name ILIKE '%%build%%' OR name ILIKE '%%instal%%'
            OR name ILIKE '%%electric%%' OR name ILIKE '%%metal%%' OR name ILIKE '%%energy%%'
            OR name ILIKE '%%solar%%' OR name ILIKE '%%wind%%' OR name ILIKE '%%transport%%'
            OR name ILIKE '%%food%%' OR name ILIKE '%%agri%%' OR name ILIKE '%%water%%'
            OR name ILIKE '%%mining%%' OR name ILIKE '%%oil%%' OR name ILIKE '%%gas%%'
            OR name ILIKE '%%infra%%' OR name ILIKE '%%engineer%%' OR name ILIKE '%%logist%%'
            OR sector_name ILIKE '%%construct%%' OR sector_name ILIKE '%%manufactur%%'
            OR sector_name ILIKE '%%energy%%' OR sector_name ILIKE '%%transport%%'
            OR sector_name ILIKE '%%mining%%' OR sector_name ILIKE '%%food%%'
        )
        ORDER BY name
        LIMIT 500
    """, (iso,))
    rows = cur_ebrd.fetchall()

    if not rows:
        # Try broader: just get all companies with email
        cur_ebrd.execute("""
            SELECT DISTINCT name, email, phone, city FROM companies
            WHERE country = %s AND email IS NOT NULL AND email != ''
            ORDER BY name LIMIT 200
        """, (iso,))
        rows = cur_ebrd.fetchall()

    if not rows:
        continue

    # Save CSV
    safe_country = re.sub(r'[^a-zA-Z]', '_', country)
    outfile = os.path.join(OUT_DIR, f"ebrd_{safe_country.lower()}.csv")
    with open(outfile, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["company", "email", "phone", "city", "country", "ebrd_projects"])
        for r in rows:
            w.writerow([r[0], r[1], r[2] or "", r[3] or "", country, project_summary[:200]])

    summary.append({
        "country": country,
        "iso": iso,
        "total_db": total,
        "relevant": len(rows),
        "projects": len(projects),
        "file": outfile,
    })
    print(f"  {country:30s} | {iso} | {total:>7} total | {len(rows):>5} relevant | {len(projects)} EBRD projects | {outfile}")

cur_ebrd.close()
conn_ebrd.close()

# Summary
print(f"\n{'='*80}")
print(f"TOTAL: {len(summary)} countries with data")
total_contacts = sum(s["relevant"] for s in summary)
print(f"TOTAL CONTACTS: {total_contacts}")
print(f"Files saved in: {OUT_DIR}")
print(f"\nTop 10:")
for s in sorted(summary, key=lambda x: -x["relevant"])[:10]:
    print(f"  {s['country']:25s}: {s['relevant']:>5} contacts, {s['projects']} EBRD projects")
