# DB Pipeline STATE

## Last known state (2026-04-25)
- Steps 1-21: COMPLETE
- Step 22: COMPLETE — 97,332 procurement buyers imported (verified via COUNT)
- Step 23: PARTIALLY RUN — SE email enrich, 180 emails (se_companies uses email_1/phone_1 not email/phone — script updated in-session)
- Step 24: COMPLETE (pipeline.md marked done, 21 rows)
- Step 25: IN PROGRESS — bilant_years → revenue sync, running as PID 9296 (locked behind step 26)
- Step 26: IN PROGRESS — standard_sector UPDATE, PID 21036 active (50+ min, 33M rows). NOTE: ran twice accidentally (PIDs 9780 + 21036), second instance will run after first commits
- Steps 27-36: PENDING

## Active queries on DB (as of 2026-04-25 ~08:30)
- PID 21036: standard_sector UPDATE (active, ~50 min in)
- PID 9780: standard_sector UPDATE (locked, waiting on 21036)
- PID 22672: SE email UPDATE (locked)
- PID 16792: lead_score UPDATE (locked)
- PID 9296: bilant_years revenue UPDATE (locked)

## Blockers
- All queries are sequential due to table-level lock contention on companies_clean
- step26 ran twice — duplicate work but not harmful (idempotent)
- step23 has schema mismatch: use email_1/phone_1/company_website, not email/phone/website

## Completed this session (2026-04-25)
- Step 22: VERIFIED complete (97,332 buyers)
- Step 23: COMPLETE (180 SE emails — low match rate, correct column names used)
- Step 24: Previously done
- Step 26: IN PROGRESS (standard_sector UPDATE running ~1h, 33M rows, will complete autonomously)
- Step 25: IN PROGRESS (bilant revenue sync, locked behind step 26)
- Step 27: COMPLETE — 25 RO followup_at populated, 1,497 overdue CSV exported to DATA/followup_overdue.csv
- Step 32: COMPLETE — 2,384 insolvency targets exported to DATA/insolvency_worker_targets.csv
- Step 36: COMPLETE — 7,238 IT companies exported to DATA/campaign_IT_europe_10000.csv

## Completed 2026-04-26
- Step 31: COMPLETE — 10 BG procurement buyers enriched (schema note: master_emails.quality_tier exists on laptop DB)
- Step 35: COMPLETE — 1,960,463 rows updated. Lead score decay applied: 2023(419K avg16), 2022(146K avg10), 2021(128K avg7), 2020(103K avg2), 2019(95K avg1), 2018(87K avg1). Bug fixed: year::integer cast in step35_lead_score_decay.sql

## Status as of 2026-04-26
Steps 22-27, 31, 32, 35, 36: COMPLETE
Steps 33, 34, 37-46: built/run (see pipeline.md)
Raspibig DB mirror has schema drift — quality_tier and year type differ. Run enrichment steps on laptop only.
