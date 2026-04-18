#!/usr/bin/env python3
"""
Automated Email Enrichment Pipeline — runs on cron, zero tokens.
Finds companies/hotels/agencies WITH website but WITHOUT email in PostgreSQL,
scrapes their websites for emails, updates the DB.

Cron: 0 2 * * 0  (weekly Sunday 2 AM — off-peak)
Deploy: /opt/ACTIVE/FLIGHTS/email_enrichment_pipeline.py

Pipeline:
  1. Query DB tables for rows with website but no email
  2. Export to temp CSV (batch of 5000)
  3. Run scrape_emails_from_websites.py on batch
  4. Import scraped emails back to DB
  5. Log results, repeat for next table
"""
import os
import sys
import csv
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path

PYTHON = "/opt/ACTIVE/INFRA/venv/bin/python3"
SCRAPER = "/opt/ACTIVE/FLIGHTS/scrape_emails_from_websites.py"
WORK_DIR = "/opt/ACTIVE/FLIGHTS/enrichment"
LOG_FILE = "/opt/ACTIVE/FLIGHTS/logs/enrichment.log"
STATE_FILE = "/opt/ACTIVE/FLIGHTS/enrichment/state.json"
BATCH_SIZE = 5000
MAX_WORKERS = 20  # conservative to not overload raspibig

DB_HOST = "localhost"
DB_NAME = "interjob_master"
DB_USER = "tudor"

# Tables to enrich: (table, website_col, email_col, id_col)
TABLES = [
    ("master_romania_companies", "website", "email", "id"),
    ("ro_companies_onrc", "web", "email", "id"),
    ("companies_clean", "website", "email", "id"),
    ("ted_winners", "contractor_website", "contractor_email", "id"),
    ("contacts", "website", "email", "id"),
    ("agencies", "website", "email", "id"),
    ("companies_no", "website", "email", "id"),
    ("companies_gb", "website", "email", "id"),
    ("pl_companies", "company_website", "email", "id"),
    ("se_companies", "company_website", "email", "id"),
    ("ch_companies", "website", "email", "id"),
    ("no_companies_full", "website", "email", "id"),
    ("bg_business_catalog", "website", "email", "id"),
    ("at_companies", "company_website", "email", "id"),
    ("dk_companies", "company_website", "email", "id"),
    ("hu_companies", "company_website", "email", "id"),
    ("it_companies", "company_website", "email", "id"),
    ("es_companies", "company_website", "email", "id"),
    ("fi_companies", "company_website", "email", "id"),
    ("be_companies", "company_website", "email", "id"),
    ("uk_charities", "website", "email", "id"),
    ("flight_agencies_campaign", "site_web", "email", "id"),
]

logging.basicConfig(
    filename=LOG_FILE, level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
log = logging.getLogger("enrichment")

NODERED_URL = "http://localhost:1880/enrichment-status"


def notify_nodered(data):
    """Post status update to Node-RED dashboard."""
    try:
        import requests as req
        req.post(NODERED_URL, json=data, timeout=5)
    except Exception:
        pass


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


def run_sql(sql, timeout=600):
    """Run SQL via psql, return output."""
    cmd = ["psql", "-U", DB_USER, "-d", DB_NAME, "-t", "-A", "-c", sql]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            log.error(f"SQL error [{r.returncode}]: {r.stderr.strip()[:200]}")
        return r.stdout.strip()
    except subprocess.TimeoutExpired:
        log.error(f"SQL timeout ({timeout}s): {sql[:100]}")
        return ""


def run_psql_copy(copy_cmd):
    """Run \\copy via psql (client-side, no superuser needed)."""
    cmd = ["psql", "-U", DB_USER, "-d", DB_NAME, "-c", copy_cmd]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        log.error(f"\\copy error: {r.stderr.strip()}")
        return False
    return True


def export_batch(table, web_col, email_col, id_col, offset=0):
    """Export rows with website but no email to CSV using \\copy."""
    validate_identifier(table)
    validate_identifier(web_col)
    validate_identifier(email_col)
    validate_identifier(id_col)
    csv_path = os.path.join(WORK_DIR, f"{table}_batch.csv")
    query = (
        f"SELECT {id_col}, {web_col} AS website "
        f"FROM {table} "
        f"WHERE {web_col} IS NOT NULL AND {web_col} != '' "
        f"AND {web_col} LIKE 'http%%' "
        f"AND ({email_col} IS NULL OR {email_col} = '' "
        f"OR {email_col} NOT LIKE '%%@%%') "
        f"ORDER BY {id_col} "
        f"OFFSET {offset} LIMIT {BATCH_SIZE}"
    )
    copy_cmd = f"\\copy ({query}) TO '{csv_path}' CSV HEADER"
    try:
        ok = run_psql_copy(copy_cmd)
        if ok and os.path.exists(csv_path):
            with open(csv_path) as f:
                count = sum(1 for _ in f) - 1
            log.info(f"Exported {count} rows from {table} to {csv_path}")
            return csv_path, count
        else:
            log.error(f"Export failed for {table}, file not created")
    except Exception as e:
        log.error(f"Export failed {table}: {e}")
    return None, 0


def scrape_batch(csv_path, output_path):
    """Run the email scraper on a batch CSV."""
    cmd = [
        PYTHON, SCRAPER,
        csv_path,
        "--url-col", "website",
        "--workers", str(MAX_WORKERS),
        "--output", output_path,
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        log.info(f"Scraper output: {r.stdout[-200:]}")
        return r.returncode == 0
    except Exception as e:
        log.error(f"Scraper failed: {e}")
        return False


def validate_identifier(name):
    """Validate SQL identifier (table/column name) to prevent injection."""
    import re as _re
    if not _re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
        raise ValueError(f"Invalid SQL identifier: {name}")
    return name


def import_results(table, email_col, id_col, output_path):
    """Import scraped emails back to DB via SQL file (single psql session)."""
    updated = 0
    try:
        csv.field_size_limit(10_000_000)
        with open(output_path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        # Write only rows with emails to a clean import CSV
        import_path = output_path.replace(".csv", "_import.csv")
        with open(import_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "scraped_email"])
            for row in rows:
                emails = row.get("emails_found", "").strip()
                if not emails or "@" not in emails:
                    continue
                email = emails.split(";")[0].strip().replace("'", "")
                rid = row.get("id", "").strip()
                if rid and email:
                    w.writerow([rid, email])
                    updated += 1

        if updated == 0:
            log.info(f"{table}: no emails to import")
            return 0

        # Validate identifiers
        validate_identifier(table)
        validate_identifier(email_col)
        validate_identifier(id_col)

        # Write SQL file — single psql session so temp table persists
        sql_path = os.path.join(WORK_DIR, f"{table}_import.sql")
        with open(sql_path, "w") as f:
            f.write("DROP TABLE IF EXISTS _email_import_tmp;\n")
            f.write("CREATE TABLE _email_import_tmp "
                    "(id bigint, scraped_email text);\n")
            f.write(f"\\copy _email_import_tmp FROM "
                    f"'{import_path}' CSV HEADER\n")
            f.write(f"UPDATE {table} t SET {email_col} = i.scraped_email "
                    f"FROM _email_import_tmp i WHERE t.{id_col} = i.id "
                    f"AND (t.{email_col} IS NULL OR t.{email_col} = '' "
                    f"OR t.{email_col} NOT LIKE '%@%');\n")
            # Also insert into master_emails (dedup)
            f.write("INSERT INTO master_emails (email, source_table, "
                    "first_seen) SELECT DISTINCT scraped_email, "
                    f"'{table}', NOW() FROM _email_import_tmp "
                    "WHERE scraped_email LIKE '%@%' "
                    "ON CONFLICT (email) DO NOTHING;\n")
            f.write("DROP TABLE _email_import_tmp;\n")

        cmd = ["psql", "-U", DB_USER, "-d", DB_NAME, "-f", sql_path]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            log.error(f"Import SQL failed: {r.stderr[:300]}")
        else:
            log.info(f"{table}: imported {updated} emails, "
                     f"psql output: {r.stdout.strip()[-200:]}")

    except Exception as e:
        log.error(f"Import failed {table}: {e}")
    return updated


def count_gap(table, web_col, email_col):
    """Count rows with website but no email."""
    sql = (
        f"SELECT count(*) FROM {table} "
        f"WHERE {web_col} IS NOT NULL AND {web_col} != '' "
        f"AND {web_col} LIKE 'http%%' "
        f"AND ({email_col} IS NULL OR {email_col} = '' "
        f"OR {email_col} NOT LIKE '%%@%%')"
    )
    result = run_sql(sql, timeout=1200)
    try:
        return int(result)
    except (ValueError, TypeError):
        log.error(f"count_gap failed for {table}: got '{result}'")
        return -1


def process_table(table, web_col, email_col, id_col, state):
    """Process one table: export, scrape, import."""
    key = f"{table}_offset"
    offset = state.get(key, 0)

    gap = count_gap(table, web_col, email_col)
    if gap <= 0:
        log.info(f"{table}: no gap (gap={gap}), skipping")
        state[key] = 0
        return 0

    log.info(f"{table}: {gap} rows with website, no email. Offset={offset}")
    print(f"  {table}: {gap} gap, offset {offset}")

    csv_path, count = export_batch(table, web_col, email_col, id_col, offset)
    if not csv_path or count == 0:
        log.info(f"{table}: no more rows at offset {offset}, resetting")
        state[key] = 0
        return 0

    output_path = os.path.join(WORK_DIR, f"{table}_enriched.csv")
    log.info(f"{table}: scraping {count} websites...")
    print(f"  Scraping {count} websites from {table}...")

    if not scrape_batch(csv_path, output_path):
        log.error(f"{table}: scraper failed")
        return 0

    updated = import_results(table, email_col, id_col, output_path)
    log.info(f"{table}: updated {updated} emails")
    print(f"  Updated {updated} emails in {table}")

    state[key] = offset + BATCH_SIZE
    state[f"{table}_last_run"] = datetime.now().isoformat()
    state[f"{table}_last_updated"] = updated

    notify_nodered({
        "table": table,
        "gap": gap,
        "scraped": count,
        "emails_added": updated,
        "offset": offset + BATCH_SIZE,
        "timestamp": datetime.now().isoformat(),
    })
    return updated


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--tables", default=None,
                        help="Comma-separated table names to process (default: all)")
    args = parser.parse_args()

    os.makedirs(WORK_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    # Filter tables if --tables specified
    tables_to_run = TABLES
    if args.tables:
        selected = set(args.tables.split(","))
        tables_to_run = [t for t in TABLES if t[0] in selected]

    log.info(f"=== Email Enrichment Pipeline START ({len(tables_to_run)} tables) ===")
    print(f"Email Enrichment Pipeline — {datetime.now()}")
    print(f"Tables: {len(tables_to_run)}, batch size: {BATCH_SIZE}")

    state = load_state()
    total_updated = 0

    for table, web_col, email_col, id_col in tables_to_run:
        try:
            updated = process_table(table, web_col, email_col, id_col, state)
            total_updated += updated
            save_state(state)
        except Exception as e:
            log.error(f"{table}: {e}")
            print(f"  ERROR {table}: {e}")

    log.info(f"=== Pipeline DONE: {total_updated} emails added ===")
    print(f"\nDONE: {total_updated} new emails added across all tables")
    save_state(state)

    notify_nodered({
        "event": "pipeline_complete",
        "tables_processed": len(tables_to_run),
        "total_emails_added": total_updated,
        "timestamp": datetime.now().isoformat(),
    })


if __name__ == "__main__":
    main()
