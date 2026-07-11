#!/usr/bin/env python3
import sqlite3, os

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for dbname in ["grain.db", "VegFru.db"]:
    path = os.path.join(BASE, "DATA", dbname)
    if not os.path.exists(path):
        print("%s: nu exista" % dbname)
        continue
    con = sqlite3.connect(path)
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM trading_partners")
    total = cur.fetchone()[0]
    print("=== %s ===" % dbname)
    print("  Total parteneri: %d" % total)
    for col in ["certificari_gmp", "depozit_licentiat", "insolventa", "rating_financiar", "calitate_certificata", "valoare_contracte"]:
        cur.execute("SELECT COUNT(*) FROM trading_partners WHERE %s != ''" % col)
        c = cur.fetchone()[0]
        if c:
            print("    %s: %d" % (col, c))
    # Top 5 by flags
    cur.execute("""SELECT firma_nume, certificari_gmp, depozit_licentiat, insolventa,
                          rating_financiar, calitate_certificata, valoare_contracte
                   FROM trading_partners
                   WHERE certificari_gmp!='' OR depozit_licentiat!='' OR insolventa!=''
                        OR rating_financiar!='' OR calitate_certificata!=''
                   LIMIT 5""")
    print("  Top 5:")
    for r in cur.fetchall():
        flags = []
        if r[1]: flags.append("GMP+")
        if r[2]: flags.append("DSVSA")
        if r[3]: flags.append("INSOLV")
        if r[4]: flags.append("MFIN")
        if r[5]: flags.append("BRM")
        print("    %s  ->  %s" % (r[0][:35].ljust(35), " ".join(flags)))
    con.close()

# Compare with GRAIN TRADING ROBOT
print()
print("=== Comparatie GRAIN TRADING ROBOT vs OPENCODE ===")
print()
gtr_csv = os.path.join(os.path.dirname(BASE), "GRAIN TRADING ROBOT", "DATA", "trading_partners_50columns.csv")
oc_csv = os.path.join(BASE, "DATA", "trading_partners_50cols.csv")
import csv
for label, path in [("GRAIN TRADING ROBOT", gtr_csv), ("OPENCODE", oc_csv)]:
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig") as f:
            r = csv.DictReader(f)
            cols = len(r.fieldnames)
            rows = sum(1 for _ in r)
        print("  %s: %d coloane, %d randuri" % (label, cols, rows))

print()
print("Diferente cheie:")
print("  GTR are 13.487 parteneri (incl. firme noi din ONRC)")
print("  OPENCODE are 12.360 (doar cei din enriched_final.csv)")
print("  GTR are VANZATORI_MASTER (1.418 producatori)")
print("  OPENCODE nu are vanzatori separat -- produce doar in CAEN 0111/0113")
