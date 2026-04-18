#!/usr/bin/env python3
"""
Agent 17: TED New Contracts Enricher — takes new TED winners,
extracts email+website, pushes to master_emails and fills gaps
in other tables.

Cron: 0 9 * * *  (daily 9 AM, after ted_scraper runs at 7:30)
Deploy: /opt/ACTIVE/FLIGHTS/agent_ted_enricher.py
"""
import subprocess
import logging
import json
from datetime import datetime, timedelta

DB_USER = "tudor"
DB_NAME = "interjob_master"
LOG = "/opt/ACTIVE/FLIGHTS/logs/ted_enricher.log"
NODERED = "http://localhost:1880/enrichment-status"

logging.basicConfig(filename=LOG, level=logging.INFO,
                    format="%(asctime)s %(message)s")
log = logging.getLogger("ted_enricher")


def sql(query, timeout=300):
    cmd = ["psql", "-U", DB_USER, "-d", DB_NAME, "-t", "-A", "-c", query]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout)
        if r.returncode != 0:
            log.error(f"SQL: {r.stderr[:200]}")
        return r.stdout.strip()
    except Exception:
        return ""


def sync_ted_to_master():
    """New TED emails → master_emails."""
    result = sql(
        "INSERT INTO master_emails (email, source_table, first_seen) "
        "SELECT DISTINCT lower(trim(contractor_email)), 'ted_winners', NOW() "
        "FROM ted_winners "
        "WHERE contractor_email LIKE '%@%' "
        "ON CONFLICT (email) DO NOTHING"
    )
    try:
        return int(result.split()[-1]) if result else 0
    except (ValueError, IndexError):
        return 0


def update_domain_in_master():
    """Fill domain column in master_emails."""
    sql("UPDATE master_emails SET domain = split_part(email, '@', 2) "
        "WHERE (domain IS NULL OR domain = '') AND email LIKE '%@%'")


def ted_to_companies_clean():
    """TED contractor email → companies_clean by website domain."""
    result = sql(
        "UPDATE companies_clean c "
        "SET email = sub.contractor_email "
        "FROM ("
        "  SELECT DISTINCT ON (lower(split_part(replace(replace("
        "    contractor_website,'https://',''),'http://',''),'/',1))) "
        "  lower(split_part(replace(replace(contractor_website,"
        "    'https://',''),'http://',''),'/',1)) as domain, "
        "  contractor_email "
        "  FROM ted_winners WHERE contractor_email LIKE '%@%' "
        "  AND contractor_website LIKE 'http%'"
        ") sub "
        "WHERE lower(split_part(replace(replace(c.website,"
        "  'https://',''),'http://',''),'/',1)) = sub.domain "
        "AND sub.domain != '' AND length(sub.domain) > 3 "
        "AND (c.email IS NULL OR c.email = '' "
        "OR c.email NOT LIKE '%@%')",
        timeout=600
    )
    try:
        return int(result.split()[-1]) if result else 0
    except (ValueError, IndexError):
        return 0


def ted_to_country_tables():
    """TED emails → country company tables via master_emails domain."""
    targets = [
        ("pl_companies", "company_website"),
        ("se_companies", "company_website"),
        ("be_companies", "company_website"),
        ("at_companies", "company_website"),
        ("dk_companies", "company_website"),
        ("it_companies", "company_website"),
        ("es_companies", "company_website"),
    ]
    total = 0
    for table, web_col in targets:
        result = sql(
            f"UPDATE {table} t SET email = m.email "
            f"FROM master_emails m "
            f"WHERE m.domain = lower(split_part(replace(replace("
            f"t.{web_col},'https://',''),'http://',''),'/',1)) "
            f"AND m.domain != '' AND length(m.domain) > 3 "
            f"AND (t.email IS NULL OR t.email = '' "
            f"OR t.email NOT LIKE '%@%') "
            f"AND m.mx_valid IS NOT false",
            timeout=120
        )
        try:
            n = int(result.split()[-1]) if result else 0
        except (ValueError, IndexError):
            n = 0
        if n > 0:
            log.info(f"  master → {table}: {n}")
        total += n
    return total


def count_recent():
    """Count TED entries from last 7 days."""
    week = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    return sql(
        f"SELECT count(*) FROM ted_winners "
        f"WHERE created_at >= '{week}'"
    )


def main():
    log.info("=== TED Enricher START ===")
    print(f"TED Enricher — {datetime.now()}")
    results = {}

    recent = count_recent()
    print(f"TED winners last 7 days: {recent}")

    print("  Syncing TED → master_emails...")
    results["ted_to_master"] = sync_ted_to_master()

    print("  Updating domains...")
    update_domain_in_master()

    print("  TED → companies_clean...")
    results["ted_to_clean"] = ted_to_companies_clean()

    print("  Master → country tables...")
    results["to_countries"] = ted_to_country_tables()

    total = sum(results.values())
    log.info(f"=== DONE: {total} ===")
    print(f"\nResults: {json.dumps(results, indent=2)}")
    print(f"TOTAL: {total}")

    try:
        import requests
        requests.post(NODERED, json={
            "event": "ted_enricher",
            "results": results, "total": total,
            "recent_ted": recent,
            "timestamp": datetime.now().isoformat(),
        }, timeout=5)
    except Exception:
        pass


if __name__ == "__main__":
    main()
