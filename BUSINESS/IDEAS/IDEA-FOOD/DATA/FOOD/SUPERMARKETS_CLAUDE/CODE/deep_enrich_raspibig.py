#!/usr/bin/env python3
"""Deep enrichment of SEAP food winners from ALL raspibig sources.

Run ON raspibig: python3 /tmp/deep_enrich_raspibig.py

Reads seap_food_winners_enriched.csv (from previous run),
enriches unenriched records from every available source.
"""

import csv
import glob
import os
import psycopg2

from shared_utils import (normalize as norm, load_enriched, save_enriched,
                          print_stats, SEAP_COLS as COLS)

ENRICHED = "/opt/ACTIVE/OPENDATA/DATA/SEAP_ENRICHED/seap_food_winners_enriched.csv"


def main():
    enriched = load_enriched(ENRICHED)

    need = {cui: r for cui, r in enriched.items() if not r.get("email") and cui}
    print(f"Total: {len(enriched)}, need email: {len(need)}")

    # -- Source 1: ANOFM (email_1, phone_1, company_org_number)
    anofm = {}
    for fp in sorted(glob.glob("/opt/ACTIVE/OPENDATA/DATA/ROMANIA/ANOFM/*.csv")):
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                for row in csv.DictReader(fh):
                    cui = row.get("company_org_number", "").strip()
                    e1 = row.get("email_1", "").strip()
                    e2 = row.get("email_2", "").strip()
                    p1 = row.get("phone_1", "").strip()
                    email = e1 or e2
                    if cui and email:
                        anofm[cui] = dict(email=email, phone=p1)
                    elif cui and p1 and cui not in anofm:
                        anofm[cui] = dict(email="", phone=p1)
        except Exception:
            pass

    hit = 0
    for cui in list(need.keys()):
        if cui in anofm:
            a = anofm[cui]
            if a.get("email"):
                enriched[cui]["email"] = a["email"]
                enriched[cui]["match_source"] = "anofm"
                hit += 1
                del need[cui]
            enriched[cui]["phone"] = enriched[cui].get("phone") or a.get("phone", "")
    print(f"ANOFM: {len(anofm)} CUIs, {hit} new emails")

    # -- Source 2: produs_montan_producers
    conn = psycopg2.connect(dbname="interjob_master", user="tudor", password="tudor")
    cur = conn.cursor()
    cur.execute(
        "SELECT name, email, phone, website_url, county "
        "FROM produs_montan_producers "
        "WHERE email IS NOT NULL AND email <> ''")
    pm = {}
    for name, email, phone, website, county in cur:
        n = norm(name)
        if n and email:
            pm[n] = dict(email=email, phone=phone or "", website=website or "", city=county or "")

    hit2 = 0
    for cui in list(need.keys()):
        n = norm(need[cui].get("winner_name", ""))
        if n in pm:
            d = pm[n]
            enriched[cui]["email"] = d["email"]
            enriched[cui]["phone"] = enriched[cui].get("phone") or d["phone"]
            enriched[cui]["website"] = enriched[cui].get("website") or d["website"]
            enriched[cui]["match_source"] = "produs_montan"
            hit2 += 1
            del need[cui]
    print(f"Produs montan: {len(pm)} producers, {hit2} new emails")

    # -- Source 3: food_distribution DB
    hit3 = 0
    try:
        conn3 = psycopg2.connect(dbname="food_distribution", user="tudor", password="tudor")
        cur3 = conn3.cursor()
        cur3.execute(
            "SELECT company, email, phone, website, cui, county "
            "FROM contacts WHERE email IS NOT NULL AND email <> ''")
        fd_cui = {}
        fd_name = {}
        for company, email, phone, website, fc, county in cur3:
            if fc:
                fd_cui[fc.strip()] = dict(email=email, phone=phone or "", website=website or "", city=county or "")
            n = norm(company)
            if n and email:
                fd_name[n] = dict(email=email, phone=phone or "", website=website or "", city=county or "")
        conn3.close()

        for cui in list(need.keys()):
            if cui in fd_cui:
                d = fd_cui[cui]
                enriched[cui]["email"] = d["email"]
                enriched[cui]["phone"] = enriched[cui].get("phone") or d["phone"]
                enriched[cui]["match_source"] = "food_distribution_cui"
                hit3 += 1
                del need[cui]
                continue
            n = norm(need[cui].get("winner_name", ""))
            if n in fd_name:
                d = fd_name[n]
                enriched[cui]["email"] = d["email"]
                enriched[cui]["phone"] = enriched[cui].get("phone") or d["phone"]
                enriched[cui]["match_source"] = "food_distribution_name"
                hit3 += 1
                del need[cui]
        print(f"food_distribution: {len(fd_cui)} CUI + {len(fd_name)} names, {hit3} new emails")
    except Exception as ex:
        print(f"food_distribution: {ex}")

    # -- Source 4: Extra PG tables (executori, anevar, etc.)
    extra = [
        ("executori", "nume", "email", "telefon"),
        ("anevar_evaluatori", "nume", "email", "telefon"),
        ("consultanti_fiscali", "nume", "email", "telefon"),
        ("firme_audit", "nume", "email", "telefon"),
        ("auditori_financiari", "nume", "email", "telefon"),
        ("experti_contabili", "name", "phone", "phone"),
    ]
    hit4 = 0
    for table, ncol, ecol, pcol in extra:
        try:
            cur.execute(
                f"SELECT {ncol}, {ecol}, {pcol} FROM {table} "
                f"WHERE {ecol} IS NOT NULL AND {ecol} <> ''")
            tbl = {}
            for name, email, phone in cur:
                n = norm(name)
                if n and email and "@" in str(email):
                    tbl[n] = dict(email=email, phone=phone or "")
            th = 0
            for cui in list(need.keys()):
                n = norm(need[cui].get("winner_name", ""))
                if n in tbl:
                    d = tbl[n]
                    enriched[cui]["email"] = d["email"]
                    enriched[cui]["phone"] = enriched[cui].get("phone") or d["phone"]
                    enriched[cui]["match_source"] = table
                    th += 1
                    del need[cui]
            if th:
                print(f"  {table}: {th} new emails")
            hit4 += th
        except Exception:
            conn.rollback()
    print(f"Extra PG tables: {hit4} total")

    # -- Source 5: insolvency table (liquidator emails for bankrupt food companies)
    cur.execute(
        "SELECT DISTINCT cui, liquidator_email FROM insolvency "
        "WHERE liquidator_email IS NOT NULL AND liquidator_email <> '' "
        "AND cui IS NOT NULL AND cui <> ''")
    liq = {}
    for cui_val, email in cur:
        if "@" in str(email):
            liq[cui_val.strip()] = email
    hit5 = 0
    for cui in list(need.keys()):
        if cui in liq:
            enriched[cui]["email"] = liq[cui]
            enriched[cui]["match_source"] = "insolvency_liquidator"
            hit5 += 1
            del need[cui]
    print(f"Insolvency liquidators: {len(liq)} CUIs, {hit5} new emails")

    # -- Source 6: Scan all CSVs in key directories
    csv_dirs = [
        "/opt/ACTIVE/OPENDATA/DATA/CONTRACTOR_MATCHES/",
        "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/",
        "/opt/ACTIVE/CONSTRUCTORI/",
        "/opt/ACTIVE/EMAIL/CAMPAIGNS/",
        "/opt/ACTIVE/SCRAPERS/",
        "/opt/ACTIVE/DATA_IMPORT/",
    ]
    hit6 = 0
    scanned = 0
    for d in csv_dirs:
        for fp in glob.glob(d + "**/*.csv", recursive=True):
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                    reader = csv.DictReader(fh)
                    if not reader.fieldnames:
                        continue
                    fnames = reader.fieldnames
                    cui_cols = [c for c in fnames if "cui" in c.lower() or "org_number" in c.lower()]
                    email_cols = [c for c in fnames if "email" in c.lower()]
                    if not cui_cols or not email_cols:
                        continue
                    cui_col = cui_cols[0]
                    email_col = email_cols[0]
                    scanned += 1
                    for row in reader:
                        c = row.get(cui_col, "").strip()
                        e = row.get(email_col, "").strip()
                        if c and e and "@" in e and c in need:
                            enriched[c]["email"] = e
                            enriched[c]["match_source"] = "csv:" + os.path.basename(fp)
                            hit6 += 1
                            del need[c]
            except Exception:
                pass
    print(f"CSV scan: {scanned} files, {hit6} new emails")

    # -- Source 7: ANAF-related data (check for any ANAF tables or CSVs)
    try:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name ILIKE '%anaf%'")
        anaf_tables = [r[0] for r in cur.fetchall()]
        if anaf_tables:
            print(f"ANAF tables found: {anaf_tables}")
    except Exception:
        conn.rollback()

    # Check for ANAF CSVs
    anaf_csvs = glob.glob("/opt/ACTIVE/**/anaf*", recursive=True)
    anaf_csvs += glob.glob("/opt/ACTIVE/**/*anaf*", recursive=True)
    anaf_csvs += glob.glob("/opt/DATA_IMPORT/**/*anaf*", recursive=True)
    if anaf_csvs:
        print(f"ANAF files found: {anaf_csvs[:5]}")

    conn.close()

    print_stats(enriched)
    save_enriched(enriched, ENRICHED, COLS)
    print(f"\nExported: {ENRICHED}")


if __name__ == "__main__":
    main()
