"""Step 37: DK/FI email pattern generation from website column.
Generates info@domain.dk / info@domain.fi for companies with website but no email.
"""
import asyncio
import aiodns
import psycopg2
import re
from urllib.parse import urlparse

DB = dict(host='127.0.0.1', port=5433, dbname='interjob_master', user='tudor', password='tudor')
BATCH = 500
PREFIXES = ['info', 'kontakt', 'post', 'mail']

def extract_domain(website):
    if not website:
        return None
    w = website.strip().lower()
    if not w.startswith('http'):
        w = 'http://' + w
    try:
        d = urlparse(w).netloc.lstrip('www.')
        return d if '.' in d else None
    except Exception:
        return None

async def mx_valid(resolver, domain):
    try:
        await resolver.query(domain, 'MX')
        return True
    except Exception:
        return False

async def process_batch(rows, resolver):
    results = []
    for company_id, website, country in rows:
        domain = extract_domain(website)
        if not domain:
            continue
        if not await mx_valid(resolver, domain):
            continue
        suffix = '.dk' if country == 'DK' else '.fi'
        # Prefer country-specific domain
        if not domain.endswith(suffix) and not domain.endswith('.com') and not domain.endswith('.eu'):
            continue
        email = f'info@{domain}'
        results.append((company_id, email))
    return results

async def main():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, website, country FROM companies_clean
        WHERE country IN ('DK','FI')
          AND website IS NOT NULL AND website != ''
          AND (email IS NULL OR email = '')
          AND (is_insolvent IS NULL OR is_insolvent = false)
        ORDER BY lead_score DESC NULLS LAST
        LIMIT 100000
    """)
    rows = cur.fetchall()
    print(f"Candidates: {len(rows)}")

    resolver = aiodns.DNSResolver()
    enriched = 0
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i+BATCH]
        results = await process_batch(batch, resolver)
        if results:
            cur.executemany(
                "UPDATE companies_clean SET email=%s, enriched_email=%s WHERE id=%s",
                [(r[1], r[1], r[0]) for r in results]
            )
            conn.commit()
            enriched += len(results)
        if i % 5000 == 0:
            print(f"  {i}/{len(rows)} processed, {enriched} enriched")

    print(f"Done. Enriched {enriched} DK/FI companies with pattern emails.")
    cur.execute("SELECT country, COUNT(*) FROM companies_clean WHERE country IN ('DK','FI') AND email IS NOT NULL AND email!='' GROUP BY country")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]} with email")
    cur.close()
    conn.close()

asyncio.run(main())
