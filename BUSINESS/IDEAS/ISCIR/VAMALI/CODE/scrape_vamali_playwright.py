#!/usr/bin/env python3
"""Scrape VAMALI AEO list using Playwright for JavaScript rendering.
Source: https://www.customs.ro/e-customs/aeo/lista-operatorilor-economici-autorizati
"""
import csv
import re
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

DATA_DIR = Path(__file__).parent.parent / "DATA"
OUT_CSV = DATA_DIR / "vamali_aeo_combined.csv"

AEO_LIST_URL = "https://www.customs.ro/e-customs/aeo/lista-operatorilor-economici-autorizati"


def clean_str(val):
    """Clean string value."""
    if not val:
        return None
    s = str(val).strip()
    return s if s else None


def clean_cui(raw):
    """Extract digits from CUI."""
    if not raw:
        return None
    s = re.sub(r"[^\d]", "", str(raw)).lstrip("0")
    return s if s else None


def scrape_with_playwright():
    """Scrape using Playwright for JS-rendered content."""
    records = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        print(f"Navigating to {AEO_LIST_URL}...")
        page.goto(AEO_LIST_URL, wait_until="networkidle")
        page.wait_for_timeout(3000)  # Wait for JS to render

        # Try to find and click pagination or load more buttons
        html = page.content()

        # Extract all text to analyze structure
        body_text = page.inner_text("body") if page.query_selector("body") else ""

        # Look for table data
        rows = page.query_selector_all("table tr")
        if rows:
            print(f"Found {len(rows)} table rows")
            for idx, row in enumerate(rows[1:], 1):  # Skip header
                try:
                    cells = row.query_selector_all("td")
                    if len(cells) >= 2:
                        rec = {
                            "source_file": "vamali_aeo",
                            "company_name": clean_str(cells[0].inner_text()) if len(cells) > 0 else None,
                            "cui": clean_cui(cells[1].inner_text()) if len(cells) > 1 else None,
                            "adresa": clean_str(cells[2].inner_text()) if len(cells) > 2 else None,
                            "localitate": clean_str(cells[3].inner_text()) if len(cells) > 3 else None,
                            "judet": clean_str(cells[4].inner_text()) if len(cells) > 4 else None,
                            "tip_autorizatie": clean_str(cells[5].inner_text()) if len(cells) > 5 else None,
                            "stare": clean_str(cells[6].inner_text()) if len(cells) > 6 else "Neclasifit",
                            "email": None,
                            "extra": json.dumps({})
                        }
                        if rec["company_name"]:
                            records.append(rec)
                except Exception as e:
                    print(f"  Error parsing row {idx}: {e}")

        # Fallback: look for div-based layout
        if not records:
            print("No tables found, looking for div-based layout...")
            items = page.query_selector_all("div[data-aeo], div.aeo, div.operator, div.company")
            print(f"Found {len(items)} items")
            for item in items:
                try:
                    texts = item.inner_text().split("\n")
                    texts = [t.strip() for t in texts if t.strip()]
                    if len(texts) >= 2:
                        rec = {
                            "source_file": "vamali_aeo",
                            "company_name": texts[0],
                            "cui": clean_cui(texts[1] if len(texts) > 1 else None),
                            "adresa": texts[2] if len(texts) > 2 else None,
                            "localitate": texts[3] if len(texts) > 3 else None,
                            "judet": texts[4] if len(texts) > 4 else None,
                            "tip_autorizatie": texts[5] if len(texts) > 5 else None,
                            "stare": texts[6] if len(texts) > 6 else "Neclasifit",
                            "email": None,
                            "extra": json.dumps({})
                        }
                        records.append(rec)
                except Exception as e:
                    pass

        browser.close()

    return records


def main():
    """Main entry point."""
    print("Starting VAMALI AEO scraper (Playwright)...")

    try:
        records = scrape_with_playwright()
    except Exception as e:
        print(f"ERROR: {e}")
        print("Falling back to basic BeautifulSoup scraper")
        records = []

    # Dedup
    seen = set()
    deduped = []
    for rec in records:
        key = (rec["source_file"], rec["company_name"], rec["cui"] or "")
        if key not in seen:
            seen.add(key)
            deduped.append(rec)

    if deduped:
        print(f"\nExtracted {len(deduped)} unique records")

        # Write CSV
        with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "source_file", "company_name", "cui", "adresa",
                "localitate", "judet", "tip_autorizatie", "stare", "email", "extra"
            ])
            writer.writeheader()
            writer.writerows(deduped)

        print(f"Output: {OUT_CSV}")

        # Summary
        with_email = sum(1 for r in deduped if r.get("email"))
        with_cui = sum(1 for r in deduped if r.get("cui"))
        print(f"\nSummary:")
        print(f"  Total records: {len(deduped)}")
        print(f"  With CUI: {with_cui}")
        print(f"  With email: {with_email}")
    else:
        print("\nWARNING: No records extracted")
        print("Page structure may require manual inspection or API endpoint discovery")


if __name__ == "__main__":
    main()
