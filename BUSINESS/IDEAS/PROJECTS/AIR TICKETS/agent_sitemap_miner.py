#!/usr/bin/env python3
"""
Agent 28: Sitemap Email Miner + Agent 29: robots.txt Analyzer.
Downloads sitemap.xml, finds /contact /team /about pages, scrapes emails.

Cron: 0 4 * * *  (daily 4 AM)
Batch: 3000 sites per run, 20 workers.
"""
import csv
import re
import subprocess
import logging
import json
import os
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

DB_USER = "tudor"
DB_NAME = "interjob_master"
WORK_DIR = "/opt/ACTIVE/FLIGHTS/enrichment"
LOG = "/opt/ACTIVE/FLIGHTS/logs/sitemap_miner.log"
STATE = "/opt/ACTIVE/FLIGHTS/enrichment/sitemap_state.json"
BATCH = 3000
WORKERS = 20
TIMEOUT = 8
UA = "Mozilla/5.0 (compatible; InterJobBot/1.0)"
HDRS = {"User-Agent": UA}

PAT_EMAIL = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
CONTACT_PATTERNS = re.compile(
    r"contact|about|team|staff|impressum|kontakt|equipe|chi-siamo|"
    r"quienes|nous-contacter|ueber-uns|o-nas|kapcsolat", re.I)
JUNK_DOMAINS = {"wixpress.com", "sentry.io", "example.com",
                "googleapis.com", "w3.org", "schema.org"}

logging.basicConfig(filename=LOG, level=logging.INFO,
                    format="%(asctime)s %(message)s")
log = logging.getLogger("sitemap")


def sql_file(path, timeout=300):
    cmd = ["psql", "-U", DB_USER, "-d", DB_NAME, "-f", path]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def get_sitemap_urls(base_url):
    """Get contact-like URLs from sitemap.xml or robots.txt."""
    urls = set()
    # Try robots.txt first
    try:
        r = requests.get(f"{base_url}/robots.txt", headers=HDRS, timeout=5)
        if r.ok:
            for line in r.text.split("\n"):
                if line.lower().startswith("sitemap:"):
                    sm_url = line.split(":", 1)[1].strip()
                    try:
                        sr = requests.get(sm_url, headers=HDRS, timeout=8)
                        if sr.ok:
                            locs = re.findall(r"<loc>([^<]+)</loc>", sr.text)
                            for loc in locs:
                                if CONTACT_PATTERNS.search(loc):
                                    urls.add(loc)
                    except Exception:
                        pass
    except Exception:
        pass
    # Try direct sitemap.xml
    if not urls:
        try:
            r = requests.get(f"{base_url}/sitemap.xml",
                             headers=HDRS, timeout=8)
            if r.ok and "<loc>" in r.text:
                locs = re.findall(r"<loc>([^<]+)</loc>", r.text)
                for loc in locs:
                    if CONTACT_PATTERNS.search(loc):
                        urls.add(loc)
        except Exception:
            pass
    return list(urls)[:5]  # max 5 contact pages


def scrape_page_emails(url):
    """Scrape one URL for emails."""
    try:
        r = requests.get(url, headers=HDRS, timeout=TIMEOUT)
        if r.ok:
            emails = set()
            for e in PAT_EMAIL.findall(r.text):
                e = e.lower()
                domain = e.split("@")[1]
                if domain not in JUNK_DOMAINS:
                    emails.add(e)
            return emails
    except Exception:
        pass
    return set()


def process_site(row):
    """Process one website: sitemap → contact pages → emails."""
    url = row.get("website", "").strip()
    rid = row.get("id", "")
    if not url:
        return None
    base = url.rstrip("/")
    if not base.startswith("http"):
        base = "https://" + base

    all_emails = set()
    # Get contact pages from sitemap
    contact_urls = get_sitemap_urls(base)
    for cu in contact_urls:
        emails = scrape_page_emails(cu)
        all_emails.update(emails)
        if len(all_emails) >= 3:
            break

    if all_emails:
        return {"id": rid, "emails": "; ".join(sorted(all_emails)[:5]),
                "first": sorted(all_emails)[0]}
    return None


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
    offset = state.get(f"sitemap_{args.table}", 0)

    log.info(f"=== Sitemap Miner START ({args.table}) ===")
    csv_path = os.path.join(WORK_DIR, f"{args.table}_sitemap_batch.csv")
    query = (
        f"SELECT id, {args.web_col} as website FROM {args.table} "
        f"WHERE {args.web_col} LIKE 'http%%' "
        f"AND (email IS NULL OR email='' OR email NOT LIKE '%%@%%') "
        f"ORDER BY id OFFSET {offset} LIMIT {BATCH}"
    )
    r = subprocess.run(
        ["psql", "-U", DB_USER, "-d", DB_NAME, "-c",
         f"\\copy ({query}) TO '{csv_path}' CSV HEADER"],
        capture_output=True, text=True, timeout=300)

    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        state[f"sitemap_{args.table}"] = 0
        save_state(state)
        return

    log.info(f"Mining sitemaps for {len(rows)} sites")
    found = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = {pool.submit(process_site, r): r for r in rows}
        for fut in as_completed(futs):
            r = fut.result()
            if r:
                found.append(r)

    log.info(f"Found {len(found)} sites with emails")
    if found:
        import_path = os.path.join(WORK_DIR, f"{args.table}_sitemap_import.csv")
        with open(import_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "email"])
            for r in found:
                w.writerow([r["id"], r["first"]])
        sql_path = os.path.join(WORK_DIR, f"{args.table}_sitemap.sql")
        with open(sql_path, "w") as f:
            f.write("DROP TABLE IF EXISTS _sitemap_tmp;\n")
            f.write("CREATE TABLE _sitemap_tmp (id bigint, email text);\n")
            f.write(f"\\copy _sitemap_tmp FROM '{import_path}' CSV HEADER\n")
            f.write(f"UPDATE {args.table} t SET email = s.email "
                    f"FROM _sitemap_tmp s WHERE t.id = s.id "
                    f"AND (t.email IS NULL OR t.email='' "
                    f"OR t.email NOT LIKE '%@%');\n")
            f.write("INSERT INTO master_emails (email, source_table, first_seen) "
                    "SELECT DISTINCT email, 'sitemap_miner', NOW() "
                    "FROM _sitemap_tmp WHERE email LIKE '%@%' "
                    "ON CONFLICT (email) DO NOTHING;\n")
            f.write("DROP TABLE _sitemap_tmp;\n")
        sql_file(sql_path)

    state[f"sitemap_{args.table}"] = offset + BATCH
    save_state(state)
    print(f"Sitemap Miner: {len(found)}/{len(rows)} sites had emails")


if __name__ == "__main__":
    main()
