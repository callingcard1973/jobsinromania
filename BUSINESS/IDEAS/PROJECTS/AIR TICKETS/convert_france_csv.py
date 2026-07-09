#!/usr/bin/env python3
"""Convert France semicolon CSV to standard CSV with website column."""
import csv
SRC = "/opt/ACTIVE/FLIGHTS/TOURISM_DATA/france_hebergements_20251220.csv"
DST = "/opt/ACTIVE/FLIGHTS/TOURISM_DATA/france_hotels_clean.csv"
with open(SRC, encoding="utf-8") as f:
    reader = csv.reader(f, delimiter=";")
    headers = next(reader)
    # Find SITE INTERNET column
    site_idx = next(i for i, h in enumerate(headers) if "SITE" in h.upper())
    out_headers = ["name", "address", "postal", "city", "website", "type", "stars", "rooms"]
    rows = []
    for row in reader:
        if len(row) > site_idx:
            rows.append({
                "name": row[5] if len(row) > 5 else "",
                "address": row[6] if len(row) > 6 else "",
                "postal": row[7] if len(row) > 7 else "",
                "city": row[8] if len(row) > 8 else "",
                "website": row[site_idx].strip(),
                "type": row[1] if len(row) > 1 else "",
                "stars": row[2] if len(row) > 2 else "",
                "rooms": row[12] if len(row) > 12 else "",
            })
with open(DST, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=out_headers)
    w.writeheader()
    w.writerows(rows)
print(f"Converted {len(rows)} France hotels -> {DST}")
with_url = sum(1 for r in rows if r["website"])
print(f"With website: {with_url}")
