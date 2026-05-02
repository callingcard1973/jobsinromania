#!/usr/bin/env python3
"""
Contact Deduplication - Find and merge duplicates across CSVs
Usage: python3 contact_dedup.py file1.csv file2.csv ... [--output merged.csv]
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, sanitize, FIELD_LIMITS

import csv, re
from collections import defaultdict
from pathlib import Path

def normalize_email(e):
    return e.strip().lower() if e else ''

def dedup(files, output=None):
    print(f"\n{'='*60}\nCONTACT DEDUPLICATION\n{'='*60}\n")
    
    all_contacts = defaultdict(list)  # email -> list of (file, row)
    total = 0
    
    for f in files:
        print(f"Reading: {Path(f).name}")
        with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
            rows = list(csv.DictReader(fp))
            email_col = next((c for c in rows[0].keys() if 'email' in c.lower()), None) if rows else None
            if not email_col: continue
            for r in rows:
                email = normalize_email(r.get(email_col,''))
                if email and '@' in email:
                    all_contacts[email].append((f, r))
                    total += 1
    
    unique = len(all_contacts)
    dupes = {e: v for e,v in all_contacts.items() if len(v) > 1}
    
    print(f"\nTOTAL RECORDS: {total}")
    print(f"UNIQUE EMAILS: {unique}")
    print(f"DUPLICATES: {len(dupes)} emails appear in multiple files\n")
    
    if dupes:
        print("DUPLICATE DETAILS:")
        for email, occurrences in sorted(dupes.items(), key=lambda x: -len(x[1]))[:20]:
            files_list = [Path(f).name for f,_ in occurrences]
            print(f"  {email}: {len(occurrences)}x in {', '.join(set(files_list))}")
    
    # Cross-file duplicates
    cross_file = {e: v for e,v in dupes.items() if len(set(f for f,_ in v)) > 1}
    print(f"\nCROSS-FILE DUPLICATES: {len(cross_file)}")
    
    if output:
        # Merge: keep first occurrence of each email
        merged = []
        seen = set()
        for email, occurrences in all_contacts.items():
            if email not in seen:
                seen.add(email)
                merged.append(occurrences[0][1])
        
        if merged:
            with open(output, 'w', encoding='utf-8', newline='') as fp:
                writer = csv.DictWriter(fp, fieldnames=merged[0].keys())
                writer.writeheader()
                writer.writerows(merged)
            print(f"\nMERGED OUTPUT: {output} ({len(merged)} unique contacts)")
    
    print(f"\n{'='*60}\n")

if __name__ == '__main__':
    args = sys.argv[1:]
    output = None
    if '--output' in args:
        idx = args.index('--output')
        output = args[idx+1]
        args = args[:idx] + args[idx+2:]
    
    if args:
        dedup(args, output)
    else:
        print("Usage: contact_dedup.py file1.csv file2.csv ... [--output merged.csv]")
