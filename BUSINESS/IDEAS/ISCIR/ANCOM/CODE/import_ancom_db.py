"""Import ancom_final.csv to raspibig interjob_master.ancom_isp."""
import csv, sys
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values

sys.stdout.reconfigure(encoding="utf-8")

INPUT = Path("/tmp/ancom_final.csv")
DB = {"host": "localhost", "port": 5432, "dbname": "interjob_master", "user": "tudor"}

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS ancom_isp (
    id SERIAL PRIMARY KEY,
    denumire TEXT,
    judet TEXT,
    cui TEXT UNIQUE,
    adresa TEXT,
    oras TEXT,
    website TEXT,
    tipuri_retele TEXT,
    tipuri_servicii TEXT,
    email TEXT,
    email2 TEXT,
    telefon TEXT,
    sursa_contact TEXT,
    imported_at TIMESTAMPTZ DEFAULT NOW()
);
"""

UPSERT_SQL = """
INSERT INTO ancom_isp (denumire, judet, cui, adresa, oras, website,
    tipuri_retele, tipuri_servicii, email, email2, telefon, sursa_contact)
VALUES %s
ON CONFLICT (cui) DO UPDATE SET
    email = EXCLUDED.email,
    telefon = EXCLUDED.telefon,
    website = EXCLUDED.website,
    sursa_contact = EXCLUDED.sursa_contact;
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
        batch.append((r.get("denumire", ""), r.get("judet", ""), cui,
                      r.get("adresa", ""), r.get("oras", ""), r.get("website", ""),
                      r.get("tipuri_retele", ""), r.get("tipuri_servicii", ""),
                      r.get("email", ""), r.get("email2", ""),
                      r.get("telefon", ""), r.get("sursa_contact", "")))
    execute_values(cur, UPSERT_SQL, batch, page_size=500)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM ancom_isp")
    print(f"ancom_isp: {cur.fetchone()[0]} rows")
    conn.close()


if __name__ == "__main__":
    main()
