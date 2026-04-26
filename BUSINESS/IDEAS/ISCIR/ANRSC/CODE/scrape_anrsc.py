"""
scrape_anrsc.py
ANRSC — operatori licentiati: apa, salubrizare, iluminat, transport local.
Source: https://www.anrsc.ro (PDFs in wp-content/uploads)
~600-700 operatori unici total across 4 servicii.

Strategy: download 4 PDFs -> pdfplumber -> parse rows -> extract CUI din cod_operator
CUI embedded: "BC27278646" -> judet_prefix="BC", cui="27278646"
Enrich email via ONRC pe laptop:5433.
"""
import csv
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

import psycopg2
import pdfplumber

DATA_DIR = Path(__file__).parent.parent / "DATA"
DATA_DIR.mkdir(exist_ok=True)
OUT_CSV = DATA_DIR / "anrsc_operatori.csv"

RASPI = "tudor@192.168.100.21"
RASPI_DB = "interjob_master"
LAPTOP_DSN = "host=localhost port=5433 dbname=interjob_master user=postgres password=postgres"

PDFS = [
    ("apa",        "https://www.anrsc.ro/wp-content/uploads/2026/03/evidenta-licente-apa-16.03.2026.pdf"),
    ("salubrizare","https://www.anrsc.ro/wp-content/uploads/2026/03/evidenta-licente-sal-16.03.2026.pdf"),
    ("iluminat",   "https://www.anrsc.ro/wp-content/uploads/2026/03/evidenta-licente-il-16.03.2026.pdf"),
    ("transport",  "https://www.anrsc.ro/wp-content/uploads/2025/12/evidenta-autorizatiilor-pentru-autoritatile-de-autorizare-valabile-22.12.2025.pdf"),
]

JUDET_PREFIX = {
    "AB":"Alba","AR":"Arad","AG":"Arges","BC":"Bacau","BH":"Bihor","BN":"Bistrita-Nasaud",
    "BT":"Botosani","BV":"Brasov","BR":"Braila","B":"Bucuresti","BZ":"Buzau","CS":"Caras-Severin",
    "CL":"Calarasi","CJ":"Cluj","CT":"Constanta","CV":"Covasna","DB":"Dambovita","DJ":"Dolj",
    "GL":"Galati","GR":"Giurgiu","GJ":"Gorj","HR":"Harghita","HD":"Hunedoara","IL":"Ialomita",
    "IS":"Iasi","IF":"Ilfov","MM":"Maramures","MH":"Mehedinti","MS":"Mures","NT":"Neamt",
    "OT":"Olt","PH":"Prahova","SJ":"Salaj","SM":"Satu-Mare","SB":"Sibiu","SV":"Suceava",
    "TR":"Teleorman","TM":"Timis","TL":"Tulcea","VS":"Vaslui","VL":"Valcea","VN":"Vrancea",
}


def parse_cod(cod):
    m = re.match(r'^([A-Z]{1,2})(\d+)$', (cod or "").strip())
    if not m:
        return None, None
    prefix, cui = m.group(1), m.group(2)
    return cui, JUDET_PREFIX.get(prefix, prefix)


def download_pdf(url, dest):
    if dest.exists():
        print(f"  cached {dest.name}")
        return
    print(f"  downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
        f.write(r.read())


def parse_pdf(pdf_path, tip_serviciu):
    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in (page.extract_tables() or []):
                for row in table:
                    if not row or len(row) < 3:
                        continue
                    cod = (row[1] or "").strip()
                    denumire_raw = (row[2] or "").strip()
                    nr_licenta = (row[4] or "").strip() if len(row) > 4 else ""
                    if not cod or not re.match(r'^[A-Z]{1,2}\d+$', cod):
                        continue
                    cui, judet = parse_cod(cod)
                    rows.append({
                        "cui": cui or "", "denumire": denumire_raw, "judet": judet or "",
                        "tip_serviciu": tip_serviciu, "nr_licenta": nr_licenta, "email": "",
                    })
    return rows


def enrich_emails(rows):
    """Optional: enrich from laptop ONRC DB. Gracefully skip if unavailable."""
    try:
        conn = psycopg2.connect(LAPTOP_DSN)
        conn.set_session(readonly=True, autocommit=True)
        cur = conn.cursor()
        enriched = 0
        for r in rows:
            if not r["cui"]:
                continue
            cur.execute(
                "SELECT email FROM master_romania_companies "
                "WHERE cui=%s AND email IS NOT NULL AND email LIKE '%%@%%' LIMIT 1",
                (r["cui"],)
            )
            row = cur.fetchone()
            if row:
                r["email"] = row[0]
                enriched += 1
        cur.close()
        conn.close()
        print(f"Enriched {enriched}/{len(rows)} emails")
    except Exception as e:
        print(f"Email enrichment skipped: {e}")
    return rows


def save_csv(rows):
    cols = ["cui", "denumire", "judet", "tip_serviciu", "nr_licenta", "email"]
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})
    print(f"CSV: {OUT_CSV} ({len(rows)} rows)")


def import_to_raspibig():
    """Optional: import to raspibig. Gracefully skip if unreachable."""
    try:
        r = subprocess.run(["scp", str(OUT_CSV), f"{RASPI}:/tmp/anrsc_operatori.csv"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            print(f"SCP skipped: {r.stderr}"); return
        print("SCP OK")
        create = (
            "CREATE TABLE IF NOT EXISTS anrsc_operatori ("
            "  id SERIAL PRIMARY KEY, cui TEXT, denumire TEXT NOT NULL, judet TEXT,"
            "  tip_serviciu TEXT, nr_licenta TEXT, email TEXT,"
            "  sursa TEXT DEFAULT 'anrsc', created_at TIMESTAMP DEFAULT NOW()"
            "); TRUNCATE anrsc_operatori;"
            "CREATE INDEX IF NOT EXISTS anrsc_judet ON anrsc_operatori(judet);"
            "CREATE INDEX IF NOT EXISTS anrsc_cui ON anrsc_operatori(cui);"
            "CREATE INDEX IF NOT EXISTS anrsc_email ON anrsc_operatori(email) WHERE email IS NOT NULL AND email != '';"
        )
        subprocess.run(["ssh", RASPI, f'psql -d {RASPI_DB} -c "{create}"'], capture_output=True, timeout=10)
        copy = r"\copy anrsc_operatori(cui,denumire,judet,tip_serviciu,nr_licenta,email) FROM '/tmp/anrsc_operatori.csv' CSV HEADER"
        r2 = subprocess.run(["ssh", RASPI, f'psql -d {RASPI_DB} -c "{copy}"'], capture_output=True, text=True, timeout=10)
        print(r2.stdout or r2.stderr)
        r3 = subprocess.run(["ssh", RASPI,
                             f'psql -d {RASPI_DB} -t -c "SELECT tip_serviciu, COUNT(*), COUNT(NULLIF(email,\'\')) FROM anrsc_operatori GROUP BY tip_serviciu ORDER BY COUNT(*) DESC;"'],
                            capture_output=True, text=True, timeout=10)
        print(r3.stdout)
    except Exception as e:
        print(f"Raspibig import skipped: {e}")


def scrape():
    all_rows = []
    for tip, url in PDFS:
        dest = DATA_DIR / f"anrsc_{tip}.pdf"
        print(f"\n[{tip}]")
        download_pdf(url, dest)
        rows = parse_pdf(dest, tip)
        print(f"  parsed {len(rows)} rows")
        all_rows.extend(rows)
    seen, deduped = set(), []
    for r in all_rows:
        key = (r["cui"], r["tip_serviciu"])
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    print(f"\nTotal unique: {len(deduped)} (from {len(all_rows)} raw)")
    deduped = enrich_emails(deduped)
    save_csv(deduped)
    import_to_raspibig()
    print("Done.")


if __name__ == "__main__":
    scrape()
