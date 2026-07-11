#!/usr/bin/env python3
"""Consolideaza furnizorii F&V din surse curate intr-un master cu provenienta.

Surse:
  A. suppliers_list.csv (robot, 29) - furnizori cu produse/calitate detaliate
  B. DATE_leads_coop_export_202.csv (COOP harness) - OP legume-fructe + coop, national
Dedup pe email (non-null). Pastreaza coloana `source` ca sa stim de unde vine fiecare.
"""

import csv
from pathlib import Path

DATA = Path(__file__).parent.parent / "DATA"
COOP = DATA.parent.parent / "COOP GOSPODARII DE ALTADATA" / "DATA"
OUT = DATA / "suppliers_master.csv"
FIELDS = ["name", "email", "judet", "supplies", "quality", "segment", "source", "notes"]


def norm_email(e):
    e = (e or "").strip().lower()
    return e if "@" in e and "necunoscut" not in e and "cauta" not in e else ""


def from_robot(path=None):
    path = path or DATA / "suppliers_list.csv"
    out = []
    for r in csv.DictReader(path.open(encoding="utf-8")):
        em = norm_email(r.get("email"))
        if not em:
            continue
        out.append({"name": r.get("name", ""), "email": em, "judet": r.get("origin", ""),
                    "supplies": r.get("supplies", ""), "quality": r.get("quality", ""),
                    "segment": "supplier_detaliat", "source": "robot/suppliers_list.csv",
                    "notes": r.get("notes", "")})
    return out


def from_coop(path=None):
    path = path or COOP / "DATE_leads_coop_export_202.csv"
    out = []
    for r in csv.DictReader(path.open(encoding="utf-8")):
        em = norm_email(r.get("email"))
        if not em:
            continue
        out.append({"name": r.get("name", ""), "email": em, "judet": r.get("judet", ""),
                    "supplies": "", "quality": "", "segment": r.get("segment", ""),
                    "source": "COOP/DATE_leads_coop_export_202.csv",
                    "notes": f"admin={r.get('admin','')}"})
    return out


def main():
    seen, rows = set(), []
    # robot first (mai detaliat) -> prioritate la dedup
    for r in from_robot() + from_coop():
        if r["email"] in seen:
            continue
        seen.add(r["email"])
        rows.append(r)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    by_src = {}
    for r in rows:
        by_src[r["source"]] = by_src.get(r["source"], 0) + 1
    print(f"Master scris: {OUT}  total unici (email): {len(rows)}")
    for s, c in by_src.items():
        print(f"  {c:>4}  {s}")


if __name__ == "__main__":
    main()
