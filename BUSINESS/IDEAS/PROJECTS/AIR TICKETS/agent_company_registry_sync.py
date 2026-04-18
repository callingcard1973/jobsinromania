#!/usr/bin/env python3
"""
Agent 32+33: EU OpenData + Company Registry Sync.
Downloads fresh data from free government APIs weekly.

Cron: 0 5 * * 2  (Tuesday 5 AM)

Sources:
  - UK Companies House (free API, 500 calls/day)
  - Norway Brreg (free, no key)
  - Latvia UR (free, no key)
  - EU OpenData portal
"""
import csv
import json
import logging
import os
import requests
from datetime import datetime

WORK_DIR = "/opt/ACTIVE/FLIGHTS/TOURISM_DATA/registries"
LOG = "/opt/ACTIVE/FLIGHTS/logs/registry_sync.log"
NODERED = "http://localhost:1880/enrichment-status"

logging.basicConfig(filename=LOG, level=logging.INFO,
                    format="%(asctime)s %(message)s")
log = logging.getLogger("registry")

SOURCES = {
    "norway_brreg": {
        "url": "https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv",
        "file": "norway_brreg_latest.csv",
        "desc": "Norway business register (all companies)",
    },
    "latvia_ur": {
        "url": "https://data.gov.lv/dati/dataset/uznemumu-registra-subjektu-dati",
        "file": "latvia_ur_page.html",
        "desc": "Latvia company register (need to find CSV link)",
        "type": "page",
    },
    "uk_charities_opendata": {
        "url": "https://ccew.org.uk/charity-details-summary.zip",
        "file": "uk_charities_summary.zip",
        "desc": "UK Charity Commission open data",
    },
    "eu_opendata_companies": {
        "url": "https://data.europa.eu/api/hub/search/datasets?q=company+register&limit=20&format=csv",
        "file": "eu_opendata_search.json",
        "desc": "EU open data portal search for company registers",
        "type": "json",
    },
}


def download(url, dest, timeout=120):
    try:
        r = requests.get(url, timeout=timeout, stream=True,
                         headers={"User-Agent": "InterJobBot/1.0"})
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return os.path.getsize(dest)
    except Exception as e:
        log.error(f"Download failed {url}: {e}")
        return 0


def main():
    os.makedirs(WORK_DIR, exist_ok=True)
    log.info("=== Registry Sync START ===")
    print(f"Registry Sync — {datetime.now()}")

    results = []
    for name, cfg in SOURCES.items():
        dest = os.path.join(WORK_DIR, cfg["file"])
        old_size = os.path.getsize(dest) if os.path.exists(dest) else 0
        print(f"  {name}: downloading...")
        size = download(cfg["url"], dest)
        if size > 0:
            results.append({"name": name, "size": size,
                            "old": old_size, "file": dest})
            print(f"    OK: {size:,} bytes")
        else:
            print(f"    FAILED")

    log.info(f"=== DONE: {len(results)}/{len(SOURCES)} ===")
    print(f"\nDone: {len(results)}/{len(SOURCES)}")

    try:
        requests.post(NODERED, json={
            "event": "registry_sync",
            "ok": len(results), "total": len(SOURCES),
            "timestamp": datetime.now().isoformat(),
        }, timeout=5)
    except Exception:
        pass


if __name__ == "__main__":
    main()
