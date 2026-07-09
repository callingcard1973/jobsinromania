# Todo — eures-scraper

## Immediate
- [ ] Re-add cron 03:00 UTC (was disabled — confirm with Tudor before enabling)
- [ ] Verify resume logic working: check last job ID in eures_jobs
- [ ] Check worker count: never exceed 2 concurrent on raspibig

## Pipeline
- [ ] Validate dedup: eures_employers count vs last run (should be 2,404+)
- [ ] Sector classification: confirm SQL classifier running post-scrape
- [ ] Pipe new employers → Brevo campaign segment

## Monitor
- [ ] Log: /opt/ACTIVE/EURES/eures.log — tail for errors after each run
- [ ] If scraper blocked: rotate user-agent, add delay, report to Tudor

## After Each Run
Report: jobs added, employers deduped, errors, duration.
Stop on any error. Wait for instruction.

---
## Session Handoff 2026-04-19

### Done this session
- Octogent installed globally (already was, Node 24 + pnpm 10)
- Workspace created: D:\MEMORY\CODE\octogent-workspace (git init)
- 3 tentacles created: eures-scraper, tiktok-videos, db-enrichment
- All CONTEXT.md + todo.md files written and copied to workspace
- EURES blocat investigat: 4 procese active (3 scrapers + 1 cpulimit), 5 PID files orfane
- PIDs: eures_de_1, eures_de,at,ch..._1, eures_es,it,..._1, eures_no,dk,..._1, eures_no,dk,se,fi_1

### Status
- EURES scraper: 3 instanțe rulează simultan (peste limita 2) — Tudor a zis că alt terminal a rezolvat
- Octogent UI: localhost:8787 LIVE
- tiktok-videos tentacle: creat, 70 videos în queue, 79 rows tiktok_posts

### Next Steps
- [ ] Verifică că scraperele sunt max 2 după rezolvarea din celălalt terminal
- [ ] Re-add cron 03:00 UTC după confirmare Tudor
- [ ] Deschide tiktok-videos tentacle în Octogent → generează batch nou
- [ ] Creează 14 canale TikTok @jobs.romania.{lang}
