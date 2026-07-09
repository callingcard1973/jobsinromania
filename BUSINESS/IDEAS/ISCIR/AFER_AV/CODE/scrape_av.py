"""
AV (Autoritatea Vamala Romana) — EU AEO scraper.

Source: ec.europa.eu/taxation_customs/dds2/eos/certificates.jsp
Fetches Romanian AEO operators: AEOC, AEOF, AEOS types.
298 total RO records (107 AEOC + 166 AEOF + 25 AEOS).

Enriches company names against ONRC 4.1M-firm DB via CUI email CSV,
imports to interjob_master.av_vamali on raspibig.
"""

import time
import re
import csv
import sys

import requests
import psycopg2
import urllib3

urllib3.disable_warnings()

# ── config ────────────────────────────────────────────────────────────────────
BASE_URL = "https://ec.europa.eu/taxation_customs/dds2/eos"
EMAIL_CSV = "/tmp/tmp_cui_email.csv"
DB_PARAMS = {
    "host": "localhost", "port": 5432,
    "dbname": "interjob_master", "user": "tudor",
}
TABLE = "av_vamali"
SLEEP = 0.5
MAX_RETRIES = 3
SOURCE = "av_vamali"
CERT_TYPES = ["AEOC", "AEOF", "AEOS"]


def make_session():
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0 (compatible; scraper)"
    s.verify = False
    # Init session cookies
    s.get(f"{BASE_URL}/aeo_home.jsp?Screen=0&Lang=en&parentfolder=.%2f", timeout=20)
    s.get(f"{BASE_URL}/aeo_consultation.jsp?Lang=en", timeout=20)
    return s


def fetch_page(session, cert_type, offset):
    """Fetch one page of AEO results for Romania."""
    url = (
        f"{BASE_URL}/certificates.jsp"
        f"?Lang=en&offset={offset}&holderName=&aeoCountry=RO"
        f"&showRecordsCount=1&certificatesTypes={cert_type}"
    )
    for attempt in range(MAX_RETRIES):
        try:
            r = session.get(url, timeout=30)
            if r.status_code == 200:
                return r.text
            time.sleep(SLEEP * 2)
        except Exception as e:
            print(f"  Retry {attempt+1}: {e}")
            time.sleep(SLEEP * 2)
    return ""


def parse_page(html):
    """Extract company rows from AEO results table."""
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)
    records = []
    for row in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
        clean = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
        # Expected: [name, country, customs_office, cert_type_full, date]
        if len(clean) >= 4 and clean[0] and clean[0] != 'Holder Name':
            records.append(clean)
    total_match = re.search(r'(\d+)\s*results match', html)
    total = int(total_match.group(1)) if total_match else None
    return records, total


def scrape_all(session):
    all_records = []
    for cert_type in CERT_TYPES:
        offset = 1
        total = None
        page = 0
        while True:
            html = fetch_page(session, cert_type, offset)
            if not html:
                break
            records, tot = parse_page(html)
            if total is None and tot is not None:
                total = tot
                pages = (total + 24) // 25
                print(f"{cert_type}: {total} records (~{pages} pages)")
            all_records.extend([
                {
                    "denumire": r[0],
                    "tip": cert_type,
                    "birou_vamal": r[2] if len(r) > 2 else "",
                    "data_autorizatie": r[4] if len(r) > 4 else "",
                }
                for r in records
            ])
            page += 1
            # Find next page offset from nav link
            next_offsets = re.findall(r'offset=(\d+)', html)
            nums = sorted(set(int(n) for n in next_offsets))
            next_offset = max((n for n in nums if n > offset), default=None)
            if not next_offset or not records:
                break
            offset = next_offset
            time.sleep(SLEEP)

        print(f"  Fetched {sum(1 for r in all_records if r['tip'] == cert_type)} {cert_type} records")

    print(f"Total scraped: {len(all_records)}")
    return all_records


def load_email_map():
    email_map = {}
    try:
        with open(EMAIL_CSV, encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cui = str(row.get("cui", "") or row.get("CUI", "")).strip()
                email = str(row.get("email", "") or row.get("EMAIL", "")).strip()
                if cui and email:
                    email_map[cui] = email
        print(f"Loaded {len(email_map):,} CUI->email entries")
    except FileNotFoundError:
        print("Warning: email CSV not found")
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
                tip TEXT,
                birou_vamal TEXT,
                data_autorizatie TEXT,
                sursa TEXT DEFAULT 'av_vamali',
                email TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(denumire, tip)
            )
        """)
        conn.commit()
    print(f"Table {TABLE} ready")


def upsert_records(conn, records, email_map):
    inserted = 0
    with conn.cursor() as cur:
        for rec in records:
            email = email_map.get(rec.get("cui", ""), None)
            try:
                cur.execute(f"""
                    INSERT INTO {TABLE}
                        (cui, denumire, tip, birou_vamal, data_autorizatie, sursa, email)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (denumire, tip) DO UPDATE
                        SET birou_vamal = EXCLUDED.birou_vamal,
                            data_autorizatie = EXCLUDED.data_autorizatie,
                            email = EXCLUDED.email
                """, (
                    rec.get("cui"), rec["denumire"], rec["tip"],
                    rec.get("birou_vamal"), rec.get("data_autorizatie"),
                    SOURCE, email,
                ))
                if cur.rowcount > 0:
                    inserted += 1
            except Exception as e:
                conn.rollback()
                print(f"  Error: {rec['denumire'][:40]}: {e}")
                continue
        conn.commit()
    return inserted


def main():
    print("=== AV Vamali Scraper (EU AEO Database) ===")

    # 1. Scrape
    session = make_session()
    records = scrape_all(session)
    if not records:
        sys.exit("No records scraped")

    # 2. Save CSV
    csv_path = "/tmp/av_vamali.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["denumire", "tip", "birou_vamal", "data_autorizatie"])
        w.writeheader()
        w.writerows(records)
    print(f"CSV saved: {csv_path}")

    # 3. Email enrichment
    email_map = load_email_map()

    # 4. DB import
    conn = psycopg2.connect(**DB_PARAMS)
    try:
        create_table(conn)
        inserted = upsert_records(conn, records, email_map)
        print(f"DB: {inserted} rows inserted/updated in {TABLE}")

        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {TABLE}")
            total = cur.fetchone()[0]
        print(f"Total rows in {TABLE}: {total}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
