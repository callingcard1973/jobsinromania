#!/usr/bin/env python3
"""Build the 50-column ANOFM offer list on raspi: union of every audience
snapshot, projected to the full 50-col scrape schema, DNC+sent suppressed.

Output: DATA/anofm_offers_SENDABLE_50col.csv (one row per employer).
Suppression = the single source of truth on raspi: anofm.dnc_master (kept fresh
every 2h by refresh_dnc_master.py) + anofm.send_log (all ANOFM history)."""
import csv
import glob
from pathlib import Path

import psycopg2

BASE = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI")
DATA = BASE / "DATA"
CSV_DIR = Path("/opt/ACTIVE/ANOFM_DATA/csv")
# latest live scrape + every manual archive (globbed so new ones are picked up)
RAW_SOURCES = [CSV_DIR / "anofm_jobs_latest.csv",
               *sorted(CSV_DIR.glob("_archive/anofm_raw_manual_*.csv"))]
EMAIL_COLS = ("email_1", "email_2", "email_3")
DB = dict(dbname="anofm", user="tudor", host="localhost", password="tudor")
OUT = DATA / "anofm_offers_SENDABLE_50col.csv"


def db_emails(query):
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute(query)
    s = {r[0].strip().lower() for r in cur.fetchall() if r[0]}
    conn.close()
    return s


def emails(path, cols):
    s = set()
    try:
        for r in csv.DictReader(open(path, encoding="utf-8-sig", errors="ignore")):
            for c in cols:
                e = (r.get(c) or "").strip().lower()
                if e and "@" in e:
                    s.add(e)
    except FileNotFoundError:
        pass
    return s


def positions(r):
    try:
        return int(r.get("positions_available") or 0)
    except ValueError:
        return 0


def main():
    dnc = db_emails("SELECT lower(email) FROM dnc_master")
    sent = db_emails("SELECT lower(email) FROM send_log")

    # universe of employers ever captured = union of all audience snapshots
    audience = emails(DATA / "anofm_angajatori_dedup.csv", ["email"])
    for bak in glob.glob(str(DATA / "anofm_angajatori_dedup.csv.bak_*")):
        audience |= emails(bak, ["email"])
    sendable = {e for e in audience if e not in dnc and e not in sent}

    header, best = None, {}
    for src in RAW_SOURCES:
        try:
            rd = csv.DictReader(open(src, encoding="utf-8-sig", errors="ignore"))
        except FileNotFoundError:
            continue
        if header is None:
            header = rd.fieldnames
        for r in rd:
            matched = None
            for c in EMAIL_COLS:
                e = (r.get(c) or "").strip().lower()
                if e in sendable:
                    matched = e
                    break
            if matched and (matched not in best or positions(r) > positions(best[matched])):
                best[matched] = r

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        for e in sorted(best):
            w.writerow(best[e])

    print(f"sendable={len(sendable)} matched_50col={len(best)} "
          f"unmatched={len(sendable)-len(best)} cols={len(header)} -> {OUT}")


if __name__ == "__main__":
    main()
