# CLAUDE.md — D:\MEMORY

**v1.6.2 | 2026-05-27**

---

## Communication Style

**ALWAYS USE NUMBERED RESPONSES** — every list, step, or option uses 1. 2. 3.

**TUDOR'S PERSONAL STYLE:**

- **Ultra-direct, action-first.** No preamble/postamble. Maximum 4 lines unless explaining complex work.
- **Staccato rhythm.** Each line stands alone. No transitions. White space as punctuation.
- **Imperative-heavy.** Commands, not suggestions. "Execute X. Then Y."
- **Numerical precision.** Always quantify. "€15K-30K/month in 6 months", "80% energy"
- **File references required.** Always include `file.txt:line` for sources.
- **Self-coaching tone.** Write as if talking to future self.
- **If/then structures.** "IF €0 + 2h/day → X. IF €5K + 4h/day → Y."
- **Bilingual awareness.** Romanian primary, English for business/technical.
- **Timeline scaffolding.** Break everything: DAY 1 → WEEK 1 → MONTH 1.
- **Problem-solution pairs.** "P1: X → Y" format.
- **Checklist format.** Use `[ ]` for action items.
- **Prioritization.** Always rank. "#1", "#2", "80/15/5 split."

**NEVER:**
- Transitions ("However," "Therefore")
- Softeners ("I think," "maybe," "possibly")
- Repetition of known context
- Long explanations
- Questions directed at others

---

## CHANGE LOG

### 2026-05-27
- # Created SSH Raspibig Setup skill: `.claude/skills/ssh-raspibig-setup.md`
- # Added SSH Raspibig convention to Conventions section
- # Added Epistemic Standards section: uncertainty, sources, numbers, recent events, people/quotes
- # Version 1.6.2

### 2026-05-22
- # Added Tudor's writing style analysis to Communication Style section
- # Updated version to 1.6.0
- # Merged personal style guidelines with existing numbered response rule

### 2026-05-17
- # Updated infrastructure section with WSL2 Debian details
- # Added Ollama service restart commands
- # Version 1.5.0

---

## Coding Standards

1. **250-line max** per file — split on responsibility if larger
2. **Python template**: `#!/usr/bin/env python3`, one-line docstring, `main()`, `if __name__ == "__main__"`
3. **Data safety**: Never delete DB tables/CSVs/contacts without verified backup. Archive first.
4. **Async I/O**: `aiohttp`/`asyncio` for email/API/file ops
5. **Local LLM only**: Ollama qwen3-4b on raspibig:1234 for pipeline. Claude API only for strategic/user-facing.
6. **Comments**: WHY only, no WHAT, no docblocks
7. **Error handling**: Only at system boundaries (user input, external APIs)

**SQL safety pattern:**
```sql
SELECT count(*) FROM table WHERE condition;           -- check first
INSERT INTO table_archive SELECT * FROM table WHERE condition;  -- archive
DELETE FROM table WHERE condition;                    -- then delete
```

## Epistemic Standards

**Source:** `D:\MEMORY\AUDIT BOTH SYSTEMS\CLAUDE GUIDELINES\guidelines.txt`

1. **Uncertainty** — Flag claims you're not certain about: "I'm not certain, but...", "Verify this..."
2. **Numbers** — Every stat/estimate cite DB schema or mark "unknown". Range only if justified.
3. **Sources** — Never invent sources (URLs, studies, quotes, legal cases). Cite real docs or say "based on general knowledge".
4. **Recent events** — Note knowledge cutoff (Feb 2025). Say "may have changed, verify current source".
5. **People & quotes** — Never attribute quotes without certainty. Separate facts from interpretation.

**CRITICAL for:**
- Legal cases (LUCIU 10.322 RON, BILIE 3.250 EUR, ASOC PROP Dosar 9510) — source every claim
- DB enrichment (33M companies_clean) — flag if ANAF lookup failed, note harvest date
- Campaign data — mark contact info age (e.g., "scraped 2026-05-15, may be stale")
- Estimates — "approx €X-Y based on Z source" NOT "€X"

**Final check:** If any claim feels guessed → revise before responding.

---

## Infrastructure

|| Machine | IP | Role |
||---------|-----|------|
|| **Windows laptop** | localhost | Python 3.14, 64GB RAM, D:\MEMORY (main coding) |
|| **WSL2 Debian** | 172.21.138.13 | Postgres 13 :5432, Ollama :11434, local dev mirror |
|| **raspibig** | 192.168.100.21 | Campaigns, enrichment, bots, N8N :5678 (prod) |
|| **raspi** | 192.168.100.20 | Scrapers, Node-RED, ProtonVPN |
|| **A2 Hosting** | nl1-cl8-ats1.a2hosting.com | Production web (cPanel only, no SSH) |

**DB**: PostgreSQL 18, port 5432, `interjob_master`, user/pass: tudor/tudor
**Key tables**: `companies_clean` (33M), `master_emails` (1.03M), `ted_awards` (6.2M), `tenders` (5.1M)

---

## Directories

**ACTIVE (LAPTOP):**
- `BUSINESS/AGROEVOLUTION.COM/` — 9,658 land listings, A2 Hosting deployment
- `CODE/CAMPAIGNS/` — Email campaigns, Brevo (1,560→2,560/day)
- `CODE/INFRA/` — AUTOMATE (distributed queue), FASTAPI (company API), CLAUDE/SITE_PAGES (job sites)
- `PERSONAL/` — Legal cases (LUCIU, BILIE, ASOC PROP)

**ARCHIVED (16.3 GB in BACKUPS/ARCHIVED/):**
- `INFRA_LLAMA_CPP_2026-05-08` — Local LLM test (6.50 GB)
- `INFRA_SANDBOX_BULGARIAN_2026-03-06` — BG procurement (3,530 emails) (1.74 GB)
- `INFRA_PROCUREMENT_ARCHIVED_2025-04-18` — Old procurement (8.06 GB)
- `INFRA_GOOSE_EBRD_2026-04-10` — EBRD research (0.3 GB)

See: `BACKUPS/ARCHIVED/MANIFEST.md` for details.

Active planning: `CODE/CAMPAIGNS/EMAIL PERSONAL/.planning/`, `BUSINESS/AGROEVOLUTION.COM/.planning/`

---

## Conventions

- **SSH Raspibig**: Use `/ssh-raspibig-setup` to configure passwordless access (generates RSA key if missing, copies to authorized_keys, updates settings.json). One-time password entry required.
- SSH: always `192.168.100.21` (not hostname — Tailscale issue)
- SSH config: ControlMaster+ControlPersist 15m active — reconnects are instant, no disconnection prompts
- SCP to Windows: forward slashes `"D:/MEMORY/path/"`
- SSH commands: single quotes around remote command
- A2 docroot: `~/domainname/` (NOT `~/public_html/`)
- RTL languages (ar, ur, ps): `dir="rtl"` in HTML
- Apply links → `https://interjob.ro/apply.html`
- Email responses → `manpower.dristor@gmail.com`
- Telegram bot: `@raspibig_controller_bot` (37 commands, only bot)

---

## Safety Blocks

|| Trigger | Action |
||---------|--------|
|| `DROP TABLE` / `TRUNCATE` | Show table + row count, wait for "yes" |
|| `DELETE FROM` without `WHERE` | Hard block |
|| `rm -rf` on `D:\MEMORY\DATA\` or `/opt/ACTIVE/` | Archive first, then ask |
|| `git push --force` | Show branch + remote, confirm first |
|| cPanel file overwrite on production | Show diff, wait for approval |

---

## Low Token Strategy

1. **Run locally** — DB steps, campaigns, scrapers are scripts, not LLM tasks
2. **Subagents**: `pg-enricher` (DB), `brevo-sender` (campaigns), `cpanel-deployer` (A2), `madr-scraper` (land)
3. **Grep/Glob first** — never read full codebase (5,869 Python files)
4. **MCP for DB** — configured in `.mcp.json`, use over manual `psql.exe`
5. **Minimal context** — load `PROJECT.md` + `STATE.md` only when resuming

---

## Key Services (raspibig)

|| Service | Port/Location |
||---------|--------------|
|| N8N | :5678, systemd, HTTPS via Caddy |
|| PostgreSQL | :5433, interjob_master |
|| Campaign orchestrator | `/opt/ACTIVE/EMAIL/CAMPAIGNS/orchestrator.py` |
|| Response tracker | `/opt/ACTIVE/INFRA/SKILLS/response_tracker.py` |
|| Bot watchdog | `/opt/ACTIVE/INFRA/SKILLS/bot_watchdog.py` |
|| NanoClaw | `/opt/ACTIVE/INFRA/GOVERNOR/nanoclaw.py` |

---

## Local Coding Machine (WSL2 Debian)

**Setup 2026-05-17:**
- Distribution: Debian 11 (bullseye) in WSL2
- Access: `wsl -d Debian` (default user `tudor`, root via `-u root`)
- Python: 3.9.2 (Linux) + 3.14.4 (Windows native)
- Postgres: 13.23 on :5432 — DB `dev_local`, owner `tudor`
- Ollama: `localhost:11434` (auto-forwarded from WSL2)
- Workflow: code on Windows D:\MEMORY → test in WSL2 → deploy raspibig/A2

**Start Postgres after WSL restart:**
```bash
wsl -d Debian -u root -- service postgresql start
```

**Start Ollama after WSL restart:**
```bash
wsl -d Debian -u root -- bash -c "nohup ollama serve > /tmp/ollama.log 2>&1 &"
```

---

## AgroEvolution.com (A2 Hosting)

|| Item | Value |
||------|-------|
|| cPanel user | `loaiidil` |
|| cPanel token | `MK0WQEH59KHVXQ8JRKKZ26LVSMT4LI7U` |
|| cPanel URL | `https://loaiidil.a2hosted.com:2083` |
|| Docroot | `/home/loaiidil/agroevolution.com/` |
|| PS DB | `loaiidil_pres849` / `S1!WS0p8[2` / prefix `psdf_` |
|| PS Admin | `https://agroevolution.com/admin123/` |

**Deploy pattern**: Python → cPanel Fileman API (multipart POST, no SSH)
**Smarty cache**: After template changes → run `ps_smarty_clear.php`, NEVER delete `var/cache/prod/` (kills Symfony container)
**Local source files**: `D:\MEMORY\CODE\INFRA\WEBPAGES\AGROEVOLUTION\`
**Unified deployer**: `cpanel_deploy.py` (TODO — currently 3 separate scripts in git history)

---

## Sensitive Files

`raspi.json`, `OPT/opt/EMAIL/.env`, `A2_SITE_DEPLOYER/env/*.env` — do not share or commit.