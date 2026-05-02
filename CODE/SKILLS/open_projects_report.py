#!/usr/bin/env python3
"""Generate report of projects with open procurement. Runs after each scrape."""
# --
import psycopg2
import csv
import json
import unicodedata
from datetime import datetime

DB = {"dbname": "european_funds", "user": "tudor", "host": "/var/run/postgresql"}

def to_ascii(t):
    if not t: return ''
    return unicodedata.normalize('NFKD', str(t)).encode('ascii', 'ignore').decode('ascii').strip()
OUT_DIR = "/opt/ACTIVE/EU_FUNDING/DATA/BENEFICIAR_FONDURI_UE/OPENPROJECTS"
OUT_CSV = f"{OUT_DIR}/open_projects.csv"
OUT_JSON = f"{OUT_DIR}/open_projects.json"

def main():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()

    # Projects with open anunturi (deadline > today)
    cur.execute("""
        SELECT p.cod_smis, p.titlu_proiect, p.beneficiar, p.program_operational,
               p.axa, p.judet, p.data_contract,
               COUNT(a.id) as open_count,
               STRING_AGG(DISTINCT a.tip_contract, ', ') as contract_types,
               STRING_AGG(DISTINCT a.titlu_achizitie, ' | ') as open_titles,
               MIN(a.data_limita) as earliest_deadline,
               MAX(a.data_limita) as latest_deadline
        FROM proiecte p
        JOIN beneficiari_privati a ON p.cod_smis = a.cod_smis
        WHERE a.cod_smis <> ''
        AND a.data_limita > to_char(CURRENT_DATE, 'DD.MM.YYYY')
        GROUP BY p.cod_smis, p.titlu_proiect, p.beneficiar,
                 p.program_operational, p.axa, p.judet, p.data_contract
        ORDER BY open_count DESC
    """)
    cols = [d[0] for d in cur.description]
    rows = [{k: to_ascii(v) if isinstance(v, str) else v for k, v in dict(zip(cols, row)).items()} for row in cur.fetchall()]

    # Stats
    cur.execute("SELECT COUNT(DISTINCT cod_smis) FROM beneficiari_privati WHERE cod_smis <> '' AND data_limita > to_char(CURRENT_DATE, 'DD.MM.YYYY')")
    total_projects = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM beneficiari_privati WHERE data_limita > to_char(CURRENT_DATE, 'DD.MM.YYYY')")
    total_open = cur.fetchone()[0]
    conn.close()

    # Write CSV
    with open(OUT_CSV, "w", newline="", encoding="ascii", errors="replace") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    # Write JSON
    report = {
        "generated": datetime.now().isoformat(),
        "total_projects_with_open": total_projects,
        "total_open_anunturi": total_open,
        "projects": rows
    }
    with open(OUT_JSON, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"Projects with open procurement: {total_projects}")
    print(f"Total open anunturi: {total_open}")
    print(f"CSV: {OUT_CSV} ({len(rows)} rows)")
    print(f"JSON: {OUT_JSON}")

    # Top 10
    for r in rows[:10]:
        print(f"  {r['cod_smis']} | {r['open_count']} open | {r['beneficiar'][:30]} | {r['judet']}")

if __name__ == "__main__":
    main()
