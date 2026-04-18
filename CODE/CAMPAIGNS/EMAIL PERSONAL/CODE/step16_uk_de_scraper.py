"""
Step 16: UK/DE contact page email scraper
Scrapes /contact, /about, /impressum pages for companies with website but no email.
Deploy on raspibig for overnight run.

Usage:
  pip install asyncpg aiohttp beautifulsoup4 lxml
  python step16_uk_de_scraper.py --country DE --limit 10000
  python step16_uk_de_scraper.py --country GB --limit 10000
"""

import asyncio
import asyncpg
import aiohttp
from bs4 import BeautifulSoup
import re
import argparse

DB = dict(user="tudor", password="tudor", host="127.0.0.1", port=5433, database="interjob_master")
EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
CONTACT_PATHS = ["/contact", "/contact-us", "/about", "/impressum", "/kontakt", "/kontakta-oss"]
TIMEOUT = aiohttp.ClientTimeout(total=10)
CONCURRENCY = 30
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; company-research-bot/1.0)"}


async def scrape_email(session, website: str) -> str | None:
    base = website.rstrip("/")
    if not base.startswith("http"):
        base = "https://" + base
    for path in [""] + CONTACT_PATHS:
        try:
            async with session.get(base + path, headers=HEADERS, allow_redirects=True) as r:
                if r.status != 200:
                    continue
                text = await r.text(errors="ignore")
                emails = EMAIL_RE.findall(text)
                # Filter out images, scripts, freemail
                valid = [e for e in emails if "." in e.split("@")[1]
                         and not any(x in e for x in ["png","jpg","js","css","example"])
                         and e.split("@")[1] not in {"gmail.com","hotmail.com","yahoo.com","outlook.com"}]
                if valid:
                    return valid[0]
        except Exception:
            pass
    return None


async def main(country: str, limit: int):
    pool = await asyncpg.create_pool(**DB)
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, website FROM companies_clean
            WHERE country=$1
              AND website IS NOT NULL AND website != ''
              AND (email IS NULL OR email='')
              AND (enriched_email IS NULL OR enriched_email='')
            ORDER BY lead_score DESC NULLS LAST
            LIMIT $2
        """, country, limit)

    print(f"{country}: {len(rows):,} companies to scrape")
    sem = asyncio.Semaphore(CONCURRENCY)
    enriched = 0

    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        async def process(row):
            nonlocal enriched
            async with sem:
                email = await scrape_email(session, row["website"])
                if email:
                    async with pool.acquire() as conn:
                        await conn.execute(
                            "UPDATE companies_clean SET enriched_email=$1 WHERE id=$2",
                            email, row["id"]
                        )
                    enriched += 1

        tasks = [process(r) for r in rows]
        for i, coro in enumerate(asyncio.as_completed(tasks), 1):
            await coro
            if i % 500 == 0:
                print(f"  {i:,}/{len(rows):,} scraped | {enriched:,} found")

    print(f"\nDone. {enriched:,}/{len(rows):,} {country} companies enriched.")
    await pool.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--country", default="DE")
    p.add_argument("--limit", type=int, default=10000)
    args = p.parse_args()
    asyncio.run(main(args.country, args.limit))
