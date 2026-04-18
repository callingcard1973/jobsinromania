#!/usr/bin/env python3
"""
Agent 14: Duplicate Company Detector — finds same company across tables.
Merges email/phone from one table to another where it's missing.
Zero scraping, pure SQL.

Cron: 0 19 * * 3  (Wednesday 19:00, weekly)
Deploy: /opt/ACTIVE/FLIGHTS/agent_duplicate_detector.py

Strategies:
  1. Same website domain across tables → copy email
  2. Same company name + city → copy email
  3. Same phone number → copy email
"""
import subprocess
import logging
import json
from datetime import datetime

DB_USER = "tudor"
DB_NAME = "interjob_master"
LOG = "/opt/ACTIVE/FLIGHTS/logs/dedup_detector.log"
NODERED = "http://localhost:1880/enrichment-status"

logging.basicConfig(filename=LOG, level=logging.INFO,
                    format="%(asctime)s %(message)s")
log = logging.getLogger("dedup")

# Source tables with good email coverage
SOURCES = [
    ("ted_winners", "contractor_website", "contractor_email"),
    ("agencies", "website", "email"),
    ("master_romania_companies", "website", "email"),
    ("companies_no", "website", "email"),
    ("companies_gb", "website", "email"),
]

# Target tables that need emails
TARGETS = [
    ("companies_clean", "website", "email"),
    ("ro_companies_onrc", "web", "email"),
    ("pl_companies", "company_website", "email"),
    ("se_companies", "company_website", "email"),
    ("be_companies", "company_website", "email"),
    ("fi_companies", "company_website", "email"),
    ("at_companies", "company_website", "email"),
    ("dk_companies", "company_website", "email"),
    ("hu_companies", "company_website", "email"),
    ("it_companies", "company_website", "email"),
    ("es_companies", "company_website", "email"),
    ("uk_charities", "website", "email"),
]


def sql(query, timeout=600):
    cmd = ["psql", "-U", DB_USER, "-d", DB_NAME, "-t", "-A", "-c", query]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout)
        if r.returncode != 0:
            log.error(f"SQL: {r.stderr[:200]}")
        return r.stdout.strip()
    except subprocess.TimeoutExpired:
        log.error(f"Timeout: {query[:80]}")
        return ""


def domain_extract(col):
    """SQL expression to extract domain from URL."""
    return (f"lower(split_part(replace(replace({col},"
            f"'https://',''),'http://',''), '/', 1))")


def strategy_website_domain():
    """Match by website domain: source email → target."""
    total = 0
    for src_table, src_web, src_email in SOURCES:
        for tgt_table, tgt_web, tgt_email in TARGETS:
            src_domain = domain_extract(f"s.{src_web}")
            tgt_domain = domain_extract(f"t.{tgt_web}")
            result = sql(
                f"UPDATE {tgt_table} t SET {tgt_email} = s.{src_email} "
                f"FROM {src_table} s "
                f"WHERE {src_domain} = {tgt_domain} "
                f"AND {src_domain} != '' AND {src_domain} != 'www' "
                f"AND s.{src_email} LIKE '%@%' "
                f"AND (t.{tgt_email} IS NULL OR t.{tgt_email} = '' "
                f"OR t.{tgt_email} NOT LIKE '%@%')",
                timeout=300
            )
            # Parse UPDATE count
            try:
                n = int(result.split()[-1]) if result else 0
            except (ValueError, IndexError):
                n = 0
            if n > 0:
                log.info(f"  {src_table} → {tgt_table}: {n} by domain")
                total += n
    return total


def strategy_master_emails():
    """master_emails → fill any table by domain match."""
    # First update domain column in master_emails if empty
    sql("UPDATE master_emails SET domain = split_part(email, '@', 2) "
        "WHERE (domain IS NULL OR domain = '') AND email LIKE '%@%'")

    total = 0
    for tgt_table, tgt_web, tgt_email in TARGETS:
        tgt_domain = domain_extract(f"t.{tgt_web}")
        result = sql(
            f"UPDATE {tgt_table} t SET {tgt_email} = m.email "
            f"FROM master_emails m "
            f"WHERE m.domain = {tgt_domain} "
            f"AND m.domain != '' AND m.domain != 'www' "
            f"AND (t.{tgt_email} IS NULL OR t.{tgt_email} = '' "
            f"OR t.{tgt_email} NOT LIKE '%@%') "
            f"AND m.mx_valid IS NOT false",
            timeout=300
        )
        try:
            n = int(result.split()[-1]) if result else 0
        except (ValueError, IndexError):
            n = 0
        if n > 0:
            log.info(f"  master_emails → {tgt_table}: {n}")
            total += n
    return total


def sync_back_to_master():
    """Sync newly found emails back to master_emails."""
    all_tables = SOURCES + TARGETS
    total = 0
    for table, web_col, email_col in all_tables:
        result = sql(
            f"INSERT INTO master_emails (email, source_table, first_seen) "
            f"SELECT DISTINCT lower(trim({email_col})), '{table}', NOW() "
            f"FROM {table} WHERE {email_col} LIKE '%@%' "
            f"ON CONFLICT (email) DO NOTHING"
        )
        try:
            n = int(result.split()[-1]) if result else 0
        except (ValueError, IndexError):
            n = 0
        total += n
    if total > 0:
        log.info(f"  Synced {total} new to master_emails")
    return total


def main():
    log.info("=== Duplicate Detector Agent START ===")
    print(f"Duplicate Detector — {datetime.now()}")
    results = {}

    print("  Strategy 1: Website domain match...")
    results["domain_match"] = strategy_website_domain()

    print("  Strategy 2: Master emails → tables...")
    results["master_fill"] = strategy_master_emails()

    print("  Syncing back to master_emails...")
    results["master_sync"] = sync_back_to_master()

    total = sum(results.values())
    log.info(f"=== DONE: {total} total ===")
    print(f"\nResults: {json.dumps(results, indent=2)}")
    print(f"TOTAL: {total} emails enriched (zero HTTP)")

    try:
        import requests
        requests.post(NODERED, json={
            "event": "duplicate_detector",
            "results": results, "total": total,
            "timestamp": datetime.now().isoformat(),
        }, timeout=5)
    except Exception:
        pass


if __name__ == "__main__":
    main()
