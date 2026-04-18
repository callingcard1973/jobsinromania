#!/usr/bin/env python3
"""Extract food winners from SEAP data via tenders table + SSH.

Reads tenders table for stats (wins, value, buyers), then
gets CUIs from raw SEAP CSV on raspibig via SSH.

Output: DATA/seap_food_winners_with_cui.csv
"""

import csv
import json
import os
import subprocess
import sys

try:
    import psycopg2
except ImportError:
    print("pip install psycopg2-binary")
    sys.exit(1)

from shared_utils import normalize, DB_MASTER as DB

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_DIR, "DATA")

SEAP_CSV = "/opt/ACTIVE/OPENDATA/DATA/ACHIZITII_PUBLICE/achizitii_publice_2025_combined.csv"


def extract_from_seap():
    """Extract food winners from SEAP CSV on raspibig via SSH."""
    print("Extracting food winners from SEAP CSV...")
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()

    cur.execute("""
        SELECT winner_name, COUNT(*) AS wins,
               SUM(value) AS total_val,
               COUNT(DISTINCT buyer_name) AS buyers
        FROM tenders
        WHERE country = 'RO'
        AND (cpv_code LIKE '15%%' OR cpv_code LIKE '03%%')
        AND winner_name IS NOT NULL AND winner_name != ''
        GROUP BY winner_name
    """)
    stats = {}
    for name, wins, val, buyers in cur:
        stats[normalize(name)] = {
            "wins": wins, "total_value_ron": val or 0,
            "distinct_buyers": buyers,
        }
    print(f"  Tenders stats: {len(stats)} winners")
    conn.close()

    # Read existing extracted data or start fresh
    winners_path = os.path.join(DATA_DIR, "seap_food_winners_unique.csv")
    winners = {}
    if os.path.exists(winners_path):
        with open(winners_path, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                norm = normalize(row["winner_name"])
                winners[norm] = {
                    "winner_name": row["winner_name"],
                    "cui": "",
                    "wins": int(row.get("wins", 0)),
                    "total_value_ron": float(row.get("total_value_ron", 0)),
                    "distinct_buyers": int(row.get("distinct_buyers", 0)),
                }
    print(f"  Loaded {len(winners)} winners from CSV")

    # Get CUIs from SEAP raw data via SSH
    cmd = [
        "ssh", "tudor@192.168.100.21",
        "python3", "-c", f"""
import csv, json
food = {{}}
with open('{SEAP_CSV}', 'r', encoding='utf-8', errors='ignore') as f:
    for row in csv.DictReader(f):
        cpv = row.get('COD_CPV', '')
        if cpv.startswith('15') or cpv.startswith('03'):
            name = row.get('OFERTANT_CASTIGATOR', '').strip()
            cui = row.get('CUI_OFERTANT_CASTIGATOR', '').strip()
            if name and cui:
                food[name] = cui
print(json.dumps(food))
"""
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            cui_map = json.loads(result.stdout)
            for name, cui in cui_map.items():
                norm = normalize(name)
                if norm in winners:
                    winners[norm]["cui"] = cui
                else:
                    s = stats.get(norm, {"wins": 1, "total_value_ron": 0,
                                         "distinct_buyers": 1})
                    winners[norm] = {
                        "winner_name": name, "cui": cui,
                        "wins": s["wins"],
                        "total_value_ron": s["total_value_ron"],
                        "distinct_buyers": s["distinct_buyers"],
                    }
            print(f"  Got CUIs for {sum(1 for w in winners.values() if w.get('cui'))} winners")
    except Exception as ex:
        print(f"  SSH error: {ex}")

    # Save intermediate
    rows = sorted(winners.values(), key=lambda x: -x["wins"])
    out_path = os.path.join(DATA_DIR, "seap_food_winners_with_cui.csv")
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=["winner_name", "cui", "wins",
                                           "total_value_ron", "distinct_buyers"])
        w.writeheader()
        w.writerows(rows)
    print(f"  Saved {len(rows)} winners with CUI to {out_path}")
    return winners


if __name__ == "__main__":
    extract_from_seap()
