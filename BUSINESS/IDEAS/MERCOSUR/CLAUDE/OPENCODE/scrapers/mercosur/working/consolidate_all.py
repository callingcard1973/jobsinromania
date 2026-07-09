#!/usr/bin/env python3
"""Consolidate all Mercosur producers into a single master file"""

import json
import csv
from pathlib import Path
from datetime import datetime
from glob import glob

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_master")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_json_files():
    """Load all producer JSON files"""
    all_producers = []
    sources = {}

    base_path = Path("/mnt/hdd/GLOBAL_DOWNLOADS")

    # Find all mercosur producer files
    patterns = [
        "mercosur_*_producers/*_producers_*.json",
        "mercosur_enriched/mercosur_producers_*.json"
    ]

    for pattern in patterns:
        for filepath in base_path.glob(pattern):
            try:
                with open(filepath) as f:
                    data = json.load(f)
                    source_name = filepath.parent.name
                    sources[source_name] = len(data)
                    all_producers.extend(data)
                    print(f"Loaded {len(data)} from {filepath.name}")
            except Exception as e:
                print(f"Error loading {filepath}: {e}")

    return all_producers, sources

def deduplicate(producers):
    """Deduplicate by company name"""
    seen = {}
    unique = []

    for p in producers:
        name = p.get("name", "").lower().strip()
        if not name:
            continue

        if name not in seen:
            seen[name] = p
            unique.append(p)
        else:
            # Merge additional data
            existing = seen[name]
            for key, val in p.items():
                if val and not existing.get(key):
                    existing[key] = val

    return unique

def main():
    print("=== Mercosur Producer Consolidator ===\n")

    all_producers, sources = load_json_files()

    print(f"\n=== SOURCE SUMMARY ===")
    for source, count in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"  {source}: {count}")
    print(f"  TOTAL RAW: {len(all_producers)}")

    # Deduplicate
    unique = deduplicate(all_producers)

    # Count by country
    countries = {}
    for p in unique:
        c = p.get("country", "Unknown")
        countries[c] = countries.get(c, 0) + 1

    # Count by sector
    sectors = {}
    for p in unique:
        s = p.get("sector", "unclassified")
        sectors[s] = sectors.get(s, 0) + 1

    print(f"\n=== DEDUPLICATED TOTAL: {len(unique)} ===")

    print(f"\nBy Country:")
    for country, count in sorted(countries.items(), key=lambda x: -x[1]):
        print(f"  {country}: {count}")

    print(f"\nBy Sector (top 15):")
    for sector, count in sorted(sectors.items(), key=lambda x: -x[1])[:15]:
        print(f"  {sector}: {count}")

    # Save master JSON
    timestamp = datetime.now().strftime("%Y%m%d")
    json_file = OUTPUT_DIR / f"mercosur_all_producers_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)
    print(f"\nSaved JSON: {json_file}")

    # Save master CSV
    csv_file = OUTPUT_DIR / f"mercosur_all_producers_{timestamp}.csv"
    fieldnames = ['name', 'country', 'sector', 'website', 'email', 'phone', 'capacity', 'source']
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for p in unique:
            writer.writerow(p)
    print(f"Saved CSV: {csv_file}")

    # Summary stats
    has_website = sum(1 for p in unique if p.get('website'))
    has_email = sum(1 for p in unique if p.get('email'))
    has_phone = sum(1 for p in unique if p.get('phone'))

    print(f"\n=== DATA QUALITY ===")
    print(f"  With website: {has_website} ({100*has_website/len(unique):.1f}%)")
    print(f"  With email: {has_email} ({100*has_email/len(unique):.1f}%)")
    print(f"  With phone: {has_phone} ({100*has_phone/len(unique):.1f}%)")

    return unique

if __name__ == "__main__":
    main()
