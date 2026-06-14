#!/usr/bin/env python3
"""Post job listings to Facebook pages in three targeted modes: by-page, weekly, drain."""

import argparse
import json
import psycopg2
import requests
from datetime import date, datetime, timezone
from pathlib import Path

DB_DSN     = "host=localhost dbname=interjob_master user=tudor password=REDACTED"
PAGES_JSON = Path("/opt/ACTIVE/SCRAPERS/ROMANIA/data/fb_pages.json")
GRAPH      = "https://graph.facebook.com/v19.0"
APPLY_URL  = "https://interjob.ro/apply.html"

# Set by --dry-run: print the message that would be posted, hit no API, write no DB rows.
DRY = False

SECTOR_EN = {"agricultura": "Agriculture", "constructii": "Construction", "productie": "Production",
             "it": "IT & Tech", "vanzari": "Sales", "sanatate": "Healthcare", "horeca": "HoReCa",
             "transport": "Transport", "logistica": "Logistics", "altul": "Other"}

# by-page mode: page_id -> {sectors, lang, tags}; trailing comment is the page name.
PAGE_CONFIG = {
    "1092630100607942": {"sectors": ["agricultura", "constructii", "productie"], "lang": "en", "tags": "#FarmworkersEurope #AgriJobs #Romania #WorkAbroad #SeasonalWork"},  # Farmworkers for Europe
    "194159297123454": {"sectors": ["it", "vanzari", "sanatate", "horeca"], "lang": "en", "tags": "#BucharestJobs #EnglishSpeaking #Romania #Expat #WorkInRomania"},  # Bucharest English speaking jobs
    "111855213712322": {"sectors": ["constructii", "productie", "transport", "logistica", "vanzari"], "lang": "ro", "tags": "#JoburiRomania #Angajari #Manpower #Munca #ANOFM"},  # ManpowerDristor
    "102068074657345": {"sectors": ["it", "sanatate", "vanzari", "horeca"], "lang": "en", "tags": "#ExpatsinRomania #BucharestJobs #WorkInRomania #Expat"},  # Expats in Romania
    "288102411055455": {"sectors": ["it", "sanatate", "vanzari"], "lang": "en", "tags": "#ExpatsinRomania #Romania #Jobs #Relocation"},  # Expats in Romania FB Page
    "1125478493983950": {"sectors": ["agricultura"], "lang": "en", "tags": "#Agroevolution #Agriculture #Romania #Farming #AgroJobs"},  # Agroevolution.com
    "819179348138132": {"sectors": ["agricultura"], "lang": "en", "tags": "#RomanianFarmland #Agriculture #Romania #FarmJobs"},  # Romanian farmland for sale
    "469572073080584": {"sectors": ["agricultura"], "lang": "en", "tags": "#BuyRomanianLand #Romania #Agriculture #FarmWork"},  # Buyromanianland
    "61590749303510": {"sectors": ["it", "vanzari", "sanatate", "horeca"], "lang": "en", "tags": "#AsianJobs #JobsInRomania #WorkInRomania #Expat"},  # Asian Jobs in Romania
}

# weekly mode: ManpowerDristor, Expats in Romania, Bucharest English speaking jobs
WEEKLY_CHANNEL = "weekly_digest"
WEEKLY_PAGES = ["111855213712322", "102068074657345", "194159297123454"]

# drain mode: base pages by name + sector-specific extras
DRAIN_PAGES = ["Expats in Romania", "Expats in Romania FB Page",
               "Bucharest English speaking jobs", "ManpowerDristor", "Farmworkers for Europe"]
SECTOR_PAGES = {"constructii": ["Farmworkers for Europe"], "agricultura": ["Farmworkers for Europe"],
                "productie": ["Farmworkers for Europe"], "sanatate": [], "horeca": [],
                "transport": [], "vanzari": []}


def load_pages() -> list:
    return json.loads(PAGES_JSON.read_text(encoding="utf-8"))


def tokens_by_id() -> dict:
    return {p["id"]: p["token"] for p in load_pages()}


def post_to_page(page_id: str, token: str, text: str) -> str:
    if DRY:
        print(f"  [DRY] would post to {page_id} ({len(text)} chars):\n{text}\n")
        return "DRY"
    try:
        r = requests.post(f"{GRAPH}/{page_id}/feed",
                          json={"message": text, "access_token": token}, timeout=30)
        if r.ok:
            return r.json().get("id", "ok")
        return f"ERR {r.status_code}: {r.text[:120]}"
    except Exception as e:
        return f"ERR: {e}"


def post_broadcast(tokens: dict, page_ids, message: str) -> bool:
    any_ok = False
    for pid in page_ids:
        token = tokens.get(pid)
        if not token:
            print(f"[SKIP] {pid}: no token")
            continue
        result = post_to_page(pid, token, message)
        ok = "ERR" not in result
        print(f"  {'OK' if ok else 'FAIL'} page={pid} -> {result}")
        any_ok = any_ok or ok
    return any_ok


def bypage_message(jobs: list, lang: str, tags: str) -> str:
    en = lang == "en"
    head = "Jobs available" if en else "Locuri de munca disponibile"
    lines = [f"{head} - {date.today().strftime('%d %b %Y')}\n"]
    for j in jobs:
        location = f"{j['city']}, {j['county']}" if j.get("county") else (j.get("city") or "Romania")
        salary = f" | {j['salary_text']}" if j.get("salary_text") else ""
        if en:
            sector_label = SECTOR_EN.get(j["sector"] or "", j["sector"] or "")
            lines.append(f"> {j['job_title']} - {sector_label} | {location}{salary}")
        else:
            lines.append(f"> {j['job_title']} - {location}{salary}")
    lines += ["", f"{'Apply free' if en else 'Aplica gratuit'}: {APPLY_URL}",
              f"{'More jobs' if en else 'Mai multe'}: https://interjob.ro", "", tags]
    return "\n".join(lines)


def mode_by_page(conn):
    tokens = tokens_by_id()
    total_ok = 0
    for page_id, cfg in PAGE_CONFIG.items():
        token = tokens.get(page_id)
        if not token:
            print(f"[SKIP] {page_id}: no token")
            continue
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, city, county, sector, CASE WHEN salary_min IS NOT NULL"
                " THEN CONCAT(salary_min::int,'-',salary_max::int,' ',salary_currency) ELSE NULL END"
                " FROM ij_jobs WHERE status='active' AND sector=ANY(%s)"
                " AND created_at >= NOW() - INTERVAL '7 days' ORDER BY created_at DESC LIMIT 3",
                (cfg["sectors"],))
            cols = ["id", "job_title", "city", "county", "sector", "salary_text"]
            jobs = [dict(zip(cols, r)) for r in cur.fetchall()]
        if not jobs:
            print(f"[SKIP] {page_id}: no recent jobs for {cfg['sectors']}")
            continue
        ids = [j["id"] for j in jobs]
        with conn.cursor() as cur:
            cur.execute("SELECT job_id FROM job_posts WHERE channel='posted'"
                        " AND post_text LIKE %s AND job_id = ANY(%s)",
                        (f"%{page_id}%", [str(j) for j in ids]))
            posted = {r[0] for r in cur.fetchall()}
        new_jobs = [j for j in jobs if str(j["id"]) not in posted]
        if not new_jobs:
            print(f"[SKIP] {page_id}: all jobs already posted")
            continue
        text = bypage_message(new_jobs, cfg["lang"], cfg["tags"])
        result = post_to_page(page_id, token, text)
        ok = "ERR" not in result
        print(f"  {'OK' if ok else 'FAIL'} page={page_id} jobs={len(new_jobs)} -> {result}")
        if ok:
            if not DRY:
                # page_id stored inside post_text is the per-page dedup marker.
                with conn.cursor() as cur:
                    for jid in ids:
                        cur.execute("INSERT INTO job_posts (job_id, channel, post_text, posted_at)"
                                    " VALUES (%s,'posted',%s,NOW()) ON CONFLICT DO NOTHING",
                                    (str(jid), f"[page:{page_id}] {text[:200]}"))
                conn.commit()
            total_ok += 1
    print(f"[DONE] Posted to {total_ok}/{len(PAGE_CONFIG)} pages")


def weekly_message(jobs: list) -> str:
    lines = ["Weekly Top Jobs in Romania - Best-paid openings this week!\n",
             "Apply now: " + APPLY_URL + "\n"]
    for i, j in enumerate(jobs, 1):
        sector = j.get("sector") or "altul"
        sec_label = SECTOR_EN.get(sector, sector.title())
        smin, smax, cur = j["salary_min"], j["salary_max"], j["salary_currency"] or ""
        salary = f"{smin:.0f}-{smax:.0f} {cur}".strip() if smin and smax else f"{smin:.0f} {cur}".strip()
        location = ", ".join(filter(None, [j.get("city"), j.get("county")]))
        lines.append(f"{i}. {j['title']}\n   {location} | {salary} | {sec_label}")
    lines.append("\n> " + APPLY_URL + "\n\n#JobsInRomania #WorkInRomania #Romania #Angajari"
                 " #Jobs #Hiring #Salary #Expat #BucharestJobs #CareerRomania")
    return "\n".join(lines)


def mode_weekly(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT job_id FROM job_posts WHERE channel=%s"
                    " AND posted_at >= NOW() - INTERVAL '7 days'", (WEEKLY_CHANNEL,))
        posted_ids = {r[0] for r in cur.fetchall()}
        cur.execute("SELECT id, title, city, county, sector, salary_min, salary_max, salary_currency"
                    " FROM ij_jobs WHERE status='active' AND salary_min IS NOT NULL"
                    " AND created_at >= NOW() - INTERVAL '7 days' ORDER BY salary_min DESC LIMIT 10")
        cols = ["id", "title", "city", "county", "sector", "salary_min", "salary_max", "salary_currency"]
        jobs = [dict(zip(cols, r)) for r in cur.fetchall()]
    new_jobs = [j for j in jobs if str(j["id"]) not in posted_ids]
    if not new_jobs:
        print("[SKIP] All top jobs already posted this week")
        return
    message = weekly_message(new_jobs)
    if not post_broadcast(tokens_by_id(), WEEKLY_PAGES, message):
        print("[DONE] No successful posts - not marking")
        return
    if DRY:
        print(f"[DRY] would mark {len(new_jobs)} jobs as posted")
        return
    now = datetime.now(timezone.utc)
    with conn.cursor() as cur:
        for jid in (j["id"] for j in new_jobs):
            cur.execute("INSERT INTO job_posts (job_id, channel, post_text, posted_at)"
                        " VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                        (str(jid), WEEKLY_CHANNEL, message[:500], now))
    conn.commit()
    print(f"[DONE] Marked {len(new_jobs)} jobs as posted")


def mode_drain(conn):
    all_pages = {p["name"]: p for p in load_pages()}
    with conn.cursor() as cur:
        cur.execute("SELECT id, job_id, job_title, sector, post_text, ig_text"
                    " FROM job_posts WHERE channel='pending' ORDER BY posted_at ASC")
        cols = [d[0] for d in cur.description]
        posts = [dict(zip(cols, r)) for r in cur.fetchall()]
    if not posts:
        print("[INFO] No pending posts")
        return
    print(f"[INFO] {len(posts)} pending posts")
    for post in posts:
        text = post["post_text"] or ""
        if not text:
            print(f"[SKIP] id={post['id']} - empty post_text")
            continue
        targets = list(dict.fromkeys(DRAIN_PAGES + SECTOR_PAGES.get(post["sector"] or "", [])))
        results = []
        for name in targets:
            page = all_pages.get(name)
            if not page:
                print(f"  [WARN] Page '{name}' not in fb_pages.json")
                continue
            result = post_to_page(page["id"], page["token"], text)
            print(f"  {'OK' if 'ERR' not in result else 'FAIL'} [{post['job_title']}] -> {name}: {result}")
            results.append(result)
        if DRY:
            continue
        status = "posted" if all("ERR" not in r for r in results) else "error"
        with conn.cursor() as cur:
            cur.execute("DELETE FROM job_posts WHERE job_id=(SELECT job_id FROM job_posts WHERE id=%s) AND channel=%s AND id!=%s", (post["id"], status, post["id"]))
            cur.execute("UPDATE job_posts SET channel=%s WHERE id=%s", (status, post["id"]))
        conn.commit()
    print("[DONE]")


MODES = {"by-page": mode_by_page, "weekly": mode_weekly, "drain": mode_drain}


def main():
    global DRY
    parser = argparse.ArgumentParser(description="Post job listings to Facebook pages.")
    parser.add_argument("--mode", choices=list(MODES), default="by-page")
    parser.add_argument("--dry-run", action="store_true", help="print messages, no FB call, no DB write")
    args = parser.parse_args()
    DRY = args.dry_run
    conn = psycopg2.connect(DB_DSN)
    try:
        MODES[args.mode](conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
