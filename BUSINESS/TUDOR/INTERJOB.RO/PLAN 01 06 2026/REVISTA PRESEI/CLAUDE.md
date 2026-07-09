# CLAUDE.md — REVISTA PRESEI

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**v1.1 | 2026-06-04 | Revista Presei — Daily Romania Press Review for expatsinromania.org**

---

## 🎯 Harness: REVISTA PRESEI

**Goal:** Run the daily press review end-to-end — fetch RSS → summarize+translate → WordPress publish + RSS deploy → social fan-out → health verdict.

**Trigger:** For any press-review operational task (run/rerun/regenerate/publish/debug/add-source/status), use the `revista-presei-orchestrator` skill. Direct factual questions can be answered without it.

**Team:** 5 agents (`.claude/agents/`): rss-fetcher → content-summarizer → wp-publisher → social-distributor → press-monitor. Skills (`.claude/skills/`): press-rss-fetch, press-summarize, press-wp-publish, press-social-distribute + orchestrator. Reuses global `a2-wp-bootstrap` + `infrastructure-health`.

**Change history:**
| Date | Change | Target | Reason |
|------|--------|--------|--------|
| 2026-06-26 | Initial harness build | `.claude/` (5 agents + 5 skills) | Pipeline pattern over the live press_review.py flow |

---

## Overview

Automated daily press review pipeline that:
1. Scrapes 11 RSS sources (7 Romanian + 4 English)
2. Translates Romanian articles to English
3. Summarizes all articles via Ollama (qwen3-4b)
4. Posts to expatsinromania.org WordPress as "Press Review" category
5. Generates RSS 2.0 feed deployed to A2 Hosting
6. Tracks all articles in PostgreSQL (interjob_master)

**Deployed on:** raspibig (`/opt/ACTIVE/EVENT_PUBLISHER/`)
**Cron:** Daily 08:00 UTC
**Output:** WordPress post + RSS feed at https://expatsinromania.org/press-review/feed.xml

---

## Architecture

### Component Breakdown

| Script | Role | Lines | Key Responsibility |
|--------|------|-------|-------------------|
| `press_review.py` | Orchestrator | 292 | DB operations, WP posting, RSS generation, cPanel deploy |
| `press_review_rss.py` | RSS Engine | 161 | Fetch RSS feeds, parse XML, classify topics, generate XML output |
| `translate_ro.py` | I18N | 68 | Romanian→English translation via Google Translate |

### Pipeline Flow

```
RSS Fetching (press_review_rss.py)
  ↓ parse XML, classify by topic, deduplicate (max 15 articles)
  ↓
Translation (translate_ro.py)
  ↓ RO articles → EN, add country flags
  ↓
Summarization (press_review.py → Ollama)
  ↓ 2-sentence English summaries via qwen3-4b
  ↓
WordPress Post
  ↓ Basic auth, ensure "Press Review" category exists, publish
  ↓
RSS Feed Generation (press_review_rss.py)
  ↓ last 30 daily reviews → RSS 2.0 XML
  ↓
cPanel Deploy (press_review.py)
  ↓ Upload feed.xml to /home/loaiidil/expatsinromania.org/press-review/feed.xml
  ↓
DB Tracking (PostgreSQL)
  ↓ 2 tables: press_review_posts + press_review_articles
```

### Data Sources (11 Total)

**English (no translation):**
- Romania Insider
- Nine O'Clock
- Agerpres EN
- Business Review EU (currently commented out — add if needed)

**Romanian (Ollama translates in summary):**
- Ziarul Financiar
- Ziare.com
- Digi24, ProTV Știri, HotNews, Mediafax, Adevărul, Capital

### Topic Classification

Topics assigned via keyword matching in title+description:
- **Economy:** GDP, inflation, budget, business, investment, afaceri, economie
- **Politics:** parliament, government, minister, election, NATO, EU, gobierno
- **Society:** health, education, crime, population, housing, energie, sănătate
- **Culture:** art, music, tourism, sport, heritage, cultura

Fallback: "Society" if no keywords match.

---

## Development Commands

### Local Testing (Windows laptop)

```powershell
# Test RSS fetching only (dry-run, no DB)
python3 .\press_review_rss.py --test-sources

# Translate smoke test
python3 .\translate_ro.py   # runs self-test at bottom

# Full pipeline dry-run (fetch+summarize, no WP post)
# (Requires Windows laptop to have psycopg2 + requests + deep_translator installed)
```

### On raspibig (over SSH)

```bash
# Test RSS + topic classification (no DB write)
plink -batch -pw 'RASPI_PW_REDACTED' tudor@192.168.100.21 "cd /opt/ACTIVE/EVENT_PUBLISHER && python3 press_review_rss.py --test-sources"

# Full dry-run: fetch → summarize → show HTML (no WP, no DB)
plink -batch -pw 'RASPI_PW_REDACTED' tudor@192.168.100.21 "cd /opt/ACTIVE/EVENT_PUBLISHER && python3 press_review.py --dry-run"

# Manual one-time publish
plink -batch -pw 'RASPI_PW_REDACTED' tudor@192.168.100.21 "cd /opt/ACTIVE/EVENT_PUBLISHER && python3 press_review.py"

# Check logs (last 50 lines)
plink -batch -pw 'RASPI_PW_REDACTED' tudor@192.168.100.21 "tail -50 /opt/ACTIVE/INFRA/LOGS/press_review.log"

# Verify cron job
plink -batch -pw 'RASPI_PW_REDACTED' tudor@192.168.100.21 "crontab -l | grep press_review"

# Test WP connectivity
plink -batch -pw 'RASPI_PW_REDACTED' tudor@192.168.100.21 "curl -s https://expatsinromania.org/wp-json/wp/v2/categories -H 'Authorization: Basic $(echo -n apaminerala:PASSWORD | base64)' | head -20"
```

### Database Inspection

```bash
# SSH to raspibig, then:
psql -d interjob_master

# Check today's articles
SELECT review_date, COUNT(*) FROM press_review_articles GROUP BY review_date ORDER BY review_date DESC LIMIT 5;

# Check WP posts
SELECT review_date, wp_post_id, wp_url FROM press_review_posts ORDER BY review_date DESC LIMIT 5;

# Count articles by topic
SELECT topic, COUNT(*) FROM press_review_articles WHERE review_date = '2026-06-04' GROUP BY topic;
```

---

## Configuration (VERIFIED 2026-06-04)

### Environment Variables (in `/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED/wp_sites.env`)

```
WP_EXPATSINROMANIA_ORG_USER=expatsinromania.org
WP_EXPATSINROMANIA_ORG_PASS=yej7 uHVG wXgd nFDH tojt KtoS
A2_CPANEL_API_TOKEN=SCLN8NYABRVUG41E9HXM4RYJ2VH6YJ1E
```

**Status:** ✅ Working — Press review posts successfully to expatsinromania.org

### Hardcoded Config (press_review.py lines 29-41)

```python
WP_URL = "https://expatsinromania.org"
WP_USER = "expatsinromania.org"  # override via env
OLLAMA = "http://localhost:11434/api/generate"  # raspibig Ollama
MODEL = "qwen3-4b:latest"  # fallback qwen2.5:1.5b if timeout > 180s
DB_DSN = "host=localhost dbname=interjob_master user=tudor password=RASPI_PW_REDACTED"
CPANEL_HOST = "nl1-cl8-ats1.a2hosting.com"
CPANEL_USER = "loaiidil"
DOCROOT = "/home/loaiidil/expatsinromania.org"
RSS_LOCAL = "/tmp/press_review_feed.xml"
```

To modify: edit hardcoded values in file or add `os.getenv("VAR", default)`.

---

## Database Schema

### press_review_posts

```sql
id          SERIAL PRIMARY KEY
review_date DATE UNIQUE NOT NULL
wp_post_id  INTEGER           — WP post ID if published
wp_url      TEXT              — WP post permalink
created_at  TIMESTAMPTZ DEFAULT NOW()
```

Used to: track which days have been published (avoid duplicates), store WP post IDs for updates.

### press_review_articles

```sql
id          SERIAL PRIMARY KEY
article_id  VARCHAR(32) UNIQUE NOT NULL  — MD5(link)
review_date DATE NOT NULL
source      TEXT                          — "Romania Insider", "Digi24", etc.
title       TEXT                          — English (translated if RO source)
link        TEXT
summary     TEXT                          — 2-3 sentence Ollama summary
topic       TEXT                          — "Economy", "Politics", "Society", "Culture"
```

Used to: build RSS feed, track historical articles, allow querying by topic/source.

---

## Key Code Patterns

### 1. RSS Parsing (press_review_rss.py:65–125)

```python
def fetch_articles(hours_back: int = 26) -> List[Dict]:
```

- Fetches from all sources in parallel (actually sequential but error-tolerant)
- Strips invalid XML chars (common in Romanian feeds)
- Supports both RSS 2.0 and Atom formats
- Deduplicates by URL hash (MD5)
- Classifies topic by keyword matching
- Returns max 15 articles sorted by recency

**Key handling:**
- Invalid XML → regex strip + try-except
- Missing fields → fallback to empty string
- Old articles (> hours_back) → skip
- Parse date → UTC timezone-aware

### 2. Ollama Summarization (press_review.py:111–144)

```python
def summarize(title: str, desc: str, lang: str = "en") -> str:
```

- Constructs prompt based on source language (RO vs EN)
- Posts to `localhost:11434/api/generate` (Ollama on raspibig)
- Strips `<think>...</think>` tags from qwen3 output
- Fallback: first 2 sentences from RSS description if Ollama fails/timeout
- Timeout: 90s per article

**Temperature:** 0.3 (deterministic), num_predict: 120 tokens.

### 3. WordPress Posting (press_review.py:148–177)

```python
def wp_post(title: str, html_body: str, category_id: int) -> dict:
```

- Basic auth (base64(user:pass))
- Auto-creates "Press Review" category if missing
- Posts to `/wp-json/wp/v2/posts` (standard WP REST API)
- Status: publish (immediate)
- Returns `{"id": post_id, "link": url, ...}`

**Auth pattern:** `Authorization: Basic {base64(user:pass)}`

### 4. cPanel File Upload (press_review.py:206–224)

```python
def deploy_to_cpanel(local_path: str, remote_rel: str) -> bool:
```

- Uses cPanel UAPI `Fileman/save_file_content` endpoint
- Auth via `cpanel user:token` header
- Saves to `/home/loaiidil/expatsinromania.org/{remote_rel}`
- Returns True if `status=1` in JSON response

**Note:** cPanel API is flaky; single failure is acceptable (RSS exists locally, can retry manually).

### 5. HTML Assembly (press_review.py:180–203)

```python
def build_html(articles, review_date) -> str:
```

- Groups by topic using `defaultdict`
- Outputs `<h2>Topic</h2>` sections in fixed order: Economy → Politics → Society → Culture
- Each article: `<h3><a href=...>Title</a></h3><p>Summary</p>`
- Footer with sources list

**Accessibility:** Links open in `target="_blank" rel="noopener"`.

---

## Common Workflows

### Debug: Why Didn't Post Publish?

1. Check WP password in wp_sites.env: `WP_EXPATSINROMANIA_ORG_PASS=SET_AFTER_INSTALL`?
2. Test WP connectivity: `curl https://expatsinromania.org/wp-json/wp/v2/categories -u user:pass`
3. Check logs: `tail /opt/ACTIVE/INFRA/LOGS/press_review.log`
4. Run dry-run: `python3 press_review.py --dry-run` (requires code edit to add flag)

### Add New RSS Source

1. Edit `city_news_config.py` — add dict to `RSS_SOURCES` list
2. Test locally: import and verify
3. Deploy: copy both `city_news_config.py` and `press_review_rss.py` to raspibig `/opt/ACTIVE/EVENT_PUBLISHER/`
4. No cron change needed (reads from config at runtime)
5. Note: `press_review_rss.py` imports RSS_SOURCES from city_news_config.py, so both files must be in sync

### Adjust Topic Keywords

1. Edit `city_news_config.py:111–138` (`TOPIC_KEYWORDS` dict)
2. Add keyword(s) to relevant topic list
3. Deploy updated `city_news_config.py` to raspibig `/opt/ACTIVE/EVENT_PUBLISHER/`
4. Note: `press_review_rss.py` imports TOPIC_KEYWORDS from city_news_config.py; classification will use new keywords immediately

### Run Manual Publish

```bash
cd /opt/ACTIVE/EVENT_PUBLISHER
python3 press_review.py
```

Respects `already_posted()` check — will skip if today's review already in DB.
Use `--force` flag to re-publish (requires code edit).

### Generate Feed Offline

```python
from press_review_rss import build_rss_feed
from datetime import datetime, timezone

items = [
    {"title": "...", "link": "...", "pub_date": datetime.now(timezone.utc), "summary": "..."}
]
build_rss_feed(items, "/tmp/test_feed.xml")
```

---

## Integration with InterJob

**Parent project:** `/PLAN 01 06 2026/CLAUDE.md` — Multi-domain job marketplace backend.

**Relationship:**
- This is one **event publisher** (alongside `daily_roundup.py`, `wordpress_publisher.py`)
- Shares: PostgreSQL (interjob_master), cPanel credentials, WP sites list
- Published to: expatsinromania.org (which is listed as press-review-focused in parent CLAUDE.md)

**Shared files:**
- `/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED/wp_sites.env` — all WP credentials
- `/opt/ACTIVE/INFRA/LOGS/press_review.log` — parent project monitors this

---

## Performance & Limits

- **Max articles per run:** 15 (to keep post size reasonable)
- **RSS feed retention:** 30 items (oldest dropped after 30 daily reviews)
- **Ollama timeout:** 180s per article (fallback to RSS description on timeout)
- **Translation batch size:** No limit (process sequentially with 0.15s delay to avoid rate limits)
- **cPanel upload:** Non-critical (RSS exists locally, manual retry possible)

---

## Status & Blockers (UPDATED — 2026-06-07)

### ✅ FULLY OPERATIONAL & ENHANCED

**Core Pipeline:**
- ✅ Scripts deployed on raspibig (`/opt/ACTIVE/EVENT_PUBLISHER/`)
- ✅ RSS sources: 10 sources (Romania Insider, Nine O'Clock, HotNews, Ziare.com, Digi24, Mediafax, Profit.ro, Ziarul Financiar, AGERPRES, G4Media)
- ✅ Topics: 12 categories (Economy, Energy, Agriculture, Real Estate, Technology, Labor, Infrastructure, Manufacturing, Legal, Politics, Society, Culture)
- ✅ Ollama qwen3-4b available (180s timeout, fallback to RSS description)
- ✅ DB tables: press_review_posts, press_review_articles
- ✅ WordPress: expatsinromania.org, app password configured
- ✅ Facebook: Expats in Romania page (ID: 102068074657345)

**Magazine-Style Layout (2026-06-07):**
- ✅ Hero section with title, date, metadata (sources, story count) — styled with inline CSS
- ✅ Featured story from Economy topic in gray box with border
- ✅ Topic sections grouped with story counts (e.g., "Energy (2 stories)")
- ✅ Individual article styling: h3 titles, summaries, source attribution
- ✅ Dynamic footer listing all contributing sources
- ✅ All 12 topics represented (no silent article omission)
- ✅ Live posts: https://expatsinromania.org/romania-press-review-june-7-2026-3/ ✅

**Facebook Integration (2026-06-07):**
- ✅ Article summaries in message (top 3 articles with sources)
- ✅ Format: Title + article previews + WordPress link + hashtags
- ✅ Successfully posts to Expats in Romania page (verified API 200 OK)
- ✅ Simultaneous publication with WordPress post at 08:50 UTC

**Previous Code Quality Fixes (2026-06-06):**
- ✅ CRITICAL: Removed hardcoded cPanel token
- ✅ CRITICAL: Removed emoji from messages
- ✅ CRITICAL: TOPIC_ORDER expanded 4→12 topics
- ✅ HIGH: RSS_SOURCES + TOPIC_KEYWORDS unified (imported from city_news_config.py)
- ✅ HIGH: GoogleTranslator moved outside loop
- ✅ HIGH: save_articles() uses executemany()

### ⏳ PRODUCTION READY

- ⏳ **Cron:** Daily 08:50 UTC (verified CRONTAB RASPIBIG in parent CLAUDE.md)
- ⏳ **Next execution:** Tomorrow will use magazine layout + Facebook summaries
- ⏳ **cPanel RSS deploy:** Non-critical — local fallback works

---

## References

- Parent project: `/PLAN 01 06 2026/CLAUDE.md`
- WP credentials: `/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED/wp_sites.env`
- Logs: `/opt/ACTIVE/INFRA/LOGS/press_review.log`
- DB: `interjob_master` on raspibig:5432
- RSS output: `https://expatsinromania.org/press-review/feed.xml`
