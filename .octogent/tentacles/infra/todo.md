# Todo

## Session 2026-04-21 — PostHog Cloud Tracking Setup

### Done
- PostHog self-hosted abandonat (Docker Desktop crash sub greutatea hobby stack)
- Decis: PostHog Cloud (US host) cu project `390426` — ManPower Dristor
- `posthog_track.py` — librărie centrală cu funcții pentru toate evenimentele
- `server_heartbeat.py` — trimite CPU/RAM/disk/servicii la fiecare 15 min
  - raspibig: `/opt/ACTIVE/INFRA/`, cron `*/15 * * * *`
  - raspi: `/opt/`, cron `*/15 * * * *`
  - laptop: Task Scheduler `PostHog Heartbeat` la 15 min
- `service_down` alert automat când serviciu mort detectat în heartbeat
- `disk_warning` alert automat când disk > 80%
- 31 scripturi instrumentate în paralel (4 agenți):
  - 4 campaign senders: `campaign_sent`, `campaign_stopped`
  - 7 scrapers: `scraper_run` cu rows + duration
  - 9 pipeline steps (2→39): `enrichment_step_complete`, `enrichment_error`
  - 7 orders/CV/solonet: `applicant_received`, `solonet_order_placed`, `cv_generated`
- Dashboard PostHog creat: https://us.posthog.com/project/390426/dashboard/1491237
  - 13 grafice: campanii, scrapers, pipeline, server metrics, CVs, orders, revenue

### Key Files
- `D:\MEMORY\CODE\POSTHOG\posthog_track.py` — librărie tracking
- `D:\MEMORY\CODE\POSTHOG\server_heartbeat.py` — server metrics
- `D:\MEMORY\CODE\POSTHOG\create_dashboard.py` — script creare dashboard
- `D:\MEMORY\CODE\POSTHOG\.env` — `phc_nUcX...` US host

### Notes
- PostHog personal key: `phx_JRSLGRcMDfVNM7K7rqJMg4GmtDbxNx2KVn4d9TCos9JhTKRV`
- Host real: `https://us.posthog.com` (nu EU cum părea inițial)
- raspibig: `send_campaign`, `bot_watchdog`, `email_processor` DEAD — Telegram alertat

## Session 2026-04-23 — PostHog fix + Telegram alerts

### Done
- Fix key mismatch: `posthog_track.py` trimitea la EU, dashboard pe US — corectat la `phc_nUcX...` + `https://us.i.posthog.com`
- Redeploy `posthog_track.py` pe raspibig + raspi
- Verificat eventi în PostHog: 6 eventi confirmați (toate 3 servere)
- `server_heartbeat.py` rescris cu Telegram alerts direct:
  - Service down → Telegram imediat (cooldown 1h anti-spam)
  - Disk > 80% → Telegram
  - Swap > 85% → Telegram
  - CPU > 90% → Telegram
- State file `/tmp/heartbeat_state.txt` previne spam alert repetat
- Deploy pe raspibig + raspi + laptop Task Scheduler
- 2 alerte PostHog create (limita plan gratuit): Service Down + Scraper Errors
- Alerte Telegram NU se suprapun cu cele existente (daily_digest/sender_healthcheck acoperite de alert_config.py)

### Key Files
- `D:\MEMORY\CODE\POSTHOG\posthog_track.py` — key US corect
- `D:\MEMORY\CODE\POSTHOG\server_heartbeat.py` — heartbeat + Telegram alerts
- Bot token: `8628341440:AAG-dLC...` Chat ID: `547047851` (din `/opt/ACTIVE/EMAIL/.env`)

### Pending
- `send_campaign`, `bot_watchdog`, `email_processor` moarte pe raspibig — de investigat

## Session 2026-04-19 — Gmail MCP + Ideas Audit

### Done
- Auditat 106 idei Gmail (AUTOMATED+AUTOMATION) — 22 implementate identificate
- 18 thread IDs găsite, user le-a șters manual (Gmail MCP read-only la momentul respectiv)
- Gmail MCP cu write scope configurat complet:
  - Google Cloud project: `inspect-gmail-with-mcp2cli`
  - Gmail API activat
  - OAuth Desktop client creat: `67715066938-pt9lvu033prc41qtfc3u85hnq2j9p5cd.apps.googleusercontent.com`
  - OAuth JSON: `C:/Users/apami/.claude/gmail-oauth.json`
  - Credentials (refresh_token): `C:/Users/apami/.claude/gmail-credentials.json`
  - Scope: `gmail.modify` (citit + trimis + șters + arhivat)
  - MCP server `@monsoft/mcp-gmail` instalat global (npm)
  - Adăugat în `settings.json` ca `gmail` în `mcpServers` + `enabled_mcp_servers`
- mcp2cli v3.0.2 confirmat instalat (era deja)

### Pending
- **Restart Claude Code** ca gmail MCP să fie activ (settings.json modificat în sesiunea curentă)
- După restart: șterge cele 18 thread-uri rămase via `gmail_batch_move_to_trash`
- 84 emailuri Gmail rămase = reading material, de parcurs când e timp
- raspibig `~/.local/` — încă director real, nu symlink (blocat de servicii active)

### Key Files
- `C:/Users/apami/.claude/settings.json` — gmail MCP adăugat
- `C:/Users/apami/.claude/gmail-oauth.json` — OAuth client credentials
- `C:/Users/apami/.claude/gmail-credentials.json` — access + refresh token
- `D:/MEMORY/.octogent/tentacles/infra/todo.md` — thread IDs de șters listați

## Session 2026-04-19 — Gmail Ideas Audit

### Implemented ideas (TRASH these 18 Gmail threads)

Gmail MCP has read-only scope — delete manually in Gmail. Thread IDs:

| # | Subject | Thread ID |
|---|---------|-----------|
| #002 | Stop Chatting With Claude. Start Orchestrating It. | 19d7e8ed352d7cd7 |
| #003 | How to Run Claude Code Agents in Parallel | 19d7dd3f36829cbd |
| #006 | I tried Claude Dispatch | 19d7e7d66fde489a |
| #011 | second-brain-starter (coleam00) | 19d6f6ed4e923c8f |
| #012 | Waza (tw93) engineering habits as skills | 19d6f762ab26b71f |
| #013 | mini-coding-agent (rasbt) | 19d6f71bad1b9740 |
| #016 | claude-code-showcase (ChrisWiles) | 19b9e850735dfaf2 |
| #017 | ralph-playbook (ClaytonFarr) | 19bab17df3d9b11c |
| #018a | Claude Code + Ralph (ships production code) | 19bbb255de1764de |
| #018b | Ralph Wiggum, explained | 19baafa9abbfd221 |
| #020 | Understand-Anything (Lum1104) | 19d098e070f40314 |
| #021 | call-me (ZeframLou) | 19baa98861f4927f |
| #024/#100 | gentleman-guardian-angel | 19b29a9f1cfabbc4 |
| #030 | Claude Code Project Structure Best Practices | 19d09169f3bd630b |
| #041a | autoresearch (karpathy) GitHub | 19ccb30e03a643d0 |
| #041b | AutoResearch in Claude Code (Medium) | 19d14e5c2763e2ee |
| #042 | The Agent Skills Directory | 19c68e4473f207de |
| #060 | AI agents create/manage content on WordPress.com | 19d14e3b5770b709 |

### Not found in Gmail (may already be gone or different label)
- #031 Claude Code routines, #032 Reduce Token Usage, #035 slash commands, #097 insolventa ANAF, #102 GitHub 101

### Remaining 84 emails = reading material / not yet implemented — keep

## Session 2026-04-19

### Ce s-a făcut
- NVMe raspibig: 79% → 35% — mutat ~82GB pe HDD (/mnt/hdd/), toate symlinked
- Telegram spam fix — telegram-moderation dezactivat, scos din bot_watchdog.py
- cifn.info eliminat din 31 fișiere (laptop + raspibig) → cifn.eu
- Octogent instalat din sursă (pnpm), 9 tentacle active, hook SessionStart wired
- auto_tentacle.ps1 actualizat cu toate 9 tentacle + patternuri pentru ai-agents, crm, business-ops, scrapers
- Windows Task Scheduler: Heartbeat creat, EURES paths fixate, AUTOMATE-Backup cu python.exe explicit
- save_context.py + /save skill + Stop hook cu reminder creat și testat

### Fișiere cheie modificate
- `D:\MEMORY\CODE\INFRA\OCTOGENT\auto_tentacle.ps1` — 17 patternuri
- `D:\MEMORY\CODE\INFRA\OCTOGENT\save_context.py` — nou
- `C:\Users\apami\.claude\skills\save\SKILL.md` — nou
- `C:\Users\apami\.claude\skills\octogent-add-tentacle\SKILL.md` — nou
- `C:\Users\apami\.claude\settings.json` — Stop hook adăugat
- `D:\MEMORY\CODE\INFRA\WEBPAGES\wp_draft_agent.py` — cifn.info scos
- `D:\MEMORY\CODE\INFRA\WEBPAGES\generate_llm_seo.py` — cifn.info scos
- raspibig: bot_watchdog.py, brevo_cifn.py, response_tracker_inboxes.py + 28 alte fișiere

### Pending
- .local pe raspibig încă e director real (nu symlink) — serviciile active blochează rm -rf
  → de rezolvat după restart raspibig sau oprire servicii
- Octogent dashboard verificat vizual (start.bat) — nefăcut de Tudor
- WP_PASS_* env vars nesetate — wp_draft_agent.py netestat

## Session 2026-04-19 05:14
## Session 2026-04-19 — DB Enrichment + Infra Automation

### Done
- Ran DB enrichment steps 22-36 (interrupted from prev session): step25 bilant_sync ✅ (306K RO companies, 90K revenue synced), step27 followup CSV, step32 insolvency pipeline, step36 IT campaign CSV
- Added step26 standard_sector column to companies_clean (33M rows, sector mapped to 10 buckets)
- Wrote + deployed steps 47-56 (running now in background):
  - step47: size_segment (micro/small/medium/large)
  - step48: email_domain extract + duplicate penalty
  - step49: times_contacted + last_contacted_at from all send_logs
  - step50: seap_ro_crossref (winner_cui → seap_wins + lead_score boost)
  - step51: opportunity_heatmap_v2 (country × sector × response_rate)
  - step52: warm_lead_rescore (+20 for INTERESTED/REPLY, +25 for solonet)
  - step53: linkedin_url_pattern (top 10K export)
  - step54: phone_normalize to E.164 per country
  - step55: last_contact_sync (20 send_log tables)
  - step56: top500_per_country export CSV
- Built cpanel_runner.py — reusable cPanel PHP runner module + CLI
- Created cpanel-php-runner skill at ~/.claude/skills/cpanel-php-runner/
- Deployed link_inspector + link_monitor_cron to raspibig
- Added weekly cron: Mon 06:00 → link_monitor_cron.py → Telegram broken link report

### Pending
- Steps 47-56 still running (step47 UPDATE on 33M rows, ~5min each)
- step49/step55 may fail if send_log tables missing sent_at column — check output
- step51 DROP/CREATE may conflict if opportunity_heatmap table exists — add IF NOT EXISTS

### Key Files
- `D:\MEMORY\CODE\CAMPAIGNS\EMAIL PERSONAL\CODE\step47-56_*.sql`
- `D:\MEMORY\CODE\INFRA\CLAUDE\cpanel_runner.py`
- `D:\MEMORY\CODE\INFRA\CLAUDE\link_monitor_cron.py`
- `/opt/ACTIVE/INFRA/SKILLS/link_monitor_cron.py` (on raspibig)

### Next Steps
- Check steps 47-56 output when background task completes
- Fix any failed steps (likely step51 table conflict, step49 missing columns)
- Run step34_sync_raspibig.sh to push enriched DB to raspibig

## Session 2026-04-19 10:05
## Session 2026-04-19 — DB Enrichment steps 47-56 BLOCKED on PG crash

### Status
- PG18 crashed during step47 (UPDATE on 33M rows — OOM/shared memory)
- PG cannot restart: shared memory block stuck in Windows kernel
- **REQUIRES LAPTOP REBOOT** before any further DB work

### Done this session
- Wrote steps 47-56 SQL files (all in EMAIL PERSONAL/CODE/)
- Fixed step47 to use batched UPDATE by country (DO loop with COMMIT per country)
- Steps 22-36 from prev session: all done (bilant_sync 306K RO, followup CSV, insolvency pipeline, IT campaign)
- cpanel_runner.py deployed + skill created
- link_monitor_cron.py deployed to raspibig, Mon 06:00 cron added

### After reboot — run this
```
PSQL='/c/Program Files/PostgreSQL/18/bin/psql.exe -U tudor -h 127.0.0.1 -p 5433 -d interjob_master'
BASE="/d/MEMORY/CODE/CAMPAIGNS/EMAIL PERSONAL/CODE"
for step in step47 step48 step49 step50 step51 step52 step53 step54 step55 step56; do
  echo "=== $step ===" && PGPASSWORD=tudor $PSQL -f "${BASE}/${step}_*.sql" 2>&1 | tail -4
done
```

### Key insight for future large UPDATEs
- Never run single UPDATE on companies_clean (33M rows) — use batched DO loop by country
- step47 now fixed with this pattern
- steps 48, 54, 55 also touch companies_clean — same risk, but they have WHERE clauses that limit rows

### Files
- `D:\MEMORY\CODE\CAMPAIGNS\EMAIL PERSONAL\CODE\step47-56_*.sql` — all written, ready to run
- step47 already fixed (batched)

## Session 2026-04-19 11:48 — `mem` CLI built (octogent-lite)

### Done
- Inspected infra: Python 3.12.10 ✓, git clean, 28/28 octogent tentacles synced laptop↔raspibig
- Fixed 6 tentacles missing todo.md (bogdan-gavra, ebrd, ideas, jim-turnbull, personal, printing) — synced via SCP
- Verified autoheal: bot_watchdog 15min cron, NanoClaw uses Ollama qwen2.5:1.5b (fast) + qwen3:8b (smart)
- Raspibig up 8d, /opt/ACTIVE with BOGDAN/CATALOGS/AUTOMATION/ANALYTICS/AGENTS
- Designed + built **`mem`** CLI — octogent-lite for D:\MEMORY projects:
  - Single Python script (stdlib only), 279 lines, 43 tests passing
  - 8 commands: ls, show, tasks, active, search, new, audit, edit
  - Convention: `PROJECT.md` (yaml frontmatter) + `todo.md` per project
  - `mem.bat` wrapper + install at `D:\MEMORY\CODE\INFRA\MEM\`
  - Executed via 11 subagents (Tasks 1-11 DONE)
- Spec + plan at `D:\MEMORY\docs\superpowers\{specs,plans}/2026-04-19-mem-cli*`

### Pending
- **Task 12 BLOCKED on user decision**: `mem audit` found 49 candidates missing PROJECT.md
  - User said "wtf" — need clarification on which to exclude
  - Likely false positives: DATA/ARCHIVE, CAMPAIGNS/CODE (generic subdir name), CAMPAIGNS/DATA
  - Legit: BOGDAN GAVRA, ASOC PROP, HARGHITA, OCTOGENT, EURES_LAPTOP, etc.
- Wordfence install on cumparlegume.com — pending (needs cPanel API route, no A2 SSH)
- Next session: resolve audit filtering, run `mem audit --fill` on approved set, install Wordfence

### Key files
- `D:\MEMORY\CODE\INFRA\MEM\mem.py` (279 lines, new)
- `D:\MEMORY\CODE\INFRA\MEM\test_mem.py` (43 tests)
- `D:\MEMORY\CODE\INFRA\MEM\mem.bat`, `README.md`
- `D:\MEMORY\docs\superpowers\specs\2026-04-19-mem-cli-design.md`
- `D:\MEMORY\docs\superpowers\plans\2026-04-19-mem-cli.md`

### Commits (master)
- Spec + plan committed
- 11 feature commits: e0fde460 (scaffold) → 70f0e586 (dispatcher)
- All 43 tests green, mem.py under 300-line cap

## Session 2026-04-21 06:21
test

## Session 2026-04-24 13:35
Session 2026-04-24 — GSD workflow + repo research\n\nDone:\n- Fetched KDNuggets article: 10 GitHub repos to master Claude Code\n- Deep-dived repos 1-4: everything-claude-code, system-prompts, gstack, get-shit-done\n- Mapped each repo to InterJob stack with concrete apply instructions\n- Added GSD Development Workflow rule to D:\MEMORY\CLAUDE.md\n- Added GSD Development Workflow rule to D:\MEMORY\CODE\CLAUDE.md\n\nKey files changed:\n- D:\MEMORY\CLAUDE.md — GSD section added before Response Style\n- D:\MEMORY\CODE\CLAUDE.md — GSD section added before File Size Rule\n\nGSD rule: Discuss→Plan→Execute→Verify→Ship, .planning/ per project, atomic commit per task.\n\nPending:\n- Repos 5-10 not reviewed\n- PreToolUse hook blocking DROP TABLE on interjob_master — not built\n- Subagents: brevo-sender, cpanel-deployer, pg-enricher — not built\n\nNext steps:\n- Implement PreToolUse safety hook for interjob_master\n- Build specialized subagents from repo 9 pattern\n- Start DB pipeline steps 22-46 with .planning/ structure

## Session 2026-04-24 14:33
Session 2026-04-24 — Subagents + CLAUDE.md upgrades\n\nDone:\n- Researched repos 6,9,10: awesome-claude-code-subagents, claude-code-templates, claude-code-system-prompts\n- Added to both CLAUDE.md (root + CODE): Safety Hooks, Subagents table+YAML, .planning/ convention, GSD workflow, PostgreSQL MCP\n- Fixed duplicates: .planning/ refs, GSD section, AGROEVOLUTION location synced\n- Created 5 subagent files in D:\MEMORY\.claude\agents\:\n  brevo-sender.md (Sonnet), cpanel-deployer.md (Haiku), pg-enricher.md (Sonnet), madr-scraper.md (Haiku), cso-reviewer.md (Opus)\n\nKey files changed:\n- D:\MEMORY\CLAUDE.md\n- D:\MEMORY\CODE\CLAUDE.md\n- D:\MEMORY\.claude\agents\brevo-sender.md (NEW)\n- D:\MEMORY\.claude\agents\cpanel-deployer.md (NEW)\n- D:\MEMORY\.claude\agents\pg-enricher.md (NEW)\n- D:\MEMORY\.claude\agents\madr-scraper.md (NEW)\n- D:\MEMORY\.claude\agents\cso-reviewer.md (NEW)\n\nPending:\n- Repos 5,7,8 not reviewed (awesome-claude-code, claude-code-templates hooks, best-practice)\n- PostgreSQL MCP not installed yet (just documented)\n- PreToolUse hook for DROP TABLE not implemented in settings.json (just documented)\n- .planning/ folders not created yet for active projects\n\nNext steps:\n- Install PostgreSQL MCP in .claude/settings.json\n- Implement PreToolUse safety hook in settings.json\n- Create .planning/ for EMAIL PERSONAL pipeline steps 22-46

## Session 2026-04-25 02:26
Session 2026-04-24/25 — Safety hook + PostgreSQL MCP + .planning/ folders\n\nDone:\n- Created safety_hook.py at CODE/INFRA/SECURITY/safety_hook.py\n  Blocks: DROP TABLE, TRUNCATE, DELETE without WHERE, DROP DATABASE, rm -rf on DATA//opt/ACTIVE/, git push --force\n  Tested: all 4 danger patterns block correctly\n- Added PreToolUse hook (Bash matcher) to ~/.claude/settings.json\n- Added PostgreSQL MCP server to ~/.claude/settings.json (postgresql, port 5433, interjob_master)\n- Created .planning/ folders for 3 active projects:\n  CODE/CAMPAIGNS/EMAIL PERSONAL/.planning/ — pipeline steps 22-46\n  CODE/CAMPAIGNS/HARGHITA/.planning/ — 3-phase campaign\n  BUSINESS/AGROEVOLUTION.COM/.planning/ — county pages + MADR\n  Each has PROJECT.md + STATE.md\n\nKey files changed:\n- C:\Users\apami\.claude\settings.json — PreToolUse hook + postgresql MCP added\n- CODE/INFRA/SECURITY/safety_hook.py (NEW)\n- 6 .planning/ files (NEW)\n\nPending:\n- safety hook + postgresql MCP active only after session restart or /hooks reload\n- Repos 5, 7, 8 not yet reviewed (awesome-claude-code, claude-code-templates hooks, best-practice)\n- Pipeline steps 22-46 not yet started (STATE.md created)\n\nNext steps:\n- Restart Claude to activate hook + MCP\n- Verify postgresql MCP connects: check /hooks or test query\n- Resume DB pipeline from step 22
