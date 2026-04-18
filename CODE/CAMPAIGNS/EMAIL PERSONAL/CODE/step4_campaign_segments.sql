-- Step 4: Extract campaign-ready segments from companies_clean
-- Uses direct email + enriched_email, tier-1 MX-valid from master_emails
-- Outputs CSV-ready views per country

-- Create reusable view: all contactable companies
CREATE OR REPLACE VIEW v_campaign_ready AS
SELECT
  cc.id,
  cc.name,
  cc.country,
  cc.city,
  cc.sector,
  cc.sector_name,
  cc.employees_count,
  cc.revenue,
  cc.phone,
  COALESCE(cc.enriched_email, cc.email) AS best_email,
  CASE
    WHEN me.quality_tier = 1 THEN 'tier1'
    WHEN me.quality_tier = 2 THEN 'tier2'
    WHEN cc.email IS NOT NULL AND cc.email != '' THEN 'direct'
    ELSE 'unknown'
  END AS email_source,
  cc.ted_wins,
  cc.is_insolvent,
  cc.lead_score
FROM companies_clean cc
LEFT JOIN master_emails me
  ON LOWER(me.email) = LOWER(COALESCE(cc.enriched_email, cc.email))
WHERE
  (cc.email IS NOT NULL AND cc.email != '')
  OR (cc.enriched_email IS NOT NULL AND cc.enriched_email != '')
  AND (cc.is_insolvent IS NULL OR cc.is_insolvent = false);

-- Segment counts
SELECT
  country,
  email_source,
  COUNT(*) AS companies,
  COUNT(phone) FILTER (WHERE phone IS NOT NULL AND phone != '') AS with_phone
FROM v_campaign_ready
WHERE country IN ('NO','RO','PL','FR','DE','BG','UA','CZ','GB')
GROUP BY country, email_source
ORDER BY country, email_source;

-- Top sectors per country (NO)
SELECT sector_name, COUNT(*) AS companies
FROM v_campaign_ready
WHERE country='NO' AND sector_name IS NOT NULL
GROUP BY sector_name ORDER BY companies DESC LIMIT 15;

-- Top sectors per country (RO)
SELECT sector_name, COUNT(*) AS companies
FROM v_campaign_ready
WHERE country='RO' AND sector_name IS NOT NULL
GROUP BY sector_name ORDER BY companies DESC LIMIT 15;

-- Export example (run separately with \copy for CSV):
-- \copy (SELECT name, best_email, phone, city, sector_name FROM v_campaign_ready WHERE country='NO' AND email_source='tier1' ORDER BY lead_score DESC NULLS LAST LIMIT 5000) TO 'NO_tier1_campaign.csv' CSV HEADER;
-- \copy (SELECT name, best_email, phone, city, sector_name FROM v_campaign_ready WHERE country='RO' ORDER BY lead_score DESC NULLS LAST LIMIT 5000) TO 'RO_campaign.csv' CSV HEADER;
-- \copy (SELECT name, best_email, phone, city, sector_name FROM v_campaign_ready WHERE country='PL' ORDER BY lead_score DESC NULLS LAST LIMIT 5000) TO 'PL_campaign.csv' CSV HEADER;
