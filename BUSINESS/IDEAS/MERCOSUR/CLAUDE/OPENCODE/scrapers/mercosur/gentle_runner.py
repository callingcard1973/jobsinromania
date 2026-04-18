#!/usr/bin/env python3
"""Gentle scraper runner - runs one at a time with delays"""

import subprocess
import time
import json
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_all_sources")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SCRAPER_DIR = Path(__file__).parent

# Scrapers in priority order (most likely to work first)
SCRAPERS = [
    # Working directory has tested scrapers
    "working/connectamericas_web.py",

    # Trade shows (usually have public exhibitor lists)
    "tradeshows/apas_show.py",
    "tradeshows/fispal.py",
    "tradeshows/mercoagro.py",

    # Associations (usually have member lists)
    "associations/abiec_beef.py",
    "associations/ipcva_argentina.py",
    "associations/abemel_honey.py",

    # Government (may require different approaches)
    "government/apex_brasil.py",
    "government/prochile.py",
    "government/uruguay_xxi.py",
]

def run_scraper(scraper_path: str, timeout: int = 120) -> dict:
    """Run a single scraper with timeout"""
    full_path = SCRAPER_DIR / scraper_path

    if not full_path.exists():
        return {"status": "not_found", "path": scraper_path}

    print(f"\n{'='*50}")
    print(f"Running: {scraper_path}")
    print(f"{'='*50}")

    try:
        result = subprocess.run(
            ["python3", str(full_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(SCRAPER_DIR)
        )

        print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)

        if result.returncode == 0:
            return {"status": "success", "output": result.stdout[-500:]}
        else:
            print(f"STDERR: {result.stderr[-500:]}")
            return {"status": "error", "error": result.stderr[-500:]}

    except subprocess.TimeoutExpired:
        print(f"TIMEOUT after {timeout}s")
        return {"status": "timeout"}
    except Exception as e:
        print(f"ERROR: {e}")
        return {"status": "exception", "error": str(e)}

def main():
    print("=" * 60)
    print("MERCOSUR GENTLE SCRAPER RUNNER")
    print(f"Started: {datetime.now().isoformat()}")
    print(f"Output: {OUTPUT_DIR}")
    print("=" * 60)

    results = {}

    for i, scraper in enumerate(SCRAPERS):
        print(f"\n[{i+1}/{len(SCRAPERS)}] {scraper}")

        result = run_scraper(scraper)
        results[scraper] = result

        # Gentle delay between scrapers
        if i < len(SCRAPERS) - 1:
            print(f"\nWaiting 5 seconds before next scraper...")
            time.sleep(5)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    success = sum(1 for r in results.values() if r.get("status") == "success")
    failed = len(results) - success

    print(f"Success: {success}/{len(SCRAPERS)}")
    print(f"Failed: {failed}/{len(SCRAPERS)}")

    for scraper, result in results.items():
        status = result.get("status", "unknown")
        print(f"  {scraper}: {status}")

    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = OUTPUT_DIR / f"gentle_run_{timestamp}.json"

    with open(report_file, 'w') as f:
        json.dump({
            "run_time": datetime.now().isoformat(),
            "success": success,
            "failed": failed,
            "results": results
        }, f, indent=2)

    print(f"\nReport: {report_file}")

if __name__ == "__main__":
    main()
