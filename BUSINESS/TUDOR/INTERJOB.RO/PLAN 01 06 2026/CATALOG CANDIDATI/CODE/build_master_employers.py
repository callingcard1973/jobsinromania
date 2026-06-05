#!/usr/bin/env python3
"""Build employers_ro_master.csv — combines RO final + ANOFM factories, dedupe by email."""

import csv
import re
from pathlib import Path

DATA = Path(__file__).parent.parent / "DATA"
FINAL = DATA / "employers_ro_final.csv"
ANOFM = DATA / "employers_anofm_factories.csv"
OUT = DATA / "employers_ro_master.csv"


def norm_email(e):
    return (e or "").lower().strip()


def main():
    seen_emails = set()
    rows = []

    # TIER 1: large factories (CAEN 10-33, 50+ emp), with full metadata
    with open(FINAL, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            email = norm_email(r.get("email"))
            employees = r.get("employees", "")
            try:
                emp_int = int(employees) if employees and str(employees).isdigit() else 0
            except Exception:
                emp_int = 0

            # Assign tier based on size
            if emp_int >= 500:
                tier = "T1-large"
            elif emp_int >= 100:
                tier = "T2-mid"
            elif emp_int >= 50:
                tier = "T3-small-formal"
            else:
                tier = "T4-unknown-size"

            rows.append({
                "tier": tier,
                "company_name": r.get("company_name", ""),
                "cui": r.get("cui", ""),
                "caen_code": r.get("caen_code", ""),
                "caen_description": r.get("caen_description", ""),
                "employees": employees,
                "turnover_ron": r.get("turnover_ron", ""),
                "city": r.get("city", ""),
                "county": r.get("county", ""),
                "email": r.get("email", ""),
                "email_source": r.get("email_source", ""),
                "email_verified": r.get("email_verified", ""),
                "phone": r.get("phone", ""),
                "website": r.get("website", ""),
                "anofm_active": "false",
            })
            if email:
                seen_emails.add(email)

    # TIER 5: ANOFM SMB factories with email but no CUI metadata
    with open(ANOFM, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            email = norm_email(r.get("email"))
            if not email or email in seen_emails:
                continue
            seen_emails.add(email)
            rows.append({
                "tier": "T5-anofm-smb",
                "company_name": r.get("company", ""),
                "cui": "",
                "caen_code": "",
                "caen_description": "",
                "employees": "",
                "turnover_ron": "",
                "city": "",
                "county": "",
                "email": r.get("email", ""),
                "email_source": r.get("source_table", "anofm"),
                "email_verified": "true",
                "phone": r.get("phone", ""),
                "website": "",
                "anofm_active": "true",
            })

    # Sort: tier ASC (T1 first), then employees DESC
    tier_order = {"T1-large": 1, "T2-mid": 2, "T3-small-formal": 3, "T4-unknown-size": 4, "T5-anofm-smb": 5}
    rows.sort(key=lambda r: (
        tier_order.get(r["tier"], 9),
        -int(r["employees"]) if str(r["employees"]).isdigit() else 0,
    ))

    fields = ["tier", "company_name", "cui", "caen_code", "caen_description",
              "employees", "turnover_ron", "city", "county",
              "email", "email_source", "email_verified", "phone", "website",
              "anofm_active"]
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    # Stats
    by_tier = {}
    with_email = 0
    for r in rows:
        t = r["tier"]
        by_tier[t] = by_tier.get(t, 0) + 1
        if r["email"]:
            with_email += 1
    total = len(rows)
    print(f"Output: {OUT}")
    print(f"Total rows: {total}  |  With email: {with_email} ({100*with_email/total:.1f}%)")
    print("Tier breakdown:")
    for t, n in sorted(by_tier.items()):
        emails = sum(1 for r in rows if r["tier"] == t and r["email"])
        print(f"  {t:<22s} {n:>5d}  ({emails} with email)")


if __name__ == "__main__":
    main()
