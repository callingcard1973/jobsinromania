#!/usr/bin/env python3
"""Memoria preturilor MEGA IMAGE: retine propunerile saptamanale de pret primite pe
apaminerala@yahoo.com de la amustatea@mega-image.ro si urmareste raspunsul furnizorului.

Model (din emailul real): WHS_CODE, CITY, SUPPLIER_CODE, CONTRACT_CODE, SUPPLIER_NAME,
PROFI_CODE, ARTICLE_NAME, WEEK, PROPUNERE_PRET, RASPUNS_FURNIZOR + DEADLINE.

Valoare trading: istoricul pret-propus vs pret-acceptat per articol/saptamana =>
robotul invata trendul si sugereaza contra-pretul. NU trimite emailuri.
"""
import argparse
import csv
import datetime as _dt
import json
import os
import statistics
import sys

BASE = os.path.dirname(__file__)
OUT_DIR = os.path.join(BASE, "CLAUDE TRADING ROBOT")
LEDGER = os.path.join(OUT_DIR, "mega_image_prices.jsonl")

FIELDS = ["week", "whs_code", "city", "supplier_code", "contract_code",
          "supplier_name", "profi_code", "article", "propunere_pret",
          "raspuns_furnizor", "deadline", "source_email"]


def _now():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _num(v):
    try:
        return float(str(v).replace(",", ".").strip())
    except (ValueError, AttributeError):
        return None


def record_proposal(row):
    """Adauga o linie de propunere (idempotent NU — append-only istoric pe saptamana)."""
    os.makedirs(OUT_DIR, exist_ok=True)
    out = {"ts": _now()}
    for f in FIELDS:
        out[f] = row.get(f, "")
    out["propunere_pret"] = _num(out["propunere_pret"])
    out["raspuns_furnizor"] = _num(out["raspuns_furnizor"])
    with open(LEDGER, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(out, ensure_ascii=True) + "\n")
    return out


def ingest_rows(rows):
    return [record_proposal(r) for r in rows]


def read_all():
    if not os.path.exists(LEDGER):
        return []
    out = []
    with open(LEDGER, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def history(article):
    a = (article or "").strip().upper()
    return [r for r in read_all() if r.get("article", "").upper() == a]


def pending():
    """Propuneri fara raspuns furnizor (de completat inainte de deadline)."""
    return [r for r in read_all() if not r.get("raspuns_furnizor")]


def suggest_response(article):
    """Sugereaza contra-pret pe baza istoricului raspunsurilor acceptate la acel articol."""
    accepted = [r["raspuns_furnizor"] for r in history(article)
                if r.get("raspuns_furnizor")]
    if not accepted:
        return None
    return round(statistics.median(accepted), 2)


SEED_ROWS = [
    # din emailul real 23.06, deadline 24.06.2026 14:00, Cooperativa Agricola Vointa Bacea
    {"week": "27", "whs_code": "714", "city": "Bolintin", "supplier_code": "8024",
     "contract_code": "802411O9", "supplier_name": "COOPERATIVA AGRICOLA VOINTA BACEA",
     "profi_code": "4207", "article": "CASTRAVETI CORNICHON", "propunere_pret": "3.50",
     "raspuns_furnizor": "2.50", "deadline": "2026-06-24 14:00",
     "source_email": "amustatea@mega-image.ro"},
    {"week": "27", "whs_code": "714", "city": "Bolintin", "supplier_code": "8024",
     "contract_code": "802411A9", "supplier_name": "COOPERATIVA AGRICOLA VOINTA BACEA",
     "profi_code": "4412", "article": "DOVLECEI", "propunere_pret": "3.50",
     "raspuns_furnizor": "2.00", "deadline": "2026-06-24 14:00",
     "source_email": "amustatea@mega-image.ro"},
    {"week": "27", "whs_code": "714", "city": "Bolintin", "supplier_code": "8024",
     "contract_code": "802411O9", "supplier_name": "COOPERATIVA AGRICOLA VOINTA BACEA",
     "profi_code": "4255", "article": "ROSII", "propunere_pret": "8.50",
     "raspuns_furnizor": "4.00", "deadline": "2026-06-24 14:00",
     "source_email": "amustatea@mega-image.ro"},
    {"week": "27", "whs_code": "714", "city": "Bolintin", "supplier_code": "8024",
     "contract_code": "802411O9", "supplier_name": "COOPERATIVA AGRICOLA VOINTA BACEA",
     "profi_code": "47673", "article": "ROSII TARANESTI", "propunere_pret": "10.00",
     "raspuns_furnizor": "7.00", "deadline": "2026-06-24 14:00",
     "source_email": "amustatea@mega-image.ro"},
    {"week": "27", "whs_code": "714", "city": "Bolintin", "supplier_code": "804",
     "contract_code": "802411A9", "supplier_name": "COOPERATIVA AGRICOLA VOINTA BACEA",
     "profi_code": "4211", "article": "VINETE", "propunere_pret": "7.50",
     "raspuns_furnizor": "4.00", "deadline": "2026-06-24 14:00",
     "source_email": "amustatea@mega-image.ro"},
]


def write_report():
    rows = read_all()
    with open(os.path.join(OUT_DIR, "mega_image_prices.csv"), "w",
              encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["ts"] + FIELDS)
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(OUT_DIR, "MEGA_IMAGE_REPORT.md"), "w", encoding="utf-8") as fh:
        fh.write("# Mega Image - memoria preturilor\n\n")
        fh.write("Sursa: apaminerala@yahoo.com <- amustatea@mega-image.ro\n")
        fh.write("Linii memorate: %d | fara raspuns furnizor: %d\n\n"
                 % (len(rows), len(pending())))
        fh.write("| Articol | Saptamana | Propunere MI | Raspuns furnizor | Deadline |\n")
        fh.write("|---|---|---|---|---|\n")
        for r in rows:
            fh.write("| %s | %s | %s | %s | %s |\n" %
                     (r.get("article"), r.get("week"), r.get("propunere_pret"),
                      r.get("raspuns_furnizor"), r.get("deadline")))
    return len(rows)


def _main():
    p = argparse.ArgumentParser(description="Memoria preturilor Mega Image")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("seed", help="incarca propunerea reala din email (week 27)")
    sub.add_parser("report")
    sub.add_parser("pending")
    s = sub.add_parser("suggest")
    s.add_argument("--article", required=True)
    args = p.parse_args()
    if args.cmd == "seed":
        ingest_rows(SEED_ROWS)
        n = write_report()
        print("seed ok, total linii=%d" % n)
    elif args.cmd == "report":
        print("total linii=%d" % write_report())
    elif args.cmd == "pending":
        for r in pending():
            print(json.dumps(r, ensure_ascii=True))
    elif args.cmd == "suggest":
        print("contra-pret sugerat pentru %s: %s" %
              (args.article, suggest_response(args.article)))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
