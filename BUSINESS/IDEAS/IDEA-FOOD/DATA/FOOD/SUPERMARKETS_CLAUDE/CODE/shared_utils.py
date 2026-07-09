#!/usr/bin/env python3
"""Shared utilities for food distribution project.

Provides: company name normalization, DB connections, CSV I/O helpers.
"""

import csv
import re
import unicodedata

# -- Database connection configs
DB_MASTER = dict(host="192.168.100.21", port=5432,
                 dbname="interjob_master", user="tudor", password="tudor")
DB_FOOD = dict(host="192.168.100.21", port=5432,
               dbname="food_distribution", user="tudor", password="tudor")

# -- Common SEAP enrichment columns
SEAP_COLS = ["winner_name", "cui", "email", "phone", "website",
             "city", "address", "sector", "wins", "total_value_ron",
             "match_source"]

# -- Company suffixes to strip during normalization
_SUFFIXES = [" SRL", " SA", " S.R.L.", " S.A.", " S.R.L", " S.A",
             " II", " PFA", " IF", " SNC", " SCS", " S.C.", " S.C", " SC"]


def normalize(name):
    """Normalize Romanian company name for matching.

    Strips diacritics, legal suffixes, SC prefix, punctuation.
    Returns uppercase ASCII string.
    """
    if not name:
        return ""
    name = unicodedata.normalize("NFKD", str(name))
    name = name.encode("ascii", "ignore").decode("ascii").upper().strip()
    for s in _SUFFIXES:
        if name.endswith(s):
            name = name[:-len(s)].strip()
    if name.startswith("SC "):
        name = name[3:]
    if name.startswith("S.C. "):
        name = name[5:]
    name = re.sub(r"[^A-Z0-9 ]", " ", name)
    return re.sub(r"\s+", " ", name).strip()


def get_master_conn():
    """Connect to interjob_master on raspibig."""
    import psycopg2
    return psycopg2.connect(**DB_MASTER)


def get_food_conn():
    """Connect to food_distribution on raspibig."""
    import psycopg2
    return psycopg2.connect(**DB_FOOD)


def load_enriched(filepath, key_col="cui"):
    """Load enriched CSV into dict keyed by key_col."""
    enriched = {}
    with open(filepath, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            enriched[row[key_col]] = row
    return enriched


def save_enriched(enriched, filepath, columns=None, sort_key="wins"):
    """Save enriched dict to CSV, sorted by sort_key descending."""
    columns = columns or SEAP_COLS
    rows = sorted(enriched.values(),
                  key=lambda x: -int(x.get(sort_key, 0)))
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in columns})


def apply_match(enriched, cui, email, phone, website, city, address, source):
    """Apply enrichment match to a record (only if cui exists)."""
    if cui not in enriched:
        return
    if email and "@" in str(email):
        enriched[cui]["email"] = email
    enriched[cui]["phone"] = enriched[cui].get("phone") or phone or ""
    enriched[cui]["website"] = enriched[cui].get("website") or website or ""
    enriched[cui]["city"] = enriched[cui].get("city") or city or ""
    enriched[cui]["address"] = enriched[cui].get("address") or address or ""
    enriched[cui]["match_source"] = source


def print_stats(enriched):
    """Print email/phone stats and source breakdown."""
    total = len(enriched)
    if not total:
        print("No records.")
        return
    we = sum(1 for r in enriched.values() if r.get("email"))
    wp = sum(1 for r in enriched.values() if r.get("phone"))
    print(f"FINAL: {total} total")
    print(f"  email: {we} ({100 * we // total}%)")
    print(f"  phone: {wp} ({100 * wp // total}%)")
    print(f"  still need email: {total - we}")
    sources = {}
    for r in enriched.values():
        s = r.get("match_source") or "none"
        sources[s] = sources.get(s, 0) + 1
    print("\nBy source:")
    for s, c in sorted(sources.items(), key=lambda x: -x[1])[:20]:
        print(f"  {s}: {c}")
