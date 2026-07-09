#!/usr/bin/env python3
"""Daily job market roundup publisher for interjob.ro — RO + EN, translation, Yoast SEO, newsletter CTA."""

import base64
import csv
import os
import time
from collections import defaultdict
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv("/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED/wp_sites.env")

DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS = "localhost", 5432, "interjob_master", "tudor", "RASPI_PW_REDACTED"
WP_URL = "https://interjob.ro"
WP_USER = os.getenv("WP_INTERJOB_USER", "apaminerala")
WP_PASS = os.getenv("WP_INTERJOB_PASS", "")
EURES_BASE = "/opt/ACTIVE/SCRAPER_DATA/csv/EURES"
APPLY_URL = "https://interjob.ro/apply.html"

EURES_COUNTRIES = ["Norway", "Denmark", "Sweden", "Finland", "Germany", "Netherlands", "France"]

SECTOR_LABELS_RO = {
    "constructii": "Construcții", "it": "IT & Tehnologie", "vanzari": "Vânzări & Retail",
    "productie": "Producție & Industrie", "horeca": "HoReCa", "transport": "Transport & Logistică",
    "logistica": "Logistică & Depozitare", "sanatate": "Sănătate & Medicină",
    "agricultura": "Agricultură", "altul": "Alte domenii",
}
SECTOR_LABELS_EN = {
    "constructii": "Construction", "it": "IT & Technology", "vanzari": "Sales & Retail",
    "productie": "Production & Manufacturing", "horeca": "HoReCa & Hospitality",
    "transport": "Transport & Logistics", "logistica": "Warehousing & Logistics",
    "sanatate": "Healthcare & Medicine", "agricultura": "Agriculture", "altul": "Other fields",
}

RO_MONTHS = ["","ianuarie","februarie","martie","aprilie","mai","iunie",
             "iulie","august","septembrie","octombrie","noiembrie","decembrie"]

_translators: dict = {}


def get_translator(src: str, tgt: str):
    key = f"{src}_{tgt}"
    if key not in _translators:
        from deep_translator import GoogleTranslator
        _translators[key] = GoogleTranslator(source=src, target=tgt)
    return _translators[key]


def translate_batch(titles: List[str], src: str = "auto", tgt: str = "ro") -> List[str]:
    if not titles:
        return titles
    try:
        tr = get_translator(src, tgt)
        joined = "\n".join(t[:120] for t in titles)
        translated = tr.translate(joined[:4900]) or joined
        parts = translated.split("\n")
        while len(parts) < len(titles):
            parts.append(titles[len(parts)])
        return [p.strip() or titles[i] for i, p in enumerate(parts[:len(titles)])]
    except Exception:
        return titles


def db_connect():
    return psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS)


def ensure_table(conn):
    with conn.cursor() as cur:
        cur.execute("""CREATE TABLE IF NOT EXISTS wp_roundup_log (
            id SERIAL PRIMARY KEY, roundup_date DATE NOT NULL,
            lang CHAR(2) NOT NULL, wp_post_id INT,
            published_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(roundup_date, lang)
        )""")
    conn.commit()


def already_published(conn, lang: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM wp_roundup_log WHERE roundup_date=%s AND lang=%s",
                    (date.today().isoformat(), lang))
        return cur.fetchone() is not None


def record_publish(conn, lang: str, post_id: int):
    with conn.cursor() as cur:
        cur.execute("INSERT INTO wp_roundup_log (roundup_date,lang,wp_post_id) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                    (date.today().isoformat(), lang, post_id))
    conn.commit()


def get_anofm_stats(conn) -> Tuple[int, Dict, Dict]:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM ij_jobs WHERE source='anofm' AND status='active'")
        total = cur.fetchone()[0]
        cur.execute("""SELECT sector, title, city, salary_min, salary_currency
            FROM ij_jobs WHERE source='anofm' AND status='active'
            ORDER BY created_at DESC LIMIT 500""")
        rows = cur.fetchall()
    by_sector: Dict[str, List[str]] = defaultdict(list)
    count_sector: Dict[str, int] = defaultdict(int)
    for sector, title, city, sal_min, currency in rows:
        s = sector or "altul"
        count_sector[s] += 1
        if len(by_sector[s]) < 4:
            loc = (city or "").split(">")[-1].strip().title()
            sal = f" ({int(sal_min):,} {currency or 'RON'})" if sal_min else ""
            by_sector[s].append((title.title(), loc, sal))
    return total, dict(by_sector), dict(count_sector)


def get_eures_stats() -> Tuple[int, Dict[str, List[Tuple[str, str, str]]]]:
    """Returns total count and jobs per country with original + Romanian translated title."""
    total = 0
    raw: Dict[str, List] = defaultdict(list)
    seen = set()
    for country in EURES_COUNTRIES:
        path = os.path.join(EURES_BASE, country, f"{country}_contacts_50.csv")
        if not os.path.exists(path):
            continue
        count = 0
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for row in csv.DictReader(f):
                if count >= 500:
                    break
                title = (row.get("job_title") or "").strip()
                if not title or len(title) < 5:
                    continue
                fprint = row.get("fingerprint") or row.get("job_id") or ""
                if fprint and fprint in seen:
                    continue
                if fprint:
                    seen.add(fprint)
                count += 1
                total += 1
                if len(raw[country]) < 4:
                    raw[country].append((title, (row.get("city") or "").strip()))

    by_country: Dict[str, List[Tuple[str, str, str]]] = {}
    for country, jobs in raw.items():
        orig_titles = [t for t, _ in jobs]
        ro_titles = translate_batch(orig_titles, src="auto", tgt="ro")
        en_titles = translate_batch(orig_titles, src="auto", tgt="en")
        time.sleep(0.4)
        by_country[country] = [
            (ro_titles[i], en_titles[i], jobs[i][1]) for i in range(len(jobs))
        ]
    return total, by_country


def newsletter_block(lang: str) -> str:
    if lang == "ro":
        return (
            '<div style="background:#f0f7ff;border:2px solid #0073aa;border-radius:8px;'
            'padding:20px;margin:30px 0;text-align:center">'
            '<h3 style="margin-top:0;color:#0073aa">📩 Primești zilnic ofertele noi pe email</h3>'
            '<p style="margin:8px 0">Abonează-te la newsletter-ul InterJob.ro și fii primul care află '
            'cele mai bune locuri de muncă din România și Europa.</p>'
            f'<a href="{APPLY_URL}" style="background:#0073aa;color:white;padding:10px 22px;'
            'text-decoration:none;border-radius:4px;display:inline-block;margin-top:8px">'
            'Abonează-te gratuit</a></div>'
        )
    else:
        return (
            '<div style="background:#f0f7ff;border:2px solid #0073aa;border-radius:8px;'
            'padding:20px;margin:30px 0;text-align:center">'
            '<h3 style="margin-top:0;color:#0073aa">📩 Get daily job alerts by email</h3>'
            '<p style="margin:8px 0">Subscribe to InterJob.ro newsletter and be the first to know '
            'about new job openings in Romania and Europe.</p>'
            f'<a href="{APPLY_URL}" style="background:#0073aa;color:white;padding:10px 22px;'
            'text-decoration:none;border-radius:4px;display:inline-block;margin-top:8px">'
            'Subscribe for free</a></div>'
        )


def build_ro(today_str: str, anofm_total: int, by_sector: Dict, count_sector: Dict,
             eures_total: int, by_country: Dict) -> Tuple[str, str, str, str]:
    datetime.now()
    title = f"Piața muncii {today_str}: {anofm_total:,} locuri de muncă în România și Europa"
    slug = f"piata-muncii-{date.today().isoformat()}"
    meta = f"Piața muncii {today_str}: {anofm_total:,} posturi active în România și {eures_total:,}+ în Europa. Construcții, IT, HoReCa, transport."
    meta = meta[:155]

    top2_ro = [SECTOR_LABELS_RO.get(s, s.title())
               for s, _ in sorted(count_sector.items(), key=lambda x: x[1], reverse=True)[:2]]
    h2_ro = f"Locuri de muncă {' și '.join(top2_ro)} în România — {today_str}"
    h2_eu = f"Oferte de muncă în Europa — {today_str}"

    L = []
    L.append(f"<p>Azi, <strong>{today_str}</strong>, sunt disponibile "
             f"<strong>{anofm_total:,} locuri de muncă active în România</strong> și "
             f"<strong>{eures_total:,}+ oferte în Europa</strong>.</p>")
    L.append(newsletter_block("ro"))
    L.append(f"<hr><h2>{h2_ro}</h2>")
    for sector, cnt in sorted(count_sector.items(), key=lambda x: x[1], reverse=True)[:7]:
        label = SECTOR_LABELS_RO.get(sector, sector.title())
        L.append(f"<h3>{label} — {cnt:,} posturi</h3><ul>")
        for t, loc, sal in by_sector.get(sector, [])[:4]:
            L.append(f"<li>{t}{' — ' + loc if loc else ''}{sal}</li>")
        L.append("</ul>")
    L.append(f"<hr><h2>{h2_eu}</h2>")
    L.append(f"<p>Peste <strong>{eures_total:,} oferte</strong> în țările partenere.</p>")
    for country, jobs in by_country.items():
        L.append(f"<h3>{country}</h3><ul>")
        for ro_title, _, city in jobs[:4]:
            L.append(f"<li>{ro_title}{' — ' + city if city else ''}</li>")
        L.append("</ul>")
    L.append(newsletter_block("ro"))
    L.append(f'<p style="text-align:center"><a href="{APPLY_URL}" style="background:#e65c00;color:white;'
             f'padding:14px 28px;text-decoration:none;border-radius:5px;font-size:1.1em;display:inline-block">'
             f'Aplică acum</a></p>')
    L.append('<p style="font-size:0.8em;color:#999;text-align:center">Date actualizate zilnic. InterJob.ro</p>')
    return title, slug, meta, "\n".join(L)


def build_en(today_str_en: str, anofm_total: int, by_sector: Dict, count_sector: Dict,
             eures_total: int, by_country: Dict) -> Tuple[str, str, str, str]:
    title = f"Job Market {today_str_en}: {anofm_total:,} Jobs in Romania + Europe Openings"
    slug = f"job-market-{date.today().isoformat()}"
    # Keep meta under 155 chars
    meta = f"Romania job market {today_str_en}: {anofm_total:,} open positions + {eures_total:,} in Europe. Construction, IT, HoReCa, transport."
    meta = meta[:155]

    # Top 2 sectors for richer H2
    top2 = [SECTOR_LABELS_EN.get(s, s.title())
            for s, _ in sorted(count_sector.items(), key=lambda x: x[1], reverse=True)[:2]]
    h2_ro = f"{' & '.join(top2)} Jobs in Romania — {today_str_en}"
    h2_eu = f"European Job Openings — {today_str_en}"

    L = []
    L.append(f"<p>Today, <strong>{today_str_en}</strong>, the job market shows "
             f"<strong>{anofm_total:,} active positions in Romania</strong> and "
             f"<strong>{eures_total:,}+ openings across Europe</strong>.</p>")
    L.append(newsletter_block("en"))
    L.append(f"<hr><h2>{h2_ro}</h2>")
    for sector, cnt in sorted(count_sector.items(), key=lambda x: x[1], reverse=True)[:7]:
        label = SECTOR_LABELS_EN.get(sector, sector.title())
        L.append(f"<h3>{label} — {cnt:,} positions</h3><ul>")
        for t, loc, sal in by_sector.get(sector, [])[:4]:
            en_t = translate_batch([t], src="ro", tgt="en")[0]
            L.append(f"<li>{en_t}{' — ' + loc + ', Romania' if loc else ' — Romania'}{sal}</li>")
        L.append("</ul>")
    L.append(f"<hr><h2>{h2_eu}</h2>")
    L.append(f"<p>Over <strong>{eures_total:,} openings</strong> in partner countries.</p>")
    for country, jobs in by_country.items():
        L.append(f"<h3>{country}</h3><ul>")
        for _, en_title, city in jobs[:4]:
            L.append(f"<li>{en_title}{' — ' + city if city else ''}</li>")
        L.append("</ul>")
    L.append(newsletter_block("en"))
    L.append(f'<p style="text-align:center"><a href="{APPLY_URL}" style="background:#0073aa;color:white;'
             f'padding:14px 28px;text-decoration:none;border-radius:5px;font-size:1.1em;display:inline-block">'
             f'Apply Now</a></p>')
    L.append('<p style="font-size:0.8em;color:#999;text-align:center">Updated daily. InterJob.ro — European Workforce Solutions.</p>')
    return title, slug, meta, "\n".join(L)


def get_auth() -> Dict:
    return {"Authorization": f"Basic {base64.b64encode(f'{WP_USER}:{WP_PASS}'.encode()).decode()}",
            "Content-Type": "application/json"}


def get_or_create_cat(auth: Dict, name: str) -> Optional[int]:
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/categories?search={requests.utils.quote(name)}",
                     headers=auth, timeout=10)
    if r.ok and r.json():
        return r.json()[0]["id"]
    r = requests.post(f"{WP_URL}/wp-json/wp/v2/categories", headers=auth, json={"name": name}, timeout=10)
    return r.json().get("id") if r.ok else None


def wp_post(auth: Dict, title: str, slug: str, content: str, cat_id: Optional[int],
            meta_desc: str, focus_kw: str, dry_run: bool) -> Optional[int]:
    if dry_run:
        print(f"  [DRY RUN] '{title[:70]}' | slug={slug} | {len(content)}c")
        print(f"  [DRY RUN] meta={meta_desc[:80]}... | kw={focus_kw}")
        return 0
    payload = {"title": title, "slug": slug, "content": content, "status": "publish",
               "categories": [cat_id] if cat_id else []}
    r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", headers=auth, json=payload, timeout=30)
    if not r.ok:
        print(f"  WP error {r.status_code}: {r.text[:150]}")
        return None
    post_id = r.json().get("id")
    # Yoast requires separate PATCH after post creation — meta fields not accepted on POST
    yoast = requests.post(f"{WP_URL}/wp-json/wp/v2/posts/{post_id}", headers=auth,
                          json={"meta": {"_yoast_wpseo_focuskw": focus_kw,
                                         "_yoast_wpseo_metadesc": meta_desc}}, timeout=15)
    if not yoast.ok:
        print(f"  Yoast meta warn: {yoast.status_code}")
    return post_id


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--lang", choices=["ro", "en", "both"], default="both")
    args = parser.parse_args()

    conn = db_connect()
    ensure_table(conn)

    now = datetime.now()
    today_ro = f"{now.day} {RO_MONTHS[now.month]} {now.year}"
    today_en = now.strftime("%B %-d, %Y")

    print(f"Building roundup for {today_ro} / {today_en}...")
    anofm_total, by_sector, count_sector = get_anofm_stats(conn)
    print(f"  ANOFM: {anofm_total} active jobs — fetching & translating EURES...")
    eures_total, by_country = get_eures_stats()
    print(f"  EURES: {eures_total} jobs, {len(by_country)} countries")

    auth = get_auth()
    cat_ro = get_or_create_cat(auth, "Piata Muncii")
    cat_en = get_or_create_cat(auth, "Job Market")

    langs = ["ro", "en"] if args.lang == "both" else [args.lang]

    for lang in langs:
        if not args.force and already_published(conn, lang):
            print(f"  [{lang.upper()}] Already published today, skipping.")
            continue
        if lang == "ro":
            title, slug, meta, content = build_ro(today_ro, anofm_total, by_sector, count_sector, eures_total, by_country)
            cat_id = cat_ro
            focus_kw = f"locuri de munca {now.day} {RO_MONTHS[now.month]} {now.year}"
        else:
            title, slug, meta, content = build_en(today_en, anofm_total, by_sector, count_sector, eures_total, by_country)
            cat_id = cat_en
            focus_kw = f"jobs Romania Europe {today_en}"

        post_id = wp_post(auth, title, slug, content, cat_id, meta, focus_kw, args.dry_run)
        if post_id is not None:
            if not args.dry_run:
                record_publish(conn, lang, post_id)
            print(f"  [{lang.upper()}] Published! post_id={post_id}")
        else:
            print(f"  [{lang.upper()}] FAILED")

    conn.close()


if __name__ == "__main__":
    main()
