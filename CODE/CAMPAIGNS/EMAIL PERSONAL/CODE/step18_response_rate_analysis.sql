-- Step 18: Response rate analysis across all campaigns
-- Find best-performing sectors, countries, templates

-- Aggregate all send logs into unified view
CREATE TEMP TABLE all_sends AS
SELECT email, company, campaign, 'NO' AS country, sent_at FROM norway_send_log WHERE status='sent'
UNION ALL SELECT email, company, campaign, 'RO', sent_at FROM romania_send_log WHERE status='sent'
UNION ALL SELECT email, company, campaign, 'DK', sent_at FROM denmark_send_log WHERE status='sent'
UNION ALL SELECT email, company, campaign, 'BG', sent_at FROM bg_send_log WHERE status='sent'
UNION ALL SELECT email, company, campaign, 'BE', sent_at FROM be_send_log WHERE status='sent'
UNION ALL SELECT email, company, campaign, 'NO', sent_at FROM no_send_log WHERE status='sent';

-- Response rate by campaign
SELECT
  s.campaign,
  s.country,
  COUNT(DISTINCT s.email) AS sent,
  COUNT(DISTINCT cr.sender_email) AS responses,
  ROUND(COUNT(DISTINCT cr.sender_email) * 100.0 / NULLIF(COUNT(DISTINCT s.email),0), 2) AS response_rate_pct
FROM all_sends s
LEFT JOIN campaign_responses cr ON LOWER(cr.sender_email) = LOWER(s.email)
GROUP BY s.campaign, s.country
HAVING COUNT(DISTINCT s.email) > 10
ORDER BY response_rate_pct DESC NULLS LAST;

-- Best responding companies (multi-campaign)
SELECT
  cr.sender_email,
  cr.campaign,
  cr.category,
  cc.name, cc.country, cc.sector_name, cc.employees_count, cc.lead_score
FROM campaign_responses cr
LEFT JOIN companies_clean cc ON LOWER(COALESCE(cc.email,cc.enriched_email)) = LOWER(cr.sender_email)
WHERE cr.category NOT IN ('BOUNCE','AUTO_REPLY','UNKNOWN')
ORDER BY cr.created_at DESC
LIMIT 50;

DROP TABLE all_sends;
