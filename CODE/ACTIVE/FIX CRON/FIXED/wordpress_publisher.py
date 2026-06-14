#!/usr/bin/env python3
"""WordPress Job Publisher — posts ANOFM(EN) and EURES(RO) to interjob.ro via Polylang."""

import argparse
import base64
import csv
import glob
import json
import os
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional

import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv("/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED/wp_sites.env")

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
ANOFM_CSV_DIR = "/opt/ACTIVE/SCRAPER_DATA/csv/ANOFM"
EURES_BASE = "/opt/ACTIVE/SCRAPER_DATA/csv/EURES"
APPLY_URL = "https://interjob.ro/apply.html"

WP_JOB_SITES = {
    "interjob.ro": {
        "url": "https://interjob.ro",
        "user": os.getenv("WP_INTERJOB_USER"),
        "password": os.getenv("WP_INTERJOB_PASS"),
        "countries": ["Norway", "Denmark", "Sweden", "Finland", "Romania"],
    },
    "buildjobs.eu": {
        "url": "https://buildjobs.eu/wp",
        "user": os.getenv("WP_BUILDJOBS_EU_USER"),
        "password": os.getenv("WP_BUILDJOBS_EU_PASS"),
        "countries": ["all"],
    },
    "meatworkers.eu": {
        "url": "https://meatworkers.eu/wp",
        "user": os.getenv("WP_MEATWORKERS_EU_USER"),
        "password": os.getenv("WP_MEATWORKERS_EU_PASS"),
        "countries": ["all"],
    },
    "factoryjobs.eu": {
        "url": "https://factoryjobs.eu/wp",
        "user": os.getenv("WP_FACTORYJOBS_EU_USER"),
        "password": os.getenv("WP_FACTORYJOBS_EU_PASS"),
        "countries": ["all"],
    },
    "warehouseworkers.eu": {
        "url": "https://warehouseworkers.eu/wp",
        "user": os.getenv("WP_WAREHOUSEWORKERS_EU_USER"),
        "password": os.getenv("WP_WAREHOUSEWORKERS_EU_PASS"),
        "countries": ["all"],
    },
    "careworkers.eu": {
        "url": "https://careworkers.eu/wp",
        "user": os.getenv("WP_CAREWORKERS_EU_USER"),
        "password": os.getenv("WP_CAREWORKERS_EU_PASS"),
        "countries": ["all"],
    },
    "mechanicjobs.eu": {
        "url": "https://mechanicjobs.eu/wp",
        "user": os.getenv("WP_MECHANICJOBS_EU_USER"),
        "password": os.getenv("WP_MECHANICJOBS_EU_PASS"),
        "countries": ["all"],
    },
    "internaltransfers.eu": {
        "url": "https://internaltransfers.eu/wp",
        "user": os.getenv("WP_INTERNALTRANSFERS_EU_USER"),
        "password": os.getenv("WP_INTERNALTRANSFERS_EU_PASS"),
        "countries": ["all"],
    },
    "nepalezi.com": {
        "url": "https://nepalezi.com",
        "user": os.getenv("WP_NEPALEZI_COM_USER"),
        "password": os.getenv("WP_NEPALEZI_COM_PASS"),
        "countries": ["all"],
    },
    "horecaworkers2026.eu": {
        "url": "https://horecaworkers2026.eu/wp",
        "user": os.getenv("WP_HORECAWORKERS2026_EU_USER"),
        "password": os.getenv("WP_HORECAWORKERS2026_EU_PASS"),
        "countries": ["all"],
    }
}

EURES_COUNTRIES = {
    "Norway": "Norway/Norway_contacts_50.csv",
    "Denmark": "Denmark/Denmark_contacts_50.csv",
    "Finland": "Finland/Finland_contacts_50.csv",
    "Sweden": "Sweden/Sweden_contacts_50.csv",
}

_translators = {}

# Nordic-specific characters that indicate a non-English title
_NORDIC_CHARS = set("æøåäöëðÆØÅÄÖËÐ")

# Common English words for heuristic detection
_EN_COMMON_WORDS = frozenset(
    "the a an is are was were be been have has had do does did will would shall should "
    "can could may might must and but or nor for yet so in on at to from by with of "
    "as not no this that these those it its he she they we you i me my your his her "
    "our their him them us manager worker driver engineer operator assistant chef "
    "cleaner welder mechanic electrician nurse care sales construction warehouse "
    "factory production transport delivery cook server receptionist teacher "
    "accountant consultant developer designer analyst specialist coordinator "
    "technician supervisor inspector planner advisor director officer leader "
    "head senior junior lead chief principal general staff team group".split()
)


def _is_nordic_title(title: str) -> bool:
    """Detect if a title is likely in a Nordic language (not English).

    Returns True if the title contains Nordic-specific characters (æ, ø, å, ö, ä, etc.)
    or if it doesn't look like English based on a common-word heuristic.
    """
    if not title:
        return False
    # Check for Nordic-specific characters
    if any(ch in _NORDIC_CHARS for ch in title):
        return True
    # Heuristic: check if any common English word appears in the title
    words = re.split(r"[\s\-/,.]+", title.lower())
    words = [w for w in words if len(w) > 1]
    if not words:
        return True  # No real words — suspicious
    if not any(w in _EN_COMMON_WORDS for w in words):
        return True  # No common English words found — likely non-English
    return False


def _is_non_latin_script(text: str) -> bool:
    """Return True if text is predominantly in a non-Latin script (Cyrillic, Arabic, CJK, etc.)."""
    if not text:
        return False
    import unicodedata
    latin = 0
    non_latin = 0
    for ch in text:
        if ch.isspace() or ch in "0123456789.,-:;()[]{}!@#$%&*+=/\\\"'":
            continue
        cp = ord(ch)
        # Latin Unicode blocks: Basic Latin, Latin Extended-A/B, Latin Extended Additional
        if (0x0041 <= cp <= 0x024F) or (0x1E00 <= cp <= 0x1EFF) or (0x2C60 <= cp <= 0x2C7F):
            latin += 1
        elif unicodedata.category(ch).startswith("L"):  # Letter but not Latin range
            non_latin += 1
    total = latin + non_latin
    if total == 0:
        return False
    return non_latin > latin  # More non-Latin than Latin letters


def translate(text: str, source: str = "ro", target: str = "en") -> str:
    """Translate via deep_translator (Google, free)."""
    if not text or not text.strip():
        return text
    key = f"{source}_{target}"
    if key not in _translators:
        try:
            from deep_translator import GoogleTranslator
            _translators[key] = GoogleTranslator(source=source, target=target)
        except Exception:
            return text
    try:
        return _translators[key].translate(text[:4900]) or text
    except Exception:
        return text


SECTOR_RO = {
    "constructii": "Construcții", "productie": "Producție", "comert": "Comerț", "horeca": "HoReCa",
    "transport": "Transport", "cleaning": "Curățenie", "vanzari": "Vânzări", "sanatate": "Sănătate",
    "auto": "Auto", "agricultura": "Agricultură", "paza": "Pază", "mobila": "Mobilă",
    "food": "Alimentară", "confectii": "Confecții", "it": "IT", "general": "Diverse",
}
SECTOR_EN = {
    "constructii": "Construction", "productie": "Manufacturing", "comert": "Retail",
    "horeca": "Hospitality", "transport": "Transport & Logistics", "cleaning": "Cleaning",
    "vanzari": "Sales", "sanatate": "Healthcare", "auto": "Automotive",
    "agricultura": "Agriculture", "paza": "Security", "mobila": "Furniture",
    "food": "Food Industry", "confectii": "Textiles", "it": "IT", "general": "General",
}


def generate_desc_rich(job: Dict, lang: str = "en") -> str:
    """Generate rich description from job data with sector, positions, contract info."""
    title = job.get("job_title", "")
    sector = (job.get("sector") or "").lower().strip()
    positions = job.get("positions", 1)
    city = job.get("city", "")
    country = job.get("country", "Romania")
    salary = job.get("salary", "")
    deadline = job.get("deadline", "")

    if lang == "ro":
        # Use pre-translated English title for EURES jobs (handles Nordic→EN→RO chain)
        title_base = job.get("title_en", title) if job.get("source") == "eures" else title
        title_ro = translate(title_base, "en", "ro") if job.get("source") == "eures" else title
        sector_ro = SECTOR_RO.get(sector, sector.title() if sector else "Diverse")
        lines = [f"<p>Căutăm candidați pentru postul de <strong>{title_ro}</strong>, disponibil prin InterJob.ro.</p>"]
        lines.append(f"<p><strong>Domeniu:</strong> {sector_ro}</p>")
        if city:
            loc = f"{city}, {country}" if country else city
            lines.append(f"<p><strong>Locație:</strong> {loc}</p>")
        if positions > 1:
            lines.append(f"<p><strong>Posturi disponibile:</strong> {positions}</p>")
        if salary:
            lines.append(f"<p><strong>Salariu:</strong> {salary}</p>")
        if deadline:
            lines.append(f"<p><strong>Termen aplicare:</strong> {deadline}</p>")
        lines.append("<p>Trimite CV-ul tău și te contactăm pentru detalii despre condiții, program și contract.</p>")
        return "\n".join(lines)
    else:
        # Use pre-translated English title for EURES jobs
        title_base = job.get("title_en", title)
        sector_en = SECTOR_EN.get(sector, sector.title() if sector else "General")
        lines = [f"<p>We are looking for candidates for the position of <strong>{title_base}</strong>, available through InterJob.ro.</p>"]
        lines.append(f"<p><strong>Sector:</strong> {sector_en}</p>")
        if city:
            loc = f"{city}, {country}" if country else city
            lines.append(f"<p><strong>Location:</strong> {loc}</p>")
        if positions > 1:
            lines.append(f"<p><strong>Positions available:</strong> {positions}</p>")
        if salary:
            lines.append(f"<p><strong>Salary:</strong> {salary}</p>")
        if deadline:
            lines.append(f"<p><strong>Apply by:</strong> {deadline}</p>")
        lines.append("<p>Send your CV and we will contact you with details about conditions, schedule and contract type.</p>")
        return "\n".join(lines)


def get_description(job: Dict, lang: str = "en") -> str:
    """Get desc from CSV or generate via template+translation."""
    desc = job.get("job_description", "").strip()
    src = job.get("source", "anofm")
    if desc:
        if src == "anofm" and lang == "en":
            return translate(desc, "ro", "en")
        if src == "eures" and lang == "ro":
            return translate(desc, "en", "ro")
        return desc
    # No CSV description — generate from job data
    return generate_desc_rich(job, lang)


def _job_posting_schema(job: Dict, title_en: str, desc_en: str, lang: str) -> str:
    """Generate JSON-LD JobPosting schema for Google Jobs indexing."""
    import json as _json
    city = (job.get("city") or "").split(">")[-1].strip().title()
    country = job.get("country", "Romania")
    schema = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": title_en,
        "description": desc_en or title_en,
        "hiringOrganization": {"@type": "Organization", "name": "InterJob.ro", "sameAs": "https://interjob.ro"},
        "jobLocation": {"@type": "Place", "address": {
            "@type": "PostalAddress",
            "addressLocality": city,
            "addressCountry": "RO" if country == "Romania" else country[:2].upper(),
        }},
        "employmentType": "FULL_TIME",
        "datePosted": datetime.now().strftime("%Y-%m-%d"),
        "validThrough": job.get("deadline", ""),
        "applyLink": APPLY_URL,
    }
    if job.get("salary"):
        schema["baseSalary"] = {"@type": "MonetaryAmount", "currency": job.get("salary_currency", "RON"),
                                 "value": {"@type": "QuantitativeValue", "value": str(job["salary"])}}
    return f'<script type="application/ld+json">{_json.dumps(schema, ensure_ascii=False)}</script>'


def format_job_html_en(job: Dict) -> str:
    """ANOFM job in English for interjob.ro/en/ (foreign workers to Romania)."""
    desc = get_description(job, lang="en")
    # For EURES jobs, use the pre-translated English title
    title_en = job.get("title_en", job["job_title"]) if job.get("source") == "eures" else translate(job["job_title"], "ro", "en") if job.get("source") == "anofm" else job["job_title"]
    job_ref = f"ANOFM-RO-{job['job_id'].replace('anofm_', '')}"
    apply_url = f"{APPLY_URL}?ref={job_ref}"
    lines = [_job_posting_schema(job, title_en, desc, "en")]
    lines.append(desc)
    lines.append(f'<p style="margin-top:20px"><a href="{apply_url}" style="background:#0073aa;color:white;padding:12px 24px;text-decoration:none;border-radius:4px;display:inline-block">Apply Now</a></p>')
    lines.append(f'<p style="font-size:0.85em;color:#999;margin-top:20px">Ref: {job_ref} &middot; Managed by InterJob.ro</p>')
    return "\n".join(lines)


def format_job_html_ro(job: Dict) -> str:
    """EURES job in Romanian for interjob.ro/ (Romanians going to Europe)."""
    desc = get_description(job, lang="ro")
    # Use pre-translated English title for Nordic EURES jobs
    title_en = job.get("title_en", job["job_title"])
    country_code = job.get("country", "EU")[:2].upper()
    job_ref = f"EURES-{country_code}-{job['job_id'].replace('eures_', '')[:8]}"
    apply_url = f"{APPLY_URL}?ref={job_ref}"
    lines = [_job_posting_schema(job, title_en, get_description(job, lang="en"), "ro")]
    lines.append(desc)
    lines.append(f'<p style="margin-top:20px"><a href="{apply_url}" style="background:#e65c00;color:white;padding:12px 24px;text-decoration:none;border-radius:4px;display:inline-block">Aplica Acum</a></p>')
    lines.append(f'<p style="font-size:0.85em;color:#999;margin-top:20px">Ref: {job_ref} &middot; Gestionat de InterJob.ro</p>')
    return "\n".join(lines)


def get_auth(user: str, pwd: str) -> Dict:
    return {"Authorization": f"Basic {base64.b64encode(f'{user}:{pwd}'.encode()).decode()}"}


def get_db():
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"DB config missing: {CONFIG_FILE}")
    with open(CONFIG_FILE) as f:
        cfg = json.load(f)
    return psycopg2.connect(host=cfg["db"]["host"], port=cfg["db"]["port"],
                            dbname=cfg["db"]["dbname"], user=cfg["db"]["user"],
                            password=cfg["db"]["password"])



def ensure_conn(conn):
    """Return a live connection, reconnecting if the server dropped it."""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        return conn
    except Exception:
        conn.close()
        return get_db()

def init_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS wp_job_posts (
                id SERIAL PRIMARY KEY, job_id TEXT NOT NULL, site TEXT NOT NULL,
                wp_post_id INT, posted_at TIMESTAMP DEFAULT NOW(),
                job_title TEXT, country TEXT, UNIQUE(job_id, site)
            )""")
    conn.commit()


def already_posted(conn, job_id: str, site: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM wp_job_posts WHERE job_id=%s AND site=%s", (job_id, site))
        return cur.fetchone() is not None


def record_post(conn, job: Dict, site: str, post_id: int):
    with conn.cursor() as cur:
        cur.execute("""INSERT INTO wp_job_posts (job_id,site,wp_post_id,job_title,country)
            VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
            (job["job_id"], site, post_id, job["job_title"], job.get("country", "")))
    conn.commit()


def get_or_create_category(site_url: str, auth: Dict, name: str) -> Optional[int]:
    base = f"{site_url}/wp-json/wp/v2"
    try:
        r = requests.get(f"{base}/categories?search={name}&per_page=20", headers=auth, timeout=10)
        for c in (r.json() if r.ok else []):
            if c["name"].lower() == name.lower():
                return c["id"]
        r = requests.post(f"{base}/categories", headers=auth, json={"name": name}, timeout=10)
        if r.ok:
            return r.json()["id"]
    except Exception:
        pass
    return None


def post_to_wp(cfg: Dict, job: Dict, lang: str, cat_id: int, dry_run: bool) -> Optional[int]:
    auth = get_auth(cfg["user"], cfg["password"])
    if lang == "ro":
        # Translate from English (pre-translated for Nordic) to Romanian
        title_base = job.get("title_en", job["job_title"]) if job.get("source") == "eures" else job["job_title"]
        title = translate(title_base, "en", "ro") if job.get("source") == "eures" else job["job_title"]
        country = job.get("country", "")
        full_title = f"{title} — {country}" if country else title
        content = format_job_html_ro(job)
    else:
        # For EURES jobs, use the pre-translated English title
        title = job.get("title_en", job["job_title"]) if job.get("source") == "eures" else translate(job["job_title"], "ro", "en") if job.get("source") == "anofm" else job["job_title"]
        city = job.get("city", "")
        full_title = f"{title} — {city}, Romania" if city else f"{title} — Romania"
        content = format_job_html_en(job)

    payload = {"title": full_title, "content": content, "status": "publish",
               "categories": [cat_id], "lang": lang,
               "comment_status": "closed", "ping_status": "closed"}

    if dry_run:
        print(f"  [DRY RUN][{lang.upper()}] {full_title[:70]}")
        desc_preview = content[:200].replace("\n", " ")
        print(f"  Content preview: {desc_preview}")
        return 0

    try:
        r = requests.post(f"{cfg['url']}/wp-json/wp/v2/posts", headers=auth, json=payload, timeout=30)
        if r.ok:
            return r.json().get("id")
        print(f"  WP error {r.status_code}: {r.text[:150]}")
    except Exception as e:
        print(f"  WP exception: {e}")
    return None


def read_anofm_jobs() -> List[Dict]:
    files = sorted(glob.glob(os.path.join(ANOFM_CSV_DIR, "anofm_*.csv")))
    if not files:
        return []
    jobs = []
    with open(files[-1], "r", encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            jobs.append({
                "job_id": f"anofm_{row.get('job_id', '')}",
                "job_title": row.get("job_title", "").strip(),
                "city": row.get("city", "").strip(),
                "country": "Romania",
                "sector": row.get("sector", ""),
                "salary": row.get("salary", ""),
                "positions": int(row.get("positions_available", 1) or 1),
                "deadline": row.get("application_deadline", ""),
                "job_description": row.get("job_description", "").strip(),
                "source": "anofm",
            })
    return jobs


def read_eures_jobs(max_per_country: int = 500) -> List[Dict]:
    """Read EURES jobs — scan from top, collect first max_per_country unique jobs with title.

    For Nordic-language titles (Norwegian, Danish, Swedish, Finnish), translates them to
    English at read time and stores both the original title and the English translation.
    Skips jobs where the title is entirely in a non-Latin script or is less than 5
    characters after translation.
    """
    jobs, seen = [], set()
    for country, csv_rel in EURES_COUNTRIES.items():
        path = os.path.join(EURES_BASE, csv_rel)
        if not os.path.exists(path):
            continue
        count = 0
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for row in csv.DictReader(f):
                if count >= max_per_country:
                    break
                title = row.get("job_title", "").strip()
                if not title or len(title) < 5:
                    continue
                # Skip titles entirely in non-Latin script
                if _is_non_latin_script(title):
                    continue
                jid = row.get("job_id", row.get("fingerprint", ""))
                if not jid or jid in seen:
                    continue
                seen.add(jid)
                # Detect and translate Nordic titles to English
                title_en = title
                if _is_nordic_title(title):
                    title_en = translate(title, "no", "en")  # 'no' covers Nordic→EN well
                    if not title_en or len(title_en.strip()) < 5:
                        continue  # Skip if translation is too short
                job = {
                    "job_id": f"eures_{jid}",
                    "job_title": title,
                    "title_en": title_en,  # Pre-translated English title
                    "city": row.get("city", "").strip(),
                    "country": country,
                    "sector": row.get("sector", "").strip(),
                    "salary": row.get("salary", ""),
                    "positions": int(row.get("positions_available", 1) or 1),
                    "deadline": row.get("application_deadline", ""),
                    "job_description": row.get("job_description", "").strip(),
                    "source": "eures",
                }
                jobs.append(job)
                count += 1
    return jobs


def rank_jobs(jobs: List[Dict]) -> List[Dict]:
    scored = []
    for job in jobs:
        score = 0
        if job.get("salary"):
            score += 50
        if job.get("positions", 1) > 1:
            score += min(job["positions"], 20) * 2
        if job.get("job_description"):
            score += 20
        keywords = ["construct", "weld", "warehouse", "factory", "driver", "mechanic",
                    "electrician", "instalator", "sofer", "depozit"]
        combo = (job.get("sector", "") + job.get("job_title", "")).lower()
        if any(k in combo for k in keywords):
            score += 30
        scored.append((score, job))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [j for _, j in scored]


def main():
    parser = argparse.ArgumentParser(description="Post jobs to WordPress")
    parser.add_argument("--site", choices=list(WP_JOB_SITES.keys()))
    parser.add_argument("--all-sites", action="store_true")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--source", choices=["anofm", "eures", "all"], default="all")
    parser.add_argument("--lang", choices=["ro", "en", "auto"], default="auto")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    conn = get_db()
    init_table(conn)

    if args.status:
        with conn.cursor() as cur:
            cur.execute("SELECT site, count(*), max(posted_at) FROM wp_job_posts GROUP BY site")
            for row in cur.fetchall():
                print(f"  {row[0]}: {row[1]} posts, last: {row[2]}")
        conn.close()
        return

    if not args.site and not args.all_sites:
        parser.error("Specify --site or --all-sites")

    sites = [args.site] if args.site else list(WP_JOB_SITES.keys())

    for site_key in sites:
        cfg = WP_JOB_SITES[site_key]
        auth = get_auth(cfg["user"], cfg["password"])
        print(f"\n=== {site_key} ===")

        # Build flux list: (source, lang)
        if args.lang == "auto":
            fluxes = []
            if args.source in ("eures", "all"):
                fluxes.append(("eures", "ro"))
            if args.source in ("anofm", "all"):
                fluxes.append(("anofm", "en"))
        else:
            src = args.source if args.source != "all" else ("eures" if args.lang == "ro" else "anofm")
            fluxes = [(src, args.lang)]

        for src, lang in fluxes:
            cat_name = "Joburi in Europa" if lang == "ro" else "Jobs in Romania"
            cat_id = get_or_create_category(cfg["url"], auth, cat_name)
            if not cat_id:
                print(f"  Could not get/create category '{cat_name}'")
                continue

            jobs = read_eures_jobs() if src == "eures" else read_anofm_jobs()
            ranked = rank_jobs(jobs)
            print(f"  {src.upper()} -> {lang.upper()}: {len(ranked)} jobs, cat_id={cat_id}")

            posted = 0
            for job in ranked:
                if posted >= args.limit:
                    break
                conn = ensure_conn(conn)
                if already_posted(conn, job["job_id"], site_key):
                    continue
                post_id = post_to_wp(cfg, job, lang, cat_id, args.dry_run)
                if post_id is not None:
                    if not args.dry_run:
                        record_post(conn, job, site_key, post_id)
                    posted += 1
                    print(f"  [{lang.upper()}] {job['job_title'][:50]} -> post_id={post_id}")

            print(f"  Posted {posted} {src} jobs ({lang})")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
