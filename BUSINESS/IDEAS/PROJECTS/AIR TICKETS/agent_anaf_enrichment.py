#!/usr/bin/env python3
"""
Agent 12: ANAF CUI Enrichment — free government API.
Takes Romanian companies with CUI, queries ANAF for official data:
address, phone, CAEN code, active status.

Cron: 0 14 * * 1-5  (weekdays 14:00, ANAF API works business hours)
Deploy: /opt/ACTIVE/FLIGHTS/agent_anaf_enrichment.py

API: https://webservicesp.anaf.ro/AsynchWebService/api/v8/ws/tva
Batch: 500 per request (ANAF limit), 5000 per run.
"""
import csv
import json
import logging
import os
import subprocess
import time
import requests
from datetime import datetime

DB_USER = "tudor"
DB_NAME = "interjob_master"
WORK_DIR = "/opt/ACTIVE/FLIGHTS/enrichment"
LOG = "/opt/ACTIVE/FLIGHTS/logs/anaf_enrichment.log"
STATE = "/opt/ACTIVE/FLIGHTS/enrichment/anaf_state.json"
NODERED = "http://localhost:1880/enrichment-status"
ANAF_URL = "https://webservicesp.anaf.ro/AsynchWebService/api/v8/ws/tva"
BATCH_API = 500  # ANAF max per request
BATCH_TOTAL = 5000  # per run

logging.basicConfig(filename=LOG, level=logging.INFO,
                    format="%(asctime)s %(message)s")
log = logging.getLogger("anaf")


def sql(query, timeout=300):
    cmd = ["psql", "-U", DB_USER, "-d", DB_NAME, "-t", "-A", "-c", query]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""


def sql_file(path, timeout=300):
    cmd = ["psql", "-U", DB_USER, "-d", DB_NAME, "-f", path]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return r.returncode == 0


def load_state():
    if os.path.exists(STATE):
        with open(STATE) as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE, "w") as f:
        json.dump(state, f, indent=2, default=str)


def query_anaf(cuis):
    """Query ANAF API for a batch of CUIs."""
    today = datetime.now().strftime("%Y-%m-%d")
    payload = [{"cui": int(c), "data": today} for c in cuis
               if str(c).isdigit()]
    if not payload:
        return []
    try:
        r = requests.post(ANAF_URL, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data.get("found", [])
    except Exception as e:
        log.error(f"ANAF API error: {e}")
        return []


def extract_info(record):
    """Extract useful fields from ANAF response."""
    gen = record.get("date_generale", {})
    addr = record.get("adresa_sediu_social", {})
    return {
        "cui": gen.get("cui"),
        "name": gen.get("denumire", ""),
        "address": f"{addr.get('sdenumire_Strada', '')} "
                   f"{addr.get('snumar_Strada', '')}".strip(),
        "city": addr.get("sdenumire_Localitate", ""),
        "county": addr.get("sdenumire_Judet", ""),
        "phone": gen.get("telefon", ""),
        "caen": gen.get("cod_CAEN", ""),
        "active": gen.get("stare_inregistrare", "") == "INREGISTRAT",
        "tva": record.get("inregistrare_scop_Tva", {}).get(
            "scpTVA", False),
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", default="master_romania_companies")
    args = parser.parse_args()

    os.makedirs(WORK_DIR, exist_ok=True)
    log.info(f"=== ANAF Enrichment START ({args.table}) ===")
    print(f"ANAF Enrichment — {datetime.now()}")

    state = load_state()
    offset = state.get(f"anaf_{args.table}_offset", 0)

    # Get CUIs without phone (not yet enriched by ANAF)
    # Assume there's a 'cui' or 'cod_fiscal' column
    cui_col = "cui"
    result = sql(
        f"SELECT {cui_col}, id FROM {args.table} "
        f"WHERE {cui_col} IS NOT NULL AND {cui_col} != '' "
        f"AND (phone IS NULL OR phone = '') "
        f"ORDER BY id OFFSET {offset} LIMIT {BATCH_TOTAL}"
    )
    if not result:
        log.info("No CUIs to process")
        state[f"anaf_{args.table}_offset"] = 0
        save_state(state)
        return

    rows = []
    for line in result.split("\n"):
        parts = line.split("|")
        if len(parts) == 2:
            rows.append({"cui": parts[0].strip(), "id": parts[1].strip()})

    print(f"Processing {len(rows)} CUIs from offset {offset}...")
    log.info(f"Processing {len(rows)} CUIs")

    # Query ANAF in batches of 500
    all_results = []
    for i in range(0, len(rows), BATCH_API):
        batch_cuis = [r["cui"] for r in rows[i:i + BATCH_API]]
        found = query_anaf(batch_cuis)
        for rec in found:
            info = extract_info(rec)
            if info["cui"]:
                all_results.append(info)
        print(f"  Batch {i // BATCH_API + 1}: "
              f"{len(found)} results from ANAF")
        time.sleep(1)  # Rate limit

    if not all_results:
        log.info("No results from ANAF")
        state[f"anaf_{args.table}_offset"] = offset + BATCH_TOTAL
        save_state(state)
        return

    # Write import CSV
    import_path = os.path.join(WORK_DIR, f"{args.table}_anaf.csv")
    with open(import_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["cui", "phone", "caen",
                                          "address", "city", "county"])
        w.writeheader()
        for r in all_results:
            if r.get("phone"):
                w.writerow({k: r.get(k, "") for k in w.fieldnames})

    phones_found = sum(1 for r in all_results if r.get("phone"))
    log.info(f"ANAF: {len(all_results)} found, {phones_found} with phone")
    print(f"Found: {len(all_results)} companies, {phones_found} with phone")

    state[f"anaf_{args.table}_offset"] = offset + BATCH_TOTAL
    state[f"anaf_last_run"] = datetime.now().isoformat()
    state[f"anaf_last_found"] = len(all_results)
    save_state(state)

    try:
        requests.post(NODERED, json={
            "event": "anaf_enrichment",
            "table": args.table,
            "processed": len(rows),
            "found": len(all_results),
            "phones": phones_found,
            "timestamp": datetime.now().isoformat(),
        }, timeout=5)
    except Exception:
        pass

    log.info(f"=== DONE: {len(all_results)} enriched ===")


if __name__ == "__main__":
    main()
