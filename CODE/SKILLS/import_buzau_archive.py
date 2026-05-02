#!/usr/bin/env python3
"""Import 10 Buzau CSVs from D:/MEMORY/DATA/ROMANIA/BUZAU_ARCHIVE/ into interjob_master.buzau_companies.

Key = cui. Later CSVs COALESCE-enrich earlier rows (non-null wins).
After successful import + row verify, deletes the remote raspi source.
"""
import csv
import io
import os
import subprocess
import sys
from pathlib import Path

import psycopg2

DB = dict(host="127.0.0.1", port=5433, dbname="interjob_master", user="tudor", password="tudor")
ROOT = Path("D:/MEMORY/DATA/ROMANIA/BUZAU_ARCHIVE")
RASPI = "tudor@192.168.100.20"

# file, remote_path, headers-present, column_map (local_col -> db_col), row_expected
JOBS = [
    {
        "local": "buzau_region_companies.csv",
        "remote": "/home/tudor/ARCHIVE/buzau_region_companies.csv",
        "has_header": False,
        "cols": ["cui", "company_name", "j_number", "founding_date", "age_years",
                 "legal_form", "county", "city", "address", "postal_code",
                 "sector", "website", "status_code", "status_name", "is_active"],
    },
    {
        "local": "buzau_companies_ANAF_FINAL.csv",
        "remote": "/home/tudor/ARCHIVE/buzau_companies_ANAF_FINAL.csv",
        "has_header": True,
        "cols": None,
    },
    {
        "local": "LEO_CASA_BUZAU/buzau_ALL_45k_ANAF_ENRICHED.csv",
        "remote": "/home/tudor/ARCHIVE/LEO_CASA_BUZAU/buzau_ALL_45k_ANAF_ENRICHED.csv",
        "has_header": True,
        "cols": None,
    },
    {
        "local": "LEO_CASA_BUZAU/buzau_all_companies_with_headers.csv",
        "remote": "/home/tudor/ARCHIVE/LEO_CASA_BUZAU/buzau_all_companies_with_headers.csv",
        "has_header": True,
        "cols": None,
    },
    {
        "local": "LEO_CASA_BUZAU/buzau_potrivite_companies_FINAL.csv",
        "remote": "/home/tudor/ARCHIVE/LEO_CASA_BUZAU/buzau_potrivite_companies_FINAL.csv",
        "has_header": False,
        "cols": ["cui", "company_name", "j_number", "founding_date", "age_years",
                 "legal_form", "county", "city", "address", "postal_code",
                 "sector", "website", "status_code", "status_name", "is_active"],
    },
    {
        "local": "LEO_CASA_BUZAU/buzau_potrivite_companies_FINAL.fuzzy_enriched.csv",
        "remote": "/home/tudor/ARCHIVE/LEO_CASA_BUZAU/buzau_potrivite_companies_FINAL.fuzzy_enriched.csv",
        "has_header": False,
        "cols": ["cui", "company_name", "j_number", "founding_date", "age_years",
                 "legal_form", "county", "city", "address", "postal_code",
                 "sector", "website", "status_code", "status_name", "is_active",
                 "fuzzy_email", "fuzzy_phone", "fuzzy_website", "fuzzy_score", "fuzzy_type"],
    },
    {
        "local": "LEO_CASA_BUZAU/buzau_companies_ANAF_SAMPLE.csv",
        "remote": "/home/tudor/ARCHIVE/LEO_CASA_BUZAU/buzau_companies_ANAF_SAMPLE.csv",
        "has_header": True,
        "cols": None,
    },
    {
        "local": "LEO_CASA_BUZAU/buzau_MASTER_CONSTRUCTION_contacts.csv",
        "remote": "/home/tudor/ARCHIVE/LEO_CASA_BUZAU/buzau_MASTER_CONSTRUCTION_contacts.csv",
        "has_header": True,
        "construction": True,
    },
    {
        "local": "LEO_CASA_BUZAU/buzau_potrivite_PHONE_ENRICHED.csv",
        "remote": "/home/tudor/ARCHIVE/LEO_CASA_BUZAU/buzau_potrivite_PHONE_ENRICHED.csv",
        "has_header": False,
        "cols": ["cui", "company_name", "j_number", "founding_date", "age_years",
                 "legal_form", "county", "city", "address", "postal_code",
                 "sector", "website", "status_code", "status_name", "phone_enriched"],
    },
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS buzau_companies (
    cui               BIGINT PRIMARY KEY,
    company_name      TEXT,
    j_number          TEXT,
    founding_date     DATE,
    age_years         INT,
    legal_form        TEXT,
    county            TEXT,
    city              TEXT,
    address           TEXT,
    postal_code       TEXT,
    sector            TEXT,
    website           TEXT,
    status_code       TEXT,
    status_name       TEXT,
    is_active         TEXT,
    phone_anaf        TEXT,
    address_anaf      TEXT,
    fuzzy_email       TEXT,
    fuzzy_phone       TEXT,
    fuzzy_website     TEXT,
    fuzzy_score       TEXT,
    fuzzy_type        TEXT,
    phone_enriched    TEXT,
    caen              TEXT,
    caen_description  TEXT,
    email             TEXT,
    phone             TEXT,
    country           TEXT,
    sources           TEXT[] DEFAULT ARRAY[]::TEXT[]
);
CREATE INDEX IF NOT EXISTS idx_buzau_county ON buzau_companies(county);
CREATE INDEX IF NOT EXISTS idx_buzau_email  ON buzau_companies(email) WHERE email IS NOT NULL;
"""

VALID_COLS = {"cui", "company_name", "j_number", "founding_date", "age_years",
              "legal_form", "county", "city", "address", "postal_code", "sector",
              "website", "status_code", "status_name", "is_active", "phone_anaf",
              "address_anaf", "fuzzy_email", "fuzzy_phone", "fuzzy_website",
              "fuzzy_score", "fuzzy_type", "phone_enriched", "caen",
              "caen_description", "email", "phone", "country"}


def parse_int(v):
    try:
        v = (v or "").strip()
        return int(v) if v else None
    except ValueError:
        return None


def parse_date(v):
    v = (v or "").strip()
    return v if v and len(v) == 10 else None


def row_to_dict(cols, row):
    d = {}
    for col, val in zip(cols, row):
        if col not in VALID_COLS:
            continue
        val = (val or "").strip() if isinstance(val, str) else val
        if val in ("", "N/A", "null", "NULL"):
            continue
        d[col] = val
    return d


def upsert(conn, rows, source):
    if not rows:
        return 0
    cur = conn.cursor()
    cols_all = sorted({k for r in rows for k in r.keys()} | {"cui"})
    # coalesce-merge: only overwrite when incoming non-null
    set_clauses = [f"{c} = COALESCE(EXCLUDED.{c}, buzau_companies.{c})"
                   for c in cols_all if c != "cui"]
    set_clauses.append(f"sources = array_append(buzau_companies.sources, %s)")
    placeholders = ", ".join(["%s"] * len(cols_all))
    sql = (f"INSERT INTO buzau_companies ({','.join(cols_all)}, sources) "
           f"VALUES ({placeholders}, ARRAY[%s]::TEXT[]) "
           f"ON CONFLICT (cui) DO UPDATE SET {', '.join(set_clauses)}")
    n = 0
    for r in rows:
        cui = parse_int(r.get("cui"))
        if not cui:
            continue
        r["cui"] = cui
        if "founding_date" in r:
            r["founding_date"] = parse_date(r["founding_date"])
        if "age_years" in r:
            r["age_years"] = parse_int(r["age_years"])
        vals = [r.get(c) for c in cols_all] + [source, source]
        try:
            cur.execute(sql, vals)
            n += 1
        except psycopg2.Error as e:
            conn.rollback()
            print(f"  SKIP cui={cui}: {e}")
            cur = conn.cursor()
            continue
    conn.commit()
    return n


def load_csv(path, has_header, col_override=None, construction=False):
    rows = []
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.reader(f)
        header = next(reader) if has_header else None
        cols = col_override or header
        if construction:
            # construction has: company_name, caen, caen_description, email, phone,
            # city, county, country, cui — but cui may be last/missing
            pass
        for row in reader:
            if not row:
                continue
            rows.append(row_to_dict(cols, row))
    return rows


def main():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute(SCHEMA)
    conn.commit()
    print("schema OK")

    cur.execute("SELECT COUNT(*) FROM buzau_companies")
    start = cur.fetchone()[0]
    print(f"start rows: {start}")

    for job in JOBS:
        p = ROOT / job["local"]
        if not p.exists():
            print(f"SKIP missing: {p}")
            continue
        print(f"\n== {job['local']} ==")
        rows = load_csv(p, job["has_header"], job.get("cols"),
                        job.get("construction", False))
        print(f"  parsed {len(rows)} rows")
        n = upsert(conn, rows, job["local"])
        print(f"  upserted {n}")
        cur.execute("SELECT COUNT(*) FROM buzau_companies")
        cur_count = cur.fetchone()[0]
        print(f"  table now: {cur_count}")

        # verify + delete remote
        if n > 0:
            if "--delete-remote" in sys.argv:
                r = subprocess.run(
                    ["ssh", RASPI, f"rm -v '{job['remote']}'"],
                    capture_output=True, text=True
                )
                print(f"  rm remote: {r.stdout.strip() or r.stderr.strip()}")

    # horeca emails — separate target table
    horeca = ROOT / "horeca_emails_campaign.csv"
    if horeca.exists():
        print("\n== horeca_emails_campaign.csv ==")
        cur.execute("""CREATE TABLE IF NOT EXISTS horeca_emails_archive (
            email TEXT PRIMARY KEY, name TEXT, country TEXT, city TEXT,
            website TEXT, phone TEXT, sector TEXT, sector_name TEXT)""")
        conn.commit()
        with open(horeca, encoding="utf-8", errors="replace") as f:
            rd = csv.DictReader(f)
            n = 0
            for r in rd:
                email = (r.get("email") or "").strip().lower()
                if not email or "@" not in email:
                    continue
                cur.execute("""INSERT INTO horeca_emails_archive
                    (email,name,country,city,website,phone,sector,sector_name)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (email) DO NOTHING""",
                    (email, r.get("name"), r.get("country"), r.get("city"),
                     r.get("website"), r.get("phone"), r.get("sector"),
                     r.get("sector_name")))
                n += 1
            conn.commit()
            print(f"  inserted {n}")
            if "--delete-remote" in sys.argv:
                r = subprocess.run(
                    ["ssh", RASPI,
                     "rm -v '/home/tudor/ARCHIVE/MEMORY_ARCHIVE/ZCLAW PERSONAL ASSISTANT/deploy/horeca_emails_campaign.csv'"],
                    capture_output=True, text=True
                )
                print(f"  rm remote: {r.stdout.strip() or r.stderr.strip()}")

    cur.execute("SELECT COUNT(*) FROM buzau_companies")
    end = cur.fetchone()[0]
    cur.execute("""SELECT COUNT(*) FROM buzau_companies
                   WHERE email IS NOT NULL OR phone IS NOT NULL
                   OR fuzzy_email IS NOT NULL OR phone_anaf IS NOT NULL""")
    enriched = cur.fetchone()[0]
    print(f"\n=== DONE: buzau_companies {start} -> {end} ({enriched} enriched) ===")
    if "--delete-remote" not in sys.argv:
        print("(dry-run: pass --delete-remote to rm source CSVs on raspi)")
    conn.close()


if __name__ == "__main__":
    main()
