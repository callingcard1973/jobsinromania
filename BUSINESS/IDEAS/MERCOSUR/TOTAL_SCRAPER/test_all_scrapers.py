#!/usr/bin/env python3
"""Test all 40 Mercosur scrapers"""
import subprocess
import sys
from pathlib import Path
from datetime import datetime

SCRAPER_DIR = Path("/opt/ACTIVE/IDEAS/MERCOSUR/CLAUDE/OPENCODE/scrapers/mercosur")
OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_test")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# All scrapers to test
SCRAPERS = [
    # Main
    ("apex_brasil_scraper.py", "--test"),
    ("connectamericas_scraper.py", "--limit 5"),
    ("brazil_exporters.py", "--quick"),
    ("gentle_runner.py", "--help"),
    
    # Working
    ("working/argentina_producers.py", "--limit 5"),
    ("working/brazil_producers.py", "--limit 5"),
    ("working/chile_producers.py", "--limit 5"),
    ("working/uruguay_producers.py", "--limit 5"),
    ("working/paraguay_producers.py", "--limit 5"),
    ("working/brazil_comex.py", "--limit 5"),
    ("working/connectamericas_web.py", "--limit 5"),
    ("working/deep_scraper.py", "--help"),
    ("working/enrich_contacts.py", "--help"),
    ("working/sector_enricher.py", "--help"),
    ("working/final_merge.py", "--help"),
    ("working/mass_scraper.py", "--help"),
    ("working/scrape_websites.py", "--help"),
    ("working/scrape_all_websites.py", "--help"),
    ("working/consolidate_all.py", "--help"),
    
    # Associations
    ("associations/abiec_beef.py", "--limit 5"),
    ("associations/abemel_honey.py", "--limit 5"),
    ("associations/ibram_mining.py", "--limit 5"),
    ("associations/ipcva_argentina.py", "--limit 5"),
    ("associations/wines_argentina.py", "--limit 5"),
    ("associations/sada_honey_ar.py", "--limit 5"),
    
    # Government
    ("government/apex_brasil.py", "--limit 5"),
    ("government/argentina_exporta.py", "--limit 5"),
    ("government/prochile.py", "--limit 5"),
    ("government/uruguay_xxi.py", "--limit 5"),
    ("government/rediex_paraguay.py", "--limit 5"),
    
    # Registries
    ("registries/brazil_cnpj.py", "--help"),
    ("registries/argentina_afip.py", "--help"),
    ("registries/chile_sii.py", "--help"),
    ("registries/uruguay_dgi.py", "--help"),
    
    # Directories
    ("directories/connectamericas.py", "--limit 5"),
    ("directories/trademap.py", "--help"),
    ("directories/kompass_latam.py", "--help"),
    ("directories/dnb_latam.py", "--help"),
    
    # Trade Shows
    ("tradeshows/apas_show.py", "--help"),
    ("tradeshows/fispal.py", "--help"),
    ("tradeshows/fenavinho.py", "--help"),
    ("tradeshows/mercoagro.py", "--help"),
    ("tradeshows/expoaladi.py", "--help"),
]

results = {"pass": [], "fail": []}

print(f"=== TESTING {len(SCRAPERS)} SCRAPERS ===\n")

for i, (scraper, args) in enumerate(SCRAPERS, 1):
    name = scraper.split("/")[-1].replace(".py", "")
    print(f"[{i:2d}/{len(SCRAPERS)}] {name}...", end=" ", flush=True)
    
    try:
        cmd = f"cd {SCRAPER_DIR} && timeout 30 python3 {scraper} {args}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=35)
        
        if result.returncode == 0:
            print("✓ PASS")
            results["pass"].append(name)
        else:
            print(f"✗ FAIL (code {result.returncode})")
            results["fail"].append((name, result.stderr[:100] if result.stderr else "unknown"))
    except subprocess.TimeoutExpired:
        print("⏱ TIMEOUT")
        results["fail"].append((name, "timeout"))
    except Exception as e:
        print(f"✗ ERROR: {e}")
        results["fail"].append((name, str(e)[:100]))

print(f"\n=== RESULTS ===")
print(f"PASSED: {len(results['pass'])}/{len(SCRAPERS)}")
print(f"FAILED: {len(results['fail'])}/{len(SCRAPERS)}")

if results["fail"]:
    print("\nFailed scrapers:")
    for name, err in results["fail"]:
        print(f"  - {name}: {err[:50]}")
