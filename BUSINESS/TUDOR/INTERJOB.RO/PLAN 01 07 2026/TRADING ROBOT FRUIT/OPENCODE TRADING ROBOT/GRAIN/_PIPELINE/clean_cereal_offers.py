#!/usr/bin/env python3
"""Clean garbage entries from trading_offers WHERE category='cereal'.

Garbage patterns detected:
  - Social-media notifications ("liked your posts", "Grow faster with...")
  - Car rental / discount ads ("Nu ratați reducerile la închirierea de mașini")
  - Newsletters ("Ultimele noutati din Industria alimentara")
  - Non-grain products misclassified as cereal (lime, mazare, etc.)

Quarantine: marks internal_only=true + freshness_note with reason.
Does NOT hard-delete. Report-only with --dry (default).

Usage:
  python GRAIN/clean_cereal_offers.py          # dry-run report
  python GRAIN/clean_cereal_offers.py --apply   # mark as internal
  python GRAIN/clean_cereal_offers.py --delete  # hard delete garbage
"""
import json
import os
import re
import sys

try:
    import psycopg2
except ImportError:
    psycopg2 = None

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as CFG

# Canonical grain product names (RO, lower).
GRAIN_PRODUCTS = {
    "grau", "grau durum", "grau furajer", "grau panificatie",
    "porumb", "porumb boabe",
    "orz", "orzoaica",
    "floarea-soarelui", "floarea soarelui",
    "rapita",
    "triticale", "ovaz", "secara", "sorg", "soia",
    "naut", "naut furajer",
    "mustar",
}

# Patterns that indicate a non-offer / garbage entry.
GARBAGE_CONTEXT_PATTERNS = [
    "liked your posts",
    "grow faster with",
    "nu ratați reducerile",
    "închirierea de mașini",
    "ultimele noutati din industria",
    "campaign-archive.com",
    "view this email in your browser",
]

# Non-grain products that were misclassified as cereal.
NON_GRAIN_PRODUCTS = {
    "lime", "mazare", "linte", "fasole", "cartofi", "ceapa",
    "usturoi", "morcovi", "telina", "praz", "varza",
    "conopida", "broccoli", "ardei", "rosii", "castraveti",
    "dovlecel", "vinete", "salata", "spanac", "marcar",
    "pierde-varza", "leustean", "patrunjel", "marar",
}

# Products that ARE grain - but only if they have substantive offer data.
# E.g., "grau" with no price/quantity is still valid if context is grain.
# But "grau" with a car rental ad is garbage.
GRAIN_NO_CONTEXT_PRODUCTS = {
    "grau", "grau durum", "porumb", "orz", "soia", "naut",
}


def _conn():
    if psycopg2 is None:
        raise RuntimeError("psycopg2 not available")
    return psycopg2.connect(**CFG.DB)


def classify(offer):
    """Classify a cereal-offer row as 'good', 'garbage', or 'suspect'.
    
    Returns (status, reason) where status is one of:
      'good'     - legitimate grain offer or inquiry
      'garbage'  - clearly not a grain offer (social spam, ads, newsletter)
      'suspect'  - marginal (e.g. product is grain but context is missing)
    """
    oid = offer[0]
    product_ro = (offer[1] or "").lower().strip()
    raw_snippet = (offer[3] or "").lower()
    context = (offer[4] or "").lower()
    internal_only = offer[5]

    search_text = raw_snippet + " " + context

    # Check for non-grain product classification.
    if product_ro in NON_GRAIN_PRODUCTS:
        return ("garbage", f"non-grain product '{product_ro}' classified as cereal")

    # Check for non-grain product classification (fuzzy).
    for np in NON_GRAIN_PRODUCTS:
        if np in product_ro:
            return ("garbage", f"non-grain product '{product_ro}' classified as cereal")

    # Check garbage context patterns.
    for pat in GARBAGE_CONTEXT_PATTERNS:
        if re.search(pat, search_text):
            return ("garbage", f"pattern match: {pat}")

    # Check if product is actually a grain.
    is_grain = product_ro in GRAIN_PRODUCTS
    if not is_grain and not product_ro:
        return ("suspect", "empty product_ro with no grain match")

    if not is_grain:
        # Product is not in our grain list at all.
        # Check if it might be grain-like (e.g. transliteration).
        if re.match(r"^[a-z\s-]+$", product_ro) and product_ro not in GRAIN_PRODUCTS:
            return ("suspect", f"unknown product '{product_ro}' - not in grain taxonomy")
        return ("garbage", f"unknown non-grain product '{product_ro}'")

    # Product IS a known grain. Check if it has real offer context.
    has_quantity = bool(offer[2])  # quantity_kg
    has_price = raw_snippet and any(kw in raw_snippet for kw in
                                     ["eur", "lei", "ron", "euro", "€"])

    if not has_quantity and not has_price and not internal_only:
        # Grain product but no pricing/quantity context - could be noise.
        # Check if context is blank or generic.
        clean_context = context.replace("classification: internal use", "").strip()
        if not clean_context or len(clean_context) < 30:
            return ("suspect", f"grain '{product_ro}' with no offer context")

    return ("good", "legitimate grain offer")


def scan(conn=None):
    """Scan all cereal offers and classify them.
    
    Returns dict with good/garbage/suspect lists.
    """
    close = False
    if conn is None:
        conn = _conn()
        close = True
    cur = conn.cursor()
    cur.execute("""SELECT offer_id, product_ro, quantity_kg, raw_snippet,
                          context, internal_only
                   FROM trading_offers
                   WHERE category='cereal'
                   ORDER BY extracted_at DESC""")
    rows = cur.fetchall()
    cur.close()
    if close:
        conn.close()

    classified = {"good": [], "garbage": [], "suspect": []}
    for row in rows:
        status, reason = classify(row)
        offer_id = row[0]
        product_ro = row[1] or ""
        classified[status].append({
            "offer_id": offer_id,
            "product_ro": product_ro,
            "reason": reason,
            "internal_only": row[5],
        })
    return classified


def apply_quarantine(offer_ids, reason_prefix, dry=True):
    """Set internal_only=true + freshness_note for the given offers.
    
    Returns number of rows updated.
    """
    if not offer_ids:
        return 0
    conn = _conn()
    cur = conn.cursor()
    note = f"[{reason_prefix}] {__file__} auto-quarantine {__import__('datetime').date.today()}"
    if dry:
        print(f"  DRY-RUN: would quarantine {len(offer_ids)} offers")
        for oid in offer_ids:
            print(f"    {oid}")
        cur.close()
        conn.close()
        return len(offer_ids)
    cur.execute(
        """UPDATE trading_offers
              SET internal_only=true,
                  freshness_note=COALESCE(freshness_note || '; ', '') || %s
            WHERE offer_id = ANY(%s)""",
        (note, offer_ids))
    conn.commit()
    updated = cur.rowcount
    cur.close()
    conn.close()
    return updated


def hard_delete(offer_ids, dry=True):
    """Hard-delete offers (use with caution)."""
    if not offer_ids:
        return 0
    conn = _conn()
    cur = conn.cursor()
    if dry:
        print(f"  DRY-RUN: would DELETE {len(offer_ids)} offers")
        for oid in offer_ids:
            print(f"    {oid}")
        cur.close()
        conn.close()
        return len(offer_ids)
    cur.execute(
        "DELETE FROM trading_offers WHERE offer_id = ANY(%s)",
        (offer_ids,))
    conn.commit()
    deleted = cur.rowcount
    cur.close()
    conn.close()
    return deleted


def print_report(cls):
    total = sum(len(v) for v in cls.values())
    print(f"\nTotal cereal offers scanned: {total}")
    print(f"  Good:    {len(cls['good'])}")
    print(f"  Garbage: {len(cls['garbage'])}")
    print(f"  Suspect: {len(cls['suspect'])}")
    print()

    if cls["garbage"]:
        print("--- GARBAGE (should quarantine) ---")
        for o in cls["garbage"]:
            flag = " [already internal]" if o["internal_only"] else ""
            print(f"  {o['offer_id']:38s} {o['product_ro']:20s} {o['reason']}{flag}")

    if cls["suspect"]:
        print("\n--- SUSPECT (review manually) ---")
        for o in cls["suspect"]:
            flag = " [internal]" if o["internal_only"] else ""
            print(f"  {o['offer_id']:38s} {o['product_ro']:20s} {o['reason']}{flag}")

    if cls["good"]:
        print("\n--- GOOD ---")
        for o in cls["good"]:
            print(f"  {o['offer_id']:38s} {o['product_ro']:20s}")


def main():
    do_apply = "--apply" in sys.argv
    do_delete = "--delete" in sys.argv

    try:
        cls = scan()
    except RuntimeError as e:
        print(f"PG connection failed: {e}", file=sys.stderr)
        print("Make sure PostgreSQL is accessible and trading_offers exists.")
        return 1

    print_report(cls)

    garbage_ids = [o["offer_id"] for o in cls["garbage"] if not o["internal_only"]]

    if do_delete and garbage_ids:
        deleted = hard_delete(garbage_ids, dry=True)
        print(f"\nWould delete: {deleted} (add --apply to actually delete)")
    elif do_apply and garbage_ids:
        updated = apply_quarantine(garbage_ids, dry=False, reason_prefix="GARBAGE")
        print(f"\nQuarantined: {updated} garbage offers")
    elif garbage_ids:
        print(f"\n{len(garbage_ids)} garbage offers found. Use --apply to quarantine or --delete to hard-delete.")
    else:
        print("\nNo garbage offers to clean.")

    if cls["suspect"]:
        print(f"Review {len(cls['suspect'])} suspect entries manually.")

    return 0


if __name__ == "__main__":
    main()
