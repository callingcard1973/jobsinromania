#!/usr/bin/env python3
"""Check all campaign CSVs + anofm.jobs for email appearing in 2+ campaigns.
Report conflicts (cross-campaign duplicates).
Deploy to: /opt/ACTIVE/INFRA/SKILLS/dedup_cross_campaigns.py
"""
import csv, glob, json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

import psycopg2

DB_PARAMS = dict(dbname="anofm", user="tudor", password="tudor", host="localhost")

# Campaign CSV directories
CAMPAIGN_DIRS = [
    "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/",
    "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/",
]
# Also check TED campaign CSVs
TED_DIR = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/"

OUTPUT_JSON = Path("/opt/ACTIVE/INFRA/SKILLS/dedup_cross_report.json")


def get_anofm_emails():
    """Get emails from anofm.jobs with their campaign_status."""
    emails = {}
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        cur.execute(
            "SELECT LOWER(email), campaign_status, sector "
            "FROM jobs WHERE email IS NOT NULL AND email != ''")
        for row in cur.fetchall():
            email = row[0].strip()
            if email and "@" in email:
                emails[email] = {
                    "source": "anofm.jobs",
                    "campaign_status": row[1] or "",
                    "sector": row[2] or "",
                }
        conn.close()
    except Exception as e:
        print(f"DB error: {e}")
    return emails


def get_csv_emails():
    """Scan all campaign CSVs for emails."""
    email_sources = defaultdict(list)
    patterns = []
    for d in CAMPAIGN_DIRS:
        patterns.extend([f"{d}ro_*.csv", f"{d}ted_*.csv", f"{d}*.csv"])
    patterns.append(f"{TED_DIR}ted_*.csv")

    seen_files = set()
    for pat in patterns:
        for fpath in glob.glob(pat):
            if fpath in seen_files:
                continue
            seen_files.add(fpath)
            fname = Path(fpath).stem
            try:
                with open(fpath, encoding="utf-8", errors="replace") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        email = (row.get("email", "") or row.get("Email", "")).strip().lower()
                        if email and "@" in email:
                            email_sources[email].append(fname)
            except Exception as e:
                print(f"Error reading {fpath}: {e}")

    return email_sources


def find_conflicts(csv_emails, anofm_emails):
    """Find emails appearing in 2+ sources."""
    conflicts = []

    for email, sources in csv_emails.items():
        all_sources = list(set(sources))
        if email in anofm_emails:
            all_sources.append("anofm.jobs")

        if len(all_sources) >= 2:
            conflicts.append({
                "email": email,
                "sources": all_sources,
                "count": len(all_sources),
            })

    # Also check anofm emails in multiple CSV campaigns
    for email, info in anofm_emails.items():
        if email not in csv_emails:
            continue
        # Already handled above

    conflicts.sort(key=lambda x: -x["count"])
    return conflicts


def main():
    print("Loading ANOFM emails...")
    anofm_emails = get_anofm_emails()
    print(f"  ANOFM: {len(anofm_emails)} emails")

    print("Scanning campaign CSVs...")
    csv_emails = get_csv_emails()
    print(f"  CSVs: {len(csv_emails)} unique emails")

    print("Finding conflicts...")
    conflicts = find_conflicts(csv_emails, anofm_emails)

    # Stats
    by_count = defaultdict(int)
    for c in conflicts:
        by_count[c["count"]] += 1

    report = {
        "generated": datetime.now().isoformat(),
        "total_anofm": len(anofm_emails),
        "total_csv": len(csv_emails),
        "total_conflicts": len(conflicts),
        "by_overlap_count": dict(by_count),
        "conflicts": conflicts[:500],  # Top 500
    }

    OUTPUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    # Print summary
    print(f"\n{'='*60}")
    print(f"CROSS-CAMPAIGN DEDUP REPORT")
    print(f"{'='*60}")
    print(f"ANOFM emails:     {len(anofm_emails):>8,}")
    print(f"CSV emails:       {len(csv_emails):>8,}")
    print(f"Conflicts found:  {len(conflicts):>8,}")
    print()
    for count, num in sorted(by_count.items()):
        print(f"  In {count} campaigns: {num:>6,} emails")
    print()

    if conflicts:
        print("Top 20 conflicts:")
        for c in conflicts[:20]:
            print(f"  {c['email']:40s} -> {', '.join(c['sources'])}")

    print(f"\nFull report: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
