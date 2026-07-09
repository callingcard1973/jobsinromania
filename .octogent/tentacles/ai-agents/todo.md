# Todo

## Consolidate LLM client config into shared module
Every script in `CODE/INFRA/AUTOMATE/skills/` that calls LM Studio duplicates the OpenAI client init (`base_url="http://localhost:1234/v1", api_key="lm-studio"`). Extract to a single `llm_client.py` in `AUTOMATE/skills/` that other scripts can import. Update 5-6 affected files (bounce_analyzer_llm.py, campaign_llm_manager.py, cv_scanner.py, etc.).

## Build CV generator API health check + restart watchdog
FastAPI CV generator runs on raspibig at :5050. No watchdog exists. Build a lightweight check script that pings `:5050/health`, restarts the service if down, and sends Telegram alert only on restart failure. Deploy as cron `*/5 * * * *` on raspibig.

## Wire SEAP enrichment output → leads pipeline
`enrich_seap_winners.py` classifies SEAP procurement winners by sector via LLM but the downstream insert into `leads` table is incomplete. Finish the insert path: deduplicate by email against existing leads + dnc_list, set `source='seap'`, `campaign='procurement'`, `status='new'`.

## Add Qwen3-8B batch processing mode to llm_cli.py
`llm_cli.py` is single-prompt interactive. Add a `--batch FILE` flag that reads lines from a file, runs each through Qwen3-8B with the tuned params (temp=0.6, top_k=20, repeat_penalty=1.1), and writes results to `FILE.out`. Useful for bulk classification tasks.

## TikTok jobs pipeline: auto-post scheduler
Memory notes 70 videos queued in `tiktok_posts` (79 rows, 14 langs). Build or complete the scheduler that reads unposted rows, posts via TikTok API or manual queue, marks `posted_at`. Clarify with Tudor whether auto-post or manual-approve flow is wanted before implementing.

---
## Session Handoff 2026-04-19 — Octogent Setup Complete

### Done
- Explained Octogent (public repo vs custom local system)
- Discovered real system: `D:\MEMORY\CODE\INFRA\OCTOGENT\` + `D:\MEMORY\.octogent\tentacles\`
- Created 10 new tentacles: eures-scraper, tiktok-videos, db-enrichment, personal, ideas, bogdan-gavra, jim-turnbull, ebrd, catalog, printing
- Total: 22 tentacles, all with CONTEXT.md
- Rewrote `auto_tentacle.ps1` — 70+ patterns covering every dir/subdir in D:\MEMORY\
- User added 3 more tentacles: security, telegestiune, web
- Verified: 22/22 CONTEXT.md present, all pattern tests pass
- EURES scraper: found 3 instances running simultaneously (over 2-worker limit), user resolved in other terminal

### Key Files Changed
- `D:\MEMORY\CODE\INFRA\OCTOGENT\auto_tentacle.ps1` — full rewrite, 70+ patterns
- `D:\MEMORY\.octogent\tentacles\*/CONTEXT.md` — 10 new files created

### Next Steps
- [ ] Open tiktok-videos tentacle → generate next video batch
- [ ] Open eures-scraper tentacle → verify max 2 workers, re-add cron 03:00 UTC
- [ ] Create 14 TikTok channels @jobs.romania.{lang}
- [ ] Test auto_tentacle.ps1 by opening Claude from each major dir
