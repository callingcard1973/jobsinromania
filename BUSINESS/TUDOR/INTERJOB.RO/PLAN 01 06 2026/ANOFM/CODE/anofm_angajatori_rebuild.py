#!/usr/bin/env python3
"""Rebuild ANOFM_ANGAJATORI dedup audience from latest ANOFM scraper CSV.

One row per company (top job by positions_available), business email only
(no free providers), excludes DNC + already-sent. Atomic write."""
import csv, glob, os, shutil, sys, unicodedata
from pathlib import Path
from datetime import datetime

import psycopg2

# ONLY deficient occupations (official ANOFM list, workinromania.gov.ro).
# Match on diacritic-stripped, lowercased job_title substring.
DEFICIT_OCC = ("bucatar", "electrician", "mecanic", "sofer",
               "sudor", "tamplar", "zidar", "zidari", "dulgher")


def is_deficit(job_title):
    jt = "".join(c for c in unicodedata.normalize("NFD", (job_title or "").lower())
                 if unicodedata.category(c) != "Mn")
    return any(occ in jt for occ in DEFICIT_OCC)

OUT       = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/anofm_angajatori_dedup.csv")
DB        = dict(dbname="anofm", user="tudor", host="localhost", password="tudor")
SCRAPE_DB = dict(dbname="anofm_scrapes", user="tudor", host="localhost", password="tudor")
FIELDS    = ["email", "company_name", "sector", "county", "job_title",
             "positions_available", "company_org_number"]
# gmail INCLUDED (2026-06-25): RO SMEs use gmail as their real business contact.
# yahoo still excluded — decision pending. Other free providers kept out.
FREE_DOMAINS = ("yahoo.", "hotmail.", "outlook.", "live.",
                "aol.com", "yandex.", "icloud.com", "protonmail.", "proton.me",
                "mail.ru", "inbox.lv", "gmx.", "tutanota.", "zoho.")


def fetch_scrape_rows():
    # all unique job postings across every scrape, straight from anofm_scrapes
    # (built by build_scrape_db.py) — instant vs parsing 227 CSVs.
    cols = ["email_1", "email_2", "email_3", "company_name", "company_org_number",
            "sector", "city", "job_title", "positions_available"]
    conn = psycopg2.connect(**SCRAPE_DB)
    cur = conn.cursor()
    cur.execute(f"SELECT {','.join(cols)} FROM scrape_jobs")
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return rows


def is_free(email):
    e = email.lower().strip()
    return any(d in e for d in FREE_DOMAINS)


def pick_email(row):
    for k in ("email_1", "email_2", "email_3"):
        v = (row.get(k) or "").strip()
        if v and "@" in v and not is_free(v):
            return v.lower()
    return None


def county_from_city(city):
    return (city.split(">")[0].strip() if city else "")


def load_exclusions():
    # single source of truth on raspi: send_log (all ANOFM history) + dnc_master
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("SELECT lower(email) FROM send_log")
    sent = {r[0].strip().lower() for r in cur.fetchall() if r[0]}
    cur.execute("SELECT lower(email) FROM dnc_master")
    dnc = {r[0].strip().lower() for r in cur.fetchall() if r[0]}
    conn.close()
    return sent, dnc


def main():
    rows = fetch_scrape_rows()
    print(f"Rebuild from anofm_scrapes: {len(rows)} unique job postings")
    sent, dnc = load_exclusions()
    print(f"Exclusions: sent={len(sent)} dnc={len(dnc)}")

    companies = {}
    for row in rows:
            if not is_deficit(row.get("job_title")):   # ONLY deficient occupations
                continue
            em = pick_email(row)
            if not em or em in sent or em in dnc:
                continue
            key = (row.get("company_org_number") or "").strip() or \
                  (row.get("company_name") or "").strip().lower()
            if not key:
                continue
            pos = int(row.get("positions_available") or 0)
            cur = companies.get(key)
            if cur is None or pos > cur["_pos"]:
                companies[key] = {
                    "email": em, "company_name": (row.get("company_name") or "").strip(),
                    "sector": (row.get("sector") or "").strip(),
                    "county": county_from_city(row.get("city")),
                    "job_title": (row.get("job_title") or "").strip(),
                    "positions_available": str(pos),
                    "company_org_number": (row.get("company_org_number") or "").strip(),
                    "_pos": pos,
                }

    # Dedup by email keeping highest positions_available
    rows = sorted(companies.values(), key=lambda r: r["_pos"], reverse=True)
    seen, final = set(), []
    for r in rows:
        if r["email"] in seen:
            continue
        seen.add(r["email"])
        final.append(r)

    if OUT.exists():
        bak = OUT.with_suffix(".csv.bak_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
        shutil.copy(OUT, bak)
    tmp = OUT.with_suffix(".csv.tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in final:
            w.writerow({k: r[k] for k in FIELDS})
    os.replace(tmp, OUT)
    print(f"Wrote {len(final)} rows to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
