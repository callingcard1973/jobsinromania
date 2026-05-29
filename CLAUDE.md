# CLAUDE.md — D:\MEMORY

**v1.6.4 | 2026-05-28**

---

## Style

**Numbered. Direct. No preamble. Max 4 lines unless explaining. Staccato. Imperative. Quantify. File:line refs. Self-coaching. No transitions/softeners.**

---

## CHANGE LOG

**See STATE.md for live infrastructure status, queue metrics, and scraper state.**

v1.6.4 additions:
- Epistemic Standards: uncertainty flags, source citations, legal case rigor
- Low Token Strategy: subagents (pg-enricher, brevo-sender, cpanel-deployer, madr-scraper)
- SSL auto-renewal, TTFB optimization (-35%), raspibig N8N, raspi recovery procedures

---

## Infrastructure

| Machine | IP | Role |
|---------|-----|------|
| Windows laptop | localhost | Python 3.14, D:\MEMORY |
| WSL2 Debian | 172.21.138.13 | PostgreSQL 13, Ollama |
| raspibig | 192.168.100.21 | N8N, campaigns, email |
| raspi | 192.168.100.20 | Scrapers, ProtonVPN |
| A2 Hosting | nl1-cl8-ats1.a2hosting.com | 30 domains (cPanel only) |

**DB:** PostgreSQL 18, interjob_master | **cPanel:** loaiidil | `MK0WQEH59KHVXQ8JRKKZ26LVSMT4LI7U`

---

## Directories (Active)

- `BUSINESS/AGROEVOLUTION.COM/` — 9,658 land listings
- `CODE/CAMPAIGNS/` — Brevo email (1,560→2,560/day)
- `CODE/INFRA/` — AUTOMATE, FASTAPI, SITE_PAGES
- `PERSONAL/` — LUCIU, BILIE, ASOC PROP cases

---

## Key Conventions

- SSH raspibig: `192.168.100.21` (always IP, not hostname)
- SSH ControlMaster+ControlPersist 15m active
- A2 docroot: `~/domainname/` (not ~/public_html/)
- Email: manpower.dristor@gmail.com
- Apply link: https://interjob.ro/apply.html

---

## Coding Standards

- **250-line max** per file
- **Python**: `#!/usr/bin/env python3`, one-liner docstring, `main()`, `if __name__`
- **Data safety**: Archive before delete. SELECT count → INSERT archive → DELETE
- **Async I/O**: aiohttp/asyncio for email/API/file ops
- **Local LLM**: Ollama on raspibig:1234. Claude API only for strategic/user-facing
- **Comments**: WHY only, no WHAT
- **Error handling**: Only at system boundaries

---

## Epistemic Standards

1. Flag uncertainty: "I'm not certain, but..." 
2. Cite numbers or mark "unknown"
3. Never invent sources (URLs, studies, quotes)
4. Note knowledge cutoff (Feb 2025)
5. Don't attribute quotes without certainty

**CRITICAL:** Legal cases (LUCIU 10.322 RON, BILIE 3.250 EUR, ASOC PROP 9510) — source every claim.

---

## Low Token Strategy

1. Run locally (DB, campaigns, scrapers = scripts, not LLM)
2. Use subagents: pg-enricher (DB), brevo-sender (campaigns), cpanel-deployer (A2), madr-scraper (land)
3. Grep/Glob first — never read full codebase
4. MCP for DB — configured in `.mcp.json`
5. Minimal context — load PROJECT.md + STATE.md only

---

## Next Maintenance (2026-06-28)

- Weekly SSL check (nepalezi.com auto-renewal)
- Monthly full audit (30 domains)
- Monitor EURES metrics pipeline
- Test cache effectiveness (post-warmup TTFB)
