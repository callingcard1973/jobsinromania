#!/usr/bin/env python3
"""Upsert land_offers.csv into interjob_master.land_offers (dedup by offer id).

Run on raspibig (DB local) or anywhere with PG reachable. Idempotent: re-running
refreshes fields (e.g. after a better OCR pass) without duplicating offers.
"""
import csv
import os
import sys
import psycopg2

DB = dict(host=os.getenv("PGHOST", "localhost"), dbname="interjob_master",
          user="tudor", password=os.getenv("PGPASSWORD", ""))
COLS = ["id", "judet_url", "slug", "detail_url", "pdf_url", "data_publicare",
        "suprafata", "pret", "vanzator", "cui", "email", "telefon"]


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "land_offers.csv"
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    up = leads = 0
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            vals = [r.get(c, "") or None for c in COLS]
            mode = r.get("_extract_mode", "")
            nr = bool(r.get("needs_review", "").strip())
            cur.execute(
                f"""INSERT INTO land_offers ({','.join(COLS)}, extract_mode, needs_review)
                    VALUES ({','.join(['%s']*len(COLS))}, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                      suprafata=EXCLUDED.suprafata, pret=EXCLUDED.pret,
                      vanzator=EXCLUDED.vanzator, cui=EXCLUDED.cui,
                      email=EXCLUDED.email, telefon=EXCLUDED.telefon,
                      extract_mode=EXCLUDED.extract_mode, needs_review=EXCLUDED.needs_review,
                      loaded_at=now()""",
                vals + [mode or None, nr])
            up += 1
            if r.get("email") or r.get("telefon"):
                leads += 1
    conn.commit()
    cur.execute("SELECT count(*), count(*) FILTER (WHERE email IS NOT NULL OR telefon IS NOT NULL) FROM land_offers")
    total, with_lead = cur.fetchone()
    print(f"upserted {up} ({leads} with contact this file); table now {total} offers, {with_lead} with a contact lead")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
