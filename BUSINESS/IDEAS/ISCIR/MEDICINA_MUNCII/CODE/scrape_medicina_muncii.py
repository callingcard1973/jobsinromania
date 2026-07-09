#!/usr/bin/env python3
"""
Scrape occupational medicine clinics (CAEN 8622) from laptop ONRC DB.
Output: CSV with cui, name, address, city, county, phone, email, website
Run: cd D:\\MEMORY\\BUSINESS\\IDEAS\\ISCIR\\MEDICINA_MUNCII && python CODE/scrape_medicina_muncii.py
"""
import csv
import sys
from pathlib import Path
from datetime import datetime

try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

# Laptop DB (companies_clean)
LAPTOP_DSN = "postgresql://postgres:postgres@127.0.0.1:5433/interjob_master"
CAEN_TARGET = "8622"  # Occupational health services
OUTPUT_CSV = Path(__file__).parent.parent / "DATA" / "medicina_muncii_raw.csv"
BACKUP_CSV = OUTPUT_CSV.with_suffix(".csv.bak")

# SQL to extract CAEN 8622 companies
QUERY = """
SELECT
    COALESCE(cod_fiscal, '') AS cui,
    COALESCE(name, '') AS name,
    COALESCE(address, '') AS address,
    COALESCE(city, '') AS city,
    COALESCE(county, '') AS county,
    COALESCE(phone, '') AS phone,
    COALESCE(email, '') AS email,
    COALESCE(website, '') AS website
FROM companies_clean
WHERE caen_main = %s
  AND country = 'RO'
ORDER BY cui
"""


def scrape_from_laptop() -> list[dict]:
    """Connect to laptop DB and extract CAEN 8622 companies."""
    rows = []
    try:
        conn = psycopg2.connect(LAPTOP_DSN)
        cur = conn.cursor()
        cur.execute(QUERY, (CAEN_TARGET,))
        cols = [desc[0] for desc in cur.description]
        for row in cur.fetchall():
            rows.append(dict(zip(cols, row)))
        cur.close()
        conn.close()
        print(f"[load] {len(rows):,} CAEN {CAEN_TARGET} companies from laptop DB")
    except Exception as e:
        print(f"ERROR: Cannot connect to laptop DB: {e}", file=sys.stderr)
        print(f"NOTE: Start PostgreSQL on :5433 or use existing CSV", file=sys.stderr)
        sys.exit(1)
    return rows


def save_csv(rows: list[dict], path: Path) -> int:
    """Save rows to CSV, backup old version."""
    if path.exists():
        path.rename(BACKUP_CSV)
        print(f"[backup] old CSV moved to {BACKUP_CSV.name}")

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["cui", "name", "address", "city", "county", "phone", "email", "website"],
        )
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main():
    print(f"[start] {datetime.now().isoformat()} — Scraping MEDICINA_MUNCII")
    print(f"[query] CAEN {CAEN_TARGET} from laptop DB: {LAPTOP_DSN}")

    rows = scrape_from_laptop()
    if not rows:
        print("WARNING: No rows found!", file=sys.stderr)
        sys.exit(1)

    # Deduplicate by CUI, keep first occurrence
    seen = set()
    deduped = []
    for row in rows:
        cui = row["cui"].strip()
        if cui and cui in seen:
            continue
        if cui:
            seen.add(cui)
        deduped.append(row)

    print(f"[dedup] {len(deduped):,} unique companies (removed {len(rows) - len(deduped):,} duplicates)")

    # Save
    count = save_csv(deduped, OUTPUT_CSV)
    print(f"[save] {count:,} rows → {OUTPUT_CSV.name}")
    print(f"[done] {datetime.now().isoformat()}")


if __name__ == "__main__":
    main()
