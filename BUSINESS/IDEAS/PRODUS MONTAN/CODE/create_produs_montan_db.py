#!/usr/bin/env python3
"""Import RNPM Excel into produs_montan tables on raspibig PostgreSQL.

Usage:
    python create_produs_montan_db.py [--dry-run] [path/to/file.xlsx]
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from produs_montan_parse import (
    parse_xlsx, extract_emails, extract_phones, classify_product,
    load_producatori_csv, load_email_csv, load_phone_csv,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, os.pardir, "DATA")
DEFAULT_XLSX = os.path.join(DATA_DIR, "RNPM-02.03.2026.xlsx")

DB_CFG = dict(host="192.168.100.21", dbname="interjob_master",
              user="tudor", password="tudor")

# --
DDL = """
DROP TABLE IF EXISTS produs_montan_products;
DROP TABLE IF EXISTS produs_montan_producers;

CREATE TABLE produs_montan_producers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    county TEXT,
    year_registered TEXT,
    addr_punct_lucru TEXT,
    addr_sediu TEXT,
    siruta TEXT,
    decision TEXT,
    contact_raw TEXT,
    email TEXT,
    phone TEXT,
    emails TEXT[],
    phones TEXT[],
    website_url TEXT,
    obs TEXT,
    is_traditional BOOL DEFAULT FALSE,
    has_qr BOOL DEFAULT FALSE,
    products TEXT[],
    categories TEXT[],
    rnpm_numbers TEXT[],
    product_count INT,
    source TEXT DEFAULT 'RNPM 02.03.2026',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE produs_montan_products (
    id SERIAL PRIMARY KEY,
    producer_id INT REFERENCES produs_montan_producers(id),
    product_name TEXT NOT NULL,
    category TEXT,
    agrip_sector TEXT,
    processing TEXT,
    rnpm_number TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pmp_name ON produs_montan_producers(name);
CREATE INDEX idx_pmp_county ON produs_montan_producers(county);
CREATE INDEX idx_pmp_email ON produs_montan_producers(email);
CREATE INDEX idx_pmpr_producer ON produs_montan_products(producer_id);
CREATE INDEX idx_pmpr_sector ON produs_montan_products(agrip_sector);
"""


def insert_data(conn, producers, url_map, extra_emails, extra_phones):
    with conn.cursor() as cur:
        for name, p in sorted(producers.items()):
            emails = extract_emails(p["contact"])
            phones = extract_phones(p["contact"])
            # Enrich from CSVs: add extra emails/phones not already found
            for xe in extra_emails:
                if xe not in emails and name.lower() in xe:
                    emails.append(xe)
            email = emails[0] if emails else ""
            phone = phones[0] if phones else ""
            url = url_map.get(email, "") if email else ""

            cur.execute("""
                INSERT INTO produs_montan_producers
                (name, county, year_registered, addr_punct_lucru, addr_sediu,
                 siruta, decision, contact_raw, email, phone, emails, phones,
                 website_url, obs, is_traditional, has_qr,
                 products, categories, rnpm_numbers, product_count)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
            """, (name, p["county"], p["year"], p["addr_pl"], p["addr_sed"],
                  p["siruta"], p["decision"], p["contact"], email, phone,
                  emails, phones, url, p["obs"],
                  p.get("is_trad", False), p.get("has_qr", False),
                  list(p["products"]), sorted(p["categories"]),
                  p["rnpm_numbers"], len(p["products"])))
            pid = cur.fetchone()[0]

            for i, prod in enumerate(p["products"]):
                rnpm = p["rnpm_numbers"][i] if i < len(p["rnpm_numbers"]) else ""
                cat = p["product_categories"][i] if i < len(p["product_categories"]) else ""
                sector, proc = classify_product(prod, cat)
                cur.execute("""
                    INSERT INTO produs_montan_products
                    (producer_id, product_name, category, agrip_sector,
                     processing, rnpm_number)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (pid, prod, cat, sector, proc, rnpm))
    conn.commit()


def print_stats(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM produs_montan_producers")
        n_prod = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM produs_montan_products")
        n_items = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM produs_montan_producers WHERE email != ''")
        n_email = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM produs_montan_producers WHERE phone != ''")
        n_phone = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM produs_montan_producers WHERE array_length(emails, 1) > 1")
        n_multi = cur.fetchone()[0]
        cur.execute("SELECT DISTINCT category FROM produs_montan_products ORDER BY 1")
        cats = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT county, COUNT(*) FROM produs_montan_producers "
                    "GROUP BY county ORDER BY COUNT(*) DESC LIMIT 10")
        top = cur.fetchall()

        cur.execute("SELECT agrip_sector, COUNT(*) FROM produs_montan_products "
                    "GROUP BY agrip_sector ORDER BY COUNT(*) DESC")
        sectors = cur.fetchall()
        cur.execute("SELECT processing, COUNT(*) FROM produs_montan_products "
                    "GROUP BY processing ORDER BY COUNT(*) DESC")
        procs = cur.fetchall()

    print(f"\n--- produs_montan DB stats ---")
    print(f"Producers: {n_prod}")
    print(f"Products:  {n_items}")
    print(f"With email: {n_email}  |  Multi-email: {n_multi}")
    print(f"With phone: {n_phone}")
    print(f"\nCategories ({len(cats)}):")
    for c in cats:
        print(f"  {c}")
    print(f"\nAGRIP sectors:")
    for sec, cnt in sectors:
        print(f"  {sec}: {cnt}")
    print(f"\nProcessing state:")
    for proc, cnt in procs:
        print(f"  {proc}: {cnt}")
    print(f"\nTop counties:")
    for county, cnt in top:
        print(f"  {county}: {cnt}")


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    xlsx = DEFAULT_XLSX
    for a in args:
        if not a.startswith("--") and os.path.exists(a):
            xlsx = a

    print(f"Parsing {os.path.basename(xlsx)}...")
    producers = parse_xlsx(xlsx)
    n_products = sum(len(p["products"]) for p in producers.values())
    print(f"  {len(producers)} producers, {n_products} products")

    print("Loading cross-reference CSVs...")
    url_map = load_producatori_csv(DATA_DIR)
    extra_emails = load_email_csv(DATA_DIR)
    extra_phones = load_phone_csv(DATA_DIR)
    print(f"  {len(url_map)} URLs, {len(extra_emails)} emails, {len(extra_phones)} phones")

    if dry_run:
        cats = set()
        sector_counts = {}
        proc_counts = {}
        for p in producers.values():
            cats.update(p["categories"])
            for i, prod in enumerate(p["products"]):
                cat = p["product_categories"][i] if i < len(p["product_categories"]) else ""
                sector, proc = classify_product(prod, cat)
                sector_counts[sector] = sector_counts.get(sector, 0) + 1
                proc_counts[proc] = proc_counts.get(proc, 0) + 1
        print(f"\nCategories ({len(cats)}):")
        for c in sorted(cats):
            print(f"  {c}")
        print(f"\nAGRIP sectors:")
        for sec, cnt in sorted(sector_counts.items(), key=lambda x: -x[1]):
            print(f"  {sec}: {cnt}")
        print(f"\nProcessing state:")
        for proc, cnt in sorted(proc_counts.items(), key=lambda x: -x[1]):
            print(f"  {proc}: {cnt}")
        print("\n--dry-run: no DB changes.")
        return

    import psycopg2
    print(f"Connecting to {DB_CFG['host']}/{DB_CFG['dbname']}...")
    conn = psycopg2.connect(**DB_CFG)
    print("Creating tables (DROP + CREATE)...")
    with conn.cursor() as cur:
        cur.execute(DDL)
    conn.commit()

    print("Inserting data...")
    insert_data(conn, producers, url_map, extra_emails, extra_phones)
    print_stats(conn)
    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
