# pipeline.md — DB Enrichment Pipeline (steps 1-46)

**Location**: `D:\MEMORY\CODE\CAMPAIGNS\EMAIL PERSONAL\CODE\`
**DB**: interjob_master PostgreSQL 18, port 5433, user tudor/tudor

## Steps Status

| Step | File | What | Status |
|------|------|------|--------|
| 1 | step1_db_filter.sql | Email quality tiers 1-4, DNC crossref | ✅ Done |
| 2 | step2_mx_check.py | Async MX validation 802K emails | ✅ Done |
| 3 | step3_link_emails_companies.sql | Domain match emails→companies_clean | ✅ Done |
| 4 | step4_campaign_segments.sql | v_campaign_ready view | ✅ Done |
| 5 | step5_fix_insolvent.sql | Cross-ref insolvency by CUI | ✅ Done |
| 6 | step6_no_enrich.sql | NO companies sync from no_companies_full | ✅ Done |
| 7 | step7_ted_crossref.sql | TED winners → ted_wins column | ✅ Done |
| 9 | step9_import_ro_missing.sql | +134K RO companies imported | ✅ Done |
| 10 | step10_lead_scoring.sql | Lead score formula (max 100) | ✅ Done |
| 11 | step11_phone_campaigns.sql | Phone CSVs: NO/RO/PL/BG | ✅ Done |
| 12 | step12_ro_revenue_segment.sql | 3yr revenue growth boost | ✅ Done |
| 13 | step13_fr_pattern_enrich.py | FR info@domain.fr pattern enrichment | ✅ Done |
| 14 | step14_procurement_buyers.sql | 97K EU buyers exported | ✅ Done |
| 17 | step17_liquidator_contacts.sql | 500 liquidators CSV | ✅ Done |
| 20 | step20_worker_employer_match.py | SQLite master_applicants.db matching | ✅ Done |
| 22 | step22_import_procurement_buyers.sql | Import 97K buyers into companies_clean | ⏳ Interrupted |
| 23 | step23_se_enrich.sql | SE email sync from se_companies | ⏳ Pending |
| 24 | step24_warm_leads.sql | Export INTERESTED/REPLY to CSV | ✅ Done (21 rows) |
| 25 | step25_bilant_sync.sql | bilant_years → companies_clean revenue | ⏳ Pending |
| 26 | step26_sector_normalize.sql | standard_sector column (10 buckets) | ⏳ Pending |
| 27 | step27_followup_scheduler.sql | followup_at = sent_at+7d | ⏳ Pending |
| 29 | step29_campaign_builder_v2.py | Cross-country --standard-sector builder | ✅ Built |
| 30 | step30_template_selector.py | Auto-select template per sector | ✅ Built |
| 31 | step31_buyer_enrich.sql | Enrich procurement buyers via domain | ⏳ Pending |
| 32 | step32_insolvency_workers.sql | 11,950 insolvency emails → CSV | ⏳ Pending |
| 33 | step33_daily_report.py | HTML + Telegram 07:00 digest | ✅ Built |
| 34 | step34_sync_raspibig.sh | pg_dump + SCP + restore | ✅ Built, not run |
| 35 | step35_lead_score_decay.sql | last_ted_year decay scoring | ⏳ Pending |
| 36 | step36_it_campaign.sql | 10K IT/tech EU campaign CSV | ⏳ Pending |
| 37 | step37_dk_fi_email_pattern.py | DK/FI pattern emails from website | ✅ Built |
| 38 | step38_agency_flag.sql | Flag staffing agencies | ✅ Run |
| 39 | step39_template_router.py | Template routing table | ✅ Built |
| 40 | step40_contact_name_extract.sql | First name from email | ✅ Run |
| 41 | step41_campaign_roi.sql | Campaign ROI view | ✅ Run |
| 42 | step42_phone_call_list.sql | 20K phone call list CSV | ✅ Run |
| 43 | step43_website_contact_scraper.py | Scrape /contact pages for emails | ✅ Built |
| 44 | step44_gdpr_tracker.sql | GDPR basis column | ✅ Run |
| 45 | step45_warm_lead_followup.py | Auto-send 7-day followups | ✅ Built |
| 46 | step46_sector_country_heatmap.sql | Opportunity heatmap → CSV | ✅ Run |

## Key DB Facts

- `companies_clean`: 33M rows, no auto-increment (use MAX(id)+ROW_NUMBER())
- `master_emails`: 1,032,944 rows, quality_tier 1-4
- `ted_awards`: 3.4GB, buyer=cae_name, winner=win_name
- `no_companies_full`: 94 cols, konkurs field for NO insolvency
- Always use `COALESCE(email, enriched_email)` for email lookups
- Campaign CSV output: `D:\MEMORY\CODE\CAMPAIGNS\EMAIL PERSONAL\DATA\`

## Resume Pending Steps

```bash
BASE="/d/MEMORY/CODE/CAMPAIGNS/EMAIL PERSONAL/CODE"
PSQL='"/c/Program Files/PostgreSQL/18/bin/psql.exe" -U tudor -h 127.0.0.1 -p 5433 -d interjob_master'
for step in step22_import_procurement_buyers step23_se_enrich step25_bilant_sync step26_sector_normalize step27_followup_scheduler step31_buyer_enrich step32_insolvency_workers step35_lead_score_decay step36_it_campaign; do
  echo "=$step="
  PGPASSWORD=tudor eval "$PSQL -f '${BASE}/${step}.sql'" 2>&1 | tail -5
done
```

## Enrichment Rules

- Min 8 char normalized name for cross-ref guards
- COUNT before UPDATE, CUI > name match priority
- No placeholders, sequential UPDATEs
- Always check redirect before marking email invalid
