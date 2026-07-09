#!/usr/bin/env python3
"""Build the sendable EURES employer audience (ASCII, deduped, suppression-stripped)."""
import re
import unicodedata
import psycopg2

DB = {'dbname': 'interjob_master', 'user': 'tudor'}
SCRAPER_DB = {'dbname': 'scraper', 'user': 'tudor'}
# strict on RAW (pre-lowercase) email
EMAIL_RE = re.compile(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,24}$')
CAMEL_TLD = re.compile(r'\.[A-Za-z]{2,}[A-Z]')  # ".fiWorknow" = concatenated junk
PHONE_PREFIX = re.compile(r'^\d{4,}')           # phone number glued to local part


# government / military / institutional domains — not employers of RO workers
BAD_DOMAIN = re.compile(r'(\.mil\.|\.gov\.|ron\.mil|\.gov$|\.mil$|@.*\.gouv\.|politie|police|minist<)', re.I)


def valid_email(raw):
    """Reject corrupt scraped emails (phone-prefixed, camel-concatenated TLD) + gov/mil."""
    if not raw:
        return False
    raw = raw.strip()
    if not EMAIL_RE.match(raw) or CAMEL_TLD.search(raw):
        return False
    if BAD_DOMAIN.search(raw):
        return False
    local = raw.split('@', 1)[0]
    return not PHONE_PREFIX.match(local)

# sector substring (lowercase) -> sender domain. EN + Swedish (source is mostly SE).
ROUTES = [
    ('manufactur', 'factoryjobs.eu'), ('industriell', 'factoryjobs.eu'),
    ('construct', 'buildjobs.eu'), ('bygg', 'buildjobs.eu'), ('hantverk', 'buildjobs.eu'),
    ('health', 'careworkers.eu'), ('care', 'careworkers.eu'),
    ('halso', 'careworkers.eu'), ('sjukvard', 'careworkers.eu'), ('social', 'careworkers.eu'),
    ('hospitalit', 'horecaworkers2026.eu'), ('horeca', 'horecaworkers2026.eu'),
    ('hotell', 'horecaworkers2026.eu'), ('restaurang', 'horecaworkers2026.eu'),
    ('transport', 'warehouseworkers.eu'), ('logistic', 'warehouseworkers.eu'), ('lager', 'warehouseworkers.eu'),
    ('agricultur', 'meatworkers.eu'), ('food', 'meatworkers.eu'),
    ('lantbruk', 'meatworkers.eu'), ('jordbruk', 'meatworkers.eu'),
]
GENERAL = 'bppltd.co.uk'


def ascii_fold(s):
    if not s:
        return None
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii').strip() or None


def route(sector):
    s = (ascii_fold(sector) or '').lower()
    for key, dom in ROUTES:
        if key in s:
            return dom
    return GENERAL


def main():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    # Sources are the CLEAN tables only. eures_employers_50plus is EXCLUDED — its
    # emails are corrupt (phone-prefixed, camel-concatenated TLD). contacts_50 lives
    # in the 'scraper' DB. Neither carries a usable sector -> routing relies on eures_jobs.
    cur.execute("""
        SELECT email1 AS email, employer AS company, country, NULL::text AS sector
        FROM eures_contacts WHERE email1 IS NOT NULL
    """)
    rows = list(cur.fetchall())
    sconn = psycopg2.connect(**SCRAPER_DB)
    scur = sconn.cursor()
    scur.execute("""
        SELECT email_1, company_name, country, NULL::text
        FROM contacts_50 WHERE email_1 IS NOT NULL
    """)
    rows += list(scur.fetchall())
    scur.close()
    sconn.close()

    # Unified suppression: master_dnc + norway_dnc (where universal_reply_handler writes
    # opt-outs every 2h) + the shared dnc_list.csv. A STOP reply to office@<domain> is
    # processed by universal_reply_handler -> norway_dnc/dnc_list.csv -> suppressed here.
    dnc = set()
    for tbl in ("master_dnc", "norway_dnc"):
        try:
            cur.execute(f"SELECT lower(trim(email)) FROM {tbl} WHERE email IS NOT NULL")
            dnc |= {r[0] for r in cur.fetchall()}
        except Exception:
            conn.rollback()
    try:
        with open("/opt/ACTIVE/EMAIL/CAMPAIGNS/dnc_list.csv", encoding="utf-8") as f:
            dnc |= {ln.split(",")[0].strip().lower() for ln in f if "@" in ln.split(",")[0]}
    except FileNotFoundError:
        pass
    cur.execute("SELECT lower(trim(email)) FROM eures_send_log")
    sent = {r[0] for r in cur.fetchall()}

    best = {}
    for raw_email, company, country, sector in rows:
        if not valid_email(raw_email):
            continue
        email = raw_email.strip().lower()
        if email in dnc or email in sent:
            continue
        # prefer the row that carries a sector (better routing) over a NULL-sector dup
        if email in best and best[email][3] and not sector:
            continue
        best[email] = (email, ascii_fold(company), ascii_fold(country), sector)

    # Max personalization: eures_jobs (429k) -> company -> (sector, real job_title, country).
    cur.execute("ALTER TABLE eures_audience_sendable ADD COLUMN IF NOT EXISTS job_title text")
    cur.execute("SELECT lower(trim(company_name)), sector, job_title, country FROM eures_jobs "
                "WHERE company_name IS NOT NULL")
    comp_sector, comp_job, comp_country = {}, {}, {}
    for cname, sec, jtitle, jcountry in cur.fetchall():
        if sec and sec != 'Other':
            comp_sector.setdefault(cname, sec)
        if jtitle and len(jtitle) < 60:
            comp_job.setdefault(cname, jtitle)
        if jcountry:
            comp_country.setdefault(cname, jcountry)

    cur.execute("TRUNCATE eures_audience_sendable")
    by_dom = {}
    for email, company, country, sector in best.values():
        ckey = (company or '').lower()
        sector = sector or comp_sector.get(ckey)
        job_title = comp_job.get(ckey)
        country = country or comp_country.get(ckey)
        dom = route(sector)
        by_dom[dom] = by_dom.get(dom, 0) + 1
        cur.execute(
            "INSERT INTO eures_audience_sendable (email, company, country, sector, sender_domain, job_title) "
            "VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (email) DO NOTHING",
            (email, company, country, sector, dom, job_title))
    conn.commit()

    print(f"audience built: {len(best)} sendable (dnc={len(dnc)} sent={len(sent)})")
    for dom, n in sorted(by_dom.items(), key=lambda x: -x[1]):
        print(f"  {dom:26} {n}")
    cur.close()
    conn.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
