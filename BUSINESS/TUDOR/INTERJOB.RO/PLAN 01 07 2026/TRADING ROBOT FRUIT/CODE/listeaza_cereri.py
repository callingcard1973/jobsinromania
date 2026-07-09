#!/usr/bin/env python3
"""Listeaza cererile memorate: cereri concrete (cu tonaj) + cumparatori conserve agregati."""

import json
from collections import Counter
from pathlib import Path

DATA = Path(__file__).parent.parent / "DATA"
SHARED = DATA.parent.parent / "DATA" / "00_SHARED_leads_si_dnc" / "requests_ledger.jsonl"


def cereri_concrete(path=None):
    """Cereri cu produs+tonaj din offers_ledger (entry_type=request)."""
    path = path or DATA / "offers_ledger.jsonl"
    out = []
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("entry_type") == "request":
            out.append(r)
    return out


def cereri_conserve(path=None):
    """Cumparatori conserve din requests_ledger shared."""
    path = path or SHARED
    out = []
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def top_produse(conserve, n=15):
    c = Counter()
    for r in conserve:
        for t in r.get("tags", []):
            c[t] += 1
    return c.most_common(n)


def main():
    concrete = cereri_concrete()
    print(f"=== CERERI CLARE cu tonaj ({len(concrete)}) ===")
    for r in concrete:
        qty = r.get("quantity_kg")
        qty_s = f"{int(qty/1000)}to" if qty else "?"
        print(f"  {r.get('product_ro','?'):<14} {qty_s:>6}  {r.get('quality',''):<11}"
              f" {r.get('origin',''):<8} <- {r.get('from_name','?')}")

    conserve = cereri_conserve()
    print(f"\n=== CUMPARATORI CONSERVE ({len(conserve)}) — top produse cerute ===")
    for p, cnt in top_produse(conserve):
        print(f"  {p:<14} {cnt}")


if __name__ == "__main__":
    main()
