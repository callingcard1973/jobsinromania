#!/usr/bin/env python3
"""Load EVERY ANOFM scrape snapshot into anofm.scrape_jobs (one table, all 50
raw columns, deduped by fingerprint). Lets the audience rebuild / offer builder
query the DB instead of parsing 227 CSVs each run. Idempotent (ON CONFLICT)."""
import csv, glob, hashlib
import psycopg2
from psycopg2.extras import execute_values

DB = dict(dbname="anofm_scrapes", user="tudor", host="localhost", password="tudor")
CSV_DIR = "/opt/ACTIVE/ANOFM_DATA/csv"
COLS = ["company_name", "company_normalized", "company_address", "company_city",
        "company_postal_code", "company_website", "company_org_number",
        "contact_person_1", "contact_person_2", "email_1", "email_2", "email_3",
        "phone_1", "phone_2", "phone_3", "contact_title", "job_title", "job_id",
        "job_description", "occupation", "sector", "location", "city", "region",
        "municipality", "country", "country_name", "employment_type",
        "contract_type", "working_hours", "positions_available", "start_date",
        "application_deadline", "salary", "salary_min", "salary_max",
        "salary_currency", "source_url", "application_url", "posting_date",
        "expiry_date", "source", "official_job_board", "scrape_server",
        "scrape_method", "scrape_timestamp", "scrape_date", "raw_source_file",
        "batch_id", "fingerprint"]


def fp(row):
    f = (row.get("fingerprint") or "").strip()
    if f:
        return f
    key = "|".join((row.get(k) or "").strip().lower()
                   for k in ("company_org_number", "job_id", "job_title", "email_1"))
    return hashlib.md5(key.encode()).hexdigest()


def main():
    files = sorted(glob.glob(f"{CSV_DIR}/anofm_jobs_2*.csv")) + \
            sorted(glob.glob(f"{CSV_DIR}/_archive/anofm_raw_manual_*.csv"))
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS scrape_jobs (" +
                ", ".join(f"{c} text" for c in COLS) +
                ", pk text PRIMARY KEY, loaded_at timestamp default now())")
    seen, batch, total, inserted = set(), [], 0, 0
    for fpath in files:
        for row in csv.DictReader(open(fpath, encoding="utf-8-sig", errors="ignore")):
            total += 1
            k = fp(row)
            if k in seen:
                continue
            seen.add(k)
            batch.append(tuple((row.get(c) or "") for c in COLS) + (k,))
            if len(batch) >= 5000:
                execute_values(cur, f"INSERT INTO scrape_jobs ({','.join(COLS)},pk) "
                               "VALUES %s ON CONFLICT (pk) DO NOTHING", batch)
                inserted += cur.rowcount
                batch = []
    if batch:
        execute_values(cur, f"INSERT INTO scrape_jobs ({','.join(COLS)},pk) "
                       "VALUES %s ON CONFLICT (pk) DO NOTHING", batch)
        inserted += cur.rowcount
    conn.commit()
    cur.execute("SELECT count(*) FROM scrape_jobs")
    print(f"files={len(files)} rows_read={total} unique={len(seen)} "
          f"inserted_now={inserted} table_total={cur.fetchone()[0]}")
    conn.close()


if __name__ == "__main__":
    main()
