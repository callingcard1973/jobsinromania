#!/usr/bin/env python3
"""Extract producers and traders by CAEN code from master_romania_companies.

Sources:
  1. master_romania_companies - direct CAEN query (fast, indexed)
  2. afir_beneficiari - cross-ref CUI from AFIR with master for email enrichment
  3. dsvsa_companies - food storage/handling (cereal/veg depozite)

CAEN codes:
  0111 - Cultivarea cerealelor (producers)
  0113 - Cultivarea legumelor (producers)
  4621 - Comert cu ridicata al cerealelor (traders)
  4631 - Comert cu ridicata al fructelor si legumelor (traders)

Output: CSV files in DATA/producers_by_caen/
"""
import csv
import os
import sys

try:
    import psycopg2
except ImportError:
    psycopg2 = None

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import config as CFG

OUT_DIR = os.path.join(CFG.DATA, "producers_by_caen")

CAEN_TARGETS = ["0111", "0113", "4621", "4631"]

CAEN_LABELS = {
    "0111": "producatori_cereale",
    "0113": "producatori_legume",
    "4621": "comercianti_cereale",
    "4631": "comercianti_legume_fructe",
}


def _conn():
    if psycopg2 is None:
        raise RuntimeError("psycopg2 not available")
    return psycopg2.connect(**CFG.DB)


def query(sql, params=None, conn=None):
    close = False
    if conn is None:
        conn = _conn()
        close = True
    cur = conn.cursor()
    cur.execute(sql, params or ())
    rows = cur.fetchall()
    cur.close()
    if close:
        conn.close()
    return rows


def write_csv(rows, path, cols):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)


def main():
    conn = _conn()
    os.makedirs(OUT_DIR, exist_ok=True)
    out = []

    # 1. CAEN from master_romania_companies (primary).
    print("=== MASTER ROMANIA COMPANIES ===")
    for caen in CAEN_TARGETS:
        lbl = CAEN_LABELS[caen]
        rows = query(
            """SELECT cui, LEFT(name, 120), city, county,
                      email, email_secondary, phone, caen
               FROM master_romania_companies
               WHERE caen=%s
               ORDER BY county, name""", (caen,), conn=conn)
        path = os.path.join(OUT_DIR, f"{lbl}.csv")
        write_csv(rows, path,
                  ["cui", "name", "city", "county", "email",
                   "email_secondary", "phone", "caen"])
        print(f"  CAEN {caen} ({lbl}): {len(rows)} -> {path}")

        for r in rows:
            out.append((r[0], r[1], r[2], r[3], r[4] or r[5] or "",
                        r[6] or "", caen, lbl, "master_romania"))

    # 2. Cross-ref AFIR CUI -> email from master_romania_companies.
    print("\n=== AFIR BENEFICIARI -> EMAIL ENRICHMENT ===")
    afir_rows = query(
        """SELECT a.cui, LEFT(a.denumire, 120), a.localitate, a.judet,
                  m.email, m.phone
           FROM afir_beneficiari a
           JOIN master_romania_companies m ON a.cui = m.cui
           WHERE m.email ~ '@' AND m.email IS NOT NULL
           GROUP BY a.cui, a.denumire, a.localitate, a.judet,
                    m.email, m.phone
           ORDER BY a.judet, a.denumire
           LIMIT 50000""", conn=conn)
    path = os.path.join(OUT_DIR, "afir_cu_email.csv")
    write_csv(afir_rows, path,
              ["cui", "denumire", "localitate", "judet", "email", "phone"])
    print(f"  AFIR with email via master: {len(afir_rows)} -> {path}")

    for r in afir_rows:
        out.append((r[0], r[1], r[3], r[2], r[4] or "",
                    r[5] or "", "", "", "afir_enriched"))

    # 3. DSVSA depozite cereale/legume (direct cursor to avoid % issues).
    print("\n=== DSVSA (depozite cereale/legume) ===")
    dsvsa_sql = ("SELECT company_name, cui, city, county, activity_type, category "
                 "FROM dsvsa_companies "
                 "WHERE (category ~* 'cereal|legum|depozit|siloz|moara|morarit') "
                 "AND cui IS NOT NULL AND cui <> '' "
                 "ORDER BY county, company_name LIMIT 20000")
    cur = conn.cursor()
    cur.execute(dsvsa_sql)
    dsvsa_rows = cur.fetchall()
    cur.close()
    path = os.path.join(OUT_DIR, "dsvsa_depozite.csv")
    write_csv(dsvsa_rows, path,
              ["company_name", "cui", "city", "county",
               "activity_type", "category"])
    print(f"  DSVSA depozite: {len(dsvsa_rows)} -> {path}")

    for r in dsvsa_rows:
        extra = "DSVSA %s/%s" % (r[4] or "", r[5] or "")
        out.append((r[1], r[0], r[2], r[3], "", "", "", "", extra))

    # 4. Unificat (primul email, primul phone).
    print("\n=== UNIFICAT ===")
    seen = {}
    for r in out:
        cui = r[0]
        if cui and cui not in seen:
            seen[cui] = r
        elif cui and not seen[cui][4] and r[4]:
            seen[cui] = (seen[cui][0], seen[cui][1], seen[cui][2],
                         seen[cui][3], r[4], seen[cui][5], *seen[cui][6:])

    unified = list(seen.values())
    path = os.path.join(OUT_DIR, "unified_all.csv")
    write_csv(unified, path,
              ["cui", "name", "city", "county", "email",
               "phone", "caen", "caen_label", "source"])
    print(f"  Unified (unique CUI): {len(unified)} -> {path}")

    has_email = sum(1 for r in unified if r[4] and "@" in r[4])
    conn.close()

    print("\n=== SUMMARY ===")
    print("  Total unique entries: %d" % len(unified))
    print("  With email: %d" % has_email)
    print("  Output dir: %s/" % OUT_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
