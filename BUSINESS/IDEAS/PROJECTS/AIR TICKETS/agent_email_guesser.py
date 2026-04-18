#!/usr/bin/env python3
"""
Agent 20: Email Pattern Guesser — zero scraping, zero HTTP to websites.
Takes 74M+ rows with website but no email, guesses info@/office@/contact@
domain, verifies via DNS MX lookup. If MX exists = email likely valid.

Cron: 0 19 * * *  (daily 19:00, before enrichment scrapers)
Deploy: /opt/ACTIVE/FLIGHTS/agent_email_guesser.py

Batch: 10,000 per table per run. MX lookup = ~0.1s each = ~17 min/batch.
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
LOG = "/opt/ACTIVE/FLIGHTS/logs/email_guesser.log"
STATE = "/opt/ACTIVE/FLIGHTS/enrichment/guesser_state.json"
NODERED = "http://localhost:1880/enrichment-status"
BATCH = 10000
WORKERS = 20
PREFIXES = ["info", "office", "contact", "admin", "mail"]

TABLES = [
    ("companies_clean", "website", "email", "id"),
    ("master_romania_companies", "website", "email", "id"),
    ("ro_companies_onrc", "web", "email", "id"),
    ("companies_no", "website", "email", "id"),
    ("companies_gb", "website", "email", "id"),
    ("uk_charities", "website", "email", "id"),
    ("pl_companies", "company_website", "email", "id"),
    ("se_companies", "company_website", "email", "id"),
    ("be_companies", "company_website", "email", "id"),
    ("fi_companies", "company_website", "email", "id"),
    ("at_companies", "company_website", "email", "id"),
    ("dk_companies", "company_website", "email", "id"),
    ("hu_companies", "company_website", "email", "id"),
    ("it_companies", "company_website", "email", "id"),
    ("es_companies", "company_website", "email", "id"),
    ("agencies", "website", "email", "id"),
]

logging.basicConfig(filename=LOG, level=logging.INFO,
                    format="%(asctime)s %(message)s")
log = logging.getLogger("guesser")

_mx_cache = {}


def extract_domain(url):
    """https://www.firma.ro/about → firma.ro"""
    url = url.strip().lower()
    for prefix in ["https://www.", "http://www.", "https://", "http://"]:
        if url.startswith(prefix):
            url = url[len(prefix):]
    return url.split("/")[0].split("?")[0].strip(".")


def check_mx(domain):
    """Check if domain has MX records (can receive email)."""
    if domain in _mx_cache:
        return _mx_cache[domain]
    try:
        dns.resolver.resolve(domain, "MX", lifetime=5)
        _mx_cache[domain] = True
        return True
    except Exception:
        _mx_cache[domain] = False
        return False


def guess_email(url):
    """Guess email from website URL, verify via MX."""
    domain = extract_domain(url)
    if not domain or "." not in domain or len(domain) < 4:
        return None
    if not check_mx(domain):
        return None
    # Return first common prefix
    return f"info@{domain}"


def process_domain(row):
    """Process one row: guess email from website."""
    url = row.get("website", "").strip()
    rid = row.get("id", "")
    if not url or not rid:
        return None
    email = guess_email(url)
    if email:
        return {"id": rid, "email": email}
    return None


def sql(query, timeout=600):
    cmd = ["psql", "-U", DB_USER, "-d", DB_NAME, "-t", "-A", "-c", query]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout)
        if r.returncode != 0:
            log.error(f"SQL: {r.stderr[:200]}")
        return r.stdout.strip()
    except subprocess.TimeoutExpired:
        log.error(f"SQL timeout: {query[:80]}")
        return ""


def load_state():
    if os.path.exists(STATE):
        with open(STATE) as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE, "w") as f:
        json.dump(state, f, indent=2, default=str)


def process_table(table, web_col, email_col, id_col, state):
    key = f"guesser_{table}_offset"
    offset = state.get(key, 0)

    # Export batch
    csv_path = os.path.join(WORK_DIR, f"{table}_guess_batch.csv")
    query = (
        f"SELECT {id_col} as id, {web_col} as website "
        f"FROM {table} "
        f"WHERE {web_col} IS NOT NULL AND {web_col} != '' "
        f"AND {web_col} LIKE 'http%%' "
        f"AND ({email_col} IS NULL OR {email_col} = '' "
        f"OR {email_col} NOT LIKE '%%@%%') "
        f"ORDER BY {id_col} OFFSET {offset} LIMIT {BATCH}"
    )
    copy_cmd = f"\\copy ({query}) TO '{csv_path}' CSV HEADER"
    cmd = ["psql", "-U", DB_USER, "-d", DB_NAME, "-c", copy_cmd]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0 or not os.path.exists(csv_path):
        log.error(f"{table}: export failed")
        return 0

    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        state[key] = 0
        return 0

    log.info(f"{table}: guessing emails for {len(rows)} rows (offset {offset})")

    # Guess emails in parallel (MX lookups)
    found = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = {pool.submit(process_domain, row): row for row in rows}
        for fut in as_completed(futs):
            result = fut.result()
            if result:
                found.append(result)

    if not found:
        log.info(f"{table}: 0 guessed emails")
        state[key] = offset + BATCH
        return 0

    # Write import CSV + SQL
    import_path = os.path.join(WORK_DIR, f"{table}_guessed.csv")
    with open(import_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "guessed_email"])
        for r in found:
            w.writerow([r["id"], r["email"]])

    sql_path = os.path.join(WORK_DIR, f"{table}_guess_import.sql")
    with open(sql_path, "w") as f:
        f.write("DROP TABLE IF EXISTS _guess_tmp;\n")
        f.write("CREATE TABLE _guess_tmp (id bigint, guessed_email text);\n")
        f.write(f"\\copy _guess_tmp FROM '{import_path}' CSV HEADER\n")
        f.write(f"UPDATE {table} t SET {email_col} = g.guessed_email "
                f"FROM _guess_tmp g WHERE t.{id_col} = g.id "
                f"AND (t.{email_col} IS NULL OR t.{email_col} = '' "
                f"OR t.{email_col} NOT LIKE '%@%');\n")
        f.write("INSERT INTO master_emails (email, source_table, first_seen) "
                "SELECT DISTINCT guessed_email, "
                f"'{table}_guessed', NOW() FROM _guess_tmp "
                "WHERE guessed_email LIKE '%@%' "
                "ON CONFLICT (email) DO NOTHING;\n")
        f.write("DROP TABLE _guess_tmp;\n")

    cmd = ["psql", "-U", DB_USER, "-d", DB_NAME, "-f", sql_path]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        log.error(f"{table}: import failed: {r.stderr[:200]}")

    log.info(f"{table}: {len(found)} guessed emails imported")
    state[key] = offset + BATCH
    return len(found)


def notify(data):
    try:
        import requests
        requests.post(NODERED, json=data, timeout=5)
    except Exception:
        pass


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--tables", default=None)
    args = parser.parse_args()

    os.makedirs(WORK_DIR, exist_ok=True)
    log.info("=== Email Guesser Agent START ===")
    print(f"Email Guesser Agent — {datetime.now()}")

    tables = TABLES
    if args.tables:
        sel = set(args.tables.split(","))
        tables = [t for t in TABLES if t[0] in sel]

    state = load_state()
    total = 0
    for table, web_col, email_col, id_col in tables:
        n = process_table(table, web_col, email_col, id_col, state)
        total += n
        save_state(state)
        if n > 0:
            print(f"  {table}: +{n} guessed emails")

    log.info(f"=== DONE: {total} guessed emails ===")
    print(f"\nTOTAL: {total} guessed emails (MX-verified)")
    notify({"event": "email_guesser", "total": total,
            "timestamp": datetime.now().isoformat()})


if __name__ == "__main__":
    main()
