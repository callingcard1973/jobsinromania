#!/usr/bin/env python3
"""
Agent 6: MX Validator — validates all emails in master_emails via DNS.
Marks invalid domains (no MX record) so campaigns skip them.

Cron: 0 18 * * 6  (Saturday 18:00, weekly)
Deploy: /opt/ACTIVE/FLIGHTS/agent_mx_validator.py

Batch: 50,000 per run. MX check ~0.1s each = ~80 min max.
"""
import csv
import dns.resolver
import subprocess
import logging
import json
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

DB_USER = "tudor"
DB_NAME = "interjob_master"
WORK_DIR = "/opt/ACTIVE/FLIGHTS/enrichment"
LOG = "/opt/ACTIVE/FLIGHTS/logs/mx_validator.log"
NODERED = "http://localhost:1880/enrichment-status"
BATCH = 50000
WORKERS = 30

logging.basicConfig(filename=LOG, level=logging.INFO,
                    format="%(asctime)s %(message)s")
log = logging.getLogger("mx_validator")

_mx_cache = {}


def check_mx(domain):
    if domain in _mx_cache:
        return _mx_cache[domain]
    try:
        dns.resolver.resolve(domain, "MX", lifetime=5)
        _mx_cache[domain] = True
        return True
    except Exception:
        _mx_cache[domain] = False
        return False


def sql(query, timeout=300):
    cmd = ["psql", "-U", DB_USER, "-d", DB_NAME, "-t", "-A", "-c", query]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""


def main():
    log.info("=== MX Validator Agent START ===")
    print(f"MX Validator — {datetime.now()}")

    # Ensure is_bounced column exists
    sql("ALTER TABLE master_emails ADD COLUMN IF NOT EXISTS "
        "mx_valid BOOLEAN DEFAULT NULL")

    # Get unchecked domains
    result = sql(
        "SELECT DISTINCT split_part(email, '@', 2) as domain "
        "FROM master_emails "
        "WHERE mx_valid IS NULL "
        f"LIMIT {BATCH}"
    )
    domains = [d.strip() for d in result.split("\n") if d.strip()]
    print(f"Checking {len(domains)} unique domains...")
    log.info(f"Checking {len(domains)} domains")

    # Check MX in parallel
    valid = set()
    invalid = set()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = {pool.submit(check_mx, d): d for d in domains}
        for fut in as_completed(futs):
            domain = futs[fut]
            if fut.result():
                valid.add(domain)
            else:
                invalid.add(domain)

    print(f"  Valid: {len(valid)}, Invalid: {len(invalid)}")
    log.info(f"Valid: {len(valid)}, Invalid: {len(invalid)}")

    # Update master_emails
    if valid:
        # Batch update valid domains
        domains_str = ",".join(f"'{d}'" for d in list(valid)[:5000])
        sql(f"UPDATE master_emails SET mx_valid = true "
            f"WHERE split_part(email, '@', 2) IN ({domains_str})"
            f"AND mx_valid IS NULL", timeout=600)

    if invalid:
        domains_str = ",".join(f"'{d}'" for d in list(invalid)[:5000])
        sql(f"UPDATE master_emails SET mx_valid = false "
            f"WHERE split_part(email, '@', 2) IN ({domains_str})"
            f"AND mx_valid IS NULL", timeout=600)

    total_valid = sql("SELECT count(*) FROM master_emails "
                      "WHERE mx_valid = true")
    total_invalid = sql("SELECT count(*) FROM master_emails "
                        "WHERE mx_valid = false")
    total_unchecked = sql("SELECT count(*) FROM master_emails "
                          "WHERE mx_valid IS NULL")

    print(f"\nmaster_emails: {total_valid} valid, "
          f"{total_invalid} invalid, {total_unchecked} unchecked")

    try:
        import requests
        requests.post(NODERED, json={
            "event": "mx_validator",
            "checked": len(domains),
            "valid": len(valid), "invalid": len(invalid),
            "total_valid": int(total_valid or 0),
            "total_invalid": int(total_invalid or 0),
            "timestamp": datetime.now().isoformat(),
        }, timeout=5)
    except Exception:
        pass

    log.info(f"=== DONE: {len(valid)} valid, {len(invalid)} invalid ===")


if __name__ == "__main__":
    main()
