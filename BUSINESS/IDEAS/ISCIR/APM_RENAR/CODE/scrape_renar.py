#!/usr/bin/env python3
"""
RENAR accredited organizations scraper.
API: https://www.renar.ro/index.php/oec/get_oecs (DataTables server-side, 1811 records)
Output: DATA/renar_laboratoare.csv
DB: raspibig interjob_master.renar_laboratoare
Max 250 lines.
"""
import csv
import json
import re
import ssl
import time
import urllib.request
from pathlib import Path

import psycopg2

DATA_DIR = Path(__file__).parent.parent / "DATA"
OUT_CSV = DATA_DIR / "renar_laboratoare.csv"
SSL_CTX = ssl._create_unverified_context()
RENAR_API = "https://www.renar.ro/index.php/oec/get_oecs"
BATCH = 500
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

# Certificate prefix → domain type
CERT_DOMAIN = {
    "LI": "laborator_incercari",
    "LE": "laborator_etalonare",
    "LM": "laborator_medical",
    "OR": "organism_certificare_produse_eco",
    "PR": "organism_certificare_produse",
    "PS": "organism_certificare_persoane",
    "ON": "organism_certificare_sisteme",
    "OI": "organism_inspectie",
    "OV": "organism_verificare_metrologica",
}


def fetch_batch(start, length=BATCH, retries=3):
    data = (
        f"draw={start // length + 1}&start={start}&length={length}"
        f"&order%5B0%5D%5Bcolumn%5D=0&order%5B0%5D%5Bdir%5D=asc&search%5Bvalue%5D="
    ).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                RENAR_API,
                data=data,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-Requested-With": "XMLHttpRequest",
                },
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=30, context=SSL_CTX)
            return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt == retries - 1:
                print(f"  FAIL batch {start}: {e}")
                return None
            time.sleep(1)
    return None


def domain_from_cert(cert_nr):
    prefix = re.match(r"^([A-Z]+)", str(cert_nr) or "")
    if prefix:
        return CERT_DOMAIN.get(prefix.group(1), "laborator_incercari")
    return "laborator_incercari"


def scrape_all():
    """Fetch all records from RENAR DataTables API."""
    rows = []
    # Get total first
    first = fetch_batch(0, 1)
    if not first:
        return rows
    total = first.get("recordsTotal", 0)
    print(f"  Total RENAR records: {total}")

    start = 0
    while start < total:
        print(f"  Fetching {start}–{start + BATCH}...", end=" ", flush=True)
        result = fetch_batch(start, BATCH)
        if not result:
            break
        batch_data = result.get("data", [])
        print(f"{len(batch_data)} rows")
        for rec in batch_data:
            # Columns: [id, cert_nr, denumire, laborator, localitate, data_emiterii, data_expirarii, referential]
            if len(rec) < 8:
                continue
            cert_nr = str(rec[1]).strip()
            denumire = str(rec[2]).strip()
            laborator = str(rec[3]).strip()
            localitate = str(rec[4]).strip()
            data_emiterii = str(rec[5]).strip()
            data_expirarii = str(rec[6]).strip()
            referential = str(rec[7]).strip()
            domeniu = domain_from_cert(cert_nr)
            rows.append({
                "cui": "",  # not in API response, will enrich by name if possible
                "denumire": denumire[:200],
                "laborator": laborator[:200],
                "localitate": localitate[:100],
                "judet": "",
                "domeniu": domeniu,
                "cert_nr": cert_nr,
                "referential": referential[:100],
                "data_emiterii": data_emiterii,
                "data_expirarii": data_expirarii,
                "sursa": "renar_lab",
                "email": "",
            })
        start += BATCH
        time.sleep(0.5)
    return rows


def load_email_map():
    email_map = {}
    email_file = Path("/tmp/tmp_cui_email.csv")
    if not email_file.exists():
        return email_map
    with open(email_file, newline="", encoding="utf-8", errors="ignore") as f:
        for row in csv.DictReader(f):
            cui = str(row.get("cui", "")).strip()
            email = str(row.get("email", "")).strip()
            if cui and email:
                email_map[cui] = email
    return email_map


def create_table(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS renar_laboratoare (
            id SERIAL PRIMARY KEY,
            cui TEXT,
            denumire TEXT,
            laborator TEXT,
            localitate TEXT,
            judet TEXT,
            domeniu TEXT,
            cert_nr TEXT,
            referential TEXT,
            data_emiterii TEXT,
            data_expirarii TEXT,
            sursa TEXT DEFAULT 'renar_lab',
            email TEXT,
            inserted_at TIMESTAMP DEFAULT NOW()
        )
    """)


def import_to_db(rows):
    conn = psycopg2.connect(host="localhost", port=5432, dbname="interjob_master", user="tudor")
    cur = conn.cursor()
    create_table(cur)
    cur.execute("TRUNCATE renar_laboratoare")
    inserted = 0
    for r in rows:
        cur.execute(
            """INSERT INTO renar_laboratoare
               (cui,denumire,laborator,localitate,judet,domeniu,cert_nr,referential,
                data_emiterii,data_expirarii,sursa,email)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (r["cui"], r["denumire"], r["laborator"], r["localitate"], r["judet"],
             r["domeniu"], r["cert_nr"], r["referential"],
             r["data_emiterii"], r["data_expirarii"], r["sursa"], r["email"]),
        )
        inserted += 1
    conn.commit()
    cur.close()
    conn.close()
    return inserted


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("=== RENAR Accredited Organizations Scraper ===")

    print("\n[1] Fetching from RENAR API...")
    rows = scrape_all()
    print(f"  Total fetched: {len(rows)}")

    print("\n[2] Email enrichment from /tmp/tmp_cui_email.csv...")
    email_map = load_email_map()
    # RENAR has no CUI in API — note this for future enrichment by name via ONRC
    print(f"  Email map loaded: {len(email_map)} CUI entries (CUI lookup not available in RENAR API)")

    print(f"\n[3] Writing {len(rows)} rows to {OUT_CSV}...")
    fieldnames = ["cui", "denumire", "laborator", "localitate", "judet", "domeniu",
                  "cert_nr", "referential", "data_emiterii", "data_expirarii", "sursa", "email"]
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("\n[4] Importing to DB...")
    n = import_to_db(rows)
    print(f"  Inserted {n} rows into renar_laboratoare")
    print("\nDone.")


if __name__ == "__main__":
    main()
