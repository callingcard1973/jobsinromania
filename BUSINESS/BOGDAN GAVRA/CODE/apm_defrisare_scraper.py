"""
APM București scraper for tree-cutting authorizations.
Targets ANPM news/announcements mentioning defrisare/arbori.
Saves to apm_defrisare.csv, logs to apm_defrisare.log
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import requests
from bs4 import BeautifulSoup
import csv, logging, re, os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_CSV = os.path.join(BASE_DIR, "apm_defrisare.csv")
LOG_FILE = os.path.join(BASE_DIR, "apm_defrisare.log")

logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s")

HEADERS = {"User-Agent": "Mozilla/5.0 (research bot)"}
KEYWORDS = ["defrisare", "taiere arbori", "aviz arbori", "toaletare", "extirpare"]

TARGETS = [
    "https://apmbucuresti.anpm.ro/anunturi",
    "https://apmbucuresti.anpm.ro/avize",
    "https://apmbucuresti.anpm.ro/autorizatii",
    "https://anpm.ro/anunturi",
    "https://anpm.ro/avize-de-mediu",
]

def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return r.text
    except Exception as e:
        logging.warning(f"FETCH FAIL {url}: {e}")
        return None

def parse_trees(text):
    """Try to extract number of trees from text."""
    m = re.search(r'(\d+)\s*(arbori|copaci|exemplare)', text, re.IGNORECASE)
    return int(m.group(1)) if m else None

def scan_page(url, html):
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for el in soup.find_all(["a", "li", "p", "h2", "h3", "td"]):
        text = el.get_text(" ", strip=True)
        if any(kw in text.lower() for kw in KEYWORDS):
            link = el.find("a")
            href = link["href"] if link and link.get("href") else url
            if href.startswith("/"):
                from urllib.parse import urlparse
                p = urlparse(url)
                href = f"{p.scheme}://{p.netloc}{href}"
            trees = parse_trees(text)
            results.append({
                "firma": text[:120],
                "adresa": "",
                "data": datetime.today().strftime("%Y-%m-%d"),
                "arbori_taiati": trees or "",
                "obligatie_plantare": trees * 6 if trees else "",
                "sursa_url": href,
            })
    return results

def main():
    all_rows = []
    for url in TARGETS:
        logging.info(f"Fetching {url}")
        html = fetch(url)
        if not html:
            continue
        rows = scan_page(url, html)
        logging.info(f"  Found {len(rows)} hits at {url}")
        all_rows.extend(rows)

    # Deduplicate by sursa_url
    seen = set()
    deduped = []
    for r in all_rows:
        key = r["sursa_url"]
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["firma","adresa","data","arbori_taiati","obligatie_plantare","sursa_url"])
        writer.writeheader()
        writer.writerows(deduped)

    print(f"Done. {len(deduped)} rows saved to {OUT_CSV}")
    for r in deduped:
        line = f"  {r['firma'][:80]} | trees={r['arbori_taiati']} | {r['sursa_url']}"
        print(line.encode('utf-8', errors='replace').decode('utf-8', errors='replace'))

if __name__ == "__main__":
    main()
