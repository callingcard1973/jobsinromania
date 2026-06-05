#!/usr/bin/env python3
"""Merge employers_ro_enriched.csv + employers_ro_anofm.csv on CUI."""

import csv
from pathlib import Path

DATA = Path(__file__).parent.parent / "DATA"
ENRICHED = DATA / "employers_ro_enriched.csv"
ANOFM = DATA / "employers_ro_anofm.csv"
OUT = DATA / "employers_ro_final.csv"


def main():
    # Load enriched (the 2,666 list with full metadata)
    by_cui = {}
    with open(ENRICHED, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cui = (row.get("cui") or "").strip()
            if not cui:
                continue
            by_cui[cui] = {
                "company_name": row.get("company_name", ""),
                "cui": cui,
                "caen_code": row.get("caen_code", ""),
                "caen_description": row.get("caen_description", ""),
                "employees": row.get("employees", ""),
                "turnover_ron": row.get("turnover_ron", ""),
                "city": row.get("city", ""),
                "county": row.get("county", ""),
                "email": (row.get("email") or "").strip(),
                "email_source": row.get("email_source", ""),
                "email_verified": row.get("email_verified", "true"),
                "phone": row.get("phone", ""),
                "website": row.get("website", ""),
            }

    # Overlay with ANOFM matches — only fill empty emails
    added = 0
    new_firms = 0
    with open(ANOFM, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cui = (row.get("cui") or "").strip()
            anofm_email = (row.get("email") or "").strip()
            if not cui or not anofm_email:
                continue
            if cui in by_cui:
                if not by_cui[cui]["email"]:
                    by_cui[cui]["email"] = anofm_email
                    by_cui[cui]["email_source"] = row.get("source_table", "anofm")
                    by_cui[cui]["email_verified"] = "true"
                    if not by_cui[cui]["phone"]:
                        by_cui[cui]["phone"] = row.get("phone", "")
                    added += 1
            else:
                # New firm from ANOFM not in original list
                by_cui[cui] = {
                    "company_name": row.get("name", ""),
                    "cui": cui,
                    "caen_code": row.get("caen", ""),
                    "caen_description": "",
                    "employees": row.get("emp", ""),
                    "turnover_ron": row.get("turnover", ""),
                    "city": "",
                    "county": "",
                    "email": anofm_email,
                    "email_source": row.get("source_table", "anofm"),
                    "email_verified": "true",
                    "phone": row.get("phone", ""),
                    "website": "",
                }
                new_firms += 1

    # Sort by employees DESC
    rows = sorted(by_cui.values(),
                  key=lambda r: int(r["employees"]) if str(r["employees"]).isdigit() else 0,
                  reverse=True)

    fields = ["company_name", "cui", "caen_code", "caen_description", "employees",
              "turnover_ron", "city", "county", "email", "email_source",
              "email_verified", "phone", "website"]
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    total = len(rows)
    with_email = sum(1 for r in rows if r["email"])
    print(f"Output: {OUT}")
    print(f"Total firms:        {total}")
    print(f"With email:         {with_email} ({100*with_email/total:.1f}%)")
    print(f"Filled from ANOFM:  {added}")
    print(f"New firms added:    {new_firms}")


if __name__ == "__main__":
    main()
