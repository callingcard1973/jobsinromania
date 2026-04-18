#!/usr/bin/env python3
"""
Agent 3: Tourism Data Collector — downloads fresh agency/hotel lists
from government open data portals weekly.

Cron: 0 6 * * 1  (Monday 6 AM)
Deploy: /opt/ACTIVE/FLIGHTS/agent_tourism_collector.py

Sources:
  - Romania SITUR (travel agencies)
  - Italy INFOTRAV (travel agencies)
  - UK CAA ATOL (tour operators)
  - Wikidata (hotels worldwide)
  - OSM Overpass (EU hotels)
"""
import os
import csv
import json
import logging
import subprocess
import requests
from datetime import datetime

WORK_DIR = "/opt/ACTIVE/FLIGHTS/TOURISM_DATA"
LOG = "/opt/ACTIVE/FLIGHTS/logs/tourism_collector.log"
DB_USER = "tudor"
DB_NAME = "interjob_master"
NODERED = "http://localhost:1880/enrichment-status"

logging.basicConfig(filename=LOG, level=logging.INFO,
                    format="%(asctime)s %(message)s")
log = logging.getLogger("collector")

SOURCES = {
    "romania_situr": {
        "url": "https://se.situr.gov.ro/OpenData/ExportToExcel?type=listaAgentii",
        "file": "romania/situr_agencies.xlsx",
        "type": "xlsx",
    },
    "italy_infotrav": {
        "url": "https://www.infotrav.it/allegati/Infotrav_elenco_agenzie.xlsx",
        "file": "italy/italy_agencies.xlsx",
        "type": "xlsx",
    },
    "uk_atol": {
        "url": "https://www.caa.co.uk/media/3ybn1oqx/historic-atolholders-combined-data-authorisation-report-2009-2025.xlsx",
        "file": "uk/uk_atol_holders.xlsx",
        "type": "xlsx",
    },
    "wikidata_hotels": {
        "url": "https://query.wikidata.org/sparql",
        "params": {
            "query": (
                "SELECT ?hotel ?hotelLabel ?countryLabel ?coord "
                "?website WHERE { ?hotel wdt:P31 wd:Q27686. "
                "?hotel wdt:P17 ?country. "
                "OPTIONAL { ?hotel wdt:P625 ?coord } "
                "OPTIONAL { ?hotel wdt:P856 ?website } "
                "SERVICE wikibase:label "
                "{ bd:serviceParam wikibase:language 'en' } "
                "} LIMIT 30000"
            ),
        },
        "headers": {"Accept": "text/csv"},
        "file": "wikidata/wikidata_hotels.csv",
        "type": "api_csv",
    },
    "osm_hotels_eu": {
        "url": "https://overpass-api.de/api/interpreter",
        "post_data": (
            '[out:csv(::id,name,"addr:street","addr:city",'
            '"addr:country",phone,website,stars,rooms;true;",")]'
            '[timeout:300];'
            'node["tourism"="hotel"]["addr:country"~'
            '"^(RO|BG|IT|ES|FR|DE|GR|HR|PT|AT|NL|BE|PL|CZ|HU|'
            'CH|TR|GB|IE|DK|SE|NO|FI)$"];out;'
        ),
        "file": "osm/osm_hotels_europe.csv",
        "type": "overpass",
    },
}


def download_file(url, dest, timeout=120):
    """Download URL to file."""
    r = requests.get(url, timeout=timeout, stream=True)
    r.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)
    return os.path.getsize(dest)


def download_source(name, cfg):
    """Download one source."""
    dest = os.path.join(WORK_DIR, cfg["file"])
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    old_size = os.path.getsize(dest) if os.path.exists(dest) else 0

    try:
        if cfg["type"] == "xlsx":
            size = download_file(cfg["url"], dest)
        elif cfg["type"] == "api_csv":
            r = requests.get(cfg["url"], params=cfg.get("params", {}),
                             headers=cfg.get("headers", {}), timeout=120)
            r.raise_for_status()
            with open(dest, "w", encoding="utf-8") as f:
                f.write(r.text)
            size = len(r.text)
        elif cfg["type"] == "overpass":
            r = requests.post(cfg["url"], data={"data": cfg["post_data"]},
                              timeout=300)
            r.raise_for_status()
            with open(dest, "w", encoding="utf-8") as f:
                f.write(r.text)
            size = len(r.text)
        else:
            log.error(f"{name}: unknown type {cfg['type']}")
            return None

        log.info(f"{name}: {size:,} bytes (was {old_size:,})")
        return {"name": name, "size": size, "old_size": old_size,
                "file": dest}
    except Exception as e:
        log.error(f"{name}: download failed: {e}")
        return None


def notify(data):
    try:
        requests.post(NODERED, json=data, timeout=5)
    except Exception:
        pass


def main():
    log.info("=== Tourism Data Collector START ===")
    print(f"Tourism Data Collector — {datetime.now()}")

    results = []
    for name, cfg in SOURCES.items():
        print(f"  Downloading {name}...")
        r = download_source(name, cfg)
        if r:
            results.append(r)
            print(f"    OK: {r['size']:,} bytes")
        else:
            print(f"    FAILED")

    log.info(f"=== DONE: {len(results)}/{len(SOURCES)} sources ===")
    print(f"\nDone: {len(results)}/{len(SOURCES)} sources downloaded")

    notify({
        "event": "tourism_collector",
        "sources_ok": len(results),
        "sources_total": len(SOURCES),
        "details": results,
        "timestamp": datetime.now().isoformat(),
    })


if __name__ == "__main__":
    main()
