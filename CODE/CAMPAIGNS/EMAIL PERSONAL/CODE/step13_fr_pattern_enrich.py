"""
Step 13: FR pattern email enrichment
Generates info@domain + contact@domain for FR companies with website but no email.
MX-checks domain before inserting. Runs overnight on raspibig or laptop.

Usage: python step13_fr_pattern_enrich.py
Requires: pip install asyncpg aiodns
"""

import asyncio
import asyncpg
import aiodns
import re

DB = dict(user="tudor", password="tudor", host="127.0.0.1", port=5433, database="interjob_master")
BATCH = 200
PREFIXES = ["info", "contact", "hr", "jobs", "recrutare"]
FREEMAIL = {"gmail.com","hotmail.com","yahoo.com","outlook.com","live.com","orange.fr",
            "free.fr","laposte.net","wanadoo.fr","sfr.fr","bbox.fr"}


def extract_domain(website: str) -> str | None:
    if not website:
        return None
    d = re.sub(r'^https?://(www\.)?', '', website.lower()).split('/')[0].strip()
    return d if '.' in d and d not in FREEMAIL else None


async def mx_ok(resolver, domain: str) -> bool:
    try:
        r = await resolver.query(domain, "MX")
        return len(r) > 0
    except Exception:
        return False


async def main():
    pool = await asyncpg.create_pool(**DB, min_size=2, max_size=5)
    resolver = aiodns.DNSResolver(timeout=3, tries=1)

    async with pool.acquire() as conn:
        total = await conn.fetchval("""
            SELECT COUNT(*) FROM companies_clean
            WHERE country='FR'
              AND (email IS NULL OR email='')
              AND (enriched_email IS NULL OR enriched_email='')
              AND website IS NOT NULL AND website != ''
        """)
    print(f"FR companies to process: {total:,}")

    offset = 0
    inserted = 0

    while True:
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, website FROM companies_clean
                WHERE country='FR'
                  AND (email IS NULL OR email='')
                  AND (enriched_email IS NULL OR enriched_email='')
                  AND website IS NOT NULL AND website != ''
                ORDER BY id LIMIT $1 OFFSET $2
            """, BATCH, offset)

        if not rows:
            break

        domains = {r["id"]: extract_domain(r["website"]) for r in rows}
        valid_domains = {eid: d for eid, d in domains.items() if d}

        # MX check unique domains
        unique = list(set(valid_domains.values()))
        mx_results = await asyncio.gather(*[mx_ok(resolver, d) for d in unique])
        mx_map = dict(zip(unique, mx_results))

        updates = []
        for eid, domain in valid_domains.items():
            if mx_map.get(domain):
                email = f"info@{domain}"
                updates.append((email, eid))

        if updates:
            async with pool.acquire() as conn:
                await conn.executemany(
                    "UPDATE companies_clean SET enriched_email=$1 WHERE id=$2 AND (enriched_email IS NULL OR enriched_email='')",
                    updates
                )
            inserted += len(updates)

        offset += BATCH
        if offset % 5000 < BATCH:
            print(f"  {offset:,}/{total:,} processed | {inserted:,} enriched")

    print(f"\nDone. {inserted:,} FR companies enriched with pattern email.")
    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
