#!/usr/bin/env python3
"""
Universal website email scraper — zero tokens, pure HTTP.
Takes any CSV with a website column, visits each site, extracts emails.

Usage:
  python3 scrape_emails_from_websites.py INPUT.csv --url-col website --output OUTPUT.csv
  python3 scrape_emails_from_websites.py INPUT.csv --url-col site_web --workers 40

What it extracts per site:
  - All email addresses found on homepage
  - Also checks /contact, /about, /impressum, /kontakt pages
  - Phone numbers (international format)
  - Social media links

Deploy: /opt/ACTIVE/FLIGHTS/scrape_emails_from_websites.py on raspibig
Works on any CSV: hotels, agencies, companies — anything with a URL column.
Max 250 lines (project rule).
"""
import csv
import re
import sys
import argparse
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

TIMEOUT = 8
UA = "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 Chrome/125.0"
HDRS = {"User-Agent": UA, "Accept-Language": "en,ro;q=0.8,fr;q=0.6,it;q=0.4"}

PAT_EMAIL = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PAT_PHONE = re.compile(r"(?:\+\d{1,3}[\s.-]?)?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}")
PAT_SOCIAL = re.compile(
    r'href=["\x27]([^"\x27]*(?:facebook|instagram|linkedin|youtube'
    r"|tiktok|twitter|x)\.com[^\"\x27]*)[\"\\x27]", re.I)

CONTACT_PATHS = ["", "/contact", "/about", "/impressum", "/kontakt",
                 "/contacto", "/contatti", "/nous-contacter"]
JUNK = {"wixpress.com", "sentry.io", "example.com", "email.com",
        "domain.com", "yoursite.com", "website.com", "test.com"}


def norm_url(url):
    if not url or not url.strip():
        return None
    url = url.strip().rstrip("/")
    if not url.startswith("http"):
        url = "https://" + url
    return url


def is_junk(email):
    email = email.lower()
    domain = email.split("@")[-1]
    if domain in JUNK:
        return True
    if email.startswith("noreply") or email.startswith("no-reply"):
        return True
    if ".png" in email or ".jpg" in email or ".gif" in email:
        return True
    return False


def scrape_site(url):
    """Visit homepage + contact pages, extract all emails."""
    emails = set()
    phones = set()
    socials = set()
    pages_checked = 0

    for path in CONTACT_PATHS:
        target = url.rstrip("/") + path
        try:
            r = requests.get(target, headers=HDRS, timeout=TIMEOUT,
                             allow_redirects=True)
            if not r.ok or len(r.text) < 200:
                continue
            pages_checked += 1
            # Emails
            found = PAT_EMAIL.findall(r.text)
            for e in found:
                if not is_junk(e):
                    emails.add(e.lower())
            # Phones (only from first 2 pages to avoid noise)
            if pages_checked <= 2:
                ph = PAT_PHONE.findall(r.text)
                for p in ph[:5]:
                    cleaned = re.sub(r"[\s.-]", "", p)
                    if len(cleaned) >= 8:
                        phones.add(p.strip())
            # Socials (homepage only)
            if path == "":
                soc = PAT_SOCIAL.findall(r.text)
                socials.update(s for s in soc[:5])
        except Exception:
            continue
        if len(emails) >= 5:
            break  # enough

    return {
        "emails_found": "; ".join(sorted(emails)[:10]),
        "email_count": len(emails),
        "phones_found": "; ".join(sorted(phones)[:5]),
        "socials_found": "; ".join(sorted(socials)[:5]),
        "pages_checked": pages_checked,
    }


def process_row(row, url_col):
    url = norm_url(row.get(url_col, ""))
    result = dict(row)
    result["_url_used"] = url or ""
    if not url:
        result.update({"emails_found": "", "email_count": 0,
                       "phones_found": "", "socials_found": "",
                       "pages_checked": 0, "_status": "no_url"})
        return result
    try:
        data = scrape_site(url)
        result.update(data)
        result["_status"] = "ok" if data["email_count"] > 0 else "no_email"
    except Exception as e:
        result.update({"emails_found": "", "email_count": 0,
                       "phones_found": "", "socials_found": "",
                       "pages_checked": 0, "_status": str(type(e).__name__)})
    return result


def main():
    parser = argparse.ArgumentParser(description="Scrape emails from CSV websites")
    parser.add_argument("input", help="Input CSV file")
    parser.add_argument("--url-col", default="website", help="Column with URLs")
    parser.add_argument("--output", default=None, help="Output CSV (default: input_enriched.csv)")
    parser.add_argument("--workers", type=int, default=30, help="Parallel workers")
    args = parser.parse_args()

    if not args.output:
        args.output = args.input.rsplit(".", 1)[0] + "_enriched.csv"

    csv.field_size_limit(10_000_000)
    with open(args.input, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    total = len(rows)
    print("Scraping %d sites with %d workers (url col: %s)..." % (total, args.workers, args.url_col))

    extra_fields = ["_url_used", "_status", "emails_found", "email_count",
                    "phones_found", "socials_found", "pages_checked"]
    out_fields = list(rows[0].keys()) + extra_fields if rows else extra_fields

    done = found = 0
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=out_fields, extrasaction="ignore")
        w.writeheader()
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futs = {pool.submit(process_row, row, args.url_col): row for row in rows}
            for fut in as_completed(futs):
                res = fut.result()
                w.writerow(res)
                done += 1
                if res.get("email_count", 0) > 0:
                    found += 1
                if done % 200 == 0:
                    f.flush()
                    print("  [%d/%d] %d%% | emails found: %d" % (done, total, done*100//total, found))
    print("\nDONE: %d/%d have emails -> %s" % (found, done, args.output))


if __name__ == "__main__":
    main()
