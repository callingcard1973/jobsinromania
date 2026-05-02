#!/usr/bin/env python3
"""Fix HARGHITA CSVs: phone prefix in email, .co instead of .com"""
import csv, re, os

files = [
    "/opt/ACTIVE/ROMANIA/HARGHITA/DATA/harghita_phase1_construction.csv",
    "/opt/ACTIVE/ROMANIA/HARGHITA/DATA/harghita_phase2_mixed.csv",
    "/opt/ACTIVE/ROMANIA/HARGHITA/DATA/harghita_phase3_all.csv",
    "/opt/ACTIVE/ROMANIA/HARGHITA/DATA/harghita_lmv_contacts.csv",
]

for fpath in files:
    if not os.path.exists(fpath):
        continue

    with open(fpath, encoding="utf-8") as f:
        content = f.read()

    # Detect columns
    lines = content.strip().split("\n")
    header = lines[0]

    rows_fixed = 0
    rows_bad = 0
    fixed_lines = [header]

    for line in lines[1:]:
        parts = line.split(",", 1)  # email, rest
        if len(parts) < 2:
            continue

        email = parts[0].strip()
        rest = parts[1]

        # Fix 1: Remove phone prefix (digits before the actual email)
        # Pattern: 07XXXXXXXX or 02XXXXXXXX followed by actual email
        m = re.match(r'^(\d{10,12})(.+@.+)$', email)
        if m:
            phone = m.group(1)
            email = m.group(2)
            rows_fixed += 1

        # Fix 2: .co → .com (yahoo.co, gmail.co)
        if email.endswith(".co") and not email.endswith(".co.uk"):
            email = email + "m"
            rows_fixed += 1

        # Fix 3: Remove leading digits (1office@, 1xxx@)
        if re.match(r'^\d+[a-zA-Z]', email) and "@" in email:
            email = re.sub(r'^\d+', '', email)
            rows_fixed += 1

        # Validate email
        if "@" in email and "." in email.split("@")[1]:
            fixed_lines.append(f"{email},{rest}")
        else:
            rows_bad += 1

    # Backup and write
    os.rename(fpath, fpath + ".bak_dirty")
    with open(fpath, "w", encoding="utf-8") as f:
        f.write("\n".join(fixed_lines) + "\n")

    print(f"{os.path.basename(fpath):40s} {len(lines)-1:>5} rows, {rows_fixed:>4} fixed, {rows_bad:>3} removed")
