#!/usr/bin/env python3
"""
EBRD Europe Master Cross-Reference
Runs on raspibig, zero tokens. Generates campaign CSV per country.
Matches EBRD projects with interjob_master companies by country + sector.

Usage: python3 ebrd_europe_master.py
Output: /opt/ACTIVE/EBRD/COUNTRIES/ebrd_{country}.csv + summary.json
"""
import psycopg2, csv, os, re, json
from datetime import datetime

DB = dict(user="tudor", password="tudor", host="localhost")
OUT_DIR = "/opt/ACTIVE/EBRD/COUNTRIES"
os.makedirs(OUT_DIR, exist_ok=True)

# EBRD country name -> ISO2 code in interjob_master
COUNTRY_MAP = {
    "Albania": "AL", "Armenia": "AM", "Azerbaijan": "AZ", "Belarus": "BY",
    "Benin": "BJ", "Bosnia and Herzegovina": "BA", "Bulgaria": "BG",
    "Croatia": "HR", "Czechia": "CZ", "Egypt": "EG", "Estonia": "EE",
    "Georgia": "GE", "Greece": "GR", "Hungary": "HU", "Jordan": "JO",
    "Kazakhstan": "KZ", "Kosovo": "XK", "Kyrgyz Republic": "KG",
    "Latvia": "LV", "Lebanon": "LB", "Lithuania": "LT", "Moldova": "MD",
    "Mongolia": "MN", "Montenegro": "ME", "Morocco": "MA",
    "Nigeria": "NG", "North Macedonia": "MK", "Poland": "PL",
    "Romania": "RO", "Russia": "RU", "Serbia": "RS",
    "Slovak Republic": "SK", "Slovenia": "SI", "Tajikistan": "TJ",
    "Tunisia": "TN", "Turkey": "TR", "Turkmenistan": "TM",
    "Ukraine": "UA", "Uzbekistan": "UZ",
}

# Sector keywords for matching companies
SECTOR_KEYWORDS = {
    "Energy": ["electric", "energy", "solar", "wind", "power", "turbine", "cable", "transform",
               "renew", "generator", "substation", "inverter", "panel", "photovoltaic"],
    "Municipal Infrastructure": ["construct", "build", "instal", "water", "canal", "pipe", "pump",
                "road", "asphalt", "bridge", "concrete", "cement", "steel", "rehabilit",
                "thermal", "heating", "isolat", "plaster", "paint", "window", "hvac"],
    "Transport": ["transport", "road", "rail", "port", "logist", "freight", "truck", "bus",
                  "airport", "asphalt", "bridge"],
    "Manufacturing and Services": ["manufactur", "factory", "product", "industrial", "machine",
                "metal", "weld", "fabricat", "assembl", "warehouse", "automat"],
    "Food and Agribusiness": ["food", "agri", "farm", "meat", "dairy", "bread", "bake",
                "process", "packag", "cold", "freez", "storage"],
    "Real Estate": ["construct", "build", "real estate", "develop", "warehouse", "logist",
                "steel", "concrete", "facade", "instal"],
    "Natural Resources": ["mining", "mineral", "oil", "gas", "copper", "gold", "coal",
                "extract", "drill", "geology"],
    "Notice Type": ["software", "tech", "digital", "IT"],
}

def get_search_keywords(ebrd_sectors):
    """Combine keywords from all relevant EBRD sectors for a country."""
    all_kw = set()
    for sector in ebrd_sectors:
        for key, keywords in SECTOR_KEYWORDS.items():
            if key in sector or sector in key:
                all_kw.update(keywords)
    if not all_kw:
        # Default broad search
        all_kw = {"construct", "electric", "energy", "transport", "food", "metal",
                  "instal", "engineer", "logist", "mining", "industrial"}
    return all_kw

print(f"{'='*80}")
print(f"EBRD EUROPE MASTER CROSS-REFERENCE")
print(f"Started: {datetime.now()}")
print(f"{'='*80}\n")

conn = psycopg2.connect(dbname="interjob_master", **DB)
cur = conn.cursor()

# Get all EBRD active projects grouped by country
cur.execute("""
    SELECT country,
        array_agg(DISTINCT sector) as sectors,
        COUNT(*) as project_count,
        COUNT(CASE WHEN contact_email IS NOT NULL AND contact_email != '' THEN 1 END) as with_email,
        array_agg(DISTINCT REPLACE(LEFT(title, 50), ' | We invest in changing lives', '')) as titles
    FROM ebrd_projects
    WHERE status NOT IN ('Complete','Repaying')
    AND country IS NOT NULL AND country != ''
    AND country NOT LIKE 'Industry%%' AND country NOT LIKE 'Countries%%' AND country != 'Regional'
    GROUP BY country
    ORDER BY COUNT(*) DESC
""")
ebrd_data = cur.fetchall()

summary = {"generated": datetime.now().isoformat(), "countries": []}

for row in ebrd_data:
    country_name = row[0]
    sectors = [s for s in row[1] if s]
    project_count = row[2]
    ebrd_with_email = row[3]
    titles = [t for t in row[4] if t][:5]

    iso = COUNTRY_MAP.get(country_name)
    if not iso:
        print(f"  SKIP {country_name}: no ISO2 mapping")
        continue

    # Check how many companies we have
    cur.execute("SELECT COUNT(*) FROM companies WHERE country = %s AND email IS NOT NULL AND email != ''", (iso,))
    total_companies = cur.fetchone()[0]

    if total_companies == 0:
        print(f"  SKIP {country_name} ({iso}): 0 companies in DB")
        continue

    # Build keyword search
    keywords = get_search_keywords(sectors)
    name_conds = " OR ".join([f"name ILIKE '%%{kw}%%'" for kw in keywords])
    sector_conds = " OR ".join([f"sector_name ILIKE '%%{kw}%%'" for kw in keywords])

    # Query relevant companies
    cur.execute(f"""
        SELECT DISTINCT name, email, phone, city FROM companies
        WHERE country = %s AND email IS NOT NULL AND email != ''
        AND ({name_conds} OR {sector_conds})
        ORDER BY name LIMIT 500
    """, (iso,))
    companies = cur.fetchall()

    if not companies:
        # Fallback: get all companies with email
        cur.execute("""
            SELECT DISTINCT name, email, phone, city FROM companies
            WHERE country = %s AND email IS NOT NULL AND email != ''
            ORDER BY name LIMIT 200
        """, (iso,))
        companies = cur.fetchall()

    if not companies:
        continue

    # Deduplicate by email
    seen = set()
    unique = []
    for c in companies:
        if c[1] not in seen:
            unique.append(c)
            seen.add(c[1])

    # Get EBRD contacts for this country
    cur.execute("""
        SELECT REPLACE(title,' | We invest in changing lives',''), sector, contact_name, contact_email, ebrd_finance
        FROM ebrd_projects
        WHERE country = %s AND status NOT IN ('Complete','Repaying')
        AND contact_email IS NOT NULL AND contact_email != '' AND contact_email != 'Related'
        AND sector NOT IN ('Financial Institutions','Equity Funds')
        ORDER BY sector
    """, (country_name,))
    ebrd_contacts = cur.fetchall()

    # Export CSV
    safe = re.sub(r'[^a-zA-Z]', '_', country_name).lower()
    outfile = os.path.join(OUT_DIR, f"ebrd_{safe}.csv")
    with open(outfile, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["company_name", "email", "phone", "city", "country_iso", "country_name",
                     "ebrd_project_count", "ebrd_sectors"])
        sector_str = ", ".join(set(s for s in sectors if s not in ("Financial Institutions", "Equity Funds", "Notice Type")))
        for c in unique:
            w.writerow([c[0], c[1], c[2] or "", c[3] or "", iso, country_name,
                       project_count, sector_str[:200]])

    # Export EBRD contacts separately
    if ebrd_contacts:
        contacts_file = os.path.join(OUT_DIR, f"ebrd_{safe}_contacts.csv")
        with open(contacts_file, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["project_title", "sector", "contact_name", "contact_email", "finance"])
            for c in ebrd_contacts:
                w.writerow(c)

    country_summary = {
        "country": country_name,
        "iso": iso,
        "ebrd_projects": project_count,
        "ebrd_with_email": ebrd_with_email,
        "ebrd_direct_contacts": len(ebrd_contacts),
        "companies_total_in_db": total_companies,
        "companies_matched": len(unique),
        "csv_file": outfile,
        "top_projects": titles[:3],
    }
    summary["countries"].append(country_summary)

    print(f"  {country_name:30s} | {iso} | {project_count:>3} EBRD | {total_companies:>6} in DB | {len(unique):>4} matched | {len(ebrd_contacts)} direct contacts")

cur.close()
conn.close()

# Save summary
summary_file = "/opt/ACTIVE/EBRD/summary.json"
with open(summary_file, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

print(f"\n{'='*80}")
print(f"DONE: {len(summary['countries'])} countries processed")
total_matched = sum(c["companies_matched"] for c in summary["countries"])
total_ebrd_contacts = sum(c["ebrd_direct_contacts"] for c in summary["countries"])
print(f"TOTAL: {total_matched} companies matched + {total_ebrd_contacts} EBRD direct contacts")
print(f"Summary: {summary_file}")
print(f"CSVs: {OUT_DIR}/")
print(f"Finished: {datetime.now()}")
