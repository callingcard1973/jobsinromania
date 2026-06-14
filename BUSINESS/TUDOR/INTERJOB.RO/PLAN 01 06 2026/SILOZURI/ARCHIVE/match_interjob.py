#!/usr/bin/env python3
"""Match silos against InterJob database."""
import csv
import subprocess
from pathlib import Path

ENRICHED_CSV = Path(__file__).parent / "silos_enriched.csv"
FINAL_CSV = Path(__file__).parent / "silos_final.csv"

def query_interjob_db(company_names):
    """Query raspibig DB for companies matching names/CUI."""
    cmd = """
plink -batch -pw REDACTED tudor@192.168.100.21 "python3 << 'SQLEOF'
import psycopg2
conn = psycopg2.connect(host='localhost', dbname='interjob_master', user='tudor', password='REDACTED')
cur = conn.cursor()

# Get all company names from ij_companies and fw_companies
cur.execute('SELECT DISTINCT lower(name) FROM ij_companies UNION SELECT DISTINCT lower(name) FROM fw_companies')
db_names = {row[0] for row in cur.fetchall()}

# Get CUI matches
cur.execute('SELECT DISTINCT lower(cui) FROM ij_companies WHERE cui IS NOT NULL UNION SELECT DISTINCT lower(cui) FROM fw_companies WHERE cui IS NOT NULL')
db_cuis = {row[0] for row in cur.fetchall()}

import json
print(json.dumps({'names': list(db_names), 'cuis': list(db_cuis)}))
cur.close()
conn.close()
SQLEOF
"
"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout.strip())
            return set(data.get("names", [])), set(data.get("cuis", []))
    except Exception as e:
        print(f"DB query error: {e}")
    return set(), set()

def main():
    # Read enriched CSV
    records = []
    with open(ENRICHED_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        records = list(reader)

    print(f"Read {len(records)} enriched silos")

    # Query InterJob DB
    print("Querying InterJob DB...")
    db_names, db_cuis = query_interjob_db([r["name"] for r in records])
    print(f"Found {len(db_names)} company names in InterJob")
    print(f"Found {len(db_cuis)} CUIs in InterJob")

    # Mark matches
    for rec in records:
        name_lower = rec["name"].lower().strip()
        cui = rec.get("cui", "").lower().strip()

        in_ij = "YES" if (name_lower in db_names or (cui and cui in db_cuis)) else "NO"
        rec["in_interjob"] = in_ij

    # Write final CSV
    fieldnames = list(records[0].keys()) if records else []
    with open(FINAL_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    # Stats
    in_ij = len([r for r in records if r["in_interjob"] == "YES"])
    print(f"\nMatched {in_ij}/{len(records)} silos to InterJob")
    print(f"OK: {FINAL_CSV}")

if __name__ == "__main__":
    main()
