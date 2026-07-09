#!/usr/bin/env python3
"""Scan ALL remaining data sources on raspibig for SEAP food winner emails.
Run ON raspibig: python3 /tmp/scan_all_sources.py
"""

import csv
import glob
import os
import sqlite3

from shared_utils import (normalize as norm, load_enriched, save_enriched,
                          print_stats, SEAP_COLS as COLS)

ENRICHED = "/opt/ACTIVE/OPENDATA/DATA/SEAP_ENRICHED/seap_food_winners_enriched.csv"


def scan_csv_by_cui(enriched, need, name_to_cui, filepath, label):
    """Scan a CSV for CUI+email matches. O(n) via dict lookups."""
    if not os.path.exists(filepath):
        return 0
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
            reader = csv.DictReader(fh)
            cols = reader.fieldnames or []
            cui_cols = [c for c in cols if c.lower() in (
                "cui", "vat_id", "registration_id", "cod_fiscal",
                "cif", "cod_unic", "company_org_number")]
            email_cols = [c for c in cols if "email" in c.lower()]
            phone_cols = [c for c in cols if "phone" in c.lower() or "telefon" in c.lower()]
            if not email_cols:
                return 0
            email_col = email_cols[0]
            cui_col = cui_cols[0] if cui_cols else None
            phone_col = phone_cols[0] if phone_cols else None
            name_cols = [c for c in cols if c.lower() in (
                "name", "company", "company_name", "denumire",
                "firma", "nume", "nume_firma")]
            name_col = name_cols[0] if name_cols else None

            hit = 0
            for row in reader:
                e = row.get(email_col, "").strip()
                if not e or "@" not in e:
                    continue
                # CUI match (O(1) dict lookup)
                if cui_col:
                    c = row.get(cui_col, "").strip()
                    if c and c in need:
                        enriched[c]["email"] = e
                        if phone_col:
                            enriched[c]["phone"] = enriched[c].get("phone") or row.get(phone_col, "").strip()
                        enriched[c]["match_source"] = label
                        hit += 1
                        del need[c]
                        continue
                # Name match (O(1) dict lookup)
                if name_col:
                    n = norm(row.get(name_col, ""))
                    if n and n in name_to_cui:
                        cui_key = name_to_cui[n]
                        if cui_key in need:
                            enriched[cui_key]["email"] = e
                            if phone_col:
                                enriched[cui_key]["phone"] = enriched[cui_key].get("phone") or row.get(phone_col, "").strip()
                            enriched[cui_key]["match_source"] = label
                            hit += 1
                            del need[cui_key]
                            del name_to_cui[n]
            return hit
    except Exception as ex:
        print(f"  ERROR {label}: {ex}")
        return 0


def main():
    enriched = load_enriched(ENRICHED)
    need = {c: r for c, r in enriched.items() if not r.get("email") and c}
    print(f"Need email: {len(need)}")

    # Build name->cui index for faster matching
    name_to_cui = {}
    for cui, r in need.items():
        n = norm(r.get("winner_name", ""))
        if n:
            name_to_cui[n] = cui

    total_new = 0

    # -- 1. DSVSA files (food companies!)
    dsvsa_files = [
        "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/DSVSA/DSVSA_WITH_CONTACTS.csv",
        "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/DSVSA/DSVSA_MASTER.fuzzy_enriched.csv",
        "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/DSVSA/DSVSA_ENRICHED.csv",
        "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/DSVSA/DSVSA_MASTER_DEDUPED.csv",
    ]
    for fp in dsvsa_files:
        h = scan_csv_by_cui(enriched, need, name_to_cui, fp, "dsvsa:" + os.path.basename(fp))
        if h:
            print(f"  DSVSA {os.path.basename(fp)}: {h} new emails")
        total_new += h

    # -- 2. Pagini Aurii
    h = scan_csv_by_cui(enriched, need, name_to_cui,
                        "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/PAGINI_AURII/pagini_aurii_contacts.csv",
                        "pagini_aurii")
    if h:
        print(f"  Pagini Aurii: {h} new emails")
    total_new += h

    # -- 3. Website contacts
    for fp in glob.glob("/opt/ACTIVE/OPENDATA/DATA/ROMANIA/WEBSITE_CONTACTS/*.csv"):
        h = scan_csv_by_cui(enriched, need, name_to_cui, fp, "web:" + os.path.basename(fp))
        if h:
            print(f"  WebContacts {os.path.basename(fp)}: {h} new emails")
        total_new += h

    # -- 4. ANAF full agriculture
    h = scan_csv_by_cui(enriched, need, name_to_cui,
                        "/opt/ACTIVE/SCRAPERS/AGRI/anaf_full_agriculture.csv",
                        "anaf_agri")
    print(f"  ANAF agriculture: {h} new emails")
    total_new += h

    # -- 5. DDG contacts (DuckDuckGo scraped)
    h = scan_csv_by_cui(enriched, need, name_to_cui,
                        "/opt/ACTIVE/SCRAPERS/AGRI/ddg_contacts.csv",
                        "ddg_contacts")
    print(f"  DDG contacts: {h} new emails")
    total_new += h

    # -- 6. Tourism agencies
    h = scan_csv_by_cui(enriched, need, name_to_cui,
                        "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/TOURISM_AGENCIES_RO_NEW.csv",
                        "tourism")
    print(f"  Tourism: {h} new emails")
    total_new += h

    # -- 7. Faliment enriched files
    faliment_files = [
        "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/faliment_all_sectors_enriched.csv",
        "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/faliment_ferme_enriched.csv",
        "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/licitatii_agricultura_enriched.csv",
    ]
    for fp in faliment_files:
        h = scan_csv_by_cui(enriched, need, name_to_cui, fp, "faliment:" + os.path.basename(fp))
        if h:
            print(f"  {os.path.basename(fp)}: {h} new emails")
        total_new += h

    # -- 8. ONRC enrichment SQLite DB
    onrc_db = "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/ONRC_ENRICHED/enrichment.db"
    if os.path.exists(onrc_db):
        try:
            sconn = sqlite3.connect(onrc_db)
            scur = sconn.cursor()
            tables = [r[0] for r in scur.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            for tbl in tables:
                cols_info = scur.execute(f"PRAGMA table_info({tbl})").fetchall()
                col_names = [c[1] for c in cols_info]
                cui_c = [c for c in col_names if "cui" in c.lower()]
                email_c = [c for c in col_names if "email" in c.lower()]
                if cui_c and email_c:
                    scur.execute(f"SELECT {cui_c[0]}, {email_c[0]} FROM {tbl} "
                                 f"WHERE {email_c[0]} IS NOT NULL AND {email_c[0]} != ''")
                    oh = 0
                    for cui_val, email_val in scur:
                        c = str(cui_val).strip()
                        if c in need and "@" in str(email_val):
                            enriched[c]["email"] = email_val.strip()
                            enriched[c]["match_source"] = "onrc_db"
                            oh += 1
                            del need[c]
                    if oh:
                        print(f"  ONRC DB ({tbl}): {oh} new emails")
                    total_new += oh
            sconn.close()
        except Exception as ex:
            print(f"  ONRC DB error: {ex}")

    # -- 9. FIRME_ROMANIA data
    for fp in glob.glob("/opt/ACTIVE/OPENDATA/DATA/ROMANIA/FIRME_ROMANIA/DATA/*.csv"):
        h = scan_csv_by_cui(enriched, need, name_to_cui, fp, "firme:" + os.path.basename(fp))
        if h:
            print(f"  FIRME {os.path.basename(fp)}: {h} new emails")
        total_new += h

    # -- 10. DATAGOV_ALL CSVs
    for fp in glob.glob("/opt/ACTIVE/OPENDATA/DATA/ROMANIA/DATAGOV_ALL/*.csv"):
        h = scan_csv_by_cui(enriched, need, name_to_cui, fp, "datagov:" + os.path.basename(fp))
        if h:
            print(f"  DATAGOV {os.path.basename(fp)}: {h} new emails")
        total_new += h

    # -- 11. Contact index JSON
    ci = "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/CONTACT_INDEX/master_contacts.json"
    if os.path.exists(ci):
        try:
            import json
            with open(ci, "r", encoding="utf-8") as f:
                contacts = json.load(f)
            if isinstance(contacts, dict):
                jh = 0
                for key, val in contacts.items():
                    if isinstance(val, dict):
                        cui_val = str(val.get("cui", "")).strip()
                        email_val = str(val.get("email", "")).strip()
                        if cui_val in need and email_val and "@" in email_val:
                            enriched[cui_val]["email"] = email_val
                            enriched[cui_val]["match_source"] = "contact_index"
                            jh += 1
                            del need[cui_val]
                if jh:
                    print(f"  Contact index: {jh} new emails")
                total_new += jh
        except Exception as ex:
            print(f"  Contact index error: {ex}")

    # -- 12. All remaining CSVs under /opt with CUI+email (broader scan)
    extra_dirs = [
        "/opt/ACTIVE/FALIMENT/",
        "/opt/ACTIVE/CUMPARFERME/",
        "/opt/DATA_IMPORT/",
        "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/CONSTRUCTII/",
        "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/EMPLOYERS/",
        "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/EU_FUNDS/",
        "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/EUFUNDS/",
    ]
    for d in extra_dirs:
        for fp in glob.glob(d + "**/*.csv", recursive=True):
            h = scan_csv_by_cui(enriched, need, name_to_cui, fp, "extra:" + os.path.basename(fp))
            if h:
                print(f"  {os.path.basename(fp)}: {h} new emails")
            total_new += h

    print(f"\nTotal new emails this run: {total_new}")

    print_stats(enriched)
    save_enriched(enriched, ENRICHED, COLS)
    print(f"\nSaved: {ENRICHED}")


if __name__ == "__main__":
    main()
