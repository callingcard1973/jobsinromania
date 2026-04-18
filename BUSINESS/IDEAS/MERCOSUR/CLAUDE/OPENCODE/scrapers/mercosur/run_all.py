#!/usr/bin/env python3
"""Master runner for all Mercosur data source scrapers"""

import sys
import json
import importlib.util
from pathlib import Path
from datetime import datetime

SCRAPER_DIR = Path(__file__).parent
OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_all_sources")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# All scrapers organized by category
SCRAPERS = {
    "government": [
        "government/apex_brasil.py",
        "government/argentina_exporta.py",
        "government/prochile.py",
        "government/uruguay_xxi.py",
        "government/rediex_paraguay.py",
    ],
    "directories": [
        "directories/connectamericas.py",
        "directories/trademap.py",
        "directories/kompass_latam.py",
        "directories/dnb_latam.py",
    ],
    "associations": [
        "associations/abiec_beef.py",
        "associations/ipcva_argentina.py",
        "associations/abemel_honey.py",
        "associations/ibram_mining.py",
        "associations/wines_argentina.py",
        "associations/sada_honey_ar.py",
    ],
    "registries": [
        "registries/brazil_cnpj.py",
        "registries/argentina_afip.py",
        "registries/chile_sii.py",
        "registries/uruguay_dgi.py",
    ],
    "tradeshows": [
        "tradeshows/apas_show.py",
        "tradeshows/fispal.py",
        "tradeshows/fenavinho.py",
        "tradeshows/mercoagro.py",
        "tradeshows/expoaladi.py",
    ]
}

def run_scraper(scraper_path: str) -> dict:
    """Run a single scraper and return results"""
    full_path = SCRAPER_DIR / scraper_path

    if not full_path.exists():
        print(f"  [SKIP] {scraper_path} not found")
        return {"status": "not_found", "records": 0}

    try:
        # Load module dynamically
        spec = importlib.util.spec_from_file_location("scraper", full_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Run main function
        if hasattr(module, 'main'):
            result = module.main()
            records = len(result) if isinstance(result, list) else 0
            return {"status": "success", "records": records}
        else:
            print(f"  [SKIP] {scraper_path} has no main()")
            return {"status": "no_main", "records": 0}

    except Exception as e:
        print(f"  [ERROR] {scraper_path}: {e}")
        return {"status": "error", "error": str(e), "records": 0}

def run_category(category: str) -> dict:
    """Run all scrapers in a category"""
    print(f"\n=== Running {category.upper()} scrapers ===")

    results = {}
    for scraper in SCRAPERS.get(category, []):
        print(f"\nRunning {scraper}...")
        results[scraper] = run_scraper(scraper)

    return results

def run_all() -> dict:
    """Run all scrapers"""
    print("=" * 60)
    print("MERCOSUR DATA SOURCE SCRAPER - MASTER RUN")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)

    all_results = {}
    total_records = 0

    for category in SCRAPERS.keys():
        results = run_category(category)
        all_results[category] = results

        for scraper, result in results.items():
            total_records += result.get("records", 0)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for category, results in all_results.items():
        print(f"\n{category.upper()}:")
        for scraper, result in results.items():
            status = result.get("status", "unknown")
            records = result.get("records", 0)
            print(f"  {scraper}: {status} ({records} records)")

    print(f"\nTOTAL RECORDS: {total_records}")
    print(f"Finished: {datetime.now().isoformat()}")

    # Save run report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = OUTPUT_DIR / f"scraper_run_{timestamp}.json"

    report = {
        "run_time": datetime.now().isoformat(),
        "total_records": total_records,
        "results": all_results
    }

    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\nReport saved to: {report_file}")

    return all_results

def main():
    """CLI entry point"""
    if len(sys.argv) > 1:
        category = sys.argv[1]
        if category in SCRAPERS:
            run_category(category)
        elif category == "list":
            print("Available categories:")
            for cat, scrapers in SCRAPERS.items():
                print(f"\n{cat}:")
                for s in scrapers:
                    print(f"  - {s}")
        else:
            print(f"Unknown category: {category}")
            print("Usage: run_all.py [category|list|all]")
    else:
        run_all()

if __name__ == "__main__":
    main()
