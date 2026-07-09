#!/usr/bin/env python3
"""Compara ofertele memorate: min/avg/max per produs din price_book.json. Fara scoruri."""

import json
from pathlib import Path

DATA = Path(__file__).parent.parent / "DATA"


def load_price_book(path=None):
    path = Path(path) if path else DATA / "price_book.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def comparison_rows(pb):
    rows = []
    for v in pb.values():
        b = v.get("benchmark")
        if not b:  # intrare malformata (edit manual / scriere partiala) => sari, nu crapa
            continue
        rows.append({
            "produs": v.get("product", "?"),
            "cur": v.get("currency", "RON"),
            "min": b.get("min_price_eur_kg"),
            "avg": b.get("avg_price_eur_kg"),
            "max": b.get("max_price_eur_kg"),
            "oferte": b.get("offer_count", 0),
            "origine": v.get("origin") or "",
            "ultim": v.get("last_updated", ""),
        })
    return sorted(rows, key=lambda r: r["produs"])


def main():
    rows = comparison_rows(load_price_book())
    if not rows:
        print("Price book gol.")
        return
    print(f"{'PRODUS':<14}{'MON':>4}{'MIN':>7}{'AVG':>7}{'MAX':>7}{'#':>3}  ORIGINE / ULTIM")
    for r in rows:
        print(f"{r['produs']:<14}{r['cur']:>4}{r['min']:>7}{r['avg']:>7}{r['max']:>7}"
              f"{r['oferte']:>3}  {r['origine'][:18]:<18} {r['ultim']}")


if __name__ == "__main__":
    main()
