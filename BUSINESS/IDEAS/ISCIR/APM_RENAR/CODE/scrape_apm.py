#!/usr/bin/env python3
"""
APM waste operators scraper — collects from data.gov.ro XLS files + ANMAP DJM county pages.
Output: DATA/apm_deseuri.csv
DB: raspibig interjob_master.apm_deseuri
Max 250 lines.
"""
import csv
import io
import re
import ssl
import time
import urllib.request
from pathlib import Path

import openpyxl
import psycopg2
from bs4 import BeautifulSoup

DATA_DIR = Path(__file__).parent.parent / "DATA"
OUT_CSV = DATA_DIR / "apm_deseuri.csv"
SSL_CTX = ssl._create_unverified_context()
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"}

# data.gov.ro direct XLS downloads + ANMAP direct files (last updated 2024)
DATA_GOV_SOURCES = [
    {
        "url": "https://data.gov.ro/dataset/9debf899-c16e-4646-bdbd-d339d19d1b00/resource/0eda9ef0-5b34-448a-a199-83268e3a8de3/download/lista-operatorilor-care-transport-deseuri-periculoase.xlsx",
        "tip": "transport_deseuri_periculoase",
    },
    # VSU (end-of-life vehicles) — note: .xls not .xlsx
    {
        "url": "https://data.gov.ro/dataset/0e2c90c8-6fe0-4a6f-9af2-b2a94e94dfdc/resource/f0a07773-13c3-44b0-a7a1-8234b2c0c073/download/operatori-economici-autorizati-pentru-colectarea-tratarea-vsu.xls",
        "tip": "colectare_vehicule_scoase_uz",
    },
    {
        "url": "https://data.gov.ro/dataset/4237cc81-cb38-4d64-9884-9748a7d15374/resource/61e35709-48c6-4638-9548-79bafe1e13fe/download/operatori-economici-autorizati-coincinerarea-deseurilor-la-1-septembrie-2014.xlsx",
        "tip": "coincinerare_deseuri",
    },
    # Uleiuri uzate (used oils)
    {
        "url": "https://data.gov.ro/dataset/0043d5eb-091e-4528-992d-69cf0521f15c/resource/f1544bd4-36b2-48c1-8aee-29e892abec8f/download/",
        "tip": "uleiuri_uzate",
    },
    # DEEE producers
    {
        "url": "https://www.anpm.ro/documents/12220/67707490/Lista+site+producatori+EEE+decembrie+2024.xls/584f3c48-d958-4d12-ac92-a32fe",
        "tip": "deee_producatori_echipamente",
    },
    # Prahova county DJM — waste oils (direct ANMAP WP file)
    {
        "url": "https://djmph.anmap.gov.ro/wp-content/uploads/sites/51/2026/01/Prahova_Tabel-uleiuri_operatori-autorizati-colectare-valorificare-eliminare.xlsx",
        "tip": "uleiuri_uzate",
    },
]

# All 41 county DJM subdomains
COUNTIES = [
    "ab", "ar", "ag", "bc", "bh", "bn", "bt", "bv", "br", "b",
    "bz", "cs", "cl", "cj", "ct", "cv", "db", "dj", "gl", "gr",
    "gj", "hr", "hd", "il", "is", "if", "mm", "mh", "ms", "nt",
    "ot", "ph", "sm", "sj", "sb", "sv", "tr", "tm", "tl", "vs",
    "vl", "vn",
]

CUI_RE = re.compile(r"\b(RO\s?)?\d{6,10}\b")
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")


def fetch(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            return urllib.request.urlopen(req, timeout=20, context=SSL_CTX).read()
        except Exception as e:
            if i == retries - 1:
                print(f"  FAIL {url}: {e}")
                return None
            time.sleep(1)
    return None


def parse_cui(text):
    m = CUI_RE.search(str(text))
    if m:
        return re.sub(r"\D", "", m.group())
    return ""


def iter_sheet_rows(data, url):
    """Yield (cells_list) for each non-empty row from xls or xlsx."""
    is_xls = url.lower().rstrip("/").endswith(".xls")
    if is_xls:
        try:
            import xlrd
            wb = xlrd.open_workbook(file_contents=data)
            ws = wb.sheet_by_index(0)
            for i in range(1, ws.nrows):
                yield [str(ws.cell_value(i, j)).strip() for j in range(ws.ncols)]
            return
        except ImportError:
            pass  # fall through to openpyxl which may fail on .xls
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    ws = wb.active
    for row in ws.iter_rows(min_row=2, values_only=True):
        yield [str(c or "").strip() for c in row]


def scrape_xls(url, tip):
    rows = []
    data = fetch(url)
    if not data:
        return rows
    try:
        for cells in iter_sheet_rows(data, url):
            if not any(cells):
                continue
            full = " ".join(cells)
            cui = parse_cui(full)
            email_m = EMAIL_RE.search(full)
            email = email_m.group() if email_m else ""
            judet = cells[1] if len(cells) > 1 else ""
            denumire = cells[2] if len(cells) > 2 else cells[0]
            rows.append({
                "cui": cui,
                "denumire": denumire[:200],
                "localitate": "",
                "judet": judet[:80],
                "tip_activitate": tip,
                "sursa": "apm_deseuri",
                "email": email[:120],
            })
    except Exception as e:
        print(f"  XLS parse error {url}: {e}")
    return rows


def scrape_djm_page(county):
    rows = []
    base = f"https://djm{county}.anmap.gov.ro"
    index = fetch(base)
    if not index:
        return rows
    soup = BeautifulSoup(index, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True).lower()
        if any(k in text for k in ["deseu", "autorizat", "operator", "colectare", "transport"]):
            full = href if href.startswith("http") else base + "/" + href.lstrip("/")
            links.append(full)
    for link in links[:5]:
        time.sleep(0.5)
        page = fetch(link)
        if not page:
            continue
        psoup = BeautifulSoup(page, "html.parser")
        for tbl in psoup.find_all("table"):
            for tr in tbl.find_all("tr")[1:]:
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if len(cells) < 2:
                    continue
                full = " ".join(cells)
                cui = parse_cui(full)
                email_m = EMAIL_RE.search(full)
                email = email_m.group() if email_m else ""
                rows.append({
                    "cui": cui,
                    "denumire": cells[1][:200] if len(cells) > 1 else cells[0][:200],
                    "localitate": "",
                    "judet": county.upper(),
                    "tip_activitate": "colectare_transport_valorificare",
                    "sursa": "apm_deseuri",
                    "email": email[:120],
                })
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
        CREATE TABLE IF NOT EXISTS apm_deseuri (
            id SERIAL PRIMARY KEY,
            cui TEXT,
            denumire TEXT,
            localitate TEXT,
            judet TEXT,
            tip_activitate TEXT,
            sursa TEXT DEFAULT 'apm_deseuri',
            email TEXT,
            inserted_at TIMESTAMP DEFAULT NOW()
        )
    """)


def import_to_db(rows):
    conn = psycopg2.connect(host="localhost", port=5432, dbname="interjob_master", user="tudor")
    cur = conn.cursor()
    create_table(cur)
    cur.execute("TRUNCATE apm_deseuri")
    inserted = 0
    for r in rows:
        cur.execute(
            "INSERT INTO apm_deseuri (cui,denumire,localitate,judet,tip_activitate,sursa,email) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (r["cui"], r["denumire"], r["localitate"], r["judet"], r["tip_activitate"], r["sursa"], r["email"]),
        )
        inserted += 1
    conn.commit()
    cur.close()
    conn.close()
    return inserted


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    all_rows = []

    print("=== APM Waste Operators Scraper ===")
    print("\n[1] data.gov.ro XLS sources...")
    for src in DATA_GOV_SOURCES:
        print(f"  Fetching {src['tip']}...")
        rows = scrape_xls(src["url"], src["tip"])
        print(f"    -> {len(rows)} rows")
        all_rows.extend(rows)
        time.sleep(0.5)

    print("\n[2] ANMAP DJM county pages...")
    for county in COUNTIES:
        print(f"  DJM {county.upper()}...", end=" ")
        rows = scrape_djm_page(county)
        print(f"{len(rows)} rows")
        all_rows.extend(rows)
        time.sleep(0.5)

    # Enrich with email map
    print(f"\n[3] Email enrichment from /tmp/tmp_cui_email.csv...")
    email_map = load_email_map()
    enriched = 0
    for r in all_rows:
        if not r["email"] and r["cui"] in email_map:
            r["email"] = email_map[r["cui"]]
            enriched += 1
    print(f"  Enriched {enriched} rows")

    # Deduplicate by CUI+tip
    seen = set()
    deduped = []
    for r in all_rows:
        key = (r["cui"], r["tip_activitate"], r["denumire"][:50])
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    print(f"\n[4] Writing {len(deduped)} rows to {OUT_CSV}...")
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["cui", "denumire", "localitate", "judet", "tip_activitate", "sursa", "email"])
        writer.writeheader()
        writer.writerows(deduped)

    print(f"\n[5] Importing to DB...")
    n = import_to_db(deduped)
    print(f"  Inserted {n} rows into apm_deseuri")
    print("\nDone.")


if __name__ == "__main__":
    main()
