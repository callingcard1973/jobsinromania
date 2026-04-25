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

## Next action after current queries complete
1. Verify step 26 standard_sector populated (SELECT COUNT(*) WHERE standard_sector IS NOT NULL)
2. Verify step 25 revenue updated
3. Run step 27 (followup_scheduler) — check send_log tables have followup_at column first
4. Run steps 31, 32, 35, 36 in sequence
5. Update this file after each step
