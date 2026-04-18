This is to register to guru.com and similar freelancing platforms to make money.

## Status (2026-04-03) — EU FUNDING v3 COMPLETE, CRONS CLEAN

## Platform Status

| Platform | Username | Status |
|----------|----------|--------|
| Upwork | ~017ae142d0861d8813 | COMPLETE |
| Guru.com | callingcard | COMPLETE (6 services) |
| Freelancer.com | @tudortel | COMPLETE (15 skills) |
| Fiverr | coderpro2030 | Bio + 11 skills Pro |
| PeoplePerHour | Tudor Tel | Application pending |
| Contra | - | 6 products to create |

## EU Funding Scraper v3 (2026-04-03)

### DB Stats
- beneficiari_privati: 22,482 (17,111 SMIS, 4,617 contractors, 100% email)
- proiecte: 15,959 (9,087 axa, 8,378 proceduri, 100% email)
- anofm.jobs: 125,909
- Bidirectional: 2,757+ contacts pushed to romania DB

### Architecture
- `parsers.py` (247 lines) + `beneficiar_fonduri_ue_scraper.py` (246 lines)
- Smart skip: only scrapes incomplete records
- Parallel: anunturi + proiecte with own semaphores
- Spec extraction split: scrape fast, fill-specs slow

### Cron (clean, all verified)
```
04:30  verify + clean
05:00  fill_axa (JOIN smis)
09:00  scrape --both (open only)
09:15  anofm_db --latest
10:00  fill-specs (nice 19)
10:30  enrich contractors (bidirectional)
16:00  scrape --both
16:15  anofm_db --latest
17:00  fill-specs
17:30  enrich contractors
Sun 01:00  fix-desc
```

### Node-RED: 2 tabs (World Crawler Master, EU Funding Pipeline)

### Skills on raspibig
- beneficiar_fonduri_ue_scraper.py, parsers.py — main scraper
- eu_funding_verify_clean.py — ASCII, emails, phones cleanup
- fill_axa.py — propagate axa from proiecte to anunturi via SMIS
- enrich_contractors.py — bidirectional enrichment (25K company lookup)
- open_projects_report.py — projects with open procurement (5K projects, 13.5K anunturi)
- open_anunturi_by_project.py — all open anunturi grouped by project (CSV + JSON)
- anofm_db_skill.py — ANOFM DB import
- enrich_external_specs.py — Google Drive/Dropbox specs
- supabase_push.py — push data to Supabase for web display

### Output Files
- `/opt/ACTIVE/EU_FUNDING/DATA/BENEFICIAR_FONDURI_UE/OPENPROJECTS/`
  - open_projects.csv — 5,033 projects with open procurement
  - open_projects.json — same with stats
  - open_anunturi_full.csv — 13,570 open anunturi with project info
  - open_anunturi_grouped.json — grouped by project, with stats by type/program/judet
- `/opt/ACTIVE/EU_FUNDING/DATA/anunturi_export.csv` — 22,575 all anunturi
- `/opt/ACTIVE/EU_FUNDING/DATA/proiecte_export.csv` — 15,959 all proiecte

### Website Spec
- `Desktop/FREELANCE/WEBSITE_SPEC_CIFN_EU.txt` — full brief for developer
- `eu_funding_display/` — HTML + config.json + supabase_push.py (backed up everywhere)

## Minipc (192.168.100.33)
- WOL: `wakeonlan ec:b1:d7:6a:6f:cd`
- Ollama qwen2.5:14b at :11434
