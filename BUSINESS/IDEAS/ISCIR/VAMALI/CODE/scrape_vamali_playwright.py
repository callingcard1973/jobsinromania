#!/usr/bin/env python3
"""Scrape VAMALI AEO list using Playwright for JavaScript rendering.
Note: customs.ro loads data dynamically, requires network monitoring.
Source: https://www.customs.ro/e-customs/aeo/lista-operatorilor-economici-autorizati
"""
import csv
import re
import json
import sys
import time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERROR: Playwright not installed. Run: pip install playwright")
    sys.exit(1)

DATA_DIR = Path(__file__).parent.parent / "DATA"
OUT_CSV = DATA_DIR / "vamali_aeo_final.csv"

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


def extract_row(cells):
    """Extract row data from table cells."""
    return {
        "source_file": "vamali_aeo",
        "company_name": clean_str(cells[0].inner_text()) if len(cells) > 0 else None,
        "cui": clean_cui(cells[1].inner_text()) if len(cells) > 1 else None,
        "adresa": clean_str(cells[2].inner_text()) if len(cells) > 2 else None,
        "localitate": clean_str(cells[3].inner_text()) if len(cells) > 3 else None,
        "judet": clean_str(cells[4].inner_text()) if len(cells) > 4 else None,
        "tip_autorizatie": clean_str(cells[5].inner_text()) if len(cells) > 5 else None,
        "stare": clean_str(cells[6].inner_text()) if len(cells) > 6 else "Activ",
        "email": clean_str(cells[7].inner_text()) if len(cells) > 7 else None,
        "telefon": clean_str(cells[8].inner_text()) if len(cells) > 8 else None
    }


def extract_from_api_data(data):
    """Extract records from API JSON response."""
    records = []
    if not isinstance(data, list):
        return records

    for item in data:
        if isinstance(item, dict):
            name = item.get("name") or item.get("company_name") or item.get("denumire")
            if name:
                rec = {
                    "source_file": "vamali_aeo",
                    "company_name": clean_str(name),
                    "cui": clean_cui(item.get("cui") or item.get("cif")),
                    "adresa": clean_str(item.get("adresa") or item.get("address")),
                    "localitate": clean_str(item.get("localitate") or item.get("city")),
                    "judet": clean_str(item.get("judet") or item.get("county")),
                    "tip_autorizatie": clean_str(item.get("tip") or item.get("type")),
                    "stare": clean_str(item.get("stare") or item.get("status") or "Activ"),
                    "email": clean_str(item.get("email")),
                    "telefon": clean_str(item.get("telefon") or item.get("phone"))
                }
                if rec.get("company_name"):
                    records.append(rec)
    return records


def scrape_with_playwright():
    """Scrape using Playwright with network interception."""
    records = []
    network_data = {}

    def capture_response(response):
        """Intercept and capture network responses."""
        url = response.url
        try:
            if "application/json" in response.headers.get("content-type", ""):
                data = response.json()
                if isinstance(data, (list, dict)):
                    if "aeo" in url or "api" in url:
                        network_data[url] = data
        except Exception:
            pass

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.on("response", capture_response)

        print(f"Navigating to {AEO_LIST_URL}...")
        try:
            page.goto(AEO_LIST_URL, wait_until="domcontentloaded")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(4000)
        except Exception as e:
            print(f"Navigation warning: {str(e)[:80]}")

        # Check for network data captured
        if network_data:
            print(f"Captured {len(network_data)} API responses")
            for url, data in network_data.items():
                extracted = extract_from_api_data(data)
                if extracted:
                    print(f"  Extracted {len(extracted)} from {url[:70]}")
                    records.extend(extracted)

        # Fallback: try DOM extraction
        if not records:
            rows = page.query_selector_all("table tbody tr")
            if not rows:
                rows = page.query_selector_all("tbody tr")

            if rows:
                print(f"Found {len(rows)} table rows")
                for row in rows:
                    try:
                        cells = row.query_selector_all("td")
                        if len(cells) >= 2:
                            rec = extract_row(cells)
                            if rec.get("company_name"):
                                records.append(rec)
                    except Exception:
                        pass

        context.close()
        browser.close()

    return records


def main():
    """Main entry point."""
    print("Starting VAMALI AEO scraper (Playwright)...\n")

    try:
        records = scrape_with_playwright()
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        records = []

    if not records:
        print("\nERROR: No records extracted from customs.ro")
        print("The website may require additional interaction or different endpoints.")
        print("Check if list loads via search form or pagination controls.")
        return

    # Dedup by (source_file, company_name, cui)
    seen = set()
    deduped = []
    for rec in records:
        key = (rec["source_file"], rec["company_name"], rec["cui"] or "")
        if key not in seen:
            seen.add(key)
            deduped.append(rec)

    print(f"\nExtracted {len(deduped)} unique records")

    # Write CSV
    fieldnames = ["source_file", "company_name", "cui", "adresa", "localitate",
                  "judet", "tip_autorizatie", "stare", "email", "telefon"]
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(deduped)

    print(f"Output: {OUT_CSV}")

    # Summary
    with_email = sum(1 for r in deduped if r.get("email"))
    with_cui = sum(1 for r in deduped if r.get("cui"))
    with_phone = sum(1 for r in deduped if r.get("telefon"))

    print(f"\nSummary:")
    print(f"  Total records: {len(deduped)}")
    print(f"  With CUI: {with_cui}")
    print(f"  With email: {with_email}")
    print(f"  With phone: {with_phone}")


if __name__ == "__main__":
    main()
