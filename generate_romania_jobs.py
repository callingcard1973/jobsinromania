#!/usr/bin/env python3
"""Extract ANOFM Romania jobs from ij_jobs, output JSON feed."""

import json
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("Error: psycopg2 not found. Install: pip install psycopg2-binary")
    sys.exit(1)

# DB config
DB_HOST = os.getenv("DB_HOST", "192.168.100.21")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "interjob_master")
DB_USER = os.getenv("DB_USER", "tudor")
DB_PASS = os.getenv("DB_PASS", "tudor")

# Output
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "data", "jobs.json")

# Sectors to include (ANOFM Romania jobs)
INCLUDED_SECTORS = [
    "agricultura", "constructii", "horeca", "logistica", "IT",
    "productie", "sanatate", "transport", "vanzari", "servicii",
    "mecanica", "energie", "alimentar", "turism"
]


def get_conn():
    """Connect to PostgreSQL."""
    try:
        return psycopg2.connect(
            host=DB_HOST, port=DB_PORT, database=DB_NAME,
            user=DB_USER, password=DB_PASS
        )
    except psycopg2.Error as e:
        print(f"DB connection failed: {e}")
        sys.exit(1)


def extract_jobs() -> List[Dict]:
    """Extract ANOFM jobs with Romania geography."""
    conn = get_conn()
    jobs = []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Query: ANOFM jobs, Romania (city or county filter), recent postings
            query = """
            SELECT
                j.id, j.source_job_id, j.title, j.description, j.sector,
                j.city, j.county, j.salary_min, j.salary_max, j.salary_currency,
                j.contract_type, j.published_at, j.source, j.company_id
            FROM ij_jobs j
            WHERE j.source = 'anofm'
                AND (j.city IS NOT NULL OR j.county IS NOT NULL)
                AND (j.sector IS NULL OR LOWER(j.sector) = ANY(%s))
                AND j.published_at >= NOW() - INTERVAL '30 days'
                AND j.status = 'active'
            ORDER BY j.published_at DESC
            LIMIT 5000
            """
            cur.execute(query, (INCLUDED_SECTORS,))
            rows = cur.fetchall()
            for row in rows:
                jobs.append(dict(row))
    except psycopg2.Error as e:
        print(f"Query error: {e}")
        conn.close()
        sys.exit(1)
    finally:
        conn.close()
    return jobs


def format_jobs(jobs: List[Dict]) -> List[Dict]:
    """Format jobs for HTML generation."""
    formatted = []
    for job in jobs:
        salary_range = ""
        if job.get("salary_min") and job.get("salary_max"):
            salary_range = f"{job['salary_min']}-{job['salary_max']} {job.get('salary_currency', 'RON')}"
        elif job.get("salary_min"):
            salary_range = f"from {job['salary_min']} {job.get('salary_currency', 'RON')}"

        city = job.get("city", "").strip() or job.get("county", "").strip()

        formatted.append({
            "id": str(job.get("id", "")),
            "title": job.get("title", "").strip(),
            "description": job.get("description", "").strip()[:500],
            "sector": (job.get("sector") or "").lower(),
            "city": city,
            "salary": salary_range,
            "contract": job.get("contract_type", "").lower(),
            "company_id": job.get("company_id"),
            "posted": job.get("published_at").isoformat() if job.get("published_at") else "",
            "url": f"https://jobsinromania.github.io/jobs/{job.get('source_job_id', '').replace('anofm_', '')}.html"
        })
    return formatted


def save_json(jobs: List[Dict]):
    """Save jobs to JSON file."""
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    output = {
        "generated": datetime.utcnow().isoformat(),
        "count": len(jobs),
        "jobs": jobs
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(jobs)} jobs to {OUTPUT_FILE}")


def main():
    jobs = extract_jobs()
    if not jobs:
        print("No jobs found.")
        return
    formatted = format_jobs(jobs)
    save_json(formatted)


if __name__ == "__main__":
    main()
