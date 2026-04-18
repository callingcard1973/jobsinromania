-- Step 28: Data freshness audit
-- Find tables with stale data (no updates in 30+ days)

SELECT
  schemaname,
  relname AS table_name,
  n_live_tup AS row_count,
  last_autoanalyze::date AS last_analyzed,
  last_autovacuum::date AS last_vacuumed,
  CURRENT_DATE - last_autoanalyze::date AS days_since_analyze
FROM pg_stat_user_tables
WHERE schemaname = 'public'
  AND n_live_tup > 1000
ORDER BY days_since_analyze DESC NULLS FIRST
LIMIT 30;

-- Tables with most recent data by created_at/updated_at
SELECT 'companies_clean' AS tbl, MAX(updated_at)::date AS last_update, COUNT(*) rows FROM companies_clean
UNION ALL SELECT 'master_emails', MAX(first_seen)::date, COUNT(*) FROM master_emails
UNION ALL SELECT 'norway_send_log', MAX(sent_at)::date, COUNT(*) FROM norway_send_log
UNION ALL SELECT 'romania_send_log', MAX(sent_at)::date, COUNT(*) FROM romania_send_log
UNION ALL SELECT 'campaign_responses', MAX(created_at)::date, COUNT(*) FROM campaign_responses
UNION ALL SELECT 'insolvency', MAX(created_at)::date, COUNT(*) FROM insolvency
UNION ALL SELECT 'bilant_years', MAX(year::text)::date, COUNT(*) FROM bilant_years
ORDER BY last_update ASC NULLS FIRST;
