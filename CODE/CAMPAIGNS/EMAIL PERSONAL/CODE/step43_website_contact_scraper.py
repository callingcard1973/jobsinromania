"""Step 43: Website contact page scraper.
For companies with website but no email: fetch /contact, extract emails.
Runs async, respects rate limits, skips known generic emails.
"""
import asyncio
import aiohttp
import psycopg2
import re
import random
from urllib.parse import urljoin, urlparse

DB = dict(host='127.0.0.1', port=5433, dbname='interjob_master', user='tudor', password='tudor')
CONCURRENCY = 20
TIMEOUT = 8
BATCH_SIZE = 200
CONTACT_PATHS = ['/contact', '/contact-us', '/kontakt', '/kontakta-oss',
                 '/contactez-nous', '/contacto', '/om-oss', '/about']

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
GENERIC_RE = re.compile(r'^(noreply|no-reply|donotreply|bounce|mailer-daemon|postmaster)@')

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; InterJob/1.0; recruitment)'}

async def fetch_url(session, url):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=TIMEOUT),
                                allow_redirects=True, headers=HEADERS) as r:
            if r.status == 200 and 'text/html' in r.headers.get('content-type', ''):
                return await r.text(errors='ignore')
    except Exception:
        pass
    return None

def extract_emails(html, domain):
    if not html:
        return []
    found = EMAIL_RE.findall(html)
    results = []
    for e in found:
        e = e.lower().rstrip('.')
        if GENERIC_RE.match(e):
            continue
        if len(e) > 80:
            continue
        results.append(e)
    return list(dict.fromkeys(results))[:3]  # max 3 per page

def normalize_website(website):
    w = website.strip()
    if not w.startswith('http'):
        w = 'https://' + w
    return w.rstrip('/')

async def scrape_company(session, company_id, website):
    base = normalize_website(website)
    domain = urlparse(base).netloc

    # Try homepage first, then contact paths
    urls = [base] + [base + p for p in CONTACT_PATHS[:3]]
    for url in urls:
        html = await fetch_url(session, url)
        emails = extract_emails(html, domain)
        if emails:
            return company_id, emails[0]
    return company_id, None

async def main():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, website FROM companies_clean
        WHERE website IS NOT NULL AND website != ''
          AND (email IS NULL OR email = '')
          AND (enriched_email IS NULL OR enriched_email = '')
          AND (is_insolvent IS NULL OR is_insolvent = false)
          AND country IN ('NO','SE','DK','FI','DE','PL','RO','FR','BG')
        ORDER BY lead_score DESC NULLS LAST
        LIMIT 50000
    """)
    rows = cur.fetchall()
    print(f"Scraping {len(rows)} websites...")

    enriched = 0
    sem = asyncio.Semaphore(CONCURRENCY)
    connector = aiohttp.TCPConnector(limit=CONCURRENCY, ssl=False)

    async with aiohttp.ClientSession(connector=connector) as session:
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i:i+BATCH_SIZE]
            async def bounded(row):
                async with sem:
                    return await scrape_company(session, row[0], row[1])

            results = await asyncio.gather(*[bounded(r) for r in batch], return_exceptions=True)
            updates = [(r[1], r[1], r[0]) for r in results
                       if isinstance(r, tuple) and r[1]]
            if updates:
                cur.executemany(
                    "UPDATE companies_clean SET email=%s, enriched_email=%s WHERE id=%s",
                    updates
                )
                conn.commit()
                enriched += len(updates)
            if i % 2000 == 0:
                print(f"  {i}/{len(rows)} scraped, {enriched} enriched")
            await asyncio.sleep(random.uniform(0.5, 1.5))

    print(f"\nDone. Scraped {enriched} new emails from websites.")
    cur.close()
    conn.close()

asyncio.run(main())
