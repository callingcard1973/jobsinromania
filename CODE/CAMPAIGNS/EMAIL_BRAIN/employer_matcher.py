#!/usr/bin/env python3
"""Employer-Applicant Matcher — matches big RO employers with CV vault candidates.
Generates personalized campaign CSV ready for orchestrator."""
import csv, json, psycopg2, re, os
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/templates/ro_hiprofile")
CSV_OUT = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs")
DB = {"host": "/var/run/postgresql", "dbname": "interjob_master",
      "user": "tudor", "password": "scraper123"}

# CAEN → skill mapping
CAEN_SKILLS = {
    "10": ("factory,horeca", "Muncitori productie alimentara, ambalare, sortare"),
    "11": ("factory", "Muncitori productie bauturi"),
    "13": ("factory", "Confectioneri textile"),
    "14": ("factory", "Confectioneri imbracaminte"),
    "16": ("construction,factory", "Tamplari, operatori masini lemn"),
    "20": ("factory", "Operatori chimie industriala"),
    "22": ("factory", "Operatori mase plastice, cauciuc"),
    "23": ("construction,factory", "Operatori materiale constructii"),
    "24": ("welding,factory", "Sudori, turnatori, metalurgisti"),
    "25": ("welding,factory", "Sudori MIG/MAG/TIG, lacatusi, operatori CNC"),
    "28": ("factory", "Operatori masini, asamblori, mecanici"),
    "29": ("factory,welding", "Muncitori industria auto"),
    "41": ("construction,welding", "Muncitori constructii, zidari, fierari betonisti"),
    "42": ("construction,driver", "Constructii drumuri, operatori utilaje"),
    "43": ("construction,welding,electrical", "Instalatori, electricieni, zugr, faiantari"),
    "46": ("driver,factory", "Manipulanti depozit, soferi"),
    "47": ("horeca,factory", "Casieri, lucrator comercial"),
    "49": ("driver", "Soferi cat. B/C/CE, curieri"),
    "52": ("driver,factory", "Depozitari, stivuitoristi"),
    "55": ("horeca", "Receptioner, camerista, menajera"),
    "56": ("horeca", "Bucatari, ospatari, barmani"),
    "01": ("agriculture", "Muncitori agricoli, sezonieri"),
    "02": ("agriculture", "Muncitori silvicultura"),
    "03": ("agriculture", "Muncitori piscicultura"),
    "81": ("construction,factory", "Curatenie industriala, intretinere cladiri"),
    "86": ("horeca", "Infirmiere, brancardieri, personal medical auxiliar"),
}

SKILL_COUNTS = {}


def load_cv_vault_counts():
    global SKILL_COUNTS
    try:
        conn = psycopg2.connect(**DB)
        cur = conn.cursor()
        cur.execute("SELECT skills FROM cv_vault")
        for row in cur.fetchall():
            for skill in (row[0] or "general").split("|"):
                SKILL_COUNTS[skill.strip()] = SKILL_COUNTS.get(skill.strip(), 0) + 1
        cur.close()
        conn.close()
    except Exception:
        SKILL_COUNTS = {"welding": 30, "construction": 50, "factory": 124,
            "horeca": 72, "driver": 22, "agriculture": 58, "general": 140}


def match_caen(caen):
    if not caen:
        return "general", "Diverse pozitii", 0
    prefix = caen[:2]
    skills_str, positions = CAEN_SKILLS.get(prefix, ("general", "Diverse pozitii"))
    count = 0
    for skill in skills_str.split(","):
        count += SKILL_COUNTS.get(skill.strip(), 0)
    return skills_str, positions, count


def generate_campaign():
    load_cv_vault_counts()
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()

    # Get big employers not in DNC
    cur.execute("""
        SELECT name, email, city, county, caen, caen_description,
               employees_count, contact_name, phone
        FROM master_romania_companies
        WHERE email IS NOT NULL AND email != ''
          AND employees_count >= 50
          AND (is_insolvent IS NULL OR is_insolvent = false)
          AND LOWER(email) NOT IN (SELECT email FROM master_dnc)
        ORDER BY employees_count DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    # Build campaign CSV
    campaign_rows = []
    for name, email, city, county, caen, caen_desc, emp, contact, phone in rows:
        skills, positions, cv_count = match_caen(caen)
        campaign_rows.append({
            "email": email,
            "company": name or "",
            "city": city or "",
            "county": county or "",
            "sector": caen_desc or "",
            "employees": emp or 0,
            "contact_name": contact or "",
            "phone": phone or "",
            "matched_skills": skills,
            "suggested_positions": positions,
            "cv_available": cv_count,
        })

    # Write CSV
    os.makedirs(str(CSV_OUT), exist_ok=True)
    out_file = CSV_OUT / "ro_hiprofile_campaign.csv"
    with open(out_file, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campaign_rows[0].keys())
        w.writeheader()
        w.writerows(campaign_rows)

    # Stats
    total = len(campaign_rows)
    with_match = sum(1 for r in campaign_rows if r["cv_available"] > 0)
    print(f"Campaign CSV: {out_file}")
    print(f"Total employers: {total}")
    print(f"With matching CVs: {with_match}")
    print(f"\nTop sectors:")
    sectors = {}
    for r in campaign_rows:
        s = r["sector"][:30] if r["sector"] else "unknown"
        sectors[s] = sectors.get(s, 0) + 1
    for s, c in sorted(sectors.items(), key=lambda x: -x[1])[:10]:
        print(f"  {s}: {c}")

    print(f"\nCV vault matches:")
    for skill, count in sorted(SKILL_COUNTS.items(), key=lambda x: -x[1]):
        if count > 0:
            print(f"  {skill}: {count} candidates")

    return campaign_rows


if __name__ == "__main__":
    generate_campaign()
