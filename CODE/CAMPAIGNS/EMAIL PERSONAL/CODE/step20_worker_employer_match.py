"""
Step 20: Worker-employer matching
Matches 756 workers in master_applicants.db (SQLite on raspibig)
with companies_clean by sector → outputs match list per worker type.

Usage:
  python step20_worker_employer_match.py
  (reads master_applicants.db from D:/MEMORY/OPT/opt/OPENDATA/DATA/)
"""

import sqlite3
import asyncpg
import asyncio
import csv
from pathlib import Path

SQLITE_PATH = "D:/MEMORY/CLAUDE/OPT/DATA/master_applicants.db"
OUT_DIR = Path(__file__).parent
DB = dict(user="tudor", password="tudor", host="127.0.0.1", port=5433, database="interjob_master")

SECTOR_MAP = {
    "construction": ["constructi", "building", "civil", "roads", "infrastructure"],
    "transport":    ["transport", "logistics", "freight", "courier", "delivery"],
    "manufacturing":["manufactur", "factory", "industrial", "production"],
    "agriculture":  ["agri", "farm", "food", "vegetable", "fruit"],
    "hospitality":  ["hotel", "restaurant", "horeca", "catering", "food service"],
    "healthcare":   ["health", "care", "medical", "nursing", "hospital"],
    "it":           ["software", "it ", "tech", "digital", "programming"],
}


def get_workers(db_path: str) -> list[dict]:
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT id, name, email, skills, target_jobs, location
            FROM applicants
        """).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"SQLite error: {e}")
        return []


async def match_employers(workers: list[dict]) -> dict:
    pool = await asyncpg.create_pool(**DB)
    results = {}

    for w in workers:
        occ = (w.get("target_jobs") or w.get("skills") or "").lower()
        matched_sector = None
        for sector, keywords in SECTOR_MAP.items():
            if any(k in occ for k in keywords):
                matched_sector = sector
                break

        if not matched_sector:
            continue

        async with pool.acquire() as conn:
            employers = await conn.fetch("""
                SELECT name, country, city, sector_name,
                  COALESCE(NULLIF(email,''), enriched_email) AS email,
                  phone, employees_count, lead_score
                FROM companies_clean
                WHERE LOWER(COALESCE(sector_name,'')) ILIKE $1
                  AND (email IS NOT NULL AND email!='' OR enriched_email IS NOT NULL AND enriched_email!='')
                  AND (is_insolvent IS NULL OR is_insolvent=false)
                  AND lead_score >= 20
                ORDER BY lead_score DESC NULLS LAST
                LIMIT 50
            """, f"%{matched_sector[:8]}%")

        results[f"{w['name']} ({matched_sector})"] = [dict(e) for e in employers]

    await pool.close()
    return results


async def main():
    workers = get_workers(SQLITE_PATH)
    print(f"Workers loaded: {len(workers)}")

    if not workers:
        print("No workers found. Check SQLite path.")
        return

    matches = await match_employers(workers)

    out = OUT_DIR / "worker_employer_matches.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["worker", "employer_name", "country", "city", "sector", "email", "phone", "lead_score"])
        for worker_name, employers in matches.items():
            for e in employers:
                w.writerow([worker_name, e["name"], e["country"], e["city"],
                             e["sector_name"], e["email"], e["phone"], e["lead_score"]])

    print(f"Matches exported -> {out}")
    print(f"Workers matched: {len(matches)}/{len(workers)}")


if __name__ == "__main__":
    asyncio.run(main())
