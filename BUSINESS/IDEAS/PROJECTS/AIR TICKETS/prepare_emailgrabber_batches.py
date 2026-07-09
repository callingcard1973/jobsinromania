#!/usr/bin/env python3
"""
Scan all CSVs in D:\MEMORY that have website but no email.
Extract unique URLs, count real websites, create batch .txt files
for EmailGrabber 2 (one URL per line, 10K per batch).

After EmailGrabber runs, use merge_emailgrabber_results.py to
merge emails back into original CSVs.

Usage: python3 prepare_emailgrabber_batches.py [--scan-only] [--batch-size 10000]
"""
import csv
import os
import sys
import glob
import argparse
import re
from collections import defaultdict

csv.field_size_limit(10_000_000)
BASE = "D:/MEMORY"
OUT_DIR = "D:/MEMORY/AIR TICKETS/EMAILGRABBER_INPUT"
REPORT = "D:/MEMORY/AIR TICKETS/EMAILGRABBER_INPUT/scan_report.txt"

# Columns that typically contain website URLs
WEB_NAMES = {"website", "site_web", "url", "web", "homepage",
             "company_website", "site", "www", "webpage", "link",
             "contractor_website", "website_url"}
# Skip these URL patterns (not real company websites)
SKIP_PAT = re.compile(
    r"data\.gov|europa\.eu/|download|\.pdf$|\.xlsx?$|\.csv$|"
    r"facebook\.com|linkedin\.com|twitter\.com|instagram\.com|"
    r"youtube\.com|google\.com|wikipedia|wikidata|openstreetmap",
    re.I)


def is_real_website(url):
    """Filter out data portals, social media, download links."""
    if not url or len(url) < 8:
        return False
    if SKIP_PAT.search(url):
        return False
    if not any(url.startswith(p) for p in ("http://", "https://", "www.")):
        return False
    return True


def norm(url):
    url = url.strip().split()[0].rstrip(",;\"'")
    if url.startswith("www."):
        url = "https://" + url
    return url


def find_web_col(headers):
    """Find the website column in a CSV."""
    low = {h.lower().strip(): h for h in headers}
    for name in WEB_NAMES:
        if name in low:
            return low[name]
    # Fuzzy match
    for h in headers:
        hl = h.lower()
        if "web" in hl or "site" in hl or "url" in hl or "homepage" in hl:
            return h
    return None


def find_email_col(headers):
    for h in headers:
        if "email" in h.lower() or "e-mail" in h.lower() or "mail" in h.lower():
            return h
    return None


def scan_csv(path):
    """Scan one CSV, return stats and URLs without email."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return None
            web_col = find_web_col(reader.fieldnames)
            if not web_col:
                return None
            email_col = find_email_col(reader.fieldnames)

            urls_no_email = set()
            total = has_web = has_email = 0
            for row in reader:
                total += 1
                raw_url = row.get(web_col, "").strip()
                if raw_url and is_real_website(raw_url):
                    has_web += 1
                    url = norm(raw_url)
                    has_em = False
                    if email_col and "@" in str(row.get(email_col, "")):
                        has_em = True
                        has_email += 1
                    if not has_em:
                        urls_no_email.add(url)

            if has_web < 5:
                return None
            return {
                "path": path,
                "short": path.replace(BASE + "/", "").replace(BASE + "\\", ""),
                "total": total,
                "has_web": has_web,
                "has_email": has_email,
                "gap": has_web - has_email,
                "web_col": web_col,
                "urls": urls_no_email,
            }
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan-only", action="store_true")
    parser.add_argument("--batch-size", type=int, default=10000)
    args = parser.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    csvs = glob.glob(os.path.join(BASE, "**/*.csv"), recursive=True)
    csvs = [c for c in csvs if "node_modules" not in c and ".git" not in c
            and "EMAILGRABBER" not in c]
    print(f"Scanning {len(csvs)} CSV files...")

    results = []
    all_urls = set()

    for i, path in enumerate(csvs):
        r = scan_csv(path)
        if r and r["gap"] > 0:
            results.append(r)
            all_urls.update(r["urls"])
        if (i + 1) % 100 == 0:
            print(f"  [{i+1}/{len(csvs)}] found {len(results)} with gaps, "
                  f"{len(all_urls)} unique URLs")

    results.sort(key=lambda x: x["gap"], reverse=True)

    # Report
    lines = []
    lines.append(f"{'CSV':<70} {'Total':>8} {'Web':>7} {'Email':>7} {'Gap':>7}")
    lines.append("-" * 100)
    total_gap = 0
    for r in results[:50]:
        lines.append(f"{r['short'][:69]:<70} {r['total']:>8,} {r['has_web']:>7,} "
                     f"{r['has_email']:>7,} {r['gap']:>7,}")
        total_gap += r["gap"]
    lines.append("-" * 100)
    lines.append(f"{'TOTAL (top 50)':<70} {'':>8} {'':>7} {'':>7} {total_gap:>7,}")
    lines.append(f"\nAll CSVs with gap: {len(results)}")
    lines.append(f"Total unique URLs to scrape: {len(all_urls):,}")
    report = "\n".join(lines)
    print(report)

    with open(REPORT, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nReport saved to {REPORT}")

    if args.scan_only:
        return

    # Create batch files for EmailGrabber
    url_list = sorted(all_urls)
    batch_num = 0
    for i in range(0, len(url_list), args.batch_size):
        batch_num += 1
        batch = url_list[i:i + args.batch_size]
        fname = f"batch_{batch_num:03d}_{len(batch)}urls.txt"
        with open(os.path.join(OUT_DIR, fname), "w", encoding="utf-8") as f:
            f.write("\n".join(batch))

    print(f"\nCreated {batch_num} batch files in {OUT_DIR}")
    print(f"Each batch has max {args.batch_size} URLs")
    print(f"\nHOW TO USE:")
    print(f"  1. Open EmailGrabber2.exe")
    print(f"  2. Import URL List -> select batch_001_*.txt")
    print(f"  3. Crawl depth: 2, Timeout: 10s")
    print(f"  4. Start, wait, Export CSV to EMAILGRABBER_OUTPUT/")
    print(f"  5. Repeat for each batch")


if __name__ == "__main__":
    main()
