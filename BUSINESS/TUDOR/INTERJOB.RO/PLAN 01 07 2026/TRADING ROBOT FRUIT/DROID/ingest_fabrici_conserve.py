#!/usr/bin/env python3
"""Ingereaza fabricile de conserve ca CERERE (demand) in requests_ledger.

Fiecare fabrica = un cumparator. raw_demand (ce legume/fructe cere ca materie prima)
=> tag-uri normalizate. Asa robotul potriveste producatori (supply) -> fabrici (demand).
NU trimite emailuri.
"""
import csv
import os
import sys

BASE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(BASE, "CODE"))
import requests_ledger as reqs  # noqa: E402

CSV = os.path.join(BASE, "DATA", "DATE_fabrici_conserve_cerere.csv")


def run():
    n, skipped = 0, 0
    with open(CSV, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            email = (r.get("email") or "").strip()
            if not email:
                skipped += 1
                continue  # leads pe email non-null
            reqs.record_request(email, "buy_conserve", r.get("raw_demand", ""),
                                text="%s | %s" % (r.get("factory_name"), r.get("products")))
            n += 1
    return n, skipped


if __name__ == "__main__":
    n, skipped = run()
    print("ingerate %d fabrici (cerere) | fara email %d" % (n, skipped))
