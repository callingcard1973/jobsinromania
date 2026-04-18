-- Step 31: Enrich procurement buyers via domain/name matching
-- 97K buyers imported with no email — match via master_emails domain

-- Match by website domain (buyers may have websites scraped elsewhere)
UPDATE companies_clean cc
SET enriched_email = me.email
FROM master_emails me
WHERE cc.source = 'ted_procurement_buyers'
  AND (cc.enriched_email IS NULL OR cc.enriched_email='')
  AND me.quality_tier IN (1,2)
  AND me.domain = REGEXP_REPLACE(
    REGEXP_REPLACE(LOWER(cc.website), '^https?://(www\.)?',''),'/.*$','')
  AND cc.website IS NOT NULL AND cc.website != '';

-- Match by normalized name similarity to master_emails company field
UPDATE companies_clean cc
SET enriched_email = me.email
FROM master_emails me
WHERE cc.source = 'ted_procurement_buyers'
  AND (cc.enriched_email IS NULL OR cc.enriched_email='')
  AND me.quality_tier = 1
  AND me.company IS NOT NULL
  AND LOWER(REGEXP_REPLACE(cc.name,'[^a-zA-Z0-9]','','g'))
    = LOWER(REGEXP_REPLACE(me.company,'[^a-zA-Z0-9]','','g'))
  AND LENGTH(cc.name) > 5;

-- Results
SELECT
  COUNT(*) total_buyers,
  COUNT(enriched_email) FILTER (WHERE enriched_email IS NOT NULL AND enriched_email!='') enriched,
  COUNT(email) FILTER (WHERE email IS NOT NULL AND email!='') direct_email
FROM companies_clean WHERE source='ted_procurement_buyers';

-- Top enriched buyers
SELECT name, country, enriched_email, lead_score
FROM companies_clean
WHERE source='ted_procurement_buyers'
  AND enriched_email IS NOT NULL AND enriched_email!=''
ORDER BY lead_score DESC LIMIT 10;
