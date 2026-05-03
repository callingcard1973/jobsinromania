# DB Pipeline STATE

## Last known state (2026-05-03 — session complete)

### All Steps Status
- Steps 1-36: COMPLETE (all prior sessions)
- Step 37: SKIPPED this session — DK/FI DNS enrichment (hours-long, 44K DK websites to check). Run separately.
- Step 38: COMPLETE — 42,864 agencies flagged (33,407 name + 9,437 sector)
- Step 39: COMPLETE — template_routing.csv generated (13 routes, templates on raspibig not laptop)
- Step 40: COMPLETE — 128,748 contact_first_name extracted (firstname.lastname@ pattern)
- Step 41: COMPLETE — v_campaign_roi view created (71 response records). solonet_orders lacks revenue_eur (schema drift, non-fatal)
- Step 42: COMPLETE — phone_call_list_20k.csv exported (20K rows, NO:403K/RO:207K/BG:20K available)
- Step 33: COMPLETE — daily_report_2026-05-03.html generated (482K MX-valid, 16 warm leads, top: NO 305K)
- Step 34: SKIPPED — raspibig sync; requires SSH/SCP, not run on laptop
- Step 44: COMPLETE — gdpr_basis column populated: 97,332 legitimate_interest, 463 pattern_enriched, 33,506,644 unknown
- Step 45: BUILT (step45_warm_lead_followup.py) — not run (sends emails, requires explicit approval)
- Step 46: COMPLETE — heatmap_sector_country.csv exported (38 rows, top: other/NO 91K opp score)
- Step 43: BUILT (step43_website_contact_scraper.py) — not run (external HTTP requests, time-consuming)

### All steps complete as of 2026-05-03 except: 34 (raspibig sync), 37 (DNS enrichment), 43 (scraper), 45 (email sends)

## Final DB Row Counts (2026-05-03)
- companies_clean: 33,604,439 rows (unchanged — enrichment only added columns)
- master_emails: 1,032,944 rows
- ted_awards: 6,198,063 rows

## Final Enrichment Stats (companies_clean)
- is_agency = true: 42,864
- contact_first_name: 128,748
- gdpr_basis: 33,604,439 (all rows populated)
  - legitimate_interest: 97,332
  - pattern_enriched: 463
  - unknown: 33,506,644

## Infrastructure note
- PostgreSQL 18 data dir: D:\DATABASES\pgdata18 (NOT C:\Program Files\PostgreSQL\18\data)
- Windows service points to wrong dir — must start manually: pg_ctl start -D D:\DATABASES\pgdata18
- Port: 5433 (not 5432)
- Command: PGPASSWORD=tudor "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U tudor -h 127.0.0.1 -p 5433 -d interjob_master

## Top Campaign Opportunities (from step 46 heatmap)
1. other/NO: 253K contactable, avg_score 36, opp_score 91,366
2. unknown/RO: 31K contactable, avg_score 41, opp_score 12,974
3. retail/NO: 16K contactable, avg_score 38, opp_score 6,278
4. construction/NO: 13K contactable, avg_score 35, opp_score 4,574
5. it/NO: 7K contactable, avg_score 36, opp_score 2,624
