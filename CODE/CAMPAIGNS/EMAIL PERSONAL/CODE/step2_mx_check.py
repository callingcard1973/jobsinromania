"""
Step 2: Async MX validation for master_emails where mx_valid IS NULL
Updates mx_valid column. Runs on laptop, ~1-2 hours for 700K emails.

Usage:
    pip install asyncpg aiodns
    python step2_mx_check.py
"""

import asyncio
import asyncpg
import aiodns
import time

DB = dict(user="tudor", password="tudor", host="127.0.0.1", port=5433, database="interjob_master")
BATCH = 500
CONCURRENCY = 200
PROGRESS_EVERY = 5000


async def check_mx(resolver, domain: str) -> bool:
    try:
        result = await resolver.query(domain, "MX")
        return len(result) > 0
    except Exception:
        return False


async def process_batch(pool, resolver, rows):
    domains = {}
    for row in rows:
        d = row["domain"] or row["email"].split("@")[-1].lower().strip()
        domains[d] = domains.get(d) or []
        domains[d].append(row["id"])

    tasks = {d: asyncio.create_task(check_mx(resolver, d)) for d in domains}
    await asyncio.gather(*tasks.values())

    updates = []
    for d, task in tasks.items():
        valid = task.result()
        for eid in domains[d]:
            updates.append((valid, eid))

    async with pool.acquire() as conn:
        await conn.executemany(
            "UPDATE master_emails SET mx_valid=$1 WHERE id=$2",
            updates
        )
    return len(updates)


async def main():
    pool = await asyncpg.create_pool(**DB, min_size=2, max_size=5)
    resolver = aiodns.DNSResolver(timeout=3, tries=1)

    async with pool.acquire() as conn:
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM master_emails WHERE mx_valid IS NULL"
        )
    print(f"Total to check: {total:,}")

    done = 0
    t0 = time.time()
    offset = 0

    while True:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, email, domain FROM master_emails WHERE mx_valid IS NULL ORDER BY id LIMIT $1 OFFSET $2",
                BATCH, offset
            )
        if not rows:
            break

        # Process in concurrent chunks
        sem = asyncio.Semaphore(CONCURRENCY)
        async def bounded(r):
            async with sem:
                return await check_mx(resolver, (r["domain"] or r["email"].split("@")[-1].lower().strip()))

        domain_results = await asyncio.gather(*[bounded(r) for r in rows])

        updates = [(domain_results[i], rows[i]["id"]) for i in range(len(rows))]
        async with pool.acquire() as conn:
            await conn.executemany(
                "UPDATE master_emails SET mx_valid=$1 WHERE id=$2",
                updates
            )

        done += len(rows)
        offset += BATCH
        elapsed = time.time() - t0
        rate = done / elapsed if elapsed > 0 else 0

        if done % PROGRESS_EVERY < BATCH:
            eta = (total - done) / rate if rate > 0 else 0
            valid_in_batch = sum(1 for v, _ in updates if v)
            print(f"  {done:,}/{total:,} ({done*100//total}%) | {rate:.0f}/s | ETA {eta/60:.1f}min | batch valid: {valid_in_batch}/{len(rows)}")

    # Final tier update
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE master_emails SET quality_tier =
                CASE
                    WHEN is_dnc=true OR is_bounced=true THEN 4
                    WHEN mx_valid=true AND is_generic=false THEN 1
                    WHEN mx_valid=true AND is_generic=true  THEN 2
                    ELSE 3
                END
        """)
        rows = await conn.fetch("""
            SELECT quality_tier, COUNT(*) as count
            FROM master_emails GROUP BY quality_tier ORDER BY quality_tier
        """)

    print("\n=== Final Quality Tiers ===")
    for r in rows:
        print(f"  Tier {r['quality_tier']}: {r['count']:,}")

    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
