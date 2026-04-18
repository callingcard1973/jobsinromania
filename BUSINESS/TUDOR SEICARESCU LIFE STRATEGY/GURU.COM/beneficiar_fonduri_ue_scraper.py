#!/usr/bin/env python3
"""Async Scraper for beneficiar.fonduri-ue.ro - EU Funds Procurement"""
# --
import sys, os, re, csv, json, asyncio, aiohttp, psycopg2
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
import logging, argparse
from parsers import parse_anunt, parse_proiect, clean, BASE_URL

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB = {'dbname': 'european_funds', 'user': 'tudor', 'host': '/var/run/postgresql', 'port': 5432}
DIR = Path("/opt/ACTIVE/EU_FUNDING/DATA/BENEFICIAR_FONDURI_UE")
(ANUNTURI_DIR := DIR / "ANUNTURI_BENEFICIARI_PRIVATI").mkdir(parents=True, exist_ok=True)
(PROIECTE_DIR := DIR / "PROIECTE").mkdir(parents=True, exist_ok=True)
WORKERS = 30

# -- Form data for filtered listing (open anunturi only)
OPEN_FILTER = {
    "option": "com_contentbuilder",
    "controller": "list",
    "view": "list",
    "Itemid": "107",
    "search_form_id": "2",
    "contentbuilder_filter_signal": "1",
    "cb_filter[48]": "Nu",
}

# --
async def fetch(sess, url, post_data=None):
    try:
        if post_data:
            async with sess.post(url, data=post_data, timeout=aiohttp.ClientTimeout(total=30)) as r:
                return await r.text()
        async with sess.get(url, timeout=aiohttp.ClientTimeout(total=30)) as r:
            return await r.text()
    except Exception:
        return None

# --
def extract_listing_dates(html):
    """Extract dates from listing page table rows."""
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table')
    dates = {}
    if not table:
        return dates
    for row in table.find_all('tr')[1:]:
        cells = row.find_all('td')
        if len(cells) < 4:
            continue
        link = cells[0].find('a', href=True)
        if link and 'details/2/' in link['href']:
            eid = link['href'].split('/')[-2]
            dates[eid] = {
                'data_publicare': cells[3].get_text(strip=True) if len(cells) > 3 else '',
                'data_limita': cells[4].get_text(strip=True) if len(cells) > 4 else '',
            }
    return dates

# --
def save_batch(batch, tbl, out_file):
    """Save batch to DB and CSV."""
    if not batch:
        return
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cols = list(batch[0].keys())
    for r in batch:
        try:
            cur.execute(
                f"INSERT INTO {tbl} ({','.join(cols)}) VALUES ({','.join(['%s']*len(cols))}) "
                f"ON CONFLICT (id) DO UPDATE SET {','.join(f'{c}=EXCLUDED.{c}' for c in cols[1:])}",
                [r.get(c, '') for c in cols])
        except Exception:
            pass
    conn.commit()
    conn.close()
    mode_w = 'a' if out_file.exists() else 'w'
    with open(out_file, mode_w, newline='', encoding='ascii') as f:
        cw = csv.DictWriter(f, fieldnames=batch[0].keys(), extrasaction='ignore')
        if mode_w == 'w':
            cw.writeheader()
        cw.writerows(batch)
    logger.info(f"Saved {len(batch)} {tbl}")

# --
async def scrape_mode(mode, semaphore, open_only=False):
    """Scrape anunturi or proiecte. Skips records already complete in DB."""
    suffix = f"_{mode}_open" if open_only else f"_{mode}"
    state_file = DIR / f"state{suffix}.json"
    state = json.load(open(state_file)) if state_file.exists() else {'scraped': [], 'page': 0}
    tbl = 'beneficiari_privati' if mode == 'anunturi' else 'proiecte'
    # Skip already-complete records
    conn = psycopg2.connect(**DB); cur = conn.cursor()
    if tbl == 'proiecte':
        cur.execute("SELECT id FROM proiecte WHERE axa != '' AND proceduri != ''")
    else:
        cur.execute("SELECT id FROM beneficiari_privati WHERE cod_smis != '' AND email LIKE '%%@%%'")
    complete = {r[0] for r in cur.fetchall()}; conn.close()
    scraped = set(state['scraped']) | complete
    logger.info(f"{mode}: {len(complete)} complete, skipping")
    out_file = (ANUNTURI_DIR / "beneficiari_privati.csv") if mode == 'anunturi' else (PROIECTE_DIR / "proiecte.csv")
    tbl = 'beneficiari_privati' if mode == 'anunturi' else 'proiecte'
    url_base = f"{BASE_URL}/anunturi" if mode == 'anunturi' else f"{BASE_URL}/proiecte"
    detail_type = 2 if mode == 'anunturi' else 1
    page_size = 100 if open_only else 10

    async with aiohttp.ClientSession(
        headers={'User-Agent': 'Mozilla/5.0'},
        connector=aiohttp.TCPConnector(ssl=False)
    ) as sess:
        page = state['page']
        while page < 5000:
            if open_only and mode == 'anunturi':
                post_data = {**OPEN_FILTER, "limit": str(page_size), "limitstart": str(page * page_size)}
                html = await fetch(sess, f"{url_base}/2/entry?search_form_id=2", post_data)
            else:
                html = await fetch(sess, f"{url_base}?start={page*page_size}")
            if not html:
                break
            listing_dates = extract_listing_dates(html) if mode == 'anunturi' else {}
            ids = [int(m) for m in re.findall(f'details/{detail_type}/(\\d+)', html)]
            if not ids:
                break

            async def scrape_one(eid):
                if eid in scraped:
                    return None
                async with semaphore:
                    detail = await fetch(sess, f"{url_base}/details/{detail_type}/{eid}/")
                    if not detail:
                        return None
                    if mode == 'anunturi':
                        d = parse_anunt(detail, eid, listing_dates.get(str(eid)))
                    else:
                        d = parse_proiect(detail, eid)
                    logger.info(f"{mode} {eid}")
                    return d

            results = await asyncio.gather(*[scrape_one(eid) for eid in ids])
            batch = [r for r in results if r]
            save_batch(batch, tbl, out_file)
            scraped.update(r['id'] for r in batch)
            state['scraped'] = list(scraped)
            state['page'] = page + 1
            json.dump(state, open(state_file, 'w'))
            page += 1

    logger.info(f"Done {mode}")

# --
def flush_batch(batch, sql):
    if not batch: return
    conn = psycopg2.connect(**DB); cur = conn.cursor()
    cur.executemany(sql, batch); conn.commit(); conn.close(); batch.clear()

async def fix_descriere(workers):
    """Fill missing descriptions by fetching lot pages."""
    import requests as req
    conn = psycopg2.connect(**DB); cur = conn.cursor()
    cur.execute("SELECT id FROM beneficiari_privati WHERE descriere IS NULL OR descriere = '' ORDER BY id DESC LIMIT 10000")
    ids = [r[0] for r in cur.fetchall()]; conn.close()
    logger.info(f"Fixing descriere for {len(ids)} entries..."); batch = []
    sql = "UPDATE beneficiari_privati SET descriere = %s WHERE id = %s"
    async with aiohttp.ClientSession(headers={'User-Agent': 'Mozilla/5.0'}, connector=aiohttp.TCPConnector(ssl=False)) as sess:
        for eid in ids:
            async with asyncio.Semaphore(workers):
                html = await fetch(sess, f"{BASE_URL}/anunturi/details/2/{eid}/")
                if not html: continue
                lm = re.search(r'desc-lot\?d=(\d+)', html)
                if not lm: continue
                lhtml = req.get(f"{BASE_URL}/desc-lot?d={lm.group(1)}", verify=False).text
                cs = BeautifulSoup(lhtml, 'html.parser').find('section', class_='article-content')
                if cs: batch.append((clean(cs.get_text()[:2000]), eid))
            if len(batch) >= 10: flush_batch(batch, sql)
    flush_batch(batch, sql)

def fill_specs(workers):
    """Download spec PDFs for records missing spec_text. Slow, safe."""
    from parsers import fetch_spec
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("SELECT id, spec_url FROM beneficiari_privati WHERE spec_url IS NOT NULL AND spec_url != '' AND (spec_text IS NULL OR spec_text = '') ORDER BY id DESC LIMIT 5000")
    rows = cur.fetchall()
    conn.close()
    logger.info(f"Filling specs for {len(rows)} records...")
    batch = []
    for i, (rid, spec_url) in enumerate(rows):
        m = re.search(r'ann=(\d+)&lot=(\d+)', spec_url)
        if not m: continue
        _, text = fetch_spec(int(m.group(1)), m.group(2))
        if text:
            batch.append((text, rid))
            logger.info(f"spec {rid} ({len(text)} chars)")
        if len(batch) >= 10:
            flush_batch(batch, "UPDATE beneficiari_privati SET spec_text = %s WHERE id = %s")
        if i and i % 100 == 0: logger.info(f"Progress: {i}/{len(rows)}")
    flush_batch(batch, "UPDATE beneficiari_privati SET spec_text = %s WHERE id = %s")

# --
def main():
    p = argparse.ArgumentParser()
    p.add_argument('--both', action='store_true')
    p.add_argument('--anunturi', action='store_true')
    p.add_argument('--proiecte', action='store_true')
    p.add_argument('--open-only', action='store_true', help='Only scrape open anunturi')
    p.add_argument('--all', action='store_true', help='Scrape all (including closed)')
    p.add_argument('--fix-desc', action='store_true')
    p.add_argument('--fill-specs', action='store_true', help='Download specs for records missing spec_text')
    p.add_argument('--workers', type=int, default=WORKERS)
    p.add_argument('--status', action='store_true')
    args = p.parse_args()
    open_only = not args.all
    if args.status:
        conn = psycopg2.connect(**DB)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*), COUNT(CASE WHEN descriere != '' THEN 1 END) FROM beneficiari_privati")
        an, an_desc = cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM proiecte")
        pr = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM beneficiari_privati WHERE data_limita > to_char(CURRENT_DATE, 'DD.MM.YYYY')")
        open_count = cur.fetchone()[0]
        conn.close()
        print(f"ANUNTURI: {an} (descriere: {an_desc}, open: {open_count}) | PROIECTE: {pr}")
        return
    if args.fill_specs:
        fill_specs(args.workers)
    elif args.fix_desc:
        asyncio.run(fix_descriere(args.workers))
    elif args.both:
        async def run_both():
            w = max(3, args.workers // 2)
            await asyncio.gather(
                scrape_mode('proiecte', asyncio.Semaphore(w)),
                scrape_mode('anunturi', asyncio.Semaphore(w), open_only))
        asyncio.run(run_both())
    elif args.proiecte:
        asyncio.run(scrape_mode('proiecte', asyncio.Semaphore(args.workers)))
    else:
        asyncio.run(scrape_mode('anunturi', asyncio.Semaphore(args.workers), open_only))

if __name__ == '__main__':
    main()
