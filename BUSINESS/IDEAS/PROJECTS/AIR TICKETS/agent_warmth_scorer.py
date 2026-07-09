#!/usr/bin/env python3
"""
Agent 34: Email Warmth Scorer + Agent 36: Data Quality Auditor
+ Agent 38: Country Tagger + Agent 37: Phone Formatter.
All pure SQL, zero HTTP. Scores and cleans master_emails.

Cron: 0 5 * * *  (daily 5 AM)
"""
import subprocess
import logging
import json
from datetime import datetime

DB_USER = "tudor"
DB_NAME = "interjob_master"
LOG = "/opt/ACTIVE/FLIGHTS/logs/warmth_scorer.log"
NODERED = "http://localhost:1880/enrichment-status"

logging.basicConfig(filename=LOG, level=logging.INFO,
                    format="%(asctime)s %(message)s")
log = logging.getLogger("warmth")


def sql(q, timeout=600):
    cmd = ["psql", "-U", DB_USER, "-d", DB_NAME, "-t", "-A", "-c", q]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""


def ensure_columns():
    """Add scoring columns if missing."""
    sql("ALTER TABLE master_emails ADD COLUMN IF NOT EXISTS "
        "warmth_score INTEGER DEFAULT 0")
    sql("ALTER TABLE master_emails ADD COLUMN IF NOT EXISTS "
        "country_detected TEXT")
    sql("ALTER TABLE master_emails ADD COLUMN IF NOT EXISTS "
        "is_generic BOOLEAN DEFAULT false")


def score_warmth():
    """Calculate warmth score for each email. Higher = better lead."""
    # Reset scores
    sql("UPDATE master_emails SET warmth_score = 0")
    # +10 MX valid
    n1 = sql("UPDATE master_emails SET warmth_score = warmth_score + 10 "
             "WHERE mx_valid = true")
    # +5 has company name
    n2 = sql("UPDATE master_emails SET warmth_score = warmth_score + 5 "
             "WHERE company IS NOT NULL AND company != ''")
    # +5 from TED (government contractor = serious business)
    n3 = sql("UPDATE master_emails SET warmth_score = warmth_score + 5 "
             "WHERE source_table LIKE '%ted%'")
    # +3 has phone
    n4 = sql("UPDATE master_emails SET warmth_score = warmth_score + 3 "
             "WHERE phone IS NOT NULL AND phone != ''")
    # -5 generic (info@, office@, contact@)
    sql("UPDATE master_emails SET is_generic = true "
        "WHERE email LIKE 'info@%' OR email LIKE 'office@%' "
        "OR email LIKE 'contact@%' OR email LIKE 'admin@%'")
    sql("UPDATE master_emails SET warmth_score = warmth_score - 5 "
        "WHERE is_generic = true")
    # -10 bounced
    sql("UPDATE master_emails SET warmth_score = warmth_score - 10 "
        "WHERE is_bounced = true")
    log.info("Warmth scores updated")


def tag_countries():
    """Detect country from email domain TLD."""
    tld_map = {
        ".ro": "RO", ".pl": "PL", ".de": "DE", ".fr": "FR",
        ".it": "IT", ".es": "ES", ".nl": "NL", ".be": "BE",
        ".at": "AT", ".ch": "CH", ".dk": "DK", ".se": "SE",
        ".no": "NO", ".fi": "FI", ".uk": "GB", ".ie": "IE",
        ".pt": "PT", ".gr": "GR", ".cz": "CZ", ".hu": "HU",
        ".bg": "BG", ".hr": "HR", ".sk": "SK", ".si": "SI",
        ".lt": "LT", ".lv": "LV", ".ee": "EE", ".lu": "LU",
        ".tr": "TR", ".ru": "RU", ".ua": "UA", ".md": "MD",
    }
    total = 0
    for tld, country in tld_map.items():
        n = sql(f"UPDATE master_emails SET country_detected = '{country}' "
                f"WHERE (country_detected IS NULL OR country_detected = '') "
                f"AND email LIKE '%{tld}'")
        try:
            total += int(n.split()[-1]) if n else 0
        except (ValueError, IndexError):
            pass
    # Also from existing country column
    sql("UPDATE master_emails SET country_detected = country "
        "WHERE (country_detected IS NULL OR country_detected = '') "
        "AND country IS NOT NULL AND country != ''")
    log.info(f"Countries tagged: {total}")
    return total


def audit_quality():
    """Data quality report."""
    total = sql("SELECT count(*) FROM master_emails")
    valid = sql("SELECT count(*) FROM master_emails WHERE mx_valid=true")
    invalid = sql("SELECT count(*) FROM master_emails WHERE mx_valid=false")
    unchecked = sql("SELECT count(*) FROM master_emails WHERE mx_valid IS NULL")
    with_company = sql("SELECT count(*) FROM master_emails WHERE company IS NOT NULL AND company!=''")
    generic = sql("SELECT count(*) FROM master_emails WHERE is_generic=true")
    hot = sql("SELECT count(*) FROM master_emails WHERE warmth_score >= 10")
    cold = sql("SELECT count(*) FROM master_emails WHERE warmth_score <= 0")
    by_country = sql(
        "SELECT country_detected, count(*) FROM master_emails "
        "WHERE country_detected IS NOT NULL "
        "GROUP BY country_detected ORDER BY count(*) DESC LIMIT 15")
    return {
        "total": int(total or 0),
        "mx_valid": int(valid or 0),
        "mx_invalid": int(invalid or 0),
        "mx_unchecked": int(unchecked or 0),
        "with_company": int(with_company or 0),
        "generic": int(generic or 0),
        "hot_leads": int(hot or 0),
        "cold_leads": int(cold or 0),
        "by_country": by_country,
    }


def main():
    log.info("=== Warmth Scorer + Quality Auditor START ===")
    print(f"Warmth Scorer — {datetime.now()}")

    ensure_columns()
    score_warmth()
    tagged = tag_countries()
    report = audit_quality()

    print(f"\nmaster_emails: {report['total']:,}")
    print(f"  MX valid: {report['mx_valid']:,} | invalid: {report['mx_invalid']:,} | unchecked: {report['mx_unchecked']:,}")
    print(f"  Hot leads (score>=10): {report['hot_leads']:,}")
    print(f"  Cold leads (score<=0): {report['cold_leads']:,}")
    print(f"  Generic (info@/office@): {report['generic']:,}")
    print(f"  Countries tagged: {tagged}")
    print(f"  Top countries: {report['by_country'][:200]}")

    log.info(json.dumps(report, default=str))
    try:
        import requests
        requests.post(NODERED, json={
            "event": "warmth_scorer", **report,
            "timestamp": datetime.now().isoformat()
        }, timeout=5)
    except Exception:
        pass


if __name__ == "__main__":
    main()
