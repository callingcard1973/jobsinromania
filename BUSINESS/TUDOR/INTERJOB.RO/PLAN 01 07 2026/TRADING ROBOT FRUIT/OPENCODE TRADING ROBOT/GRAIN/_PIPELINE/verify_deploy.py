#!/usr/bin/env python3
import os, sqlite3, subprocess, sys

ROOT = "/opt/ACTIVE/TRADING_ROBOT_FRUIT"
GRAIN = os.path.join(ROOT, "GRAIN")
DATA = os.path.join(ROOT, "DATA")

print("=== Verify OPENCODE deploy ===")
print("ROOT:", ROOT)
print()

errors = 0

# Files
files = [
    "GRAIN/grain_buyer_match.py",
    "GRAIN/fv_buyer_match.py",
    "GRAIN/grain_deal_detector.py",
    "GRAIN/agrointel_cereale_benchmark_scraper.py",
    "GRAIN/_PIPELINE/enrich_to_db.py",
    "GRAIN/_PIPELINE/create_dbs.py",
    "GRAIN/_PIPELINE/check_db.py",
    "DATA/enriched_final.csv",
    "DATA/cereale_port_prices.csv",
    "DATA/grain.db",
    "DATA/VegFru.db",
    "config.py",
]
for f in files:
    p = os.path.join(ROOT, f)
    exists = os.path.exists(p)
    sz = os.path.getsize(p) if exists else 0
    ok = "OK" if exists else "MISSING"
    if not exists:
        errors += 1
    print("  %s %s (%d bytes)" % (ok.ljust(7), f, sz))

print()

# DB grain.db
for dbname in ["grain.db", "VegFru.db"]:
    p = os.path.join(DATA, dbname)
    if os.path.exists(p):
        con = sqlite3.connect(p)
        c = con.execute("SELECT COUNT(*) FROM trading_partners")
        total = c.fetchone()[0]
        c = con.execute("SELECT COUNT(*) FROM trading_partners WHERE firma_cui != ''")
        with_cui = c.fetchone()[0]
        con.close()
        print("  %s: %d parteneri (%d cu CUI)" % (dbname, total, with_cui))
    else:
        errors += 1

print()

# Script tests
scripts = [
    ("grain_buyer_match.py", "cd GRAIN && python3 grain_buyer_match.py 2>&1 | head -4"),
    ("fv_buyer_match.py", "cd GRAIN && python3 fv_buyer_match.py 2>&1 | head -4"),
    ("grain_deal_detector.py", "cd GRAIN && python3 grain_deal_detector.py 2>&1 | head -5"),
    ("enrich_to_db.py", "cd GRAIN && python3 _PIPELINE/enrich_to_db.py 2>&1 | tail -5"),
]
for name, cmd in scripts:
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    out = res.stdout.strip().split("\n")
    print("  %s: %s" % (name, out[0] if out else "FAIL"))
    if res.returncode != 0:
        errors += 1
        print("    ERROR: %s" % res.stderr[:200])

print()
# Cron
res = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
cron_all = res.stdout.split("\n")
opencode_section = False
opencode_lines = []
for l in cron_all:
    if "OPENCODE GRAIN" in l:
        opencode_section = True
    if opencode_section:
        opencode_lines.append(l.strip())
    if "END OPENCODE GRAIN" in l:
        break
print("  Cron OPENCODE:")
for l in opencode_lines:
    print("    %s" % l if l else "    (empty)")

print()
if errors:
    print("=== EROARE: %d probleme ===" % errors)
    sys.exit(1)
else:
    print("=== VERIFICARE OK ===")
