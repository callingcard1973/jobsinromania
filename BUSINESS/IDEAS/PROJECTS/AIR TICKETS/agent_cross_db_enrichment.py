#!/usr/bin/env python3
"""
Agent 5: Cross-DB Email Enrichment — zero scraping, zero HTTP.
Copies emails between DB tables by matching website domains, CUI, names.

Cron: 0 20 * * 0  (Sunday 20:00, before nightly scrapers)
Deploy: /opt/ACTIVE/FLIGHTS/agent_cross_db_enrichment.py

Strategies:
  1. Website domain match: email from table A → table B with same domain
  2. enriched_email backfill: companies.enriched_email → companies.email
  3. email_1/2/3 backfill: country tables email_1 → email
  4. Master emails → fill gaps in any table
"""
import subprocess
import logging
import json
import os
from datetime import datetime

PYTHON = "/opt/ACTIVE/INFRA/venv/bin/python3"
DB_USER = "tudor"
DB_NAME = "interjob_master"
LOG = "/opt/ACTIVE/FLIGHTS/logs/cross_db.log"
NODERED = "http://localhost:1880/enrichment-status"

logging.basicConfig(filename=LOG, level=logging.INFO,
                    format="%(asctime)s %(message)s")
log = logging.getLogger("cross_db")


def sql(query, timeout=1200):
    cmd = ["psql", "-U", DB_USER, "-d", DB_NAME, "-t", "-A", "-c", query]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout)
        if r.returncode != 0:
            log.error(f"SQL err: {r.stderr[:200]}")
        return r.stdout.strip()
    except subprocess.TimeoutExpired:
        log.error(f"SQL timeout: {query[:80]}")
        return ""


def sql_update(query, timeout=1200):
    """Run UPDATE and return rows affected."""
    result = sql(query, timeout)
    # psql -t -A returns "UPDATE N"
    try:
        return int(result.split()[-1]) if result else 0
    except (ValueError, IndexError):
        return 0


def notify(data):
    try:
        import requests
        requests.post(NODERED, json=data, timeout=5)
    except Exception:
        pass


def strategy_enriched_email():
    """companies.enriched_email → companies.email"""
    log.info("Strategy: enriched_email backfill")
    n = sql_update(
        "UPDATE companies SET email = enriched_email "
        "WHERE (email IS NULL OR email = '' OR email NOT LIKE '%@%') "
        "AND enriched_email IS NOT NULL AND enriched_email LIKE '%@%'"
    )
    log.info(f"  enriched_email → email: {n}")
    return n


def strategy_email_columns():
    """email_1/email_2/email_3 → email for country tables."""
    tables = [
        "pl_companies", "se_companies", "be_companies", "fi_companies",
        "at_companies", "dk_companies", "hu_companies", "it_companies",
        "es_companies",
    ]
    total = 0
    for t in tables:
        for col in ["email_1", "email_2", "email_3"]:
            n = sql_update(
                f"UPDATE {t} SET email = {col} "
                f"WHERE (email IS NULL OR email = '') "
                f"AND {col} IS NOT NULL AND {col} LIKE '%@%'"
            )
            if n > 0:
                log.info(f"  {t}.{col} → email: {n}")
                total += n
    return total


def strategy_master_to_tables():
    """master_emails → fill gaps in tables by website domain match."""
    targets = [
        ("companies_clean", "website", "email"),
        ("companies_no", "website", "email"),
        ("companies_gb", "website", "email"),
        ("agencies", "website", "email"),
        ("ro_companies_onrc", "web", "email"),
    ]
    total = 0
    for table, web_col, email_col in targets:
        n = sql_update(
            f"UPDATE {table} t SET {email_col} = m.email "
            f"FROM master_emails m "
            f"WHERE m.domain = split_part("
            f"replace(replace(t.{web_col},'https://',''),"
            f"'http://',''), '/', 1) "
            f"AND m.domain != '' "
            f"AND (t.{email_col} IS NULL OR t.{email_col} = '' "
            f"OR t.{email_col} NOT LIKE '%@%')"
        )
        if n > 0:
            log.info(f"  master_emails → {table}: {n}")
        total += n
    return total


def strategy_ted_to_tables():
    """ted_winners contractor_email → other tables by website domain."""
    n = sql_update(
        "UPDATE companies_clean c SET email = sub.contractor_email "
        "FROM (SELECT DISTINCT ON (split_part("
        "replace(replace(contractor_website,'https://',''),"
        "'http://',''), '/', 1)) "
        "split_part(replace(replace(contractor_website,"
        "'https://',''),'http://',''), '/', 1) as domain, "
        "contractor_email FROM ted_winners "
        "WHERE contractor_email LIKE '%@%' "
        "AND contractor_website LIKE 'http%') sub "
        "WHERE split_part(replace(replace(c.website,"
        "'https://',''),'http://',''), '/', 1) = sub.domain "
        "AND sub.domain != '' "
        "AND (c.email IS NULL OR c.email = '' "
        "OR c.email NOT LIKE '%@%') "
    )
    log.info(f"  ted_winners → companies_clean: {n}")
    return n


def update_master_emails():
    """Sync newly found emails back to master_emails."""
    tables = [
        ("companies_clean", "email"),
        ("companies_no", "email"),
        ("agencies", "email"),
        ("pl_companies", "email"),
        ("se_companies", "email"),
    ]
    total = 0
    for table, col in tables:
        n = sql_update(
            f"INSERT INTO master_emails (email, source_table, first_seen) "
            f"SELECT DISTINCT lower(trim({col})), '{table}', NOW() "
            f"FROM {table} WHERE {col} LIKE '%@%' "
            f"ON CONFLICT (email) DO NOTHING"
        )
        total += n
    log.info(f"  master_emails sync: {total} new")
    return total


def main():
    log.info("=== Cross-DB Enrichment Agent START ===")
    print(f"Cross-DB Enrichment Agent — {datetime.now()}")
    results = {}

    results["enriched_email"] = strategy_enriched_email()
    results["email_columns"] = strategy_email_columns()
    results["master_to_tables"] = strategy_master_to_tables()
    results["ted_to_tables"] = strategy_ted_to_tables()
    results["master_sync"] = update_master_emails()

    total = sum(results.values())
    log.info(f"=== DONE: {total} emails enriched ===")
    print(f"Results: {json.dumps(results, indent=2)}")
    print(f"TOTAL: {total} emails enriched (zero HTTP)")

    notify({
        "event": "cross_db_enrichment",
        "results": results,
        "total": total,
        "timestamp": datetime.now().isoformat(),
    })


if __name__ == "__main__":
    main()
