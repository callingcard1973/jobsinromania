"""Import arr_raw.csv to raspibig interjob_master.arr_operators + enrich emails."""
import csv, sys
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values

sys.stdout.reconfigure(encoding="utf-8")

INPUT = Path("/tmp/arr_raw.csv")
DB = {"host": "localhost", "port": 5432, "dbname": "interjob_master", "user": "tudor"}

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS arr_operators (
    id SERIAL PRIMARY KEY,
    judet TEXT,
    cod_fiscal TEXT UNIQUE,
    denumire TEXT,
    adresa TEXT,
    localitate TEXT,
    email TEXT,
    telefon TEXT,
    sursa_contact TEXT,
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);
"""

UPSERT_SQL = """
INSERT INTO arr_operators (judet, cod_fiscal, denumire, adresa, localitate)
VALUES %s
ON CONFLICT (cod_fiscal) DO UPDATE SET
    judet = EXCLUDED.judet,
    denumire = EXCLUDED.denumire,
    adresa = EXCLUDED.adresa,
    localitate = EXCLUDED.localitate,
    scraped_at = NOW();
"""

ENRICH_SQL = """
UPDATE arr_operators ao
SET email = cc.email,
    telefon = COALESCE(NULLIF(cc.phone,''), ao.telefon),
    sursa_contact = 'companies_clean'
FROM companies_clean cc
WHERE cc.cui = ao.cod_fiscal
  AND cc.country = 'RO'
  AND cc.email IS NOT NULL AND cc.email != ''
  AND ao.email IS NULL;
"""


def main():
    with open(INPUT, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    print(f"Loaded {len(rows)} rows from CSV")

    seen: set[str] = set()
    batch = []
    for r in rows:
        cf = r.get("cod_fiscal", "").strip()
        if not cf or cf in seen:
            continue
        seen.add(cf)
        batch.append((r["judet"], cf, r["denumire"], r["adresa"], r["localitate"]))

    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute(CREATE_SQL)
    conn.commit()

    execute_values(cur, UPSERT_SQL, batch, page_size=1000)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM arr_operators")
    total = cur.fetchone()[0]
    print(f"arr_operators: {total} rows")

    print("Enriching emails from companies_clean...")
    cur.execute(ENRICH_SQL)
    updated = cur.rowcount
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM arr_operators WHERE email IS NOT NULL")
    with_email = cur.fetchone()[0]
    print(f"Email enrichment: {updated} updated | {with_email} total with email ({with_email*100//total}%)")
    conn.close()


if __name__ == "__main__":
    main()
