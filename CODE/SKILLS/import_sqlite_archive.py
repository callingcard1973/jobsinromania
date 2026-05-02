#!/usr/bin/env python3
"""Import SQLite DBs from D:/MEMORY/DATA/ROMANIA/RASPIBIG_DEC_2025_DBS/ into PG.

Creates archive_<dbname>_<table> tables. Skips empty tables. All columns TEXT
(simplest, safe, and these are archives — no queries need types).
"""
import sqlite3
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_batch

DB = dict(host="127.0.0.1", port=5433, dbname="interjob_master",
          user="tudor", password="tudor")
ROOT = Path("D:/MEMORY/DATA/ROMANIA/RASPIBIG_DEC_2025_DBS")

# db file -> prefix for PG table names
FILES = {
    "elena.db": "elena",
    "MASTER_EMPLOYERS_DATABASE.db": "master_employers",
    "swiss_campaign.db": "swiss",
    "scraped_jobs.db": "nhs",
    "campaign.db": "fruitnature4",
    "denmark_campaign.db": "denmark",
}


def safe(name):
    return "".join(c if c.isalnum() or c == "_" else "_" for c in name).lower()


def import_db(sqlite_path, prefix, pg):
    cx = sqlite3.connect(sqlite_path)
    cx.row_factory = sqlite3.Row
    cur = cx.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'")
    tables = [r[0] for r in cur.fetchall()]
    imported = {}
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM \"{t}\"")
        n = cur.fetchone()[0]
        if n == 0:
            continue
        cur.execute(f"SELECT * FROM \"{t}\" LIMIT 1")
        cols = [safe(d[0]) for d in cur.description]
        pg_table = f"archive_{safe(prefix)}_{safe(t)}"
        with pg.cursor() as pc:
            pc.execute(f"DROP TABLE IF EXISTS {pg_table}")
            cols_def = ", ".join(f"{c} TEXT" for c in cols)
            pc.execute(f"CREATE TABLE {pg_table} ({cols_def})")
            pg.commit()
            cur.execute(f"SELECT * FROM \"{t}\"")
            batch = []
            placeholders = ", ".join(["%s"] * len(cols))
            sql = f"INSERT INTO {pg_table} ({','.join(cols)}) VALUES ({placeholders})"
            for row in cur:
                batch.append([str(v) if v is not None else None for v in row])
                if len(batch) >= 1000:
                    execute_batch(pc, sql, batch)
                    batch = []
            if batch:
                execute_batch(pc, sql, batch)
            pg.commit()
        imported[pg_table] = n
        print(f"  {pg_table}: {n}")
    cx.close()
    return imported


def main():
    pg = psycopg2.connect(**DB)
    totals = {}
    for fname, prefix in FILES.items():
        p = ROOT / fname
        if not p.exists():
            print(f"SKIP missing: {p}")
            continue
        print(f"\n== {fname} ({prefix}) ==")
        totals.update(import_db(p, prefix, pg))
    pg.close()

    print(f"\n=== DONE: {len(totals)} tables, {sum(totals.values())} rows ===")
    for t, n in sorted(totals.items()):
        print(f"  {t}: {n}")


if __name__ == "__main__":
    main()
