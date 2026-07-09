#!/usr/bin/env python3
"""Ingest the raw EURES job table -> consumer jobs table, with country normalized.

Source: scraper.scraped_jobs (273k+, what the always-on scraper writes, richer than
contacts_50 — has job_url + sector). Dest: interjob_master.eures_jobs.

- job_id = md5(job_url) when present, else md5(employer|title|country) (idempotent).
- country: scraped_jobs.country holds the SEARCH GROUP (e.g. 'de,nl,be,at,ch,lu'),
  not the job's country. Single ISO codes map to a real country; group values -> NULL
  (no reliable per-job country signal). Normalization happens HERE, not in the raw table.
"""
import hashlib
import psycopg2

SRC = {'dbname': 'scraper', 'user': 'tudor'}
DST = {'dbname': 'interjob_master', 'user': 'tudor'}
BATCH = 2000

ISO = {
    'se': 'Sweden', 'no': 'Norway', 'fr': 'France', 'pl': 'Poland', 'de': 'Germany',
    'dk': 'Denmark', 'fi': 'Finland', 'be': 'Belgium', 'at': 'Austria', 'ch': 'Switzerland',
    'nl': 'Netherlands', 'es': 'Spain', 'it': 'Italy', 'pt': 'Portugal', 'gr': 'Greece',
    'ie': 'Ireland', 'lu': 'Luxembourg', 'cz': 'Czechia', 'sk': 'Slovakia', 'hu': 'Hungary',
    'ro': 'Romania', 'bg': 'Bulgaria', 'mt': 'Malta',
}


def norm_country(raw):
    """Single ISO code -> country name; group/unknown -> None."""
    if not raw:
        return None
    v = raw.strip().lower()
    if ',' in v:          # search group, not a per-job country
        return None
    return ISO.get(v)     # None if unrecognized


def job_id(url, employer, title, country):
    if url:
        return hashlib.md5(url.encode('utf-8')).hexdigest()
    raw = f"{(employer or '').strip().lower()}|{(title or '').strip().lower()}|{(country or '').strip().lower()}"
    return hashlib.md5(raw.encode('utf-8')).hexdigest()


def _flush(cur, rows):
    args = b",".join(cur.mogrify("(%s,%s,%s,%s,%s,%s,%s,now(),now())", r) for r in rows)
    cur.execute(
        b"INSERT INTO eures_jobs "
        b"(job_id, job_title, company_name, country, sector, job_url, posted_date, created_at, updated_at) "
        b"VALUES " + args +
        b" ON CONFLICT (job_id) DO UPDATE SET "
        b"sector = COALESCE(EXCLUDED.sector, eures_jobs.sector), "
        b"country = COALESCE(EXCLUDED.country, eures_jobs.country), "
        b"updated_at = now()"
    )
    return cur.rowcount


def main():
    src = psycopg2.connect(**SRC)
    dst = psycopg2.connect(**DST)
    sc, dc = src.cursor(name='scjobs'), dst.cursor()
    sc.itersize = BATCH
    sc.execute("""
        SELECT job_url, employer, title, country, sector, scraped_at
        FROM scraped_jobs
        WHERE coalesce(title,'') <> '' OR coalesce(employer,'') <> ''
    """)

    seen, upserted, scanned, rows = set(), 0, 0, []
    for url, employer, title, country, sector, scraped_at in sc:
        scanned += 1
        jid = job_id(url, employer, title, country)
        if jid in seen:
            continue
        seen.add(jid)
        rows.append((jid, title or None, employer or None, norm_country(country),
                     sector or None, url or None, scraped_at))
        if len(rows) >= BATCH:
            upserted += _flush(dc, rows); dst.commit(); rows = []
    if rows:
        upserted += _flush(dc, rows); dst.commit()

    dc.execute("SELECT count(*), count(country) FROM eures_jobs")
    total, with_country = dc.fetchone()
    print(f"scanned={scanned} distinct={len(seen)} upserted={upserted} "
          f"eures_jobs_total={total} with_real_country={with_country}")
    for c in (sc, dc, src, dst):
        c.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
