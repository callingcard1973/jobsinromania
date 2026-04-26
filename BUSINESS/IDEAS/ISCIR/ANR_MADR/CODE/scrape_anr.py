"""
scrape_anr.py — Download ANR (Autoritatea Navala Romana) authorized companies PDFs,
parse them with pdfplumber, export CSV, import to raspibig interjob_master.anr_naval,
enrich with /tmp/tmp_cui_email.csv via CUI cross-reference.

Sources:
  - autorizatii.pdf: river/maritime transport operators (~185 rows)
  - crewing.pdf: navigator supply agencies (~40 rows)

Usage:
  python scrape_anr.py
"""

import csv
import io
import re
import sys
import time
from pathlib import Path

import pdfplumber
import psycopg2
import requests

# ── Config ────────────────────────────────────────────────────────────────────
PDF_URLS = {
    "autorizatii": "https://portal.rna.ro/SiteAssets/PDF/autorizatii.pdf",
    "crewing": "https://portal.rna.ro/SiteAssets/PDF/crewing.pdf",
}
DATA_DIR = Path(__file__).parent.parent / "DATA"
OUT_CSV = DATA_DIR / "anr_naval.csv"
DB = dict(host="localhost", port=5432, dbname="interjob_master", user="tudor")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
TIMEOUT = 30
SLEEP = 0.5


# ── Helpers ───────────────────────────────────────────────────────────────────
def download_pdf(url: str, label: str) -> bytes:
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            print(f"  Downloaded {label}: {len(r.content):,} bytes")
            return r.content
        except Exception as exc:
            print(f"  Attempt {attempt + 1} failed: {exc}")
            time.sleep(SLEEP * 2)
    raise RuntimeError(f"Could not download {url}")


def clean(s: str | None) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", s).strip()


def parse_autorizatii(data: bytes) -> list[dict]:
    """Parse transport operator PDF — clear 6-col table."""
    rows = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for row in table:
                    if not row or not row[0]:
                        continue
                    crt = clean(row[0])
                    # Skip header rows
                    if crt in ("CRT", "NR."):
                        continue
                    serie = clean(row[1]) if len(row) > 1 else ""
                    company = clean(row[2]) if len(row) > 2 else ""
                    activity = clean(row[3]) if len(row) > 3 else ""
                    phone = clean(row[4]) if len(row) > 4 else ""
                    fax = clean(row[5]) if len(row) > 5 else ""
                    if not company:
                        continue
                    rows.append({
                        "denumire": company,
                        "cui": "",
                        "localitate": "",
                        "judet": "",
                        "tip": activity[:120],
                        "autorizatie": serie,
                        "telefon": phone or fax,
                        "sursa": "anr_autorizatii",
                        "email": "",
                    })
    return rows


def parse_crewing(data: bytes) -> list[dict]:
    """Parse crewing agencies PDF — messy multi-table layout, use text extraction."""
    rows = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            # Try main wide table first
            tables = page.extract_tables()
            # Pick the widest table (most columns)
            main_table = max(tables, key=lambda t: len(t[0]) if t else 0, default=None)
            if not main_table:
                continue
            for row in main_table:
                if not row:
                    continue
                # Row pattern: [nr, name, None, None, autorizatie, valabilitate, tel, adresa, ...]
                # Filter: row[1] should be company name (not None), row[6] = tel
                name_cell = None
                tel_cell = None
                adresa_cell = None
                # Find non-None cells
                non_none = [(i, c) for i, c in enumerate(row) if c and str(c).strip()]
                if len(non_none) < 2:
                    continue
                # Heuristic: company name is 2nd distinct non-number token
                for idx, cell in non_none:
                    cell_clean = clean(cell)
                    if re.search(r"[A-Z]{2,}", cell_clean) and len(cell_clean) > 5:
                        if "Nr." not in cell_clean and not re.match(r"^\d", cell_clean):
                            name_cell = cell_clean
                            break
                if not name_cell:
                    continue
                # Tel: 10-digit Romanian number
                for _, cell in non_none:
                    if re.search(r"0\d{9}", clean(cell)):
                        tel_cell = clean(cell)
                        break
                # Adresa: longer string with comma or digits
                for _, cell in non_none:
                    cc = clean(cell)
                    if len(cc) > 20 and ("," in cc or re.search(r"\d", cc)):
                        adresa_cell = cc
                        break
                # Extract localitate from address
                localitate = ""
                if adresa_cell:
                    parts = adresa_cell.split(",")
                    if parts:
                        localitate = parts[0].strip()[:50]
                rows.append({
                    "denumire": name_cell[:150],
                    "cui": "",
                    "localitate": localitate,
                    "judet": "",
                    "tip": "FURNIZARE NAVIGATORI (CREWING)",
                    "autorizatie": "",
                    "telefon": tel_cell or "",
                    "sursa": "anr_crewing",
                    "email": "",
                })
    # Deduplicate by name
    seen = set()
    unique = []
    for r in rows:
        key = r["denumire"].upper()
        if key not in seen and len(key) > 4:
            seen.add(key)
            unique.append(r)
    return unique


def save_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"  Saved {len(rows)} rows to {path}")


def import_to_db(rows: list[dict]) -> int:
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS anr_naval (
            id SERIAL PRIMARY KEY,
            denumire TEXT,
            cui TEXT,
            localitate TEXT,
            judet TEXT,
            tip TEXT,
            autorizatie TEXT,
            telefon TEXT,
            email TEXT,
            sursa TEXT DEFAULT 'anr_naval',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    cur.execute("TRUNCATE anr_naval")
    inserted = 0
    for r in rows:
        cur.execute("""
            INSERT INTO anr_naval (denumire, cui, localitate, judet, tip, autorizatie, telefon, email, sursa)
            VALUES (%(denumire)s, %(cui)s, %(localitate)s, %(judet)s, %(tip)s, %(autorizatie)s,
                    %(telefon)s, %(email)s, %(sursa)s)
        """, r)
        inserted += 1
    conn.commit()
    cur.close()
    conn.close()
    print(f"  Inserted {inserted} rows into anr_naval")
    return inserted


def enrich_email(conn_params: dict) -> int:
    # Load email map
    email_map: dict[str, str] = {}
    email_csv = Path("/tmp/tmp_cui_email.csv")
    if not email_csv.exists():
        print("  Email CSV not found locally — will enrich on raspibig")
        return 0
    with open(email_csv, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(",", 1)
            if len(parts) == 2:
                email_map[parts[0].strip()] = parts[1].strip()

    conn = psycopg2.connect(**conn_params)
    cur = conn.cursor()
    updated = 0
    for cui, email in email_map.items():
        cur.execute(
            "UPDATE anr_naval SET email=%s WHERE cui=%s AND (email IS NULL OR email='')",
            (email, cui),
        )
        updated += cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    print(f"  Email enrichment: {updated} rows updated")
    return updated


def main() -> None:
    print("=== ANR Naval Scraper ===")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Download
    print("\n[1] Downloading PDFs...")
    autorizatii_data = download_pdf(PDF_URLS["autorizatii"], "autorizatii")
    time.sleep(SLEEP)
    crewing_data = download_pdf(PDF_URLS["crewing"], "crewing")

    # Parse
    print("\n[2] Parsing PDFs...")
    rows_a = parse_autorizatii(autorizatii_data)
    rows_c = parse_crewing(crewing_data)
    print(f"  autorizatii: {len(rows_a)} rows")
    print(f"  crewing: {len(rows_c)} rows")
    all_rows = rows_a + rows_c

    # Save CSV
    print("\n[3] Saving CSV...")
    save_csv(all_rows, OUT_CSV)

    # Import DB
    print("\n[4] Importing to DB...")
    import_to_db(all_rows)

    # Enrich
    print("\n[5] Email enrichment...")
    enrich_email(DB)

    print(f"\nDone. Total: {len(all_rows)} companies")


if __name__ == "__main__":
    main()
