#!/usr/bin/env python3
"""Data Validator Agent — validates ANOFM + EURES data before publishing."""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime
import csv

import psycopg2

def validate_anofm(conn, cursor) -> tuple:
    """Validate ANOFM job counts and sector distribution."""
    # Total count
    cursor.execute("SELECT COUNT(*) FROM ij_jobs WHERE source='anofm' AND status='active'")
    total = cursor.fetchone()[0]

    if total == 0:
        return None, None, "HARD_FAIL_ZERO_JOBS", "ANOFM query returned 0 jobs"

    # Sector distribution (top 7)
    cursor.execute("""
        SELECT sector, COUNT(*) as cnt
        FROM ij_jobs WHERE source='anofm' AND status='active'
        GROUP BY sector ORDER BY cnt DESC LIMIT 7
    """)
    count_sector = {row[0] or "altul": row[1] for row in cursor.fetchall()}

    # Sample jobs per sector (for output)
    cursor.execute("""
        SELECT sector, title, city, salary_min, salary_currency
        FROM ij_jobs WHERE source='anofm' AND status='active'
        ORDER BY created_at DESC LIMIT 500
    """)
    by_sector = defaultdict(list)
    for sector, title, city, sal_min, currency in cursor.fetchall():
        s = sector or "altul"
        if len(by_sector[s]) < 4:
            loc = (city or "").split(">")[-1].strip().title() if city else ""
            f" ({int(sal_min):,} {currency or 'RON'})" if sal_min else ""
            by_sector[s].append({
                "title": title.title(),
                "city": loc,
                "salary_min": sal_min,
                "salary_currency": currency
            })

    # Check: no sector > 90% of total
    if count_sector:
        max_sector_pct = max(count_sector.values()) / total
        if max_sector_pct > 0.9:
            return None, None, "WARN_SKEWED", f"Sector distribution skewed: max {max_sector_pct*100:.1f}%"

    return total, dict(by_sector), dict(count_sector), None

def validate_eures(eures_base: str, countries: list) -> tuple:
    """Validate EURES CSV files and count jobs."""
    total = 0
    by_country = {}
    seen = set()
    warnings = []

    for country in countries:
        path = os.path.join(eures_base, country, f"{country}_contacts_50.csv")
        if not os.path.exists(path):
            warnings.append(f"EURES {country} CSV not found")
            continue

        # Check file age
        mtime = os.path.getmtime(path)
        age_days = (datetime.now() - datetime.fromtimestamp(mtime)).days
        if age_days > 7:
            warnings.append(f"EURES {country} CSV is {age_days} days old")

        # Count and deduplicate
        country_total = 0
        jobs = []
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if country_total >= 500:
                        break
                    title = (row.get("job_title") or "").strip()
                    if not title or len(title) < 5:
                        continue
                    fprint = row.get("fingerprint") or row.get("job_id") or ""
                    if fprint and fprint in seen:
                        continue
                    if fprint:
                        seen.add(fprint)
                    country_total += 1
                    total += 1
                    if len(jobs) < 4:
                        city = (row.get("city") or "").strip()
                        jobs.append((title, city))
        except Exception as e:
            warnings.append(f"Error reading EURES {country}: {e}")
            continue

        by_country[country] = jobs

    if total == 0:
        warnings.append("EURES total = 0 (continue with RO-only data)")

    return total, by_country, warnings

def main():
    config = json.loads(sys.stdin.read())

    try:
        conn = psycopg2.connect(
            host=config["db_host"],
            port=config["db_port"],
            dbname=config["db_name"],
            user=config["db_user"],
            password=config["db_pass"]
        )
        cursor = conn.cursor()

        # Validate ANOFM
        anofm_total, anofm_by_sector, anofm_count_sector, error = validate_anofm(conn, cursor)

        if error:
            output = {
                "status": "invalid",
                "error": error,
                "reason": "HARD_FAIL_ZERO_JOBS",
                "action": "ABORT"
            }
            print(json.dumps(output))
            sys.exit(1)

        # Validate EURES
        eures_total, eures_by_country, eures_warnings = validate_eures(
            config["eures_base"],
            config["eures_countries"]
        )

        # Determine status
        warnings = eures_warnings
        status = "valid" if not warnings else "valid_with_warnings"

        output = {
            "status": status,
            "anofm_total": anofm_total,
            "anofm_by_sector": anofm_by_sector,
            "anofm_count_sector": anofm_count_sector,
            "eures_total": eures_total,
            "eures_by_country": eures_by_country,
            "warnings": warnings,
            "validation_timestamp": datetime.now().isoformat()
        }

        print(json.dumps(output))
        cursor.close()
        conn.close()

    except Exception as e:
        output = {
            "status": "invalid",
            "error": f"DB error: {str(e)}",
            "reason": "DB_CONNECTION_FAILED"
        }
        print(json.dumps(output))
        sys.exit(1)

if __name__ == "__main__":
    main()
