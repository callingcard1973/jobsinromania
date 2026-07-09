"""
scrape_madr_consultanti.py — Scrape AFIR consulting firms directory
(firme de consultanta PNDR/FEADR), export CSV, import to raspibig
interjob_master.madr_consultanti, enrich with CUI→email.

Source: https://www.afir.ro/instrumente/nomenclator/firme-de-consultanta/
Pages: ~12 pages, ~10 firms per page, ~120 total

Detail page fields: name, website, phone, address, CAEN, coverage,
year, programs (PNDR 2014-2020, PS 2023-2027)

NOTE: CUI is NOT shown on AFIR — enriched via ONRC match by name
using the raspibig 4.1M firms table if available.

Usage:
  python scrape_madr_consultanti.py
"""

import csv
import re
import time
from pathlib import Path

import psycopg2
import requests
from bs4 import BeautifulSoup

# ── Config ────────────────────────────────────────────────────────────────────
BASE_URL = "https://www.afir.ro/instrumente/nomenclator/firme-de-consultanta/"
DATA_DIR = Path(__file__).parent.parent / "DATA"
OUT_CSV = DATA_DIR / "madr_consultanti.csv"
DB = dict(host="localhost", port=5432, dbname="interjob_master", user="tudor")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ro-RO,ro;q=0.9",
}
TIMEOUT = 20
SLEEP = 0.5
MAX_PAGES = 20  # safety limit


# ── Helpers ───────────────────────────────────────────────────────────────────
def get(url: str, params: dict | None = None) -> BeautifulSoup:
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, params=params, timeout=TIMEOUT)
            r.raise_for_status()
            return BeautifulSoup(r.text, "html.parser")
        except Exception as exc:
            print(f"  Attempt {attempt + 1} failed for {url}: {exc}")
            time.sleep(SLEEP * 2)
    raise RuntimeError(f"Could not fetch {url}")


def clean(s: str | None) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", s).strip()


def get_firm_slugs(soup: BeautifulSoup) -> list[str]:
    """Extract firm detail page slugs from listing page."""
    slugs = []
    for a in soup.select("a[href*='/firme-de-consultanta/']"):
        href = a.get("href", "")
        # Skip the base listing page itself
        if href.rstrip("/") == "/instrumente/nomenclator/firme-de-consultanta":
            continue
        # Extract slug
        m = re.search(r"/firme-de-consultanta/([^/?#]+)", href)
        if m:
            slug = m.group(1)
            if slug not in slugs and len(slug) > 2:
                slugs.append(slug)
    return slugs


def get_total_pages(soup: BeautifulSoup) -> int:
    """Find last page number from pagination."""
    pages = []
    for a in soup.select("a[href*='page='], .pagination a, nav a"):
        text = clean(a.get_text())
        if re.match(r"^\d+$", text):
            pages.append(int(text))
    return max(pages) if pages else 1


def scrape_firm_detail(slug: str) -> dict:
    """Scrape individual firm detail page."""
    url = f"{BASE_URL}{slug}/"
    try:
        soup = get(url)
    except Exception as exc:
        print(f"  Detail fetch failed for {slug}: {exc}")
        return {}

    result: dict[str, str] = {
        "denumire": "",
        "cui": "",
        "localitate": "",
        "judet": "",
        "website": "",
        "telefon": "",
        "adresa": "",
        "caen": "",
        "acoperire": "",
        "an_infiintare": "",
        "programe": "",
        "sursa": "madr_consultanti",
        "email": "",
    }

    # Firm name: h1, h2, or page title
    for tag in ["h1", "h2", "h3"]:
        heading = soup.find(tag)
        if heading:
            text = clean(heading.get_text())
            # Skip generic site headings
            if text and "AFIR" not in text and "Portal" not in text and len(text) > 3:
                result["denumire"] = text
                break
    # Fallback: title tag (strip site name suffix)
    if not result["denumire"]:
        title = soup.find("title")
        if title:
            t = clean(title.get_text())
            result["denumire"] = t.split(" - ")[0].strip()

    # Collect all text blocks — AFIR uses various layouts
    all_text = soup.get_text(" ", strip=True)

    # Phone
    m = re.search(r"(0\d{8,9}|0\d{2}[\s.-]\d{3}[\s.-]\d{3,4})", all_text)
    if m:
        result["telefon"] = m.group(1)

    # CAEN code
    m = re.search(r"CAEN[:\s]+(\d{4})", all_text, re.I)
    if m:
        result["caen"] = m.group(1)

    # Year
    m = re.search(r"(19\d{2}|20\d{2})", all_text[:500])
    if m:
        result["an_infiintare"] = m.group(1)

    # Coverage
    if "Național" in all_text:
        result["acoperire"] = "National"
    elif "Regional" in all_text:
        result["acoperire"] = "Regional"

    # Address — look for Romanian address patterns
    for tag in soup.find_all(["p", "li", "span", "div"]):
        text = clean(tag.get_text())
        if re.search(r"\b(str\.|bd\.|bld\.|nr\.|sector)\b", text, re.I) and len(text) > 10:
            result["adresa"] = text[:200]
            # Extract localitate (city before comma or first word)
            parts = text.split(",")
            if parts:
                result["localitate"] = parts[0].strip()[:60]
            break

    # Website
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("http") and "afir.ro" not in href:
            result["website"] = href[:100]
            break

    # Programs / measures
    measures = []
    for tag in soup.find_all(string=re.compile(r"sM \d|M \d|PNDR|PS 2")):
        measures.append(clean(str(tag))[:30])
    result["programe"] = "; ".join(sorted(set(measures)))[:200]

    return result


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
        CREATE TABLE IF NOT EXISTS madr_consultanti (
            id SERIAL PRIMARY KEY,
            denumire TEXT,
            cui TEXT,
            localitate TEXT,
            judet TEXT,
            website TEXT,
            telefon TEXT,
            adresa TEXT,
            caen TEXT,
            acoperire TEXT,
            an_infiintare TEXT,
            programe TEXT,
            email TEXT,
            sursa TEXT DEFAULT 'madr_consultanti',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    cur.execute("TRUNCATE madr_consultanti")
    inserted = 0
    for r in rows:
        cur.execute("""
            INSERT INTO madr_consultanti
              (denumire, cui, localitate, judet, website, telefon, adresa,
               caen, acoperire, an_infiintare, programe, email, sursa)
            VALUES
              (%(denumire)s, %(cui)s, %(localitate)s, %(judet)s, %(website)s,
               %(telefon)s, %(adresa)s, %(caen)s, %(acoperire)s, %(an_infiintare)s,
               %(programe)s, %(email)s, %(sursa)s)
        """, r)
        inserted += 1
    conn.commit()
    cur.close()
    conn.close()
    print(f"  Inserted {inserted} rows into madr_consultanti")
    return inserted


def enrich_email(conn_params: dict) -> int:
    """Enrich via /tmp/tmp_cui_email.csv on raspibig (by CUI match)."""
    email_csv = Path("/tmp/tmp_cui_email.csv")
    if not email_csv.exists():
        print("  Email CSV not found locally — enrich on raspibig with enrich_email.sql")
        return 0

    email_map: dict[str, str] = {}
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
            "UPDATE madr_consultanti SET email=%s WHERE cui=%s AND (email IS NULL OR email='')",
            (email, cui),
        )
        updated += cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    print(f"  Email enrichment: {updated} rows updated")
    return updated


def main() -> None:
    print("=== MADR/AFIR Consultanti Scraper ===")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Get all slugs from listing pages
    print("\n[1] Collecting firm slugs...")
    all_slugs: list[str] = []
    page_num = 1

    while page_num <= MAX_PAGES:
        params = {"page": page_num} if page_num > 1 else {}
        print(f"  Listing page {page_num}...", end=" ")
        soup = get(BASE_URL, params)

        slugs = get_firm_slugs(soup)
        if not slugs:
            print("no firms found, stopping")
            break

        new_slugs = [s for s in slugs if s not in all_slugs]
        all_slugs.extend(new_slugs)
        print(f"{len(new_slugs)} slugs (total: {len(all_slugs)})")

        # Check if there's a next page
        total_pages = get_total_pages(soup)
        if page_num >= total_pages:
            print(f"  Reached last page ({total_pages})")
            break

        page_num += 1
        time.sleep(SLEEP)

    print(f"\n  Found {len(all_slugs)} unique firm slugs")

    # Scrape detail pages
    print("\n[2] Scraping firm detail pages...")
    rows = []
    for i, slug in enumerate(all_slugs):
        print(f"  [{i+1}/{len(all_slugs)}] {slug}")
        firm = scrape_firm_detail(slug)
        if firm and firm.get("denumire"):
            rows.append(firm)
        time.sleep(SLEEP)

    print(f"\n  Scraped {len(rows)} firms with data")

    if not rows:
        print("No data scraped — aborting")
        return

    # Save CSV
    print("\n[3] Saving CSV...")
    save_csv(rows, OUT_CSV)

    # Import DB
    print("\n[4] Importing to DB...")
    import_to_db(rows)

    # Enrich
    print("\n[5] Email enrichment...")
    enrich_email(DB)

    print(f"\nDone. Total: {len(rows)} consultants")


if __name__ == "__main__":
    main()
