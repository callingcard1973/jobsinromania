#!/usr/bin/env python3
"""
Universal CSV Search Tool
Searches any term across ALL CSV files under D:\\MEMORY.
Usage: python search_csvs.py "search term" [--caen 8220] [--dir D:\\MEMORY] [--out results.csv]
"""

import argparse
import csv
import os
import re
import sys
from pathlib import Path


def read_csv_safe(path):
    """Read CSV with fallback encodings."""
    for enc in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
        try:
            with open(path, "r", encoding=enc, errors="replace") as f:
                sample = f.read(4096)
                f.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
                    reader = csv.DictReader(f, dialect=dialect)
                except csv.Error:
                    reader = csv.DictReader(f)
                rows = list(reader)
                return rows, reader.fieldnames or []
        except Exception:
            continue
    return [], []


def search_csvs(search_term, base_dir, caen_filter=None, output_file=None, max_per_file=500):
    """Search all CSVs under base_dir for search_term."""
    pattern = re.compile(re.escape(search_term), re.IGNORECASE)
    caen_pattern = re.compile(r"\b" + re.escape(caen_filter) + r"\b") if caen_filter else None

    results = []
    files_searched = 0
    files_matched = 0

    csv_files = list(Path(base_dir).rglob("*.csv"))
    print(f"Found {len(csv_files)} CSV files under {base_dir}")
    print(f"Searching for: '{search_term}'" + (f" + CAEN {caen_filter}" if caen_filter else ""))
    print()

    for csv_path in sorted(csv_files):
        # Skip our own output files
        if "callcenters_" in csv_path.name:
            continue

        try:
            rows, fields = read_csv_safe(str(csv_path))
        except Exception:
            continue

        if not rows:
            continue

        files_searched += 1
        file_matches = []

        for row in rows:
            row_text = " ".join(str(v) for v in row.values())

            text_match = bool(pattern.search(row_text))

            caen_match = False
            if caen_pattern:
                for key in row:
                    if key and "caen" in key.lower():
                        if caen_pattern.search(str(row.get(key, ""))):
                            caen_match = True
                            break

            if text_match or caen_match:
                # Build a summary record
                rel_path = str(csv_path.relative_to(base_dir))
                match_type = []
                if text_match:
                    match_type.append("text")
                if caen_match:
                    match_type.append("caen")

                # Extract key fields
                name = ""
                for k in ["company", "company_name", "name", "denumire", "nume_firma",
                           "employer", "contractor", "firmenbezeichnung", "Company name"]:
                    for key in row:
                        if key and key.strip().lower() == k.lower():
                            name = str(row[key]).strip()
                            if name and name.lower() not in ("nan", "none", ""):
                                break
                    if name and name.lower() not in ("nan", "none", ""):
                        break

                email = ""
                for k in ["email", "best_email", "email_1", "contact_email", "email1"]:
                    for key in row:
                        if key and key.strip().lower() == k.lower():
                            email = str(row[key]).strip()
                            if "@" in email:
                                break
                    if "@" in email:
                        break

                phone = ""
                for k in ["phone", "best_phone", "phone_1", "telefon", "contact_phone",
                           "anaf_phone", "phone1"]:
                    for key in row:
                        if key and key.strip().lower() == k.lower():
                            phone = str(row[key]).strip()
                            if phone and phone.lower() not in ("nan", "none", ""):
                                break
                    if phone and phone.lower() not in ("nan", "none", ""):
                        break

                cui = ""
                for k in ["cui", "employer_tax_code", "company_id"]:
                    for key in row:
                        if key and key.strip().lower() == k.lower():
                            cui = str(row[key]).strip()
                            if cui and cui.lower() not in ("nan", "none", ""):
                                break
                    if cui and cui.lower() not in ("nan", "none", ""):
                        break

                caen = ""
                for k in ["caen", "anaf_caen"]:
                    for key in row:
                        if key and key.strip().lower() == k.lower():
                            caen = str(row[key]).strip()
                            if caen and caen.lower() not in ("nan", "none", ""):
                                break
                    if caen and caen.lower() not in ("nan", "none", ""):
                        break

                file_matches.append({
                    "source_file": rel_path,
                    "company": name,
                    "cui": cui,
                    "caen": caen,
                    "email": email if "@" in email else "",
                    "phone": phone if phone.lower() not in ("nan", "none", "") else "",
                    "match_type": "+".join(match_type),
                    "raw_row": row_text[:200],
                })

                if len(file_matches) >= max_per_file:
                    break

        if file_matches:
            files_matched += 1
            results.extend(file_matches)
            print(f"  {csv_path.relative_to(base_dir)}: {len(file_matches)} matches")

    print(f"\n{'='*60}")
    print(f"Files searched: {files_searched}")
    print(f"Files with matches: {files_matched}")
    print(f"Total matches: {len(results)}")

    # Deduplicate by company name
    seen = set()
    unique = []
    for r in results:
        key = (r["company"].lower().strip(), r["cui"])
        if key not in seen and r["company"]:
            seen.add(key)
            unique.append(r)
    print(f"Unique companies: {len(unique)}")

    if output_file:
        out_cols = ["company", "cui", "caen", "email", "phone", "source_file", "match_type"]
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=out_cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(unique)
        print(f"\nSaved to: {output_file}")

    return unique


def main():
    parser = argparse.ArgumentParser(description="Search all CSVs for a term")
    parser.add_argument("term", help="Search term (regex-escaped)")
    parser.add_argument("--caen", help="Also match by CAEN code")
    parser.add_argument("--dir", default=r"D:\MEMORY\CLAUDE",
                        help="Base directory to search (default: D:\\MEMORY\\CLAUDE)")
    parser.add_argument("--out", help="Output CSV file path")
    parser.add_argument("--max", type=int, default=500,
                        help="Max matches per file (default: 500)")
    args = parser.parse_args()

    search_csvs(args.term, args.dir, args.caen, args.out, args.max)


if __name__ == "__main__":
    main()
