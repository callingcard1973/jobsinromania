#!/usr/bin/env python3
"""Scrape VAMALI (Customs) AEO authorized operators list.
Source: https://www.customs.ro/e-customs/aeo/lista-operatorilor-economici-autorizati
"""
import csv
import re
import json
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

DATA_DIR = Path(__file__).parent.parent / "DATA"
OUT_CSV = DATA_DIR / "vamali_aeo_combined.csv"

AEO_LIST_URL = "https://www.customs.ro/e-customs/aeo/lista-operatorilor-economici-autorizati"

# Session with tolerant SSL handling
session = requests.Session()
session.verify = False
requests.packages.urllib3.disable_warnings()


def clean_str(val):
    """Clean string value."""
    if not val:
        return None
    s = str(val).strip()
    return s if s else None


def clean_cui(raw):
    """Extract digits from CUI, remove leading zeros."""
    if not raw:
        return None
    s = re.sub(r"[^\d]", "", str(raw)).lstrip("0")
    return s if s else None


def fetch_page(url):
    """Fetch page with user-agent."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        resp = session.get(url, headers=headers, timeout=10)
        resp.encoding = "utf-8"
        return resp.text
    except Exception as e:
        print(f"ERROR fetching {url}: {e}")
        return None


def parse_aeo_list(html):
    """Parse AEO list from HTML page."""
    records = []
    if not html:
        return records

    soup = BeautifulSoup(html, "html.parser")

    # Look for table rows or list items containing AEO data
    # Strategy: Find all rows/items and extract fields
    # Customs.ro may use table, divs, or modals

    # Try table-based layout first
    table = soup.find("table")
    if table:
        rows = table.find_all("tr")[1:]  # Skip header
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                try:
                    rec = extract_row_data(cells)
                    if rec:
                        records.append(rec)
                except Exception as e:
                    print(f"  Skipping row: {e}")

    # Fallback: look for div-based layout
    if not records:
        # Many modern sites use divs with data attributes
        items = soup.find_all("div", class_=re.compile("aeo|operator|company", re.I))
        for item in items:
            try:
                rec = extract_div_data(item)
                if rec:
                    records.append(rec)
            except Exception as e:
                print(f"  Skipping item: {e}")

    # Final fallback: look for any links containing company info
    if not records:
        links = soup.find_all("a", href=re.compile("aeo|operator", re.I))
        for link in links[:50]:  # Limit to avoid excessive processing
            text = clean_str(link.get_text())
            if text and len(text) > 3:
                records.append({
                    "source_file": "vamali_aeo",
                    "company_name": text,
                    "cui": None,
                    "adresa": None,
                    "localitate": None,
                    "judet": None,
                    "tip_autorizatie": None,
                    "stare": "Neclaificat",
                    "email": None,
                    "extra": json.dumps({})
                })

    return records


def extract_row_data(cells):
    """Extract data from table row cells."""
    if len(cells) < 2:
        return None

    rec = {
        "source_file": "vamali_aeo",
        "company_name": clean_str(cells[0].get_text()),
        "cui": clean_cui(cells[1].get_text() if len(cells) > 1 else None),
        "adresa": clean_str(cells[2].get_text() if len(cells) > 2 else None),
        "localitate": clean_str(cells[3].get_text() if len(cells) > 3 else None),
        "judet": clean_str(cells[4].get_text() if len(cells) > 4 else None),
        "tip_autorizatie": clean_str(cells[5].get_text() if len(cells) > 5 else None),
        "stare": clean_str(cells[6].get_text() if len(cells) > 6 else "Neclasifit"),
        "email": None,
        "extra": json.dumps({})
    }

    # Only keep if company_name is present
    if rec["company_name"]:
        return rec
    return None


def extract_div_data(div):
    """Extract data from div-based layout."""
    texts = [t.strip() for t in div.stripped_strings if t.strip()]
    if len(texts) < 2:
        return None

    # Try to infer structure
    rec = {
        "source_file": "vamali_aeo",
        "company_name": texts[0] if texts else None,
        "cui": clean_cui(texts[1] if len(texts) > 1 else None),
        "adresa": texts[2] if len(texts) > 2 else None,
        "localitate": texts[3] if len(texts) > 3 else None,
        "judet": texts[4] if len(texts) > 4 else None,
        "tip_autorizatie": texts[5] if len(texts) > 5 else None,
        "stare": texts[6] if len(texts) > 6 else "Neclasifit",
        "email": None,
        "extra": json.dumps({})
    }

    if rec["company_name"]:
        return rec
    return None


def scrape_aeo_list():
    """Main scraper function."""
    print(f"Fetching AEO list from {AEO_LIST_URL}...")
    html = fetch_page(AEO_LIST_URL)

    if not html:
        print("ERROR: Failed to fetch page")
        return []

    print("Parsing HTML...")
    records = parse_aeo_list(html)

    # Dedup by (source_file, company_name, cui)
    seen = set()
    deduped = []
    for rec in records:
        key = (rec["source_file"], rec["company_name"], rec["cui"] or "")
        if key not in seen:
            seen.add(key)
            deduped.append(rec)

    return deduped


def main():
    """Main entry point."""
    records = scrape_aeo_list()

    if records:
        print(f"\nExtracted {len(records)} records")

        # Write CSV
        with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "source_file", "company_name", "cui", "adresa",
                "localitate", "judet", "tip_autorizatie", "stare", "email", "extra"
            ])
            writer.writeheader()
            writer.writerows(records)

        print(f"Output: {OUT_CSV}")

        # Summary
        with_email = sum(1 for r in records if r.get("email"))
        with_cui = sum(1 for r in records if r.get("cui"))
        print(f"\nSummary:")
        print(f"  Total records: {len(records)}")
        print(f"  With CUI: {with_cui}")
        print(f"  With email: {with_email}")
    else:
        print("\nERROR: No records extracted")
        print("\nDEBUG: customs.ro may use JavaScript rendering.")
        print("Recommendation: Use Playwright/Selenium for dynamic content scraping.")
        print("See CODE/scrape_vamali_js.py (TODO)")


if __name__ == "__main__":
    main()
