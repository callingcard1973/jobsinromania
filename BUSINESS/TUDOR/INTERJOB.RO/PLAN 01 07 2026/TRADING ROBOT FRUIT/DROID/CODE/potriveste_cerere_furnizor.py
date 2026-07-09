#!/usr/bin/env python3
"""Pentru cererile clare, gaseste furnizori contactabili (email) din suppliers_list.csv.

Prioritate: acelasi judet > Romania > import. Fara scoruri.
"""

import csv
from pathlib import Path

from listeaza_cereri import cereri_concrete

DATA = Path(__file__).parent.parent / "DATA"


def load_suppliers(path=None):
    path = path or DATA / "suppliers_list.csv"
    if not path.exists():
        return []
    return list(csv.DictReader(path.open(encoding="utf-8")))


def has_email(row):
    em = (row.get("email") or "").lower()
    return "@" in em and "necunoscut" not in em and "cauta" not in em


def suppliers_for(product, suppliers):
    p = product.lower().split()[0]  # "ardei kapia" -> "ardei"
    return [r for r in suppliers if p in (r.get("supplies", "").lower())]


def main():
    suppliers = load_suppliers()
    for req in cereri_concrete():
        prod = req.get("product_ro", "?")
        qty = req.get("quantity_kg")
        qty_s = f"{int(qty/1000)}to" if qty else "?"
        print(f"\n=== {prod.upper()} {qty_s} {req.get('quality','')} "
              f"<- {req.get('from_name','?')} ===")
        hits = suppliers_for(prod, suppliers)
        contactabili = [r for r in hits if has_email(r)]
        if not contactabili:
            print(f"  GOL: {len(hits)} furnizori dar 0 cu email")
            continue
        for r in contactabili[:8]:
            print(f"  {r['name'][:38]:<38} {r.get('origin',''):<10} {r['email']}")


if __name__ == "__main__":
    main()
