#!/usr/bin/env python3
"""ANRM concesiuni scraper — titulari de licente/permise active.
Sources:
- https://www.namr.ro/resurse-de-petrol/acorduri-petroliere/ (PDF links)
- https://www.namr.ro/legea-co2/raportare-nzia/date-titulari/ (company PDF files)
- WP pages with download links
- Concurs public arhiva pages (company mentions)
Table: anrm_concesiuni
"""
import csv
import re
import time
import psycopg2
import requests
import urllib3
from pathlib import Path
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = "https://www.namr.ro"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ro-RO,ro;q=0.9,en;q=0.8",
}
DB = {"host": "localhost", "port": 5432, "dbname": "interjob_master", "user": "tudor"}
_SCRIPT_DIR = Path(__file__).parent.parent
OUT = str(_SCRIPT_DIR / "DATA" / "anrm_concesiuni.csv")
EMAIL_CSV = "/tmp/tmp_cui_email.csv"
SLEEP = 0.5
RETRIES = 3

PAGES_TO_SCRAPE = [
    f"{BASE}/resurse-de-petrol/acorduri-petroliere/",
    f"{BASE}/legea-co2/raportare-nzia/date-titulari/",
    f"{BASE}/resurse-minerale/licentepermise-active/",
    f"{BASE}/resurse-minerale/concurs-public-de-oferta-arhiva/anunt-public/",
    f"{BASE}/resurse-de-petrol/concurs-public-de-oferta-arhiva-petrol/anunt-public/",
    f"{BASE}/resurse-minerale/15887-2/",
]

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS anrm_concesiuni (
    id SERIAL PRIMARY KEY,
    cui TEXT,
    denumire TEXT,
    localitate TEXT,
    judet TEXT,
    tip_resursa TEXT,
    nr_licenta TEXT,
    sursa TEXT DEFAULT 'anrm',
    email TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(denumire, nr_licenta)
);
"""


def get(url, **kwargs):
    kwargs.setdefault("verify", False)
    session = kwargs.pop("session", None)
    caller = session or requests
    for attempt in range(RETRIES):
        try:
            r = caller.get(url, headers=HEADERS, timeout=20, **kwargs)
            r.raise_for_status()
            return r
        except Exception as e:
            if attempt == RETRIES - 1:
                print(f"Failed {url}: {e}")
                return None
            time.sleep(1 + attempt)


def scrape_page(url, session):
    """Extract company data from a page."""
    records = []
    r = get(url, session=session)
    if not r:
        return records

    soup = BeautifulSoup(r.text, "html.parser")

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if ".pdf" in href.lower():
            # Extract company name from filename
            filename = href.split("/")[-1].replace(".pdf", "").replace("-", " ").replace("_", " ")
            # Remove date patterns
            filename = re.sub(r"\d{4,}", "", filename).strip()
            # Remove common non-name patterns
            if len(filename) > 4 and not filename.lower().startswith("harta"):
                tip = "petrol"
                if "minier" in url or "mineral" in url:
                    tip = "minier"
                elif "co2" in url:
                    tip = "co2"
                # Also use anchor text
                anchor_text = a.get_text(strip=True)
                name = anchor_text if len(anchor_text) > 4 else filename
                records.append({
                    "denumire": name[:200],
                    "tip_resursa": tip,
                    "localitate": "", "judet": "", "cui": "", "nr_licenta": "", "email": ""
                })

    text = soup.get_text(separator=" ")
    company_patterns = [
        r'\b((?:SC|SRL|SA|SNP|RA|RNP|OMV|ROMGAZ|PETROM|ENGIE|AMROMCO|CONPET|RAAN)\s+[A-ZĂÂÎȘȚ][A-ZA-ZĂÂÎȘȚa-zăâîșț\s&\-\.]{3,50}?)(?=\s*(?:SRL|SA|S\.R\.L\.|S\.A\.|NV|SE|\.|\,|\;))',
    ]
    for pat in company_patterns:
        matches = re.findall(pat, text)
        for m in matches:
            m = m.strip()
            if len(m) > 5:
                records.append({
                    "denumire": m,
                    "tip_resursa": "necunoscut",
                    "localitate": "", "judet": "", "cui": "", "nr_licenta": "", "email": ""
                })

    known_companies = re.findall(
        r'(?:Titularul?|titular?)\s+([A-ZĂÂÎȘȚ][A-ZA-ZĂÂÎȘȚa-zăâîșț\s&\-\.]{3,60}?)(?=\s+(?:a|au|are|are|SA|SRL|este|detine|detin))',
        text, re.IGNORECASE
    )
    for c in known_companies:
        c = c.strip()
        if len(c) > 5:
            records.append({
                "denumire": c, "tip_resursa": "necunoscut",
                "localitate": "", "judet": "", "cui": "", "nr_licenta": "", "email": ""
            })

    return records


def scrape_all_pages():
    session = requests.Session()
    # Warm up with homepage
    get(f"{BASE}/", session=session)
    time.sleep(SLEEP)

    all_records = []
    for url in PAGES_TO_SCRAPE:
        recs = scrape_page(url, session)
        all_records.extend(recs)
        print(f"  {url.split('/')[-2]}: {len(recs)}")
        time.sleep(SLEEP)
    return all_records


def scrape_wp_sitemap(session):
    """Scrape all WP pages for ANRM data."""
    records = []
    r = get(f"{BASE}/ro/wp-sitemap-posts-page-1.xml", session=session)
    if not r:
        return records
    urls = re.findall(r"<loc>([^<]+)</loc>", r.text)
    for url in urls:
        if any(kw in url.lower() for kw in ["anunt", "concurs", "titular", "licent", "acord"]):
            page_records = scrape_page(url, session)
            records.extend(page_records)
            time.sleep(SLEEP)
    return records


def load_email_map():
    em = {}
    try:
        with open(EMAIL_CSV, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                cui = row.get("cui", "").strip().lstrip("0")
                email = row.get("email", "").strip()
                if cui and email:
                    em[cui] = email
    except Exception:
        pass
    return em


def save_and_import(records):
    seen = set()
    unique = []
    for r in records:
        name = r.get("denumire", "").strip()
        nr = r.get("nr_licenta", "").strip()
        key = (name.lower(), nr.lower())
        if key not in seen and name and len(name) > 3:
            seen.add(key)
            unique.append(r)

    em = load_email_map()
    for r in unique:
        cui = r.get("cui", "").strip().lstrip("0")
        if cui and cui in em:
            r["email"] = em[cui]

    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["cui","denumire","localitate","judet","tip_resursa","nr_licenta","sursa","email"])
        w.writeheader()
        for r in unique:
            w.writerow({k: r.get(k, "") for k in ["cui","denumire","localitate","judet","tip_resursa","nr_licenta","sursa","email"]})
    print(f"CSV: {OUT} ({len(unique)} rows)")

    try:
        conn = psycopg2.connect(**DB)
        cur = conn.cursor()
        cur.execute(CREATE_TABLE)
        conn.commit()

        inserted = 0
        for r in unique:
            try:
                cur.execute("""
                    INSERT INTO anrm_concesiuni (cui, denumire, localitate, judet, tip_resursa, nr_licenta, sursa, email)
                    VALUES (%s,%s,%s,%s,%s,%s,'anrm',%s)
                    ON CONFLICT (denumire, nr_licenta) DO NOTHING
                """, (r.get("cui",""), r["denumire"], r.get("localitate",""), r.get("judet",""),
                      r.get("tip_resursa",""), r.get("nr_licenta",""), r.get("email","")))
                if cur.rowcount:
                    inserted += 1
            except Exception:
                conn.rollback()
        conn.commit()

        cur.execute("SELECT COUNT(*) FROM anrm_concesiuni")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM anrm_concesiuni WHERE email != ''")
        with_email = cur.fetchone()[0]
        cur.close()
        conn.close()
        print(f"DB: {len(unique)} unique, {inserted} inserted, total={total}, emails={with_email}")
    except Exception as e:
        print(f"DB import skipped: {e}")


if __name__ == "__main__":
    print("Scraping ANRM...")
    session = requests.Session()
    get(f"{BASE}/", session=session)

    records = scrape_all_pages()
    records.extend(scrape_wp_sitemap(session))
    print(f"Raw records: {len(records)}")
    save_and_import(records)
