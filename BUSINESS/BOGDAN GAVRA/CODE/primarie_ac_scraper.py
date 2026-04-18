"""
PMB autorizatii de construire scraper — filters for tree/green-space conditions.
Tries PMB urbanism portal and sector primarie pages.
Saves to pmb_ac_leads.csv
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import requests
from bs4 import BeautifulSoup
import csv, os, re, logging
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_CSV  = os.path.join(BASE_DIR, "pmb_ac_leads.csv")
LOG_FILE = os.path.join(BASE_DIR, "pmb_ac_scraper.log")

logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s")

HEADERS  = {"User-Agent": "Mozilla/5.0 (research bot)"}
KEYWORDS = ["arbori", "defrisare", "spatii verzi", "plantat", "taiere", "copaci", "compensare"]

TARGETS = [
    "https://pmb.ro/servicii/urbanism/autorizatii_de_construire/index.php",
    "https://pmb.ro/institutii/directii_generale/dguat/index.php",
    "https://pmb.ro/anunturi/index.php",
    "https://ps1.ro/autorizatii-de-construire/",
    "https://ps2.ro/autorizatii-construire/",
    "https://ps3.ro/category/autorizatii-de-construire/",
    "https://ps4.ro/urbanism/",
    "https://ps5.ro/servicii/urbanism/",
    "https://ps6.ro/urbanism-autorizatii/",
]

def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return r.text
    except Exception as e:
        logging.warning(f"FAIL {url}: {e}")
        return None

def scan_for_leads(url, html):
    soup = BeautifulSoup(html, "html.parser")
    results = []
    # Look in tables (common for permit lists)
    for row in soup.find_all("tr"):
        text = row.get_text(" ", strip=True)
        if any(kw in text.lower() for kw in KEYWORDS):
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            results.append({
                "firma_beneficiara": cells[0] if cells else text[:80],
                "adresa_proiect": cells[1] if len(cells) > 1 else "",
                "conditii_arbori": text[:200],
                "data": datetime.today().strftime("%Y-%m-%d"),
                "sursa_url": url,
            })
    # Also scan paragraphs / list items
    for el in soup.find_all(["p", "li", "h3", "h4"]):
        text = el.get_text(" ", strip=True)
        if any(kw in text.lower() for kw in KEYWORDS) and len(text) > 30:
            link = el.find("a")
            href = link["href"] if link and link.get("href") else url
            results.append({
                "firma_beneficiara": text[:80],
                "adresa_proiect": "",
                "conditii_arbori": text[:200],
                "data": datetime.today().strftime("%Y-%m-%d"),
                "sursa_url": href if href.startswith("http") else url,
            })
    return results

def main():
    all_rows = []
    for url in TARGETS:
        logging.info(f"Fetching {url}")
        html = fetch(url)
        if not html:
            print(f"  SKIP (unreachable): {url}")
            continue
        rows = scan_for_leads(url, html)
        logging.info(f"  {len(rows)} hits at {url}")
        print(f"  {len(rows)} hits: {url}")
        all_rows.extend(rows)

    # Deduplicate by conditii text
    seen = set()
    deduped = []
    for r in all_rows:
        key = r["conditii_arbori"][:60]
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        cols = ["firma_beneficiara","adresa_proiect","conditii_arbori","data","sursa_url"]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(deduped)

    print(f"\nDone. {len(deduped)} rows saved to {OUT_CSV}")
    for r in deduped[:5]:
        line = f"  {r['firma_beneficiara'][:70]} | {r['sursa_url']}"
        print(line.encode('utf-8', errors='replace').decode('utf-8', errors='replace'))

if __name__ == "__main__":
    main()
