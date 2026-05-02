# DB Pipeline STATE

## Last known state (2026-05-03)
- Steps 1-36: COMPLETE (all prior work per previous sessions)
- Step 38: COMPLETE — 42,864 agencies flagged (33,407 name + 9,437 sector). Column already existed.
- Step 39: COMPLETE — Template routing CSV exported to DATA/template_routing.csv (13 routes). All templates are on raspibig, not laptop — all show MISSING locally, expected.
- Step 40: COMPLETE — 128,748 contact_first_name values extracted from firstname.lastname@ patterns.
- Step 41: COMPLETE — v_campaign_roi view created. 71 response records. solonet_orders lacks revenue_eur column (schema drift, non-fatal).
- Step 42: COMPLETE — 20,000 phone call list exported to DATA/phone_call_list_20k.csv. NO: 403K, RO: 207K, BG: 20K contactable by phone.
- Step 33: COMPLETE — Daily report HTML generated: daily_report_2026-05-03.html. MX valid: 482K, warm leads: 16, top: NO 305K contactable.
- Step 34: NOT RUN — raspibig sync; infrastructure step requiring SSH/SCP, skip for laptop-only pipeline.
- Step 44: IN PROGRESS — GDPR basis UPDATE running (PID 18440, ~33M rows). 97,795 rows done (legitimate_interest + pattern_enriched). Large UPDATE unknown still active.
- Step 46: PENDING (depends on step 44 completing)

## Completed this session (2026-05-03)
- DB started: PostgreSQL 18 on D:\DATABASES\pgdata18, port 5433 (had stale postmaster.pid after crash)
- Step 33: HTML daily report generated
- Step 38: Re-run, agency flagging complete (42,864 total)
- Step 39: Template routing CSV generated
- Step 40: 128,748 contact_first_name values extracted
- Step 41: v_campaign_roi view created
- Step 42: phone_call_list_20k.csv exported (20,000 rows)
- Step 44: Running (GDPR basis column ADD + updates — estimated 60+ min total)

## Blockers
- Step 44 large UPDATE (33M rows, ~30min remaining)
- Step 46 (heatmap) must wait for step 44 to complete

## DB state
- companies_clean: 33,604,439 rows
- master_emails: 1,032,944 rows  
- ted_awards: 6,198,063 rows
- Step 38 is_agency: 42,864 flagged
- Step 40 contact_first_name: 128,748 populated
- Step 44 gdpr_basis: 97,795 so far (UPDATE unknown pending)

## Infrastructure note
- PostgreSQL 18 data dir: D:\DATABASES\pgdata18 (NOT C:\Program Files\PostgreSQL\18\data)
- Windows service points to wrong dir — must start manually: pg_ctl start -D D:\DATABASES\pgdata18
- Port: 5433 (not 5432 which is the default service instance)
