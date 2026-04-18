#!/usr/bin/env python3
"""Merge ALL scraped Mercosur producer data"""

import json
import csv
from pathlib import Path
from datetime import datetime
from glob import glob

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_final")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_all():
    """Load all JSON files from all directories"""
    all_data = []
    base = Path("/mnt/hdd/GLOBAL_DOWNLOADS")

    patterns = [
        "mercosur_*/mercosur*.json",
        "mercosur_*/brazil*.json",
        "mercosur_*/argentina*.json",
        "mercosur_*/chile*.json",
        "mercosur_*/uruguay*.json",
        "mercosur_*/paraguay*.json",
        "mercosur_mass/*.json",
        "mercosur_deep/*.json",
    ]

    loaded_files = set()
    for pattern in patterns:
        for filepath in base.glob(pattern):
            if filepath in loaded_files:
                continue
            loaded_files.add(filepath)

            try:
                with open(filepath) as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        print(f"Loaded {len(data):4} from {filepath.name}")
                        all_data.extend(data)
            except Exception as e:
                print(f"Error {filepath}: {e}")

    return all_data

def normalize_name(name):
    """Normalize company name for deduplication"""
    if not name:
        return ""
    name = name.lower().strip()
    # Remove common suffixes
    for suffix in [' s.a.', ' s/a', ' ltda', ' ltd', ' inc', ' corp', ' s.r.l.', ' sa', ' srl']:
        name = name.replace(suffix, '')
    return name.strip()

def deduplicate(data):
    """Deduplicate and merge"""
    seen = {}

    for item in data:
        name = item.get('name', '')
        key = normalize_name(name)

        if not key or len(key) < 3:
            continue

        if key in seen:
            # Merge data
            existing = seen[key]
            for k, v in item.items():
                if v and not existing.get(k):
                    existing[k] = v
        else:
            seen[key] = item.copy()

    return list(seen.values())

def main():
    print("=== FINAL MERGE ===\n")

    all_data = load_all()
    print(f"\nTotal raw: {len(all_data)}")

    unique = deduplicate(all_data)
    print(f"Unique: {len(unique)}")

    # Stats
    countries = {}
    sectors = {}
    with_email = 0
    with_website = 0
    with_phone = 0

    for item in unique:
        c = item.get('country', 'Unknown')
        countries[c] = countries.get(c, 0) + 1

        s = item.get('sector', 'unclassified')
        sectors[s] = sectors.get(s, 0) + 1

        if item.get('email'):
            with_email += 1
        if item.get('website'):
            with_website += 1
        if item.get('phone'):
            with_phone += 1

    print(f"\nBy Country:")
    for c, n in sorted(countries.items(), key=lambda x: -x[1])[:10]:
        print(f"  {c}: {n}")

    print(f"\nBy Sector (top 10):")
    for s, n in sorted(sectors.items(), key=lambda x: -x[1])[:10]:
        print(f"  {s}: {n}")

    print(f"\nData Quality:")
    print(f"  With email: {with_email} ({100*with_email/len(unique):.1f}%)")
    print(f"  With website: {with_website} ({100*with_website/len(unique):.1f}%)")
    print(f"  With phone: {with_phone} ({100*with_phone/len(unique):.1f}%)")

    # Save
    timestamp = datetime.now().strftime("%Y%m%d")

    json_file = OUTPUT_DIR / f"mercosur_all_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {json_file}")

    csv_file = OUTPUT_DIR / f"mercosur_all_{timestamp}.csv"
    fields = ['name', 'country', 'sector', 'website', 'email', 'phone', 'capacity', 'source']
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(unique)
    print(f"Saved: {csv_file}")

    # Also save contacts-only version
    contacts = [p for p in unique if p.get('email')]
    contacts_file = OUTPUT_DIR / f"mercosur_contacts_{timestamp}.csv"
    with open(contacts_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(contacts)
    print(f"Saved: {contacts_file} ({len(contacts)} with email)")

    return unique

if __name__ == "__main__":
    main()
