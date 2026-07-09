"""
Import itm_plasare.csv + itm_temp.csv → raspibig DB interjob_master
Tables: itm_agentii_plasare, itm_agentii_temp
Enrich email from /tmp/tmp_cui_email.csv
Run on raspibig: python3 /tmp/import_itm.py
"""
import csv
import sys
import time
import psycopg2
import psycopg2.extras

DB = dict(host="localhost", port=5432, dbname="interjob_master", user="tudor")
PLASARE_CSV = "/tmp/itm_plasare.csv"
TEMP_CSV = "/tmp/itm_temp.csv"
EMAIL_CSV = "/tmp/tmp_cui_email.csv"


def load_emails(path):
    emails = {}
    try:
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cui = str(row.get("cui", "")).strip()
                email = str(row.get("email", "")).strip()
                if cui and email:
                    emails[cui] = email
        print(f"Loaded {len(emails)} CUI→email mappings", file=sys.stderr)
    except FileNotFoundError:
        print(f"WARN: {path} not found, skipping email enrichment", file=sys.stderr)
    return emails


def create_tables(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS itm_agentii_plasare (
            id SERIAL PRIMARY KEY,
            itm TEXT,
            denumire TEXT,
            data_inregistrare TEXT,
            cui TEXT,
            adresa TEXT,
            judet TEXT,
            email TEXT,
            sursa TEXT DEFAULT 'itm_plasare',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS itm_agentii_temp (
            id SERIAL PRIMARY KEY,
            nr TEXT,
            denumire TEXT,
            sediu TEXT,
            cui TEXT,
            telefon TEXT,
            nr_autorizatie TEXT,
            data_prelungire TEXT,
            data_retragere TEXT,
            email TEXT,
            sursa TEXT DEFAULT 'itm_temp',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("TRUNCATE itm_agentii_plasare RESTART IDENTITY")
    cur.execute("TRUNCATE itm_agentii_temp RESTART IDENTITY")


def import_plasare(cur, path, emails):
    rows = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cui = row["cui"].strip()
            row["email"] = emails.get(cui, "")
            rows.append(row)
    psycopg2.extras.execute_batch(cur, """
        INSERT INTO itm_agentii_plasare
            (itm, denumire, data_inregistrare, cui, adresa, judet, email)
        VALUES
            (%(itm)s, %(denumire)s, %(data_inregistrare)s, %(cui)s, %(adresa)s,
             %(judet)s, %(email)s)
    """, rows, page_size=500)
    print(f"Inserted {len(rows)} plasare rows", file=sys.stderr)
    return len(rows)


def import_temp(cur, path, emails):
    rows = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cui = row["cui"].strip()
            row["email"] = emails.get(cui, "")
            rows.append(row)
    psycopg2.extras.execute_batch(cur, """
        INSERT INTO itm_agentii_temp
            (nr, denumire, sediu, cui, telefon, nr_autorizatie,
             data_prelungire, data_retragere, email)
        VALUES
            (%(nr)s, %(denumire)s, %(sediu)s, %(cui)s, %(telefon)s,
             %(nr_autorizatie)s, %(data_prelungire)s, %(data_retragere)s, %(email)s)
    """, rows, page_size=500)
    print(f"Inserted {len(rows)} temp rows", file=sys.stderr)
    return len(rows)


def main():
    emails = load_emails(EMAIL_CSV)
    conn = psycopg2.connect(**DB)
    conn.autocommit = False
    cur = conn.cursor()
    try:
        create_tables(cur)
        n_p = import_plasare(cur, PLASARE_CSV, emails)
        n_t = import_temp(cur, TEMP_CSV, emails)
        conn.commit()
        print(f"\nDONE: {n_p} plasare | {n_t} temp agencies imported")
        # Summary: how many got emails
        cur.execute("SELECT COUNT(*) FROM itm_agentii_plasare WHERE email != ''")
        e_p = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM itm_agentii_temp WHERE email != ''")
        e_t = cur.fetchone()[0]
        print(f"Email-enriched: {e_p} plasare | {e_t} temp")
    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}", file=sys.stderr)
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
