#!/usr/bin/env python3
"""Scan big Romania CSVs on raspibig for remaining emails by CUI.
Run ON raspibig: python3 /tmp/scan_big_csvs.py
"""

import csv
import os

ENRICHED = "/opt/ACTIVE/OPENDATA/DATA/SEAP_ENRICHED/seap_food_winners_enriched.csv"
COLS = ["winner_name", "cui", "email", "phone", "website",
        "city", "address", "sector", "wins", "total_value_ron", "match_source"]

BIG_FILES = [
    "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/MASTER/romania_unified.csv",
    "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/BILANT/virgil_schema_full.csv",
    "/opt/ACTIVE/OPENDATA/DATA/MASTER_ALL.csv",
    "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/BUCHAREST_ILFOV_ESTABLISHED/buc_ilfov_fully_enriched.csv",
    "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/BILANT/virgil_schema_enriched.csv",
    "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/BUCHAREST_ILFOV_ESTABLISHED/oldest_companies_enriched.csv",
    "/opt/ACTIVE/OPENDATA/DATA/MONTHLY/2025-12/month_2025-12_all.csv",
    "/opt/SCRAPERS/EUROPE/DATA/GENERAL_MASTER_50.csv",
]


def main():
    enriched = {}
    with open(ENRICHED, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            enriched[row["cui"]] = row

    need = {c: r for c, r in enriched.items() if not r.get("email") and c}
    print(f"Need email: {len(need)}")

    total_hit = 0
    for fp in BIG_FILES:
        if not os.path.exists(fp):
            continue
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                reader = csv.DictReader(fh)
                cols = reader.fieldnames or []
                cui_cols = [c for c in cols if c.lower() in (
                    "cui", "vat_id", "registration_id", "company_org_number")]
                email_cols = [c for c in cols if "email" in c.lower()]
                if not cui_cols or not email_cols:
                    fname = os.path.basename(fp)
                    print(f"  SKIP {fname}: no cui/email cols")
                    continue
                cui_col = cui_cols[0]
                email_col = email_cols[0]
                hit = 0
                for row in reader:
                    c = row.get(cui_col, "").strip()
                    e = row.get(email_col, "").strip()
                    if c and e and "@" in e and c in need:
                        enriched[c]["email"] = e
                        enriched[c]["match_source"] = "big:" + os.path.basename(fp)
                        hit += 1
                        del need[c]
                total_hit += hit
                print(f"  {os.path.basename(fp)}: {hit} new emails")
        except Exception as ex:
            print(f"  ERROR {os.path.basename(fp)}: {ex}")

    print(f"Total new from big files: {total_hit}")

    total = len(enriched)
    we = sum(1 for r in enriched.values() if r.get("email"))
    wp = sum(1 for r in enriched.values() if r.get("phone"))
    print(f"FINAL: email={we} ({100 * we // total}%), phone={wp} ({100 * wp // total}%), need={len(need)}")

    # Save
    rows = sorted(enriched.values(), key=lambda x: -int(x.get("wins", 0)))
    with open(ENRICHED, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLS})
    print("Saved.")


if __name__ == "__main__":
    main()
