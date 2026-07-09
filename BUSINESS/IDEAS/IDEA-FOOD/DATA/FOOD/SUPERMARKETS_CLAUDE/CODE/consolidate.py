#!/usr/bin/env python3
"""Consolidate all Romania food distribution contacts into one CSV.

Reads all DATA/ CSVs + masterdb extract, deduplicates by email,
categorizes by sector, outputs standardized CSV.

Usage:
    python consolidate.py                    # Run consolidation
    python consolidate.py --stats            # Show stats only
    python consolidate.py --output out.csv   # Custom output path
"""

import csv
import os
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_DIR, "DATA")
DEFAULT_OUTPUT = os.path.join(DATA_DIR, "ROMANIA_FOOD_DISTRIBUTION_CONTACTS.csv")

# -- Output columns
OUT_COLS = [
    "company", "cui", "county", "city", "address", "phone", "email",
    "website", "category", "subcategory", "source"
]

# -- Source files and their default category
SOURCE_MAP = {
    "SUPERMARKETS_RO.csv": "supermarket",
    "DISTRIBUTORS_RO.csv": "distributor",
    "COLD_STORAGE_RO.csv": "cold-storage",
    "MEAT_PROCESSORS_RO.csv": "meat",
    "DAIRY_RO.csv": "dairy",
    "LOGISTICS_RO.csv": "logistics",
    "HORECA_RO.csv": "horeca",
    "ALL_SUPERMARKET_CHAINS.csv": "supermarket",
    "WHOLESALE_EUROPE.csv": "en-gros",
    "MASTER_CLEAN.csv": "other",
    "masterdb_food_companies.csv": "masterdb",
}

# -- Category detection from activity/category/subcategory fields
CATEGORY_RULES = [
    (r"supermarket|magazin|comert.*amanunt|retail", "supermarket"),
    (r"en.?gros|wholesale|cash.*carry|angro", "en-gros"),
    (r"distribut|livrare|furniz", "distributor"),
    (r"carne|meat|abator|slaughter|carmangerie", "meat"),
    (r"lact|dairy|lapte|branz|cheese|iaurt|yogurt|smantana", "dairy"),
    (r"frig|cold|refriger|congel|frozen|depozit.*frigorific", "cold-storage"),
    (r"logist|transport|expedit|freight|curier", "logistics"),
    (r"hotel|restaurant|catering|cantina|horeca|pensiune|bar\b", "horeca"),
    (r"panif|bread|paine|patiser|bak|cofet|cake", "processor"),
    (r"conserv|process|prelucr|fabrica|manufactur", "processor"),
    (r"agric|farm|ferma|legum|fruct|cereal|animal", "agriculture"),
]


def to_ascii(text):
    if not text:
        return ""
    return unicodedata.normalize('NFKD', str(text)).encode(
        'ascii', 'ignore').decode('ascii').strip()


def extract_email(text):
    if not text:
        return None
    text = str(text).strip().lower()
    try:
        text.encode('ascii')
    except UnicodeEncodeError:
        return None
    m = re.search(r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}', text)
    return m.group(0) if m else None


def detect_category(row, default_cat):
    """Detect category from row fields."""
    search_text = " ".join([
        str(row.get("category", "")),
        str(row.get("subcategory", "")),
        str(row.get("activity", "")),
        str(row.get("products", "")),
        str(row.get("type", "")),
        str(row.get("sector", "")),
        str(row.get("sector_name", "")),
    ]).lower()
    for pattern, cat in CATEGORY_RULES:
        if re.search(pattern, search_text):
            return cat
    if default_cat != "other":
        return default_cat
    return "other"


def read_csv_file(filepath, default_category):
    """Read a CSV and yield normalized records."""
    if not os.path.exists(filepath):
        return
    fname = os.path.basename(filepath)
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = extract_email(row.get("email") or row.get("best_email") or "")
                if not email:
                    email = extract_email(row.get("email2", ""))
                if not email:
                    email = extract_email(row.get("web_email", ""))
                company = to_ascii(row.get("company", "") or row.get("name", ""))
                if not company and not email:
                    continue
                cat = detect_category(row, default_category)
                yield {
                    "company": company,
                    "cui": to_ascii(row.get("cui", "") or row.get("vat_id", "")),
                    "county": to_ascii(row.get("county", "")),
                    "city": to_ascii(row.get("city", "")),
                    "address": to_ascii(row.get("address", "") or row.get("best_address", "")),
                    "phone": to_ascii(row.get("phone", "") or row.get("best_phone", "")),
                    "email": email or "",
                    "website": to_ascii(row.get("website", "") or row.get("web_website", "")),
                    "category": cat,
                    "subcategory": to_ascii(row.get("subcategory", "") or row.get("sector_name", "")),
                    "source": fname,
                }
    except Exception as e:
        print(f"  Error reading {fname}: {e}")


def richest(a, b):
    """Merge two records, keeping the one with more data."""
    score_a = sum(1 for v in a.values() if v)
    score_b = sum(1 for v in b.values() if v)
    if score_b > score_a:
        base, extra = b.copy(), a
    else:
        base, extra = a.copy(), b
    for k, v in extra.items():
        if not base.get(k) and v:
            base[k] = v
    return base


def main():
    output_path = DEFAULT_OUTPUT
    stats_only = False
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--stats":
            stats_only = True
        elif arg == "--output" and i < len(sys.argv) - 1:
            output_path = sys.argv[i + 1]

    # -- Read all sources
    all_records = []
    source_counts = defaultdict(int)

    for fname, default_cat in SOURCE_MAP.items():
        filepath = os.path.join(DATA_DIR, fname)
        if fname == "masterdb_food_companies.csv":
            filepath = os.path.join(DATA_DIR, fname)
        count = 0
        for rec in read_csv_file(filepath, default_cat):
            all_records.append(rec)
            count += 1
        if count:
            source_counts[fname] = count
            print(f"  {fname}: {count} records")

    print(f"\nTotal raw records: {len(all_records)}")

    # -- Deduplicate by email (keep richest)
    by_email = {}
    no_email = []
    for rec in all_records:
        email = rec.get("email", "").lower().strip()
        if email and "@" in email:
            if email in by_email:
                by_email[email] = richest(by_email[email], rec)
            else:
                by_email[email] = rec
        else:
            no_email.append(rec)

    # -- Deduplicate no-email records by company name
    by_name = {}
    for rec in no_email:
        name = rec.get("company", "").lower().strip()
        if name and len(name) > 3:
            if name not in by_name:
                by_name[name] = rec
            else:
                by_name[name] = richest(by_name[name], rec)

    deduped = list(by_email.values()) + list(by_name.values())

    # -- Stats
    cat_counts = defaultdict(int)
    email_count = 0
    for rec in deduped:
        cat_counts[rec.get("category", "other")] += 1
        if rec.get("email"):
            email_count += 1

    print(f"\nDeduplicated: {len(deduped)} unique contacts")
    print(f"With email: {email_count}")
    print(f"\nBy category:")
    for cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {cnt}")

    if stats_only:
        return

    # -- Write output
    deduped.sort(key=lambda r: (r.get("category", ""), r.get("county", ""), r.get("company", "")))
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=OUT_COLS)
        writer.writeheader()
        writer.writerows(deduped)

    print(f"\nOutput: {output_path} ({len(deduped)} rows)")


if __name__ == "__main__":
    main()
