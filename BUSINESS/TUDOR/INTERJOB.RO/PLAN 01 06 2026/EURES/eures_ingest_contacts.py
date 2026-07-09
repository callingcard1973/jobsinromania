#!/usr/bin/env python3
"""Ingest live EURES scraper output -> consumer jobs table.

Reads scraper.contacts_50 (where the Playwright scraper actually writes) and
upserts distinct vacancies into interjob_master.eures_jobs (what catalogs,
roundup and classify read). Closes the DB-disconnect: the old normalizer wrote
normalized_* tables in a csv_raw DB that doesn't exist on raspibig.

Idempotent: job_id = md5(company|job_title|country); ON CONFLICT does nothing.
"""
import hashlib
import psycopg2

SRC = {'dbname': 'scraper', 'user': 'tudor'}
DST = {'dbname': 'interjob_master', 'user': 'tudor'}
BATCH = 1000


def job_id(company, title, country):
    raw = f"{(company or '').strip().lower()}|{(title or '').strip().lower()}|{(country or '').strip().lower()}"
    return hashlib.md5(raw.encode('utf-8')).hexdigest()


def main():
    src = psycopg2.connect(**SRC)
    dst = psycopg2.connect(**DST)
    sc = src.cursor()
    dc = dst.cursor()

    # Only rows with at least a company or job title carry job signal.
    sc.execute("""
        SELECT company_name, job_title, country, source, scraped_at
        FROM contacts_50
        WHERE coalesce(company_name,'') <> '' OR coalesce(job_title,'') <> ''
    """)

    seen, inserted, scanned = set(), 0, 0
    rows = []
    while True:
        chunk = sc.fetchmany(BATCH)
        if not chunk:
            break
        for company, title, country, source, scraped_at in chunk:
            scanned += 1
            jid = job_id(company, title, country)
            if jid in seen:
                continue
            seen.add(jid)
            rows.append((jid, title or None, company or None, country or None,
                         source or 'eures_raspibig', scraped_at))
            if len(rows) >= BATCH:
                inserted += _flush(dc, rows)
                dst.commit()
                rows = []
    if rows:
        inserted += _flush(dc, rows)
        dst.commit()

    dc.execute("SELECT count(*) FROM eures_jobs")
    total = dc.fetchone()[0]
    print(f"scanned={scanned} distinct={len(seen)} newly_inserted={inserted} eures_jobs_total={total}")
    for c in (sc, dc, src, dst):
        c.close()
    return 0


def _flush(cur, rows):
    """Upsert a batch, return count actually inserted (ON CONFLICT skipped)."""
    before = cur.rowcount
    args = b",".join(
        cur.mogrify("(%s,%s,%s,%s,%s,%s,now(),now())", r) for r in rows
    )
    cur.execute(
        b"INSERT INTO eures_jobs "
        b"(job_id, job_title, company_name, country, source, posted_date, created_at, updated_at) "
        b"VALUES " + args + b" ON CONFLICT (job_id) DO NOTHING"
    )
    return cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0


if __name__ == '__main__':
    raise SystemExit(main())
