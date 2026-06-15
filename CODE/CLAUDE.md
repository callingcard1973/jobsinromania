# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Quick Start

**Repository Structure:** Monorepo with 3 main areas:
- `ACTIVE/` — active projects, skills, campaigns, infrastructure automation
- `COWORK/` — collaborative scripts, FastAPI deployment tools, MADR land/property data
- `INFRA/` — infrastructure utilities and documentation

**Environment:** Windows laptop (dev) → raspibig (192.168.100.21, production 24/7) → raspi (192.168.100.20, scrapers)

---

## OpenRouter Integration (Free Models)

**Configuration:** `.env` or environment variables

```bash
OPENROUTER_API_KEY=sk-or-v1-REDACTED
```

**Free Models Available:**
- `openrouter/auto` — Fallback routing to free tier
- `meta-llama/llama-3-8b-instruct` — 8B parameter, fast inference
- `mistralai/mistral-7b-instruct` — 7B parameter, balanced
- `nvidia/nemotron-3-super` — NVIDIA's free offering (fast)
- `nvidia/nemotron-3-ultra` — NVIDIA's premium free tier
- `owl-ai/owl-alpha` — Owl Alpha (new free model)

**Usage in Python:**

```python
import httpx

async def call_openrouter(prompt: str, model: str = "openrouter/auto"):
    """Call OpenRouter with free tier."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                "HTTP-Referer": "https://interjob.ro",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2048,
            },
        )
    return resp.json()
```

**Default behavior:** Start with `openrouter/auto` for cost-free routing; switch to specific model if consistency needed.

---

## Core Projects

### 1. Universal Classified Ads Platform

**Location:** `ACTIVE/Universal Classified Ads Platform/`

**Architecture:**
- Backend: FastAPI (Python, `backend/app/`)
- Database: SQLite (`classified_ads.db`) + SQLAlchemy ORM
- Auth: JWT (python-jose) + bcrypt
- Payments: Stripe integration
- Analytics: PostHog
- Frontend: Jinja2 templates + static files (`frontend/` — not tracked in git)

**Key entry point:** `backend/app/main.py` (FastAPI app, routes, middleware)

**Routers:**
- `auth_router` — Login, register, JWT tokens
- `ads_router` — CRUD for classified ads
- `users_router` — User profiles
- `admin_router` — Admin dashboard
- `categories_router` — Ad categories
- `payments_router` — Stripe checkout
- `media_router` — Image upload/download

**Database schema:** `app/models/` (SQLAlchemy models). Default categories seeded on startup.

**Key services:**
- `app/core/database.py` — SQLAlchemy SessionLocal, engine
- `app/core/config.py` — Pydantic settings from env
- `app/core/analytics.py` — PostHog client
- `app/services/` — Business logic (ad filtering, payments, user ops)

**Tests:** `pytest` configured in `pytest.ini`. Run: `pytest` or `pytest -v --cov=app`

**Dependencies:** See `backend/requirements.txt` (FastAPI, SQLAlchemy, Celery/Redis for async tasks, Stripe, PostHog)

**Common commands:**
```bash
cd "ACTIVE/Universal Classified Ads Platform/backend"
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pytest                                  # Run all tests
pytest tests/test_auth.py -v           # Single test file
pytest -k "test_create_ad" --cov=app   # Filter + coverage
```

**Deployment:** `deploy.ps1` (PowerShell script, handles Docker build, push to raspibig)

---

### 2. Skills Library (640 Python Agents)

**Location:** `ACTIVE/SKILLS/` (laptop source) | synced to raspibig `/opt/ACTIVE/SKILLS/`

**Organization:** 640 .py files, each ≤250 lines, one skill per file

**Naming:** `skill_name.py` or `noun_verb.py` (e.g., `email_send.py`, `database_query.py`)

**Standard structure:**
```python
#!/usr/bin/env python3
"""One-line skill description."""

async def main():
    """Entry point."""
    pass

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

**Key skills:**
- Email: `email_send.py`, `email_parse.py`, `gmail_api_*.py`
- Database: `postgres_query.py`, `db_*.py`
- Scraping: `scrape_madr.py`, `scrape_*.py`
- Data processing: `csv_to_json.py`, `dedup_*.py`
- Automation: `cron_*.py`, `scheduler_*.py`

**Sync:** Manual with `COWORK/INFRA/sync_skills.ps1` (pushes laptop → raspibig + raspi)

---

### 3. Email Campaigns & Orchestration

**Location:** `ACTIVE/CAMPAIGNS/` + `/opt/ACTIVE/EMAIL/CAMPAIGNS/` (raspibig)

**Active campaigns:**
- PRIMARII — Cold email to 2,904 Romanian mayors (gentle 50/day)
- FACTORY_RO — Factory outreach (728 leads)
- Plus 8 others managed via `campaigns.json` config

**Dashboard:** Port 8096 on raspibig (Command Center showing active campaigns)

**Orchestrator:** `supervisor_email_orchestrator.py` (respects rate limits, bounce suppression, DNC list)

**Brevo integration:** 9 accounts, API calls via `aiohttp` (never SMTP on raspibig directly)

---

### 4. Infrastructure & Automation

**Location:** `ACTIVE/INFRA/` + `COWORK/INFRA/`

**Key services on raspibig:**
- FastAPI (port 8000) — internal stub, not public
- PostgreSQL 15.15 (port 5432) — interjob_master database
- Redis — caching + Celery task queue
- N8N (port 5678) — visual workflow automation
- Caddy reverse proxy — public HTTPS frontend

**Monitoring:** `monitor_crons.py` (checks 25+ scheduled jobs every 30 min, alerts via email/Telegram/daily digest)

**Common tasks:**
- SSH to raspibig: `plink -batch -pw 'REDACTED' tudor@192.168.100.21 "<cmd>"`
- Check service status: `systemctl status <service>`
- View logs: `/opt/ACTIVE/INFRA/LOGS/` (cron_history.log, monitor.log)

---

## Coding Standards (This Codebase)

1. **File size:** ≤250 lines per file (exceptions: generated catalogs, data files)
2. **Python:** 3.12+ async-first where applicable; use aiohttp, asyncio, httpx
3. **Database:** PostgreSQL (15.15) on raspibig; local SQLite for testing only
4. **Comments:** WHY only, not WHAT. Keep them rare.
5. **Error handling:** At system boundaries (user input, external APIs); trust internal code
6. **No premature abstractions:** 3 similar functions is fine; abstract only when a 4th appears
7. **Data safety:** Archive before delete. SELECT count → INSERT archive → DELETE

**Test structure:** Colocate tests near code. Pytest fixtures for DB/API setup. Minimum 70% coverage for new features.

---

## Development Workflow

**Before committing:**
1. Run linting: (project-specific; check each subproject)
2. Run tests: `pytest` (or project-specific test runner)
3. Verify no secrets in code: `grep -r "api_key\|password\|token" app/`

**Git workflow:**
- Branch: Feature branches off `main` (short-lived)
- Commits: Clear messages; reference issue if applicable
- PR: Include test coverage + summary of changes

**Local dev with raspibig:**
- SSH keys: Use `plink` (Windows laptop via PuTTY); no password entry needed
- Persistent connection: ControlMaster pooling (configure once, reuse)
- File sync: Use `pscp` for small files; git push for larger changesets

---

## Performance & Optimization

**Database queries:**
- Use indexed columns; avoid N+1 queries (use SQLAlchemy `joinedload` or `selectinload`)
- For large datasets, paginate (limit + offset or keyset pagination)

**Caching:**
- Redis for session state, rate-limit counters
- PostHog analytics batched, not per-request

**Async I/O:**
- Email sends: batch with `aiofiles` + asyncio gather
- External APIs: use `httpx.AsyncClient` pooling
- Celery for long-running tasks (not synchronous blocking)

---

## Troubleshooting

**PostgreSQL connection errors:**
- Verify `~/.pgpass` has correct credentials (chmod 600)
- Check port 5432 open on raspibig
- Check interjob_master database exists: `psql -h 192.168.100.21 -U postgres -l`

**FastAPI not responding:**
- SSH to raspibig: `systemctl status interjob-api`
- Check logs: `journalctl -u interjob-api -n 50`
- Verify port 8000 listening: `netstat -tlnp | grep 8000`

**Skills sync issues:**
- Manually run: `.\COWORK\INFRA\sync_skills.ps1`
- Verify SSH key works: `plink -batch -pw 'REDACTED' tudor@192.168.100.21 "ls /opt/ACTIVE/SKILLS | wc -l"`

**Campaign delivery failures:**
- Check Brevo API quota: `curl https://api.brevo.com/v3/account`
- Verify Gmail bounce cleaner ran: Check `/opt/ACTIVE/EMAIL/CAMPAIGNS/PRIMARII/` for latest bounce report

---

## Key Contacts & Credentials

**Email:** fruitnature4@gmail.com (primary account)

**Infrastructure:** See parent `/MEMORY/CLAUDE.md` for detailed credential storage (`.env` files, not in git)

**APIs:**
- Brevo: 9 accounts in `/MEMORY/STATE.md`
- PostHog: Key in `ACTIVE/Universal Classified Ads Platform/backend/.env`
- Stripe: Keys in same .env

---

## References

- **Parent CLAUDE.md:** `/MEMORY/CLAUDE.md` (system-wide architecture, strategic directives, infrastructure reference)
- **STATE.md:** `/MEMORY/STATE.md` (live infrastructure status, queue metrics)
- **Raspibig guide:** `/MEMORY/COWORK/CLAUDE.md` (deployment details, SSH patterns)

---

## Notes for Future Sessions

- This monorepo spans 15+ GB; Glob/Grep before reading full files
- Universal Classified Ads Platform is the primary active project; focus there for most feature work
- 640 skills are helpers; don't modify unless adding new capability
- raspibig is always-on production; never restart without backup
- Campaigns run on strict schedules; verify cron config before changes

---

**Last Updated:** 2026-06-15 | **Format:** Markdown (UTF-8)
