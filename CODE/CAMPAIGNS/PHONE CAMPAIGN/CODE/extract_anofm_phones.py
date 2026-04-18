#!/usr/bin/env python3
"""
Extract all unique companies with phones+emails from ANOFM CSVs.
Output: anofm_phones_YYYYMMDD.csv ready for phone campaign.
"""
import csv, glob, os, re, sys
from datetime import date
from collections import defaultdict

ANOFM_DIR = "/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ROMANIA/ANOFM/DOCKER/PROGRAMS/"
BLACKLIST_FILE = "/opt/EMAIL/master_blacklist.csv"
OUTPUT_DIR = "/opt/ACTIVE/PHONE_CAMPAIGN/"
OUTPUT_FILE = f"{OUTPUT_DIR}anofm_phones_{date.today().strftime('%Y%m%d')}.csv"

OUTPUT_COLS = [
    "company_name", "cui", "phone", "phone_e164",
    "sector", "city", "jobs", "positions_total", "source_date"
]


def normalize_phone(raw: str) -> str:
    """Normalize Romanian phone to E.164 (+40XXXXXXXXX). Returns '' if invalid/foreign."""
    # Take first number if multiple separated by , ; or space-semicolon
    raw = re.split(r"[;,]", raw.strip())[0].strip()

    # Already E.164 Romanian
    if raw.startswith("+40") and len(raw) == 12:
        return raw

    # Foreign numbers (not Romanian) — skip
    if raw.startswith("+") and not raw.startswith("+40"):
        return ""

    digits = re.sub(r"[^\d]", "", raw)
    if not digits:
        return ""

    # 0049..., 0033... — foreign via 00 prefix
    if digits.startswith("00") and not digits.startswith("004"):
        return ""

    # Strip leading 00 (international dialing)
    if digits.startswith("00"):
        digits = digits[2:]

    # +40XXXXXXXXX → already correct length 11 digits
    if digits.startswith("40") and len(digits) == 11:
        return f"+{digits}"

    # 07XXXXXXXX or 02XXXXXXXX (mobile/landline with leading 0)
    if digits.startswith("0") and len(digits) == 10:
        return f"+40{digits[1:]}"

    # 9-digit without leading 0
    if len(digits) == 9:
        return f"+40{digits}"

    # Short landlines (6-8 digits) — local format, unusable for campaign
    return ""


def load_blacklist() -> set:
    blacklist = set()
    if not os.path.exists(BLACKLIST_FILE):
        return blacklist
    with open(BLACKLIST_FILE, encoding="utf-8") as f:
        for line in f:
            e = line.strip().lower()
            if e:
                blacklist.add(e)
    return blacklist


def load_all_anofm() -> dict:
    """Load all ANOFM CSVs, dedup by CUI (fallback: company_name)."""
    files = sorted(glob.glob(ANOFM_DIR + "anofm_jobs_*.csv"))
    if not files:
        print(f"No files found in {ANOFM_DIR}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(files)} CSV files", file=sys.stderr)

    # key: cui or company_name_normalized
    companies = {}

    for fpath in files:
        src_date = os.path.basename(fpath).split("_")[2][:8]  # YYYYMMDD
        try:
            with open(fpath, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get("company_name", "").strip()
                    if not name:
                        continue

                    cui = row.get("company_org_number", "").strip()
                    key = cui if cui else name.lower()

                    phone_raw = (
                        row.get("phone_1", "").strip()
                        or row.get("phone_2", "").strip()
                        or row.get("phone_3", "").strip()
                    )
                    email = (
                        row.get("email_1", "").strip()
                        or row.get("email_2", "").strip()
                        or row.get("email_3", "").strip()
                    )
                    sector = row.get("sector", "").strip()
                    city_raw = row.get("city", "").strip()
                    # city is "County > MUNICIPALITY > CITY" — take last part
                    city = city_raw.split(">")[-1].strip() if ">" in city_raw else city_raw
                    job_title = row.get("job_title", "").strip()
                    positions = row.get("positions_available", "").strip()

                    if key not in companies:
                        companies[key] = {
                            "company_name": name,
                            "cui": cui,
                            "phone": phone_raw,
                            "email": email,
                            "sector": sector,
                            "city": city,
                            "jobs": [],
                            "positions_total": 0,
                            "source_date": src_date,
                        }
                    else:
                        # Fill in missing data from newer records
                        if phone_raw and not companies[key]["phone"]:
                            companies[key]["phone"] = phone_raw
                        if email and not companies[key]["email"]:
                            companies[key]["email"] = email
                        # Keep latest source_date
                        if src_date > companies[key]["source_date"]:
                            companies[key]["source_date"] = src_date

                    # Accumulate jobs
                    if job_title:
                        job_entry = f"{job_title}({positions})" if positions else job_title
                        if job_entry not in companies[key]["jobs"]:
                            companies[key]["jobs"].append(job_entry)
                    if positions.isdigit():
                        companies[key]["positions_total"] += int(positions)

        except Exception as ex:
            print(f"Error reading {fpath}: {ex}", file=sys.stderr)

    return companies


def main():
    blacklist = load_blacklist()
    print(f"Blacklist: {len(blacklist)} emails", file=sys.stderr)

    companies = load_all_anofm()
    print(f"Unique companies loaded: {len(companies)}", file=sys.stderr)

    rows = []
    stats = {"no_phone": 0, "no_email": 0, "blacklisted": 0, "ok": 0}

    for data in companies.values():
        phone_raw = data["phone"]
        email = data["email"]

        if not phone_raw:
            stats["no_phone"] += 1
            continue

        phone_e164 = normalize_phone(phone_raw)
        if not phone_e164:
            stats["no_phone"] += 1
            continue

        if email and email.lower() in blacklist:
            stats["blacklisted"] += 1
            continue

        rows.append({
            "company_name": data["company_name"],
            "cui": data["cui"],
            "phone": phone_raw,
            "phone_e164": phone_e164,
            "sector": data["sector"],
            "city": data["city"],
            "jobs": " | ".join(data["jobs"][:5]),  # max 5 jobs listed
            "positions_total": data["positions_total"] or "",
            "source_date": data["source_date"],
        })
        stats["ok"] += 1

    # Sort: sectors most useful for placement first
    PRIORITY_SECTORS = [
        "Construcții", "Producție", "transport", "Agricultură",
        "Turism", "RESTAURANTE", "COMERT"
    ]

    def sector_priority(row):
        s = row["sector"]
        for i, p in enumerate(PRIORITY_SECTORS):
            if p.lower() in s.lower():
                return i
        return 99

    rows.sort(key=sector_priority)

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n=== RESULTS ===", file=sys.stderr)
    print(f"Output: {OUTPUT_FILE}", file=sys.stderr)
    print(f"Ready for calling: {stats['ok']}", file=sys.stderr)
    print(f"No phone (skipped): {stats['no_phone']}", file=sys.stderr)
    print(f"Blacklisted: {stats['blacklisted']}", file=sys.stderr)
    print(f"No email: {stats['no_email']}", file=sys.stderr)
    print(OUTPUT_FILE)  # stdout for scripting

    # Keep only last 7 daily files
    old_files = sorted(glob.glob(f"{OUTPUT_DIR}anofm_phones_*.csv"))[:-7]
    for f in old_files:
        os.remove(f)
        print(f"Removed old: {f}", file=sys.stderr)


if __name__ == "__main__":
    main()
