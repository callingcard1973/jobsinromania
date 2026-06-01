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
            # Query: ANOFM jobs, Romania geography, recent postings
            query = """
            SELECT
                j.job_id, j.job_title, j.job_description, j.sector,
                j.city, j.salary, j.positions_available,
                j.application_deadline, j.company_name,
                j.posted_at, j.source
            FROM ij_jobs j
            WHERE j.source = 'anofm'
                AND (j.geography = 'Romania' OR j.city IS NOT NULL)
                AND j.sector IN %s
                AND j.posted_at >= NOW() - INTERVAL '30 days'
            ORDER BY j.posted_at DESC
            LIMIT 5000
            """
            cur.execute(query, (tuple(INCLUDED_SECTORS),))
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
        formatted.append({
            "id": str(job.get("job_id", "")),
            "title": job.get("job_title", "").strip(),
            "description": job.get("job_description", "").strip()[:500],
            "sector": job.get("sector", "").lower(),
            "city": job.get("city", "").strip(),
            "salary": job.get("salary", ""),
            "positions": int(job.get("positions_available", 1) or 1),
            "deadline": str(job.get("application_deadline", "")) if job.get("application_deadline") else "",
            "company": job.get("company_name", "").strip(),
            "posted": job.get("posted_at").isoformat() if job.get("posted_at") else "",
            "url": f"https://jobsinromania.github.io/jobs/{job.get('job_id', '').replace('anofm_', '')}.html"
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
