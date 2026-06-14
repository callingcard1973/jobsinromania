#!/usr/bin/env python3
"""Direct InterJob match via plink SSH."""
import csv
import subprocess
from pathlib import Path

ENRICHED_CSV = Path(__file__).parent / "silos_enriched.csv"
FINAL_CSV = Path(__file__).parent / "silos_final.csv"

def get_db_companies():
    """Query raspibig for all company names and CUIs."""
    cmd = '''plink -batch -pw REDACTED tudor@192.168.100.21 "psql -h localhost -U tudor -d interjob_master -t -c \\"SELECT DISTINCT lower(name) FROM ij_companies WHERE name IS NOT NULL UNION SELECT DISTINCT lower(name) FROM fw_companies WHERE name IS NOT NULL\\" 2>/dev/null" '''
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        names = {line.strip() for line in result.stdout.strip().split('\n') if line.strip()}
        return names
    except Exception as e:
        print(f"Query error: {e}")
    return set()

def main():
    records = []
    with open(ENRICHED_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        records = list(reader)

    print(f"Read {len(records)} silos")
    print("Querying InterJob DB...")
    db_names = get_db_companies()
    print(f"Found {len(db_names)} companies in InterJob")

    # Match
    matched = 0
    for rec in records:
        name_lower = rec["name"].lower().strip()
        # Try exact match and partial matches
        if name_lower in db_names or any(name_lower.startswith(db) or db.startswith(name_lower[:20]) for db in db_names):
            rec["in_interjob"] = "YES"
            matched += 1
        else:
            rec["in_interjob"] = "NO"

    # Write
    fieldnames = list(records[0].keys())
    with open(FINAL_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"Matched: {matched}/{len(records)}")
    print(f"OK: {FINAL_CSV}")

if __name__ == "__main__":
    main()
