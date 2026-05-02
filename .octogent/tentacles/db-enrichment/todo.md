# Todo — db-enrichment

## Pending Steps (run in order)

- [ ] step22_import_procurement_buyers.sql — import 97K EU buyers into companies_clean (INTERRUPTED, check last inserted id first)
- [ ] step23_se_enrich.sql — SE email sync from se_companies table
- [ ] step25_bilant_sync.sql — bilant_years → companies_clean revenue columns
- [ ] step26_sector_normalize.sql — standard_sector column, 10 buckets
- [ ] step27_followup_scheduler.sql — followup_at = sent_at + 7 days
- [ ] step31_buyer_enrich.sql — enrich procurement buyers via domain match
- [ ] step32_insolvency_workers.sql — export 11,950 insolvency emails → CSV
- [ ] step35_lead_score_decay.sql — last_ted_year decay scoring
- [ ] step36_it_campaign.sql — 10K IT/tech EU campaign CSV

## After Each Step
- Report: rows affected, errors, duration
- Update this file: [ ] → [x]
- If error: paste last 5 lines, stop, wait for instruction

## Built but Not Run
- step34_sync_raspibig.sh — pg_dump + SCP + restore (run manually, ask Tudor first)

## Done (reference)
Steps 1-21, 24, 29-30, 33, 37-46 — all complete ✅
