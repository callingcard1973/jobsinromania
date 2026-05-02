#!/usr/bin/env python3
"""
SEAP Construction Winner Enrichment Pipeline

Matches SEAP public procurement winners (by CUI) against all internal data sources
to find email addresses. Outputs campaign-ready contacts per sector.

Sources (priority order):
  1. interjob_master PostgreSQL (cui + email)
  2. contractors_enriched.csv (cui + email, from enrich_contractors.py)
  3. EUFUNDS contacts (company_name fuzzy match)
  4. ANOFM job postings (company_org_number = CUI, phone only)

Usage:
    python3 enrich_seap_winners.py                    # Full run, all sectors
    python3 enrich_seap_winners.py --sector 45        # Construction only (CPV 45)
    python3 enrich_seap_winners.py --dry-run           # Preview without writing
    python3 enrich_seap_winners.py --status            # Show current enrichment stats
    python3 enrich_seap_winners.py --append-campaigns  # Append new contacts to campaign CSVs

Output:
    /opt/ACTIVE/OPENDATA/DATA/SEAP_ENRICHED/seap_winners_enriched.csv
    /opt/ACTIVE/OPENDATA/DATA/SEAP_ENRICHED/seap_construction_new.csv  (deduped vs campaigns)
"""

import csv
import glob
import json
import re
import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Paths
SEAP_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/ACHIZITII_PUBLICE")
ENRICHED_CSV = Path("/opt/ACTIVE/OPENDATA/DATA/CONTRACTOR_MATCHES/contractors_enriched.csv")
EUFUNDS_CSV = Path("/opt/ACTIVE/OPENDATA/DATA/ROMANIA/EUFUNDS/eufunds_contacts.csv")
ANOFM_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/ROMANIA/ANOFM")
OUTPUT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/SEAP_ENRICHED")
CAMPAIGN_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/CONSTRUCTORI")
CAMPAIGN_SOURCE = Path("/opt/ACTIVE/CONSTRUCTORI/romanian_construction_companies_1025.csv")

# Campaign sector mapping: CPV prefix -> campaign directory
SECTOR_CAMPAIGNS = {
    "45": "CONSTRUCTORI",
    "42": "HEAVY_INDUSTRY",
    "44": "HEAVY_INDUSTRY",
    "60": "LOGISTICS",
    "63": "LOGISTICS",
    "55": "HOSPITALITY",
    "03": "AGRICULTURE",
    "77": "AGRICULTURE",
}

# Government email patterns to exclude
GOV_PATTERNS = [
    r"@primari[ae]",
    r"@cj[a-z]*\.ro$",
    r"@dgaspc",
    r"@gov\.ro$",
    r"@edu\.ro$",
    r"@mfinante",
    r"@anaf",
    r"@cnair",
    r"@apele-romane",
]

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def is_gov_email(email):
    for p in GOV_PATTERNS:
        if re.search(p, email):
            return True
    return False


def load_seap_winners(sector_filter=None):
    """Load SEAP winners from latest CSV files, grouped by CUI."""
    winners = {}  # cui -> {name, cpv_codes, total_value, contract_count}
    latest_files = sorted(SEAP_DIR.glob("*_20*.csv"))
    if not latest_files:
        logger.error("No SEAP CSV files found in %s", SEAP_DIR)
        return winners

    # Find latest date
    dates = set()
    for f in latest_files:
        m = re.search(r"_(\d{8})\.csv$", f.name)
        if m:
            dates.add(m.group(1))
    if not dates:
        return winners
    latest_date = max(dates)
    files = [f for f in latest_files if latest_date in f.name]

    logger.info("Loading SEAP data from %d files (date: %s)", len(files), latest_date)

    for f in files:
        with open(f, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                cui = (row.get("CUI_OFERTANT_CASTIGATOR") or "").strip()
                cpv = (row.get("COD_CPV") or "").strip()
                name = (row.get("OFERTANT_CASTIGATOR") or "").strip()

                if not cui or not cpv:
                    continue

                cpv_prefix = cpv[:2]
                if sector_filter and cpv_prefix != sector_filter:
                    continue

                if cui not in winners:
                    winners[cui] = {
                        "name": name,
                        "cpv_codes": set(),
                        "total_value": 0,
                        "contract_count": 0,
                    }

                winners[cui]["cpv_codes"].add(cpv_prefix)
                winners[cui]["contract_count"] += 1
                try:
                    val = float((row.get("VALOARE_ACHIZITIE_(RON)") or "0").replace(",", "."))
                    winners[cui]["total_value"] += val
                except (ValueError, TypeError):
                    pass

    logger.info("Loaded %d unique SEAP winners", len(winners))
    return winners


def load_db_contacts():
    """Load RO companies with email from interjob_master DB."""
    contacts = {}
    try:
        import psycopg2
        conn = psycopg2.connect(
            dbname="interjob_master", user="tudor", password="tudor", host="127.0.0.1"
        )
        cur = conn.cursor()
        cur.execute(
            "SELECT cui, email, phone, name FROM companies "
            "WHERE country='RO' AND email IS NOT NULL AND email != '' "
            "AND cui IS NOT NULL AND cui != ''"
        )
        for row in cur.fetchall():
            cui = str(row[0]).strip()
            email = str(row[1]).strip().lower()
            phone = str(row[2] or "").strip()
            name = str(row[3] or "").strip()
            if cui and email and "@" in email:
                contacts[cui] = {"name": name, "email": email, "phone": phone}
        conn.close()
        logger.info("DB: %d RO companies with CUI+email", len(contacts))
    except Exception as e:
        logger.warning("DB unavailable: %s", e)
    return contacts


def load_enriched_contacts():
    """Load contractors_enriched.csv."""
    contacts = {}
    if not ENRICHED_CSV.exists():
        return contacts
    with open(ENRICHED_CSV) as f:
        for row in csv.DictReader(f):
            cui = (row.get("cui") or "").strip()
            email = (row.get("email") or "").strip().lower()
            phone = (row.get("phone") or "").strip()
            name = (row.get("company_name") or "").strip()
            if cui and email and "@" in email:
                contacts[cui] = {"name": name, "email": email, "phone": phone}
    logger.info("Enriched CSV: %d companies with CUI+email", len(contacts))
    return contacts


def load_anofm_phones():
    """Load ANOFM data for phone numbers by CUI."""
    phones = {}
    for f in sorted(ANOFM_DIR.glob("*.csv")):
        try:
            with open(f, encoding="utf-8", errors="ignore") as fh:
                for row in csv.DictReader(fh):
                    cui = (row.get("company_org_number") or "").strip()
                    phone = (row.get("phone_1") or "").strip()
                    name = (row.get("company_name") or "").strip()
                    if cui and phone:
                        phones[cui] = {"name": name, "phone": phone}
        except Exception:
            pass
    logger.info("ANOFM: %d CUIs with phone", len(phones))
    return phones


def load_campaign_emails():
    """Load already-sent and existing campaign emails to avoid duplicates."""
    existing = set()

    # sent_companies.csv
    sent_file = CAMPAIGN_DIR / "sent_companies.csv"
    if sent_file.exists():
        with open(sent_file) as f:
            for row in csv.DictReader(f):
                existing.add((row.get("email") or "").strip().lower())

    # Source CSV
    if CAMPAIGN_SOURCE.exists():
        with open(CAMPAIGN_SOURCE) as f:
            for row in csv.DictReader(f):
                existing.add((row.get("email") or "").strip().lower())

    # Also check other campaign directories
    campaigns_root = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/CAMPAIGNS")
    for campaign_dir in campaigns_root.iterdir():
        if campaign_dir.is_dir():
            for csv_file in campaign_dir.glob("*.csv"):
                try:
                    with open(csv_file) as f:
                        for row in csv.DictReader(f):
                            email = (row.get("email") or row.get("Email") or "").strip().lower()
                            if email:
                                existing.add(email)
                except Exception:
                    pass

    logger.info("Campaign dedup: %d existing emails", len(existing))
    return existing


def enrich(winners, db_contacts, enriched_contacts, anofm_phones):
    """Match winners against all sources."""
    results = []

    for cui, info in winners.items():
        email = ""
        phone = ""
        source = ""
        name = info["name"]

        # Priority 1: DB
        if cui in db_contacts:
            d = db_contacts[cui]
            email = d["email"]
            phone = d.get("phone", "")
            name = d.get("name") or name
            source = "interjob_master"

        # Priority 2: Enriched CSV
        elif cui in enriched_contacts:
            d = enriched_contacts[cui]
            email = d["email"]
            phone = d.get("phone", "")
            name = d.get("name") or name
            source = "contractors_enriched"

        # Phone from ANOFM
        if not phone and cui in anofm_phones:
            phone = anofm_phones[cui]["phone"]
            if not name:
                name = anofm_phones[cui]["name"]

        results.append({
            "cui": cui,
            "name": name,
            "email": email,
            "phone": phone,
            "source": source,
            "cpv_codes": ",".join(sorted(info["cpv_codes"])),
            "contract_count": info["contract_count"],
            "total_value_ron": int(info["total_value"]),
        })

    return results


def main():
    parser = argparse.ArgumentParser(description="SEAP Winner Enrichment")
    parser.add_argument("--sector", help="CPV prefix filter (e.g. 45 for construction)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--status", action="store_true", help="Show stats only")
    parser.add_argument("--append-campaigns", action="store_true", help="Append new contacts to campaign CSVs")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load all sources
    winners = load_seap_winners(args.sector)
    if not winners:
        logger.error("No SEAP winners found")
        return

    if args.status:
        print("SEAP winners: %d" % len(winners))
        # Check existing enrichment
        out_file = OUTPUT_DIR / "seap_winners_enriched.csv"
        if out_file.exists():
            with open(out_file) as f:
                rows = list(csv.DictReader(f))
                with_email = sum(1 for r in rows if r.get("email"))
                print("Enriched: %d total, %d with email (%.1f%%)" % (len(rows), with_email, 100 * with_email / len(rows) if rows else 0))
        return

    db_contacts = load_db_contacts()
    enriched_contacts = load_enriched_contacts()
    anofm_phones = load_anofm_phones()

    # Enrich
    results = enrich(winners, db_contacts, enriched_contacts, anofm_phones)

    # Filter valid emails
    valid = []
    gov_removed = 0
    invalid_removed = 0
    for r in results:
        if r["email"]:
            if is_gov_email(r["email"]):
                gov_removed += 1
                r["email"] = ""
                r["source"] = ""
            elif not EMAIL_RE.match(r["email"]):
                invalid_removed += 1
                r["email"] = ""
                r["source"] = ""
        valid.append(r)

    with_email = sum(1 for r in valid if r["email"])
    with_phone = sum(1 for r in valid if r["phone"])

    logger.info("=== Enrichment Results ===")
    logger.info("Total winners: %d", len(valid))
    logger.info("With email: %d (%.1f%%)", with_email, 100 * with_email / len(valid))
    logger.info("With phone only: %d", sum(1 for r in valid if r["phone"] and not r["email"]))
    logger.info("Gov emails removed: %d", gov_removed)
    logger.info("Invalid emails removed: %d", invalid_removed)
    logger.info("No contact info: %d", sum(1 for r in valid if not r["email"] and not r["phone"]))

    # Source breakdown
    sources = defaultdict(int)
    for r in valid:
        if r["email"]:
            sources[r["source"]] += 1
    for src, count in sorted(sources.items(), key=lambda x: -x[1]):
        logger.info("  %s: %d emails", src, count)

    if args.dry_run:
        logger.info("DRY RUN - no files written")
        return

    # Write full enriched output
    out_file = OUTPUT_DIR / "seap_winners_enriched.csv"
    fieldnames = ["cui", "name", "email", "phone", "source", "cpv_codes", "contract_count", "total_value_ron"]
    with open(out_file, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in sorted(valid, key=lambda x: -x["total_value_ron"]):
            w.writerow(r)
    logger.info("Wrote %s (%d rows)", out_file, len(valid))

    # Campaign dedup and append
    if args.append_campaigns:
        existing_emails = load_campaign_emails()
        new_contacts = [r for r in valid if r["email"] and r["email"] not in existing_emails]
        logger.info("New contacts for campaigns: %d (after dedup vs %d existing)", len(new_contacts), len(existing_emails))

        if new_contacts and CAMPAIGN_SOURCE.exists():
            with open(CAMPAIGN_SOURCE, "a", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["name", "email", "phone", "city", "employees_count"])
                for r in new_contacts:
                    # Only construction companies
                    if "45" in r["cpv_codes"].split(","):
                        w.writerow({
                            "name": r["name"],
                            "email": r["email"],
                            "phone": r["phone"],
                            "city": "",
                            "employees_count": "0",
                        })
            logger.info("Appended construction contacts to %s", CAMPAIGN_SOURCE)

        # Save standalone new contacts file
        new_file = OUTPUT_DIR / "seap_construction_new.csv"
        with open(new_file, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in new_contacts:
                w.writerow(r)
        logger.info("Wrote %s (%d new contacts)", new_file, len(new_contacts))

    # Save stats
    stats = {
        "timestamp": datetime.now().isoformat(),
        "total_winners": len(valid),
        "with_email": with_email,
        "with_phone_only": sum(1 for r in valid if r["phone"] and not r["email"]),
        "gov_removed": gov_removed,
        "sources": dict(sources),
        "sector_filter": args.sector,
    }
    with open(OUTPUT_DIR / "enrichment_stats.json", "w") as f:
        json.dump(stats, f, indent=2)


if __name__ == "__main__":
    main()
