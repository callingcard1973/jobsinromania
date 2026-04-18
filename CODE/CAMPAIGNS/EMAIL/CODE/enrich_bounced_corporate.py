#!/usr/bin/env python3
"""Read bounced corporate emails from bounces.log, check website, scrape for
contact/info/office@ emails. Save to enriched_contacts.csv.
Deploy to: /opt/ACTIVE/INFRA/SKILLS/enrich_bounced_corporate.py
"""
import csv, json, re, sys
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

import requests

BOUNCES_LOG = Path("/opt/ACTIVE/EMAIL/ORDERS/bounces.log")
OUTPUT_CSV = Path("/opt/ACTIVE/INFRA/SKILLS/enriched_contacts.csv")
STATE_FILE = Path("/opt/ACTIVE/INFRA/SKILLS/enrich_bounced_state.json")

EMAIL_RE = re.compile(
    r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', re.ASCII
)
USEFUL_PREFIXES = {"contact", "info", "office", "hr", "jobs", "recruitment",
                   "hiring", "resurseumane", "recrutare", "angajari", "personal"}
TIMEOUT = 8
MAX_PROCESS = 200  # limit per run


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"checked_domains": {}, "found": 0, "errors": 0}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_domain(email):
    return email.split("@")[1].lower() if "@" in email else ""


def is_corporate(email):
    personal = {"gmail.com", "yahoo.com", "yahoo.ro", "yahoo.fr", "hotmail.com",
                "outlook.com", "live.com", "aol.com", "mail.ru", "protonmail.com",
                "web.de", "gmx.de", "gmx.net", "icloud.com", "zoho.com",
                "hotmail.ro", "hotmail.fr", "seznam.cz", "wp.pl", "o2.pl",
                "free.fr", "orange.fr", "laposte.net", "ymail.com"}
    return extract_domain(email) not in personal


def read_bounced_emails():
    """Parse bounces.log for unique corporate email domains."""
    if not BOUNCES_LOG.exists():
        return {}
    domains = {}
    with open(BOUNCES_LOG, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) < 3:
                continue
            email = parts[2].strip()
            if is_corporate(email):
                dom = extract_domain(email)
                if dom and dom not in domains:
                    domains[dom] = email
    return domains


def check_website(domain):
    """HEAD check if website exists."""
    for proto in ["https", "http"]:
        try:
            r = requests.head(f"{proto}://{domain}/", timeout=TIMEOUT,
                              allow_redirects=True)
            if r.status_code < 400:
                return f"{proto}://{domain}/"
        except Exception:
            continue
    return None


def scrape_emails(url):
    """Scrape page for useful email addresses."""
    found = set()
    try:
        r = requests.get(url, timeout=TIMEOUT, headers={
            "User-Agent": "Mozilla/5.0 (compatible; InterJob/1.0)"
        })
        if r.status_code >= 400:
            return found
        emails = EMAIL_RE.findall(r.text)
        for e in emails:
            prefix = e.split("@")[0].lower()
            if prefix in USEFUL_PREFIXES or any(p in prefix for p in USEFUL_PREFIXES):
                found.add(e.lower())
    except Exception:
        pass

    # Also try /contact, /about pages
    for page in ["/contact", "/about", "/impressum", "/kontakt", "/about-us"]:
        try:
            r = requests.get(url.rstrip("/") + page, timeout=TIMEOUT, headers={
                "User-Agent": "Mozilla/5.0 (compatible; InterJob/1.0)"
            })
            if r.status_code < 400:
                for e in EMAIL_RE.findall(r.text):
                    prefix = e.split("@")[0].lower()
                    if prefix in USEFUL_PREFIXES or any(p in prefix for p in USEFUL_PREFIXES):
                        found.add(e.lower())
        except Exception:
            continue
    return found


def append_results(results):
    """Append found emails to CSV."""
    write_header = not OUTPUT_CSV.exists()
    fields = ["domain", "original_bounced", "found_email", "source_url", "found_at"]
    with open(OUTPUT_CSV, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            writer.writeheader()
        for r in results:
            writer.writerow(r)


def main():
    state = load_state()
    checked = state.get("checked_domains", {})
    domains = read_bounced_emails()

    new_domains = {d: e for d, e in domains.items() if d not in checked}
    print(f"Bounced corporate domains: {len(domains)}, new: {len(new_domains)}")

    results = []
    count = 0
    for domain, orig_email in list(new_domains.items())[:MAX_PROCESS]:
        count += 1
        url = check_website(domain)
        if not url:
            checked[domain] = {"status": "no_website", "at": datetime.now().isoformat()}
            continue

        emails = scrape_emails(url)
        if emails:
            for e in emails:
                results.append({
                    "domain": domain, "original_bounced": orig_email,
                    "found_email": e, "source_url": url,
                    "found_at": datetime.now().isoformat(),
                })
            checked[domain] = {"status": "found", "count": len(emails),
                               "at": datetime.now().isoformat()}
            state["found"] = state.get("found", 0) + len(emails)
            print(f"  {domain}: found {len(emails)} emails")
        else:
            checked[domain] = {"status": "no_emails", "at": datetime.now().isoformat()}

        if count % 20 == 0:
            print(f"  Processed {count}/{min(len(new_domains), MAX_PROCESS)}...")

    if results:
        append_results(results)

    state["checked_domains"] = checked
    state["last_run"] = datetime.now().isoformat()
    save_state(state)
    print(f"Done. Checked {count} domains, found {len(results)} new emails. "
          f"Output: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
