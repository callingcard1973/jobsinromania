#!/usr/bin/env python3
"""Enrich silos with ANAF CUI data and InterJob DB match."""
import csv
import re
from pathlib import Path
import requests
import time

INPUT_CSV = Path(__file__).parent / "silos_master.csv"
OUTPUT_CSV = Path(__file__).parent / "silos_enriched.csv"

def clean_company_name(name):
    """Extract base company name (remove extra text)."""
    name = str(name).strip()
    # Remove common suffixes and prefixes
    name = re.sub(r'\b(SRL|SA|PFA|II|I\.I\.|SC|FILIAL|FILIA)\b.*$', '', name, flags=re.IGNORECASE).strip()
    name = re.sub(r'^(SC|SRL|SA|PFA|II|I\.I\.)\s+', '', name, flags=re.IGNORECASE).strip()
    return name[:50]  # Keep first 50 chars

def anaf_lookup(company_name):
    """Query ANAF for company CUI and details."""
    try:
        url = "https://webservicesp.anaf.ro/api/PlatitorTvaRest/v9/titular"
        params = {
            "judet": "",
            "denumire": company_name,
            "cif": "",
            "nrInreg": "",
            "tipoiSearchParam": 1
        }
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code == 200 and resp.json().get("found"):
            result = resp.json()["record"][0]  # First match
            return {
                "cui": result.get("cif", ""),
                "status": result.get("stare", ""),
                "address": result.get("address", ""),
                "activity": result.get("activity", ""),
            }
    except Exception as e:
        pass
    return {"cui": "", "status": "", "address": "", "activity": ""}

def read_csv():
    """Read input CSV and return list of dicts."""
    records = []
    with open(INPUT_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
    return records

def main():
    records = read_csv()
    print(f"Read {len(records)} silos")

    enriched = []
    for i, rec in enumerate(records, 1):
        if i % 50 == 0:
            print(f"  [{i}/{len(records)}]")

        clean_name = clean_company_name(rec["name"])
        anaf_data = anaf_lookup(clean_name)
        time.sleep(0.1)  # Rate limit

        enriched_rec = {
            **rec,
            "cui": anaf_data.get("cui", ""),
            "company_status": anaf_data.get("status", ""),
            "anaf_activity": anaf_data.get("activity", ""),
            "anaf_address": anaf_data.get("address", ""),
            "in_interjob": "",  # Will be filled by DB query
        }
        enriched.append(enriched_rec)

    print(f"\nANAF lookup complete. {len([r for r in enriched if r['cui']])} with CUI found")

    # Write enriched CSV
    fieldnames = list(enriched[0].keys()) if enriched else []
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(enriched)

    print(f"\nOK: {OUTPUT_CSV}")
    print("Columns:", ", ".join(fieldnames))

if __name__ == "__main__":
    main()
