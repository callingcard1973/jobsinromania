"""Consolidate all ANRE CSVs into raspibig interjob_master.anre_operators.
Files with CUI: upsert on (cui, sursa).
Files without CUI: lookup CUI from companies_clean by name, then upsert.
"""
import csv, sys, re
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values

sys.stdout.reconfigure(encoding="utf-8")

DATA_DIR = Path("/tmp/anre_data")
DB = {"host": "localhost", "port": 5432, "dbname": "interjob_master", "user": "tudor"}

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS anre_operators (
    id SERIAL PRIMARY KEY,
    sursa TEXT,
    denumire TEXT,
    cui TEXT,
    email TEXT,
    telefon TEXT,
    judet TEXT,
    tip_licenta TEXT,
    sursa_contact TEXT,
    imported_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS anre_operators_cui_sursa
    ON anre_operators(cui, sursa) WHERE cui IS NOT NULL AND cui != '';
CREATE UNIQUE INDEX IF NOT EXISTS anre_operators_name_sursa
    ON anre_operators(sursa, denumire) WHERE (cui IS NULL OR cui = '');
"""


def load_csv(path: Path) -> list[dict]:
    for enc in ["utf-8-sig", "utf-8", "latin-1"]:
        try:
            with open(path, encoding=enc) as f:
                return list(csv.DictReader(f))
        except Exception:
            continue
    return []


def find_col(cols: list[str], *keywords: str) -> str | None:
    for kw in keywords:
        for c in cols:
            if kw in c.lower():
                return c
    return None


def lookup_cui_by_name(cur, names: list[str]) -> dict[str, str]:
    """Batch CUI lookup from companies_clean by exact/prefix name match."""
    if not names:
        return {}
    # Use ILIKE with cleaned names — first 40 chars
    result: dict[str, str] = {}
    for name in names:
        key = name[:40].strip()
        if not key:
            continue
        cur.execute(
            "SELECT cui FROM companies_clean WHERE name ILIKE %s AND country='RO' LIMIT 1",
            (f"{key}%",)
        )
        row = cur.fetchone()
        if row:
            result[name] = row[0]
    return result


def main():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    for stmt in CREATE_SQL.strip().split(";"):
        s = stmt.strip()
        if s:
            try:
                cur.execute(s)
            except Exception:
                conn.rollback()
    conn.commit()

    total = 0
    for csv_path in sorted(DATA_DIR.glob("*.csv")):
        rows = load_csv(csv_path)
        if not rows:
            print(f"  SKIP {csv_path.name} — empty")
            continue
        sursa = csv_path.stem
        cols = list(rows[0].keys())

        cui_col = find_col(cols, "cui", "fiscal", "cod_f")
        name_col = find_col(cols, "societate", "denu", "name", "firma", "operator", "titular")
        judet_col = find_col(cols, "judet", "county")
        email_col = find_col(cols, "email", "mail")
        phone_col = find_col(cols, "telefon", "phone", "tel", "fax")
        tip_col = find_col(cols, "tip", "licenta", "atesta", "tip_serv", "nratestat", "nrlicenta")

        if not name_col:
            print(f"  SKIP {sursa} — no name col. Available: {cols[:8]}")
            continue

        # Build rows
        batch_rows = []
        no_cui_names = []
        for r in rows:
            name = r.get(name_col, "").strip()
            if not name:
                continue
            cui = r.get(cui_col, "").strip() if cui_col else ""
            batch_rows.append({
                "sursa": sursa,
                "denumire": name,
                "cui": cui,
                "email": r.get(email_col, "") if email_col else "",
                "telefon": r.get(phone_col, "") if phone_col else "",
                "judet": r.get(judet_col, "") if judet_col else "",
                "tip": r.get(tip_col, "") if tip_col else "",
            })
            if not cui:
                no_cui_names.append(name)

        # Batch CUI lookup for rows without CUI
        if no_cui_names:
            print(f"  {sursa}: looking up CUI for {len(no_cui_names)} rows...")
            cui_map = lookup_cui_by_name(cur, list(set(no_cui_names)))
            for r in batch_rows:
                if not r["cui"] and r["denumire"] in cui_map:
                    r["cui"] = cui_map[r["denumire"]]
            found = sum(1 for r in batch_rows if r["cui"])
            print(f"  {sursa}: {found}/{len(batch_rows)} with CUI after lookup")

        # Dedupe
        seen_cui: set[str] = set()
        seen_name: set[str] = set()
        deduped = []
        for r in batch_rows:
            if r["cui"]:
                key = (r["cui"], sursa)
                if key in seen_cui:
                    continue
                seen_cui.add(key)
            else:
                key2 = (sursa, r["denumire"])
                if key2 in seen_name:
                    continue
                seen_name.add(key2)
            deduped.append(r)

        if not deduped:
            print(f"  SKIP {sursa} — no rows after dedup")
            continue

        cur.executemany(
            "INSERT INTO anre_operators (sursa, denumire, cui, email, telefon, judet, tip_licenta) "
            "VALUES (%(sursa)s,%(denumire)s,%(cui)s,%(email)s,%(telefon)s,%(judet)s,%(tip)s) "
            "ON CONFLICT DO NOTHING",
            deduped
        )
        conn.commit()
        print(f"  {sursa}: {len(deduped)} rows")
        total += len(deduped)

    cur.execute("SELECT COUNT(*) FROM anre_operators")
    db_count = cur.fetchone()[0]
    print(f"\nDone. Processed ~{total} | anre_operators table: {db_count} rows")
    conn.close()


if __name__ == "__main__":
    main()
