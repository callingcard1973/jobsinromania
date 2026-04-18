#!/usr/bin/env python3
"""Dedup all Romania campaign sectors from romania_emails + anofm DBs."""
import psycopg2, csv, os

OUTPUT_DIR = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA"

# Sector definitions: (name, caen_filter, sector_filter, occupation_filter)
SECTORS = {
    "agricultura": {
        "caen": ["01", "02", "03"],
        "sector_kw": ["agricultur", "zooteh", "agri", "farm"],
        "occupation_kw": ["agricultor", "tractorist", "zooteh", "combiner", "legumicult"],
    },
    "confectii": {
        "caen": ["13", "14", "15"],
        "sector_kw": ["confect", "textil", "croitor", "tricot"],
        "occupation_kw": ["croitor", "confect", "cusator", "calcat", "tricot"],
    },
    "lemn": {
        "caen": ["16", "31"],
        "sector_kw": ["lemn", "mobil", "tampl", "cherestea"],
        "occupation_kw": ["tamplar", "lemn", "mobil", "dulgh", "cherest"],
    },
    "curierat": {
        "caen": ["49", "52", "53"],
        "sector_kw": ["transport", "curier", "logistic", "livr", "delivery"],
        "occupation_kw": ["curier", "sofer", "livr", "expedit", "sortator"],
    },
    "horeca": {
        "caen": ["55", "56"],
        "sector_kw": ["horeca", "hotel", "restaurant", "aliment", "turism", "ospital"],
        "occupation_kw": ["bucatar", "ospatar", "barman", "receptioner", "camerist"],
    },
    "lichidatori": {
        "caen": [],
        "sector_kw": ["insolv", "lichid", "faliment"],
        "occupation_kw": [],
    },
    "ferme_insolventa": {
        "caen": [],
        "sector_kw": ["insolv", "lichid", "faliment"],
        "occupation_kw": [],
        "extra_filter": "agriculture",  # insolvent farms specifically
    },
}

def get_dnc():
    conn = psycopg2.connect(dbname="interjob_master", user="tudor", host="localhost", password="tudor")
    cur = conn.cursor()
    cur.execute("SELECT LOWER(email) FROM dnc_list")
    dnc = {r[0] for r in cur.fetchall()}
    conn.close()
    return dnc

def build_where(cfg, prefix=""):
    parts = []
    if cfg["caen"]:
        caen_parts = [f"{prefix}caen LIKE '{c}%%'" for c in cfg["caen"]]
        parts.append(f"({' OR '.join(caen_parts)})")
    for kw in cfg.get("sector_kw", []):
        parts.append(f"{prefix}sector_name ILIKE '%%{kw}%%'")
    return " OR ".join(parts) if parts else "1=0"

def build_where_anofm(cfg):
    parts = []
    for kw in cfg.get("sector_kw", []):
        parts.append(f"sector ILIKE '%%{kw}%%'")
    for kw in cfg.get("occupation_kw", []):
        parts.append(f"occupation ILIKE '%%{kw}%%'")
    return " OR ".join(parts) if parts else "1=0"

def dedup_sector(name, cfg, dnc):
    emails = {}

    # romania_emails
    where = build_where(cfg)
    if where == "1=0":
        where = "1=0"
    conn = psycopg2.connect(dbname="romania_emails", user="tudor", host="localhost", password="tudor")
    cur = conn.cursor()
    cur.execute(f"""SELECT DISTINCT ON (LOWER(email)) email, company_name, city, contact_name, phone, sector_name
        FROM contacts WHERE email IS NOT NULL AND email != '' AND ({where})
        ORDER BY LOWER(email), id""")
    for r in cur.fetchall():
        e = r[0].lower().strip()
        if e not in emails:
            emails[e] = list(r)
    conn.close()
    src1 = len(emails)

    # anofm
    where2 = build_where_anofm(cfg)
    if where2 != "1=0":
        conn = psycopg2.connect(dbname="anofm", user="tudor", host="localhost", password="tudor")
        cur = conn.cursor()
        cur.execute(f"""SELECT DISTINCT ON (LOWER(email)) email, company_name, city, contact_person, phone, sector
            FROM jobs WHERE email IS NOT NULL AND email != '' AND ({where2})
            ORDER BY LOWER(email), id""")
        for r in cur.fetchall():
            e = r[0].lower().strip()
            if e not in emails:
                emails[e] = list(r)
        conn.close()
    src2 = len(emails) - src1

    # Remove DNC
    clean = {e: v for e, v in emails.items() if e not in dnc}

    # Count corporate vs personal
    personal_domains = {"gmail.com","yahoo.com","yahoo.ro","hotmail.com","outlook.com","live.com","icloud.com","ymail.com","aol.com","mail.ru","protonmail.com","web.de","gmx.de","gmx.net","t-online.de"}
    corp = sum(1 for e in clean if e.split("@")[1] not in personal_domains)
    pers = len(clean) - corp

    # Save CSV
    outfile = os.path.join(OUTPUT_DIR, f"ro_{name}_{len(clean)}.csv")
    with open(outfile, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["email", "company_name", "city", "contact_name", "phone", "sector"])
        for e, row in clean.items():
            w.writerow(row)

    print(f"{name:20s} | ro_emails:{src1:>5} + anofm:{src2:>4} = {len(emails):>5} - dnc:{len(emails)-len(clean):>3} = {len(clean):>5} clean ({corp} corp, {pers} pers)")
    return outfile, len(clean), corp, pers

dnc = get_dnc()
print(f"DNC: {len(dnc)} emails\n")

results = {}
for name, cfg in SECTORS.items():
    outfile, total, corp, pers = dedup_sector(name, cfg, dnc)
    results[name] = {"file": outfile, "total": total, "corporate": corp, "personal": pers}

print(f"\nGRAND TOTAL: {sum(r['total'] for r in results.values())} contacts across {len(results)} campaigns")
