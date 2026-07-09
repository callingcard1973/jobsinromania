"""
AFER Feroviar scraper — downloads ROGOP-2026.xls from afer.ro,
extracts unique vendor/contractor companies, enriches via CUI email CSV,
imports to interjob_master.afer_feroviar on raspibig.

Source: http://www.afer.ro/rogop/ROGOP-2026.xls
(ROGOP = Register of payments - AFER's authorized contractor companies)
"""

import time
import csv
import sys
import urllib.request
import ssl

import xlrd
import psycopg2

# ── config ────────────────────────────────────────────────────────────────────
ROGOP_URL = "http://www.afer.ro/rogop/ROGOP-2026.xls"
XLS_PATH = "/tmp/ROGOP-2026.xls"
EMAIL_CSV = "/tmp/tmp_cui_email.csv"
DB_PARAMS = {
    "host": "localhost", "port": 5432,
    "dbname": "interjob_master", "user": "tudor",
}
TABLE = "afer_feroviar"
SLEEP = 0.5
SOURCE = "afer_feroviar"


def download_xls():
    ctx = ssl._create_unverified_context()
    req = urllib.request.Request(ROGOP_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
        data = resp.read()
    with open(XLS_PATH, "wb") as f:
        f.write(data)
    print(f"Downloaded {len(data):,} bytes -> {XLS_PATH}")


def parse_xls():
    """Extract unique company names from ROGOP sheet (col 2 = Furnizor)."""
    wb = xlrd.open_workbook(XLS_PATH)
    sh = wb.sheet_by_index(0)
    seen = set()
    companies = []
    for r in range(5, sh.nrows):  # skip header rows
        name = str(sh.cell(r, 2).value).strip()
        if not name or len(name) < 4:
            continue
        # Skip if cell looks like an invoice number not a company name
        if name[0].isdigit() and len(name) < 20:
            continue
        if name in seen:
            continue
        seen.add(name)
        companies.append({"denumire": name})
    print(f"Parsed {len(companies)} unique companies from ROGOP")
    return companies


def load_email_map():
    """Load CUI->email mapping from /tmp/tmp_cui_email.csv."""
    email_map = {}
    try:
        with open(EMAIL_CSV, encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cui = str(row.get("cui", "") or row.get("CUI", "")).strip()
                email = str(row.get("email", "") or row.get("EMAIL", "")).strip()
                if cui and email:
                    email_map[cui] = email
        print(f"Loaded {len(email_map):,} CUI->email mappings")
    except FileNotFoundError:
        print("Warning: email CSV not found, proceeding without enrichment")
    return email_map


def create_table(conn):
    with conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE} (
                id SERIAL PRIMARY KEY,
                cui TEXT,
                denumire TEXT NOT NULL,
                localitate TEXT,
                judet TEXT,
                tip_autorizatie TEXT DEFAULT 'contractor_afer',
                sursa TEXT DEFAULT 'afer_feroviar',
                email TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(denumire)
            )
        """)
        conn.commit()
    print(f"Table {TABLE} ready")


def upsert_companies(conn, companies, email_map):
    inserted = 0
    with conn.cursor() as cur:
        for c in companies:
            email = email_map.get(c.get("cui", ""), None)
            try:
                cur.execute(f"""
                    INSERT INTO {TABLE} (cui, denumire, tip_autorizatie, sursa, email)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (denumire) DO UPDATE
                        SET email = EXCLUDED.email,
                            sursa = EXCLUDED.sursa
                """, (c.get("cui"), c["denumire"], "contractor_afer", SOURCE, email))
                if cur.rowcount > 0:
                    inserted += 1
            except Exception as e:
                conn.rollback()
                print(f"  Error inserting {c['denumire'][:40]}: {e}")
                continue
        conn.commit()
    return inserted


def main():
    print("=== AFER Feroviar Scraper ===")

    # 1. Download
    print("Downloading ROGOP XLS...")
    for attempt in range(3):
        try:
            download_xls()
            break
        except Exception as e:
            print(f"  Attempt {attempt+1} failed: {e}")
            time.sleep(SLEEP * 2)
            if attempt == 2:
                sys.exit("Download failed after 3 attempts")

    # 2. Parse
    companies = parse_xls()
    if not companies:
        sys.exit("No companies found in XLS")

    # 3. Email map
    email_map = load_email_map()

    # 4. DB import
    conn = psycopg2.connect(**DB_PARAMS)
    try:
        create_table(conn)
        inserted = upsert_companies(conn, companies, email_map)
        print(f"DB: {inserted} rows inserted/updated in {TABLE}")

        # Final count
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {TABLE}")
            total = cur.fetchone()[0]
        print(f"Total rows in {TABLE}: {total}")
    finally:
        conn.close()

    # 5. Save CSV locally
    csv_path = "/tmp/afer_feroviar.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["denumire", "cui", "email"])
        w.writeheader()
        w.writerows(companies)
    print(f"CSV saved: {csv_path}")


if __name__ == "__main__":
    main()
