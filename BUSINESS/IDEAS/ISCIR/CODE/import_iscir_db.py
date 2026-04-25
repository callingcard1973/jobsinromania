"""Import ISCIR_TOATE_FIRMELE.csv to raspibig interjob_master.iscir_operators."""
import csv, sys
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values

sys.stdout.reconfigure(encoding="utf-8")

INPUT = Path("/tmp/iscir_toate.csv")
DB = {"host": "localhost", "port": 5432, "dbname": "interjob_master", "user": "tudor"}

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS iscir_operators (
    id SERIAL PRIMARY KEY,
    source TEXT,
    company_name TEXT,
    cui TEXT UNIQUE,
    reg_number TEXT,
    address TEXT,
    it_iscir TEXT,
    email TEXT,
    telefon TEXT,
    sursa_contact TEXT,
    imported_at TIMESTAMPTZ DEFAULT NOW()
);
"""

UPSERT_SQL = """
INSERT INTO iscir_operators (source, company_name, cui, reg_number, address, it_iscir)
VALUES %s
ON CONFLICT (cui) DO UPDATE SET
    company_name = EXCLUDED.company_name,
    address = EXCLUDED.address,
    it_iscir = EXCLUDED.it_iscir;
"""


def main():
    with open(INPUT, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    print(f"Loaded {len(rows)} rows")

    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute(CREATE_SQL)
    conn.commit()

    seen: set[str] = set()
    batch = []
    for r in rows:
        cui = r.get("cui", "").strip()
        if not cui or cui in seen:
            continue
        seen.add(cui)
        batch.append((r.get("source", ""), r.get("company_name", ""), cui,
                      r.get("reg_number", ""), r.get("address", ""), r.get("it_iscir", "")))
    execute_values(cur, UPSERT_SQL, batch, page_size=500)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM iscir_operators")
    print(f"iscir_operators: {cur.fetchone()[0]} rows")
    conn.close()


if __name__ == "__main__":
    main()
