#!/usr/bin/env python3
"""
Agent 30: WHOIS Bulk Email Extractor + Agent 27: DNS SOA Email.
Extracts admin emails from WHOIS and SOA records. Zero HTTP.

Cron: 0 3 * * *  (daily 3 AM)
Batch: 5000 domains per run, 20 workers.
"""
import csv
import subprocess
import logging
import json
import os
import socket
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

DB_USER = "tudor"
DB_NAME = "interjob_master"
WORK_DIR = "/opt/ACTIVE/FLIGHTS/enrichment"
LOG = "/opt/ACTIVE/FLIGHTS/logs/whois_soa.log"
STATE = "/opt/ACTIVE/FLIGHTS/enrichment/whois_state.json"
BATCH = 5000
WORKERS = 20

logging.basicConfig(filename=LOG, level=logging.INFO,
                    format="%(asctime)s %(message)s")
log = logging.getLogger("whois_soa")


def sql(q, timeout=600):
    cmd = ["psql", "-U", DB_USER, "-d", DB_NAME, "-t", "-A", "-c", q]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""


def sql_file(path, timeout=300):
    cmd = ["psql", "-U", DB_USER, "-d", DB_NAME, "-f", path]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def extract_domain(url):
    url = url.strip().lower()
    for p in ["https://www.", "http://www.", "https://", "http://"]:
        if url.startswith(p): url = url[len(p):]
    return url.split("/")[0].split("?")[0].strip(".")


def get_soa_email(domain):
    """Get admin email from DNS SOA record."""
    try:
        import dns.resolver
        answers = dns.resolver.resolve(domain, "SOA", lifetime=5)
        for rdata in answers:
            rname = str(rdata.rname).rstrip(".")
            # SOA rname: admin.example.com → admin@example.com
            parts = rname.split(".", 1)
            if len(parts) == 2:
                email = f"{parts[0]}@{parts[1]}"
                if "@" in email and "." in email.split("@")[1]:
                    return email
    except Exception:
        pass
    return None


def get_whois_email(domain):
    """Get registrant email from whois (command line)."""
    try:
        r = subprocess.run(["whois", domain], capture_output=True,
                           text=True, timeout=10)
        for line in r.stdout.split("\n"):
            low = line.lower()
            if "email" in low or "e-mail" in low or "contact" in low:
                parts = line.split(":")
                if len(parts) >= 2:
                    val = parts[-1].strip()
                    if "@" in val and "." in val.split("@")[1]:
                        if "abuse" not in val and "whois" not in val:
                            return val.lower()
    except Exception:
        pass
    return None


def process_domain(domain):
    """Try SOA first (fast), then WHOIS (slower)."""
    email = get_soa_email(domain)
    source = "soa"
    if not email:
        email = get_whois_email(domain)
        source = "whois"
    return {"domain": domain, "email": email, "source": source}


def load_state():
    if os.path.exists(STATE):
        with open(STATE) as f: return json.load(f)
    return {}


def save_state(state):
    with open(STATE, "w") as f:
        json.dump(state, f, indent=2, default=str)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", default="companies_clean")
    parser.add_argument("--web-col", default="website")
    args = parser.parse_args()

    os.makedirs(WORK_DIR, exist_ok=True)
    state = load_state()
    offset = state.get(f"whois_{args.table}", 0)

    log.info(f"=== WHOIS/SOA Agent START ({args.table}) ===")
    csv_path = os.path.join(WORK_DIR, f"{args.table}_whois_batch.csv")
    query = (
        f"SELECT DISTINCT split_part(replace(replace({args.web_col},"
        f"'https://',''),'http://',''),'/',1) as domain "
        f"FROM {args.table} "
        f"WHERE {args.web_col} LIKE 'http%%' "
        f"AND (email IS NULL OR email='' OR email NOT LIKE '%%@%%') "
        f"ORDER BY domain OFFSET {offset} LIMIT {BATCH}"
    )
    r = subprocess.run(
        ["psql", "-U", DB_USER, "-d", DB_NAME, "-c",
         f"\\copy ({query}) TO '{csv_path}' CSV HEADER"],
        capture_output=True, text=True, timeout=300)
    if not os.path.exists(csv_path):
        return

    with open(csv_path) as f:
        domains = [r["domain"] for r in csv.DictReader(f)
                   if r.get("domain") and "." in r["domain"]]
    if not domains:
        state[f"whois_{args.table}"] = 0
        save_state(state)
        return

    log.info(f"Checking {len(domains)} domains")
    found = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = {pool.submit(process_domain, d): d for d in domains}
        for fut in as_completed(futs):
            r = fut.result()
            if r["email"]:
                found.append(r)

    log.info(f"Found {len(found)} emails ({len(domains)} checked)")
    if found:
        import_path = os.path.join(WORK_DIR, f"{args.table}_whois_import.csv")
        with open(import_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["domain", "email", "source"])
            for r in found:
                w.writerow([r["domain"], r["email"], r["source"]])
        # Import to master_emails
        sql_path = os.path.join(WORK_DIR, f"{args.table}_whois.sql")
        with open(sql_path, "w") as f:
            f.write("DROP TABLE IF EXISTS _whois_tmp;\n")
            f.write("CREATE TABLE _whois_tmp (domain text, email text, source text);\n")
            f.write(f"\\copy _whois_tmp FROM '{import_path}' CSV HEADER\n")
            f.write("INSERT INTO master_emails (email, source_table, first_seen) "
                    f"SELECT DISTINCT email, 'whois_soa', NOW() FROM _whois_tmp "
                    "WHERE email LIKE '%@%' ON CONFLICT (email) DO NOTHING;\n")
            f.write("DROP TABLE _whois_tmp;\n")
        sql_file(sql_path)

    state[f"whois_{args.table}"] = offset + BATCH
    save_state(state)
    print(f"WHOIS/SOA: {len(found)}/{len(domains)} emails found")


if __name__ == "__main__":
    main()
