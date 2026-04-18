"""
Step 14: Sector Campaign Builder
Input: country + sector keyword → outputs campaign CSV in 30 seconds.

Usage:
  python campaign_builder.py --country NO --sector construction --limit 5000
  python campaign_builder.py --country RO --sector transport --limit 2000
  python campaign_builder.py --country BG --limit 10000
"""

import asyncpg
import asyncio
import csv
import argparse
from pathlib import Path

DB = dict(user="tudor", password="tudor", host="127.0.0.1", port=5433, database="interjob_master")
OUT_DIR = Path(__file__).parent


async def build(country: str, sector: str | None, limit: int, min_score: int):
    pool = await asyncpg.create_pool(**DB)

    where = ["cc.country = $1", "(cc.is_insolvent IS NULL OR cc.is_insolvent=false)",
             "(cc.email IS NOT NULL AND cc.email != '' OR cc.enriched_email IS NOT NULL AND cc.enriched_email != '')"]
    params = [country]

    if sector:
        params.append(f"%{sector.lower()}%")
        where.append(f"LOWER(COALESCE(cc.sector_name,'')) LIKE ${len(params)}")

    if min_score:
        params.append(min_score)
        where.append(f"cc.lead_score >= ${len(params)}")

    params.append(limit)
    query = f"""
        SELECT
            cc.name,
            COALESCE(NULLIF(cc.email,''), cc.enriched_email) AS email,
            cc.phone,
            cc.city,
            cc.sector_name,
            cc.employees_count,
            cc.revenue,
            cc.ted_wins,
            cc.lead_score,
            cc.website
        FROM companies_clean cc
        WHERE {' AND '.join(where)}
        ORDER BY cc.lead_score DESC NULLS LAST
        LIMIT ${len(params)}
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    sector_slug = f"_{sector}" if sector else ""
    out = OUT_DIR / f"campaign_{country}{sector_slug}_{len(rows)}.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name","email","phone","city","sector_name",
                                           "employees_count","revenue","ted_wins","lead_score","website"])
        w.writeheader()
        w.writerows([dict(r) for r in rows])

    print(f"Exported {len(rows):,} companies -> {out}")
    await pool.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--country", required=True)
    p.add_argument("--sector", default=None)
    p.add_argument("--limit", type=int, default=5000)
    p.add_argument("--min-score", type=int, default=0)
    args = p.parse_args()
    asyncio.run(build(args.country, args.sector, args.limit, args.min_score))
