#!/usr/bin/env python3
"""Match applicants.csv with body.txt files, extract CV text."""
import csv, re, os, json
from pathlib import Path

APPS_CSV = "/opt/ACTIVE/EMAIL/ORDERS/applicants.csv"
BODY_DIRS = [
    "/opt/ACTIVE/OPENDATA/DATA/APPLICATIONS/BUILDJOBS",
    "/opt/ACTIVE/OPENDATA/DATA/APPLICATIONS/CAREWORKERS",
    "/opt/ACTIVE/OPENDATA/DATA/APPLICATIONS/FACTORYJOBS",
    "/opt/ACTIVE/OPENDATA/DATA/APPLICATIONS/HORECA",
    "/opt/ACTIVE/OPENDATA/DATA/APPLICATIONS/INTERJOB",
    "/opt/ACTIVE/OPENDATA/DATA/APPLICATIONS/YAHOO_APAMINERALA",
    "/opt/ACTIVE/OPENDATA/DATA/APPLICATIONS/YAHOO_SECRETARIAT",
]
OUTPUT = "/opt/ACTIVE/WORKFORCE/applicants_with_cv.json"

JUNK_EMAILS = {
    "manpowerdristor@gmail.com", "fruitnature4@gmail.com",
    "apollomanpower2021@gmail.com", "tudor.seicarescu@gmail.com",
}

# Load applicants
with open(APPS_CSV, encoding="utf-8-sig") as f:
    applicants = list(csv.DictReader(f))

# Index by email and name
by_email = {}
by_name = {}
for r in applicants:
    em = r["Email"].strip().lower()
    nm = r["Name"].strip().lower()
    if em and em not in JUNK_EMAILS:
        by_email[em] = r
    if nm and len(nm) > 2:
        by_name[nm] = r

print(f"Applicants: {len(applicants)}, unique email: {len(by_email)}")

# Scan body files
matched = {}  # email -> cv_text

for bdir in BODY_DIRS:
    for body_path in Path(bdir).rglob("body.txt"):
        try:
            text = body_path.read_text(encoding="utf-8", errors="ignore")
        except:
            continue

        # Extract email from body header
        em_match = re.search(r"From:.*?([\w.+-]+@[\w-]+\.[\w.-]+)", text)
        found_email = em_match.group(1).lower() if em_match else None

        applicant = None
        if found_email and found_email in by_email:
            applicant = by_email[found_email]
        else:
            # try name match from folder name
            folder = body_path.parent.name
            # folder like: 2026-01-05_firstname_lastname_subject
            parts = folder.split("_")
            if len(parts) >= 3:
                name_guess = (parts[1] + " " + parts[2]).lower()
                if name_guess in by_name:
                    applicant = by_name[name_guess]

        if not applicant:
            continue

        key = applicant["Email"].strip().lower() or applicant["Name"].strip().lower()
        if key in matched:
            continue

        # Clean body text - remove headers, keep content
        lines = text.split("\n")
        content_lines = []
        in_content = False
        for line in lines:
            if "---" in line and not in_content:
                in_content = True
                continue
            if in_content:
                l = line.strip()
                if l and len(l) > 2:
                    # skip quoted email headers
                    if re.match(r"^(From|To|Subject|Date|Cc|Bcc):", l):
                        continue
                    content_lines.append(l)
            if len(content_lines) >= 40:
                break

        cv_text = "\n".join(content_lines[:30])
        if len(cv_text) < 30:
            continue

        matched[key] = {
            "name": applicant["Name"].strip(),
            "email": applicant["Email"].strip().lower(),
            "phone": applicant["Phone"].strip(),
            "country": applicant["Country"].strip(),
            "lang": applicant["Language"].strip(),
            "account": applicant["Account"].strip().lower(),
            "subject": re.sub(r"^(subject:\s*)", "", applicant["Subject"].strip(), flags=re.IGNORECASE),
            "cv_text": cv_text,
        }

print(f"Matched with CV body: {len(matched)}")

# For unmatched applicants, add subject-only entries
seen_keys = set(matched.keys())
seen_emails = set()
for r in applicants:
    em = r["Email"].strip().lower()
    nm = r["Name"].strip().lower()
    if not nm or len(nm) < 3:
        continue
    if em in JUNK_EMAILS:
        continue
    key = em if em else nm
    if key in seen_keys or em in seen_emails:
        continue
    seen_emails.add(em)
    seen_keys.add(key)
    subj = re.sub(r"^(subject:\s*)", "", r["Subject"].strip(), flags=re.IGNORECASE)
    matched[key] = {
        "name": r["Name"].strip(),
        "email": em,
        "phone": r["Phone"].strip(),
        "country": r["Country"].strip(),
        "lang": r["Language"].strip(),
        "account": r["Account"].strip().lower(),
        "subject": subj,
        "cv_text": "",
    }

print(f"Total entries: {len(matched)}")
with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(list(matched.values()), f, ensure_ascii=False, indent=2)
print(f"Saved: {OUTPUT}")

# Stats
with_cv = sum(1 for v in matched.values() if v["cv_text"])
print(f"With CV text: {with_cv} | Subject only: {len(matched)-with_cv}")
