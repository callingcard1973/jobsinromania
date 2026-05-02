#!/usr/bin/env python3
"""Export all open anunturi grouped by project. Runs after open_projects_report."""
# --
import psycopg2
import csv
import json
import unicodedata
from datetime import datetime

DB = {"dbname": "european_funds", "user": "tudor", "host": "/var/run/postgresql"}
OUT_DIR = "/opt/ACTIVE/EU_FUNDING/DATA/BENEFICIAR_FONDURI_UE/OPENPROJECTS"

def to_ascii(t):
    if not t: return ''
    return unicodedata.normalize('NFKD', str(t)).encode('ascii', 'ignore').decode('ascii').strip()

def main():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()

    # All open anunturi with their project info
    cur.execute("""
        SELECT a.id as anunt_id, a.cod_smis, a.titlu_achizitie, a.tip_contract,
               a.buget, a.data_publicare, a.data_limita, a.judet as anunt_judet,
               a.descriere, a.spec_url, a.contractors, a.url as anunt_url,
               p.titlu_proiect, p.beneficiar, p.program_operational, p.axa,
               p.judet as project_judet, p.data_contract
        FROM beneficiari_privati a
        LEFT JOIN proiecte p ON a.cod_smis = p.cod_smis AND a.cod_smis <> ''
        WHERE a.data_limita > to_char(CURRENT_DATE, 'DD.MM.YYYY')
        ORDER BY a.data_limita ASC, a.cod_smis
    """)
    cols = [d[0] for d in cur.description]
    rows = [{k: to_ascii(v) if isinstance(v, str) else v for k, v in dict(zip(cols, row)).items()} for row in cur.fetchall()]

    # Stats
    with_project = sum(1 for r in rows if r['cod_smis'])
    no_project = sum(1 for r in rows if not r['cod_smis'])
    by_type = {}
    by_program = {}
    by_judet = {}
    for r in rows:
        t = r['tip_contract'] or 'Unknown'
        by_type[t] = by_type.get(t, 0) + 1
        p = r['program_operational'] or 'No project link'
        by_program[p] = by_program.get(p, 0) + 1
        j = r['anunt_judet'] or 'Unknown'
        by_judet[j] = by_judet.get(j, 0) + 1
    conn.close()

    # CSV - flat list
    with open(f"{OUT_DIR}/open_anunturi_full.csv", "w", newline="", encoding="ascii", errors="replace") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    # JSON - grouped by project
    grouped = {}
    orphans = []
    for r in rows:
        smis = r['cod_smis']
        if smis:
            if smis not in grouped:
                grouped[smis] = {
                    'cod_smis': smis, 'titlu_proiect': r['titlu_proiect'],
                    'beneficiar': r['beneficiar'], 'program': r['program_operational'],
                    'axa': r['axa'], 'judet': r['project_judet'],
                    'data_contract': r['data_contract'], 'anunturi': []
                }
            grouped[smis]['anunturi'].append({
                'id': r['anunt_id'], 'titlu': r['titlu_achizitie'],
                'tip': r['tip_contract'], 'buget': r['buget'],
                'deadline': r['data_limita'], 'publicare': r['data_publicare'],
                'judet': r['anunt_judet'], 'spec_url': r['spec_url'],
                'descriere': r['descriere'][:200] if r['descriere'] else ''
            })
        else:
            orphans.append(r)

    report = {
        "generated": datetime.now().isoformat(),
        "total_open": len(rows),
        "linked_to_project": with_project,
        "no_project_link": no_project,
        "by_type": dict(sorted(by_type.items(), key=lambda x: -x[1])),
        "by_program": dict(sorted(by_program.items(), key=lambda x: -x[1])[:15]),
        "by_judet": dict(sorted(by_judet.items(), key=lambda x: -x[1])[:15]),
        "projects": sorted(grouped.values(), key=lambda x: -len(x['anunturi'])),
        "orphan_count": len(orphans)
    }
    with open(f"{OUT_DIR}/open_anunturi_grouped.json", "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"Total open: {len(rows)}")
    print(f"Linked to project: {with_project}, Orphan: {no_project}")
    print(f"Projects with open: {len(grouped)}")
    print(f"By type: {by_type}")
    print(f"CSV: {OUT_DIR}/open_anunturi_full.csv")
    print(f"JSON: {OUT_DIR}/open_anunturi_grouped.json")

if __name__ == "__main__":
    main()
