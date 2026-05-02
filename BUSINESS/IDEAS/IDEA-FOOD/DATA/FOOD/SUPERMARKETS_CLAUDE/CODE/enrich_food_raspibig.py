#!/usr/bin/env python3
"""Enrich SEAP food winners on raspibig. Run ON raspibig only.

Extracts food winners (CPV 15*, 03*) from SEAP CSV, enriches from:
1. interjob_master.companies (by CUI + name)
2. interjob_master.contacts
3. contractors_enriched.csv
4. ANOFM data
5. Prefix name matching

Usage: python3 /tmp/enrich_food_raspibig.py
Output: /opt/ACTIVE/OPENDATA/DATA/SEAP_ENRICHED/seap_food_winners_enriched.csv
"""

import csv
import glob
import os
import psycopg2

from shared_utils import normalize as norm, SEAP_COLS as COLS

SEAP = "/opt/ACTIVE/OPENDATA/DATA/ACHIZITII_PUBLICE/achizitii_publice_2025_combined.csv"
CONTRACTORS = "/opt/ACTIVE/OPENDATA/DATA/CONTRACTOR_MATCHES/contractors_enriched.csv"
ANOFM_DIR = "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/ANOFM"
OUT = "/opt/ACTIVE/OPENDATA/DATA/SEAP_ENRICHED/seap_food_winners_enriched.csv"


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)

    # -- Step 1: Extract food winners
    print("1. Extracting food winners from SEAP CSV...")
    winners = {}
    with open(SEAP, "r", encoding="utf-8", errors="ignore") as f:
        for row in csv.DictReader(f):
            cpv = row.get("COD_CPV", "")
            if not (cpv.startswith("15") or cpv.startswith("03")):
                continue
            name = row.get("OFERTANT_CASTIGATOR", "").strip()
            cui = row.get("CUI_OFERTANT_CASTIGATOR", "").strip()
            val = 0
            try:
                val = float(row.get("VALOARE_CONTRACT_(RON)", 0) or
                            row.get("VALOARE_ACHIZITIE_(RON)", 0) or 0)
            except Exception:
                pass
            if not name:
                continue
            key = cui if cui else norm(name)
            if key in winners:
                winners[key]["wins"] += 1
                winners[key]["value"] += val
            else:
                winners[key] = dict(name=name, cui=cui, wins=1, value=val)

    total_cui = sum(1 for w in winners.values() if w["cui"])
    print(f"   {len(winners)} unique winners, {total_cui} with CUI")

    # -- Step 2: Load enrichment sources
    print("2. Loading sources...")
    conn = psycopg2.connect(dbname="interjob_master", user="tudor", password="tudor")
    cur = conn.cursor()

    # 2a. companies by CUI (batch)
    cuis = [w["cui"] for w in winners.values() if w["cui"]]
    cui_data = {}
    for i in range(0, len(cuis), 500):
        b = cuis[i:i + 500]
        ph = ",".join(["%s"] * len(b))
        cur.execute(
            "SELECT cui, email, phone, website, city, address, sector_name "
            "FROM companies WHERE cui IN (" + ph + ") AND country = %s",
            b + ["RO"])
        for cui, email, phone, website, city, addr, sector in cur:
            if cui not in cui_data or (email and not cui_data[cui].get("email")):
                cui_data[cui] = dict(email=email or "", phone=phone or "",
                                     website=website or "", city=city or "",
                                     address=addr or "", sector=sector or "")
    ce = sum(1 for v in cui_data.values() if v["email"])
    print(f"   companies(CUI): {len(cui_data)} matched, {ce} email")

    # 2b. companies by name
    cur.execute(
        "SELECT name, email, phone, website, city, address, cui, sector_name "
        "FROM companies WHERE country = 'RO' AND (email != '' OR phone != '')")
    by_name = {}
    for name, email, phone, website, city, addr, cui, sector in cur:
        n = norm(name)
        if not n:
            continue
        rec = dict(email=email or "", phone=phone or "", website=website or "",
                   city=city or "", address=addr or "", cui=cui or "", sector=sector or "")
        if n not in by_name or (email and not by_name[n].get("email")):
            by_name[n] = rec
    print(f"   companies(name): {len(by_name)}")

    # 2c. contacts table
    cur.execute(
        "SELECT c.name, ct.email, ct.phone, c.city, c.cui "
        "FROM contacts ct JOIN companies c ON c.id = ct.company_id "
        "WHERE c.country = 'RO' AND ct.email IS NOT NULL AND ct.email != ''")
    ca = 0
    for name, email, phone, city, cui in cur:
        n = norm(name)
        if n and n not in by_name:
            by_name[n] = dict(email=email, phone=phone or "", website="",
                              city=city or "", address="", cui=cui or "", sector="")
            ca += 1
    print(f"   contacts: +{ca}")
    conn.close()

    # 2d. ANOFM
    anofm = {}
    for fp in glob.glob(os.path.join(ANOFM_DIR, "*.csv")):
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                for row in csv.DictReader(fh):
                    c = row.get("company_org_number", "").strip()
                    p = row.get("company_phone", "").strip()
                    e = row.get("company_email", "").strip()
                    if c and (p or e):
                        if c not in anofm or (e and not anofm[c].get("email")):
                            anofm[c] = dict(phone=p, email=e)
        except Exception:
            pass
    ae = sum(1 for v in anofm.values() if v.get("email"))
    print(f"   ANOFM: {len(anofm)} CUIs, {ae} email")

    # 2e. contractors
    contractors = {}
    try:
        with open(CONTRACTORS, "r", encoding="utf-8", errors="ignore") as f:
            for row in csv.DictReader(f):
                c = row.get("cui", "").strip()
                e = row.get("email", "").strip()
                if c and e:
                    contractors[c] = dict(email=e, phone=row.get("phone", ""))
    except Exception:
        pass
    print(f"   contractors: {len(contractors)}")

    # 2f. prefix index
    prefix_idx = {}
    for n, rec in by_name.items():
        if len(n) >= 10 and rec.get("email"):
            px = n[:10]
            if px not in prefix_idx:
                prefix_idx[px] = rec
    print(f"   prefix index: {len(prefix_idx)}")

    # -- Step 3: Merge
    print("3. Merging...")
    results = []
    for key, w in winners.items():
        name, cui = w["name"], w["cui"]
        n = norm(name)
        e = p = ws = city = addr = sector = src = ""

        if cui and cui in cui_data:
            d = cui_data[cui]
            e, p, ws = d["email"], d["phone"], d["website"]
            city, addr, sector = d["city"], d["address"], d["sector"]
            if e:
                src = "companies_cui"

        if not e and n in by_name:
            d = by_name[n]
            e = d.get("email", "")
            p = p or d.get("phone", "")
            ws = ws or d.get("website", "")
            city = city or d.get("city", "")
            addr = addr or d.get("address", "")
            cui = cui or d.get("cui", "")
            sector = sector or d.get("sector", "")
            if e:
                src = "companies_name"

        if not e and n and len(n) >= 10:
            px = n[:10]
            if px in prefix_idx:
                d = prefix_idx[px]
                e = d["email"]
                p = p or d.get("phone", "")
                ws = ws or d.get("website", "")
                city = city or d.get("city", "")
                cui = cui or d.get("cui", "")
                src = "companies_prefix"

        if not e and cui and cui in contractors:
            d = contractors[cui]
            e = d["email"]
            p = p or d.get("phone", "")
            src = "contractors"

        if cui and cui in anofm:
            a = anofm[cui]
            if not e and a.get("email"):
                e = a["email"]
                src = "anofm"
            p = p or a.get("phone", "")

        results.append(dict(
            winner_name=name, cui=cui, email=e, phone=p, website=ws,
            city=city, address=addr, sector=sector, wins=w["wins"],
            total_value_ron=round(w["value"], 2), match_source=src))

    # -- Stats
    total = len(results)
    we = sum(1 for r in results if r["email"])
    wp = sum(1 for r in results if r["phone"])
    wc = sum(1 for r in results if r["cui"])
    print(f"\nRESULTS: {total} total")
    print(f"  email: {we} ({100 * we // total}%)")
    print(f"  phone: {wp} ({100 * wp // total}%)")
    print(f"  CUI:   {wc} ({100 * wc // total}%)")

    sources = {}
    for r in results:
        s = r["match_source"] or "none"
        sources[s] = sources.get(s, 0) + 1
    print("\nBy source:")
    for s, c in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"  {s}: {c}")

    results.sort(key=lambda x: -x["wins"])
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in results:
            w.writerow({c: r.get(c, "") for c in COLS})
    print(f"\nExported: {OUT}")


if __name__ == "__main__":
    main()
