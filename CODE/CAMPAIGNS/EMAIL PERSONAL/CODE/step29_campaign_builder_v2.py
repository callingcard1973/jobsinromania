"""
Campaign Builder v2 — supports standard_sector across all countries.
After step26 runs, use --standard-sector for cross-country queries.

Usage:
  python step29_campaign_builder_v2.py --standard-sector construction --limit 10000
  python step29_campaign_builder_v2.py --country NO --standard-sector transport --limit 5000
  python step29_campaign_builder_v2.py --country RO --sector transport --limit 2000
  python step29_campaign_builder_v2.py --country BG --min-score 30 --limit 5000
"""

import asyncpg
import asyncio
import csv
import argparse
from pathlib import Path

DB = dict(user="tudor", password="tudor", host="127.0.0.1", port=5433, database="interjob_master")
OUT_DIR = Path(__file__).parent

STANDARD_SECTORS = ["construction","transport","manufacturing","agriculture",
                    "hospitality","healthcare","it","retail","facility","trades"]


async def build(country, sector, standard_sector, limit, min_score):
    pool = await asyncpg.create_pool(**DB)

    where = ["(is_insolvent IS NULL OR is_insolvent=false)",
             "(email IS NOT NULL AND email!='' OR enriched_email IS NOT NULL AND enriched_email!='')"]
    params = []

    if country:
        params.append(country)
        where.append(f"country=${ len(params)}")
    if standard_sector:
        params.append(standard_sector)
        where.append(f"standard_sector=${len(params)}")
    elif sector:
        params.append(f"%{sector.lower()}%")
        where.append(f"LOWER(COALESCE(sector_name,'')) LIKE ${len(params)}")
    if min_score:
        params.append(min_score)
        where.append(f"lead_score>=${len(params)}")

    params.append(limit)
    query = f"""
        SELECT name, COALESCE(NULLIF(email,''),enriched_email) AS email,
          phone, city, country, sector_name, standard_sector,
          employees_count, revenue, ted_wins, lead_score, website
        FROM companies_clean
        WHERE {' AND '.join(where)}
        ORDER BY lead_score DESC NULLS LAST
        LIMIT ${len(params)}
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    parts = []
    if country: parts.append(country)
    if standard_sector: parts.append(standard_sector)
    elif sector: parts.append(sector)
    parts.append(str(len(rows)))
    out = OUT_DIR / f"campaign_{'_'.join(parts)}.csv"

    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name","email","phone","city","country",
            "sector_name","standard_sector","employees_count","revenue","ted_wins","lead_score","website"])
        w.writeheader()
        w.writerows([dict(r) for r in rows])

    print(f"Exported {len(rows):,} -> {out.name}")
    await pool.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--country", default=None)
    p.add_argument("--sector", default=None)
    p.add_argument("--standard-sector", default=None, choices=STANDARD_SECTORS + [None])
    p.add_argument("--limit", type=int, default=5000)
    p.add_argument("--min-score", type=int, default=0)
    args = p.parse_args()
    asyncio.run(build(args.country, args.sector, args.standard_sector, args.limit, args.min_score))
