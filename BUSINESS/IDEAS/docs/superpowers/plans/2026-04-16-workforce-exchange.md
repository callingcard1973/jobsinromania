# Workforce Exchange Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Match workers from `master_applicants.db` to employers from ANOFM/TED/FACTORYJOBS/EBRD, send personalized Brevo pitches, track responses and placements.

**Architecture:** Single Python pipeline on raspibig — load employers from all sources, match by sector+country to workers, render email per employer, send via Brevo, log to `interjob_master.workforce_matches`. Cron daily 08:00.

**Tech Stack:** Python 3.11, psycopg2 (interjob_master PostgreSQL), sqlite3 (master_applicants.db), Brevo API, Jinja2

---

## Chunk 1: Database + Config

### Task 1: Create `workforce_matches` table

**Files:**
- Create: `/opt/ACTIVE/WORKFORCE/init_db.py`

- [ ] SSH to raspibig: `ssh tudor@192.168.100.21`
- [ ] Create directory: `mkdir -p /opt/ACTIVE/WORKFORCE`
- [ ] Write and run init script:

```python
# /opt/ACTIVE/WORKFORCE/init_db.py
import psycopg2, os

conn = psycopg2.connect(os.environ["INTERJOB_PG_DSN"])
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS workforce_matches (
    id SERIAL PRIMARY KEY,
    employer_source TEXT NOT NULL,       -- ANOFM/TED/FACTORYJOBS/EBRD
    employer_name TEXT,
    employer_email TEXT NOT NULL,
    sector TEXT,
    country TEXT DEFAULT 'RO',
    workers_matched INT DEFAULT 0,
    worker_names TEXT,                   -- comma-separated first names
    sent_at TIMESTAMP,
    response TEXT,
    placement_fee NUMERIC DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(employer_email, employer_source)
);
CREATE INDEX IF NOT EXISTS idx_wm_source ON workforce_matches(employer_source);
CREATE INDEX IF NOT EXISTS idx_wm_sent ON workforce_matches(sent_at);
""")
conn.commit()
print("workforce_matches table ready")
```

- [ ] Run: `python3 /opt/ACTIVE/WORKFORCE/init_db.py`
- [ ] Verify: `psql $INTERJOB_PG_DSN -c "\d workforce_matches"`
- [ ] Commit: `git add init_db.py && git commit -m "feat: workforce_matches table"`

---

### Task 2: Config file

**Files:**
- Create: `/opt/ACTIVE/WORKFORCE/config.py`

```python
# /opt/ACTIVE/WORKFORCE/config.py
import os

PG_DSN = os.environ["INTERJOB_PG_DSN"]
APPLICANTS_DB = "/opt/ACTIVE/DATA/master_applicants.db"
BREVO_API_KEY = os.environ.get("BREVO_API_KEY_MIVROMANIA")
BREVO_SENDER = {"name": "InterJob Recruitment", "email": "office@mivromania.info"}
DAILY_LIMIT = 100          # emails per run
MIN_WORKERS_TO_SEND = 1    # only pitch if at least 1 worker matches

# Sector mapping: normalize to canonical tags
SECTOR_MAP = {
    "constructii": "construction",
    "transport": "logistics",
    "curierat": "logistics",
    "depozit": "warehouse",
    "productie": "manufacturing",
    "fabrica": "manufacturing",
    "ingrijire": "care",
    "horeca": "hospitality",
    "agricultura": "agriculture",
    "ferma": "agriculture",
    "electric": "electrical",
    "instalatii": "plumbing",
    "mecanic": "mechanical",
    "call center": "callcenter",
}
```

- [ ] Confirm `APPLICANTS_DB` path exists on raspibig: `ls /opt/ACTIVE/DATA/master_applicants.db`
- [ ] If different path, update `APPLICANTS_DB` accordingly
- [ ] Commit

---

## Chunk 2: Employer Loader + Worker Matcher

### Task 3: Employer loader (all 4 sources)

**Files:**
- Create: `/opt/ACTIVE/WORKFORCE/employer_loader.py`

```python
# /opt/ACTIVE/WORKFORCE/employer_loader.py
# Returns list of dicts: {name, email, sector, country, source}
# Max 250 lines — split if needed

import psycopg2
from config import PG_DSN, SECTOR_MAP

def _normalize_sector(raw):
    if not raw:
        return "general"
    raw = raw.lower().strip()
    for key, val in SECTOR_MAP.items():
        if key in raw:
            return val
    return "general"

def load_anofm(conn, limit=500):
    cur = conn.cursor()
    cur.execute("""
        SELECT company_name, email, sector, 'RO' as country
        FROM anofm_employers
        WHERE email IS NOT NULL AND email != ''
        ORDER BY created_at DESC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    return [{"name": r[0], "email": r[1],
             "sector": _normalize_sector(r[2]),
             "country": r[3], "source": "ANOFM"} for r in rows]

def load_ted(conn, limit=300):
    cur = conn.cursor()
    cur.execute("""
        SELECT contractor_name, contractor_email, sector, country
        FROM ted_winners
        WHERE contractor_email IS NOT NULL
          AND awarded_date > NOW() - INTERVAL '60 days'
        ORDER BY awarded_date DESC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    return [{"name": r[0], "email": r[1],
             "sector": _normalize_sector(r[2]),
             "country": r[3] or "EU", "source": "TED"} for r in rows]

def load_factoryjobs(conn, limit=200):
    cur = conn.cursor()
    cur.execute("""
        SELECT company_name, email, sector, 'RO' as country
        FROM factoryjobs_employers
        WHERE email IS NOT NULL AND email != ''
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    return [{"name": r[0], "email": r[1],
             "sector": _normalize_sector(r[2]),
             "country": r[3], "source": "FACTORYJOBS"} for r in rows]

def load_ebrd(conn, limit=130):
    cur = conn.cursor()
    cur.execute("""
        SELECT contractor_name, contractor_email, sector, country
        FROM ebrd_contractors
        WHERE contractor_email IS NOT NULL
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    return [{"name": r[0], "email": r[1],
             "sector": _normalize_sector(r[2]),
             "country": r[3] or "EU", "source": "EBRD"} for r in rows]

def load_all_employers(limit_each=300):
    conn = psycopg2.connect(PG_DSN)
    employers = []
    for fn in [load_anofm, load_ted, load_factoryjobs, load_ebrd]:
        try:
            employers += fn(conn, limit_each)
        except Exception as e:
            print(f"[WARN] {fn.__name__} failed: {e}")
    conn.close()
    # Deduplicate by email
    seen = set()
    unique = []
    for e in employers:
        if e["email"] not in seen:
            seen.add(e["email"])
            unique.append(e)
    print(f"Loaded {len(unique)} unique employers")
    return unique
```

- [ ] Check actual table names on raspibig:
  ```bash
  psql $INTERJOB_PG_DSN -c "\dt" | grep -E "anofm|ted|factory|ebrd"
  ```
- [ ] Update table/column names if different
- [ ] Test: `python3 -c "from employer_loader import load_all_employers; print(len(load_all_employers()))"`
- [ ] Commit

---

### Task 4: Worker matcher

**Files:**
- Create: `/opt/ACTIVE/WORKFORCE/worker_matcher.py`

```python
# /opt/ACTIVE/WORKFORCE/worker_matcher.py
import sqlite3
from config import APPLICANTS_DB, SECTOR_MAP

# Reverse sector map for matching
SECTOR_KEYWORDS = {v: [] for v in SECTOR_MAP.values()}
for k, v in SECTOR_MAP.items():
    SECTOR_KEYWORDS[v].append(k)

def get_workers_for_sector(sector, country=None, limit=5):
    """Returns list of worker dicts matching sector."""
    conn = sqlite3.connect(APPLICANTS_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    keywords = SECTOR_KEYWORDS.get(sector, [sector])
    placeholders = " OR ".join([
        "LOWER(skills) LIKE ?" for _ in keywords
    ] + [
        "LOWER(desired_job) LIKE ?" for _ in keywords
    ])
    params = [f"%{k}%" for k in keywords] * 2

    query = f"""
        SELECT first_name, last_name, skills, desired_job, country
        FROM applicants
        WHERE ({placeholders})
        LIMIT ?
    """
    cur.execute(query, params + [limit])
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def match_employer(employer):
    """Returns workers matching employer's sector."""
    workers = get_workers_for_sector(employer["sector"])
    if not workers and employer["sector"] != "general":
        # Fallback: any worker
        workers = get_workers_for_sector("general")[:3]
    return workers
```

- [ ] Check `master_applicants.db` schema:
  ```bash
  sqlite3 /opt/ACTIVE/DATA/master_applicants.db ".schema applicants"
  ```
- [ ] Update column names to match actual schema
- [ ] Test: `python3 -c "from worker_matcher import match_employer; print(match_employer({'sector':'construction'}))"`
- [ ] Commit

---

## Chunk 3: Email + Pipeline

### Task 5: Email pitcher

**Files:**
- Create: `/opt/ACTIVE/WORKFORCE/pitcher.py`

```python
# /opt/ACTIVE/WORKFORCE/pitcher.py
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from config import BREVO_API_KEY, BREVO_SENDER

def _render_email(employer, workers):
    worker_list = "\n".join([
        f"- {w['first_name']} {w['last_name'][0]}. ({w['skills'][:60]})"
        for w in workers[:3]
    ])
    sector_ro = employer.get("sector_ro", employer["sector"])
    name = employer.get("name") or "Stimate angajator"

    subject = f"Avem {len(workers)} muncitori disponibili pentru {sector_ro}"
    body = f"""Buna ziua,

Suntem InterJob, retea europeana de recrutare cu peste 756 candidati activi.

Am identificat ca firma dumneavoastra activeaza in sectorul {sector_ro}.
In baza noastra avem {len(workers)} muncitori disponibili imediat:

{worker_list}

Plasam muncitori in Romania si UE. Fara costuri initiale — platiti doar la angajare reusita.

Raspundeti la acest email sau sunati: +40 XXX XXX XXX

Cu stima,
InterJob Recruitment
https://interjob.ro/apply.html
"""
    return subject, body

def send_pitch(employer, workers):
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key["api-key"] = BREVO_API_KEY
    api = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )
    subject, body = _render_email(employer, workers)
    email = sib_api_v3_sdk.SendSmtpEmail(
        sender=BREVO_SENDER,
        to=[{"email": employer["email"], "name": employer.get("name", "")}],
        subject=subject,
        text_content=body,
        reply_to={"email": "manpower.dristor@gmail.com"}
    )
    try:
        api.send_transac_email(email)
        return True
    except ApiException as e:
        print(f"[ERR] Brevo send failed {employer['email']}: {e}")
        return False
```

- [ ] Commit

---

### Task 6: Main pipeline

**Files:**
- Create: `/opt/ACTIVE/WORKFORCE/run_pipeline.py`

```python
# /opt/ACTIVE/WORKFORCE/run_pipeline.py
import psycopg2
from datetime import datetime
from config import PG_DSN, DAILY_LIMIT, MIN_WORKERS_TO_SEND
from employer_loader import load_all_employers
from worker_matcher import match_employer
from pitcher import send_pitch

def already_sent(cur, email, source):
    cur.execute(
        "SELECT 1 FROM workforce_matches WHERE employer_email=%s AND employer_source=%s AND sent_at IS NOT NULL",
        (email, source)
    )
    return cur.fetchone() is not None

def log_match(cur, employer, workers, sent):
    worker_names = ", ".join([w["first_name"] for w in workers])
    cur.execute("""
        INSERT INTO workforce_matches
            (employer_source, employer_name, employer_email, sector, country,
             workers_matched, worker_names, sent_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (employer_email, employer_source) DO UPDATE
            SET sent_at = EXCLUDED.sent_at,
                workers_matched = EXCLUDED.workers_matched
    """, (
        employer["source"], employer.get("name"), employer["email"],
        employer["sector"], employer.get("country"),
        len(workers), worker_names,
        datetime.now() if sent else None
    ))

def run():
    conn = psycopg2.connect(PG_DSN)
    cur = conn.cursor()
    employers = load_all_employers()
    sent_count = 0

    for employer in employers:
        if sent_count >= DAILY_LIMIT:
            break
        if already_sent(cur, employer["email"], employer["source"]):
            continue
        workers = match_employer(employer)
        if len(workers) < MIN_WORKERS_TO_SEND:
            continue
        sent = send_pitch(employer, workers)
        log_match(cur, employer, workers, sent)
        conn.commit()
        if sent:
            sent_count += 1
            print(f"[SENT] {employer['source']} {employer['email']} ({len(workers)} workers)")

    conn.close()
    print(f"Pipeline done. Sent {sent_count}/{DAILY_LIMIT}")

if __name__ == "__main__":
    run()
```

- [ ] Dry run (no sends): comment out `send_pitch`, run pipeline, verify logs
- [ ] Re-enable `send_pitch`, send to 3 test employers
- [ ] Verify rows in `workforce_matches`: `psql $INTERJOB_PG_DSN -c "SELECT * FROM workforce_matches LIMIT 5"`
- [ ] Commit

---

## Chunk 4: Cron + Telegram

### Task 7: Cron + Telegram summary

**Files:**
- Modify: `/opt/ACTIVE/INFRA/SKILLS/bot_watchdog.py` (add workforce check)
- Create: `/opt/ACTIVE/WORKFORCE/workforce_summary.py`

- [ ] Add cron on raspibig:
  ```bash
  crontab -e
  # Add:
  0 8 * * * cd /opt/ACTIVE/WORKFORCE && python3 run_pipeline.py >> /home/tudor/.logs/workforce.log 2>&1
  ```

- [ ] Create summary script (called by bot `/workforce` command):

```python
# /opt/ACTIVE/WORKFORCE/workforce_summary.py
import psycopg2, os

def summary():
    conn = psycopg2.connect(os.environ["INTERJOB_PG_DSN"])
    cur = conn.cursor()
    cur.execute("""
        SELECT employer_source, COUNT(*) as sent,
               SUM(CASE WHEN response IS NOT NULL THEN 1 ELSE 0 END) as responses,
               SUM(placement_fee) as revenue
        FROM workforce_matches
        WHERE sent_at IS NOT NULL
        GROUP BY employer_source
        ORDER BY sent DESC
    """)
    rows = cur.fetchall()
    conn.close()
    lines = ["*Workforce Exchange Summary*"]
    total_sent = total_resp = total_rev = 0
    for r in rows:
        lines.append(f"{r[0]}: {r[1]} sent, {r[2]} responses, €{r[3] or 0:.0f}")
        total_sent += r[1]; total_resp += r[2]; total_rev += float(r[3] or 0)
    lines.append(f"TOTAL: {total_sent} sent | {total_resp} responses | €{total_rev:.0f} revenue")
    return "\n".join(lines)

if __name__ == "__main__":
    print(summary())
```

- [ ] Add `/workforce` to Telegram bot commands in `raspibig_controller_bot.py`
- [ ] Test: `python3 workforce_summary.py`
- [ ] Commit all

---

## Chunk 5: Landing Page

### Task 8: interjob.ro/contractors/ page

**Files:**
- Create: `D:\MEMORY\SITE_PAGES\interjob.ro\contractors\index.html`
- Deploy via cPanel API to `~/interjob.ro/contractors/index.html`

- [ ] Create simple page (static HTML, <100 lines):
  - Headline: "We place workers in your company — pay only on success"
  - 3 bullet benefits
  - CTA: email `office@mivromania.info`
  - Pricing: €299/placement or €79/month pool access

- [ ] Deploy via A2 cPanel API (UAPI FileManager):
  ```python
  # Use existing A2_SITE_DEPLOYER pattern
  ```
- [ ] Verify live: `curl -I https://interjob.ro/contractors/`
- [ ] Commit

---

## Summary

| File | Lines | Purpose |
|------|-------|---------|
| `init_db.py` | 20 | Create workforce_matches table |
| `config.py` | 25 | Keys, limits, sector map |
| `employer_loader.py` | 80 | Load from 4 sources, deduplicate |
| `worker_matcher.py` | 50 | Match workers by sector |
| `pitcher.py` | 55 | Render + send Brevo email |
| `run_pipeline.py` | 60 | Orchestrate daily run |
| `workforce_summary.py` | 35 | Telegram /workforce stats |

**Total: ~325 lines across 7 files. Deploy to raspibig `/opt/ACTIVE/WORKFORCE/`.**
