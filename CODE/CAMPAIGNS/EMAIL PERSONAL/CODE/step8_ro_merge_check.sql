-- Step 8: Merge missing emails from master_romania_companies → companies_clean
-- master_romania_companies has 10M rows, 148K emails vs 25K in companies_clean RO

-- How many RO companies in master_ro have email but companies_clean doesn't?
SELECT COUNT(*) AS enrichable
FROM master_romania_companies mrc
JOIN companies_clean cc ON cc.cui = mrc.cui AND cc.country = 'RO'
WHERE (mrc.email IS NOT NULL AND mrc.email != '')
  AND (cc.email IS NULL OR cc.email = '')
  AND (cc.enriched_email IS NULL OR cc.enriched_email = '');

-- Apply enrichment
UPDATE companies_clean cc
SET enriched_email = mrc.email
FROM master_romania_companies mrc
WHERE cc.cui = mrc.cui
  AND cc.country = 'RO'
  AND (mrc.email IS NOT NULL AND mrc.email != '')
  AND (cc.email IS NULL OR cc.email = '')
  AND (cc.enriched_email IS NULL OR cc.enriched_email = '');

-- Also sync phone where missing
UPDATE companies_clean cc
SET phone = mrc.phone
FROM master_romania_companies mrc
WHERE cc.cui = mrc.cui
  AND cc.country = 'RO'
  AND (mrc.phone IS NOT NULL AND mrc.phone != '')
  AND (cc.phone IS NULL OR cc.phone = '');

-- How many RO companies in master_ro not yet in companies_clean? (just report)
SELECT COUNT(*) AS ro_only_in_master
FROM master_romania_companies mrc
WHERE NOT EXISTS (
  SELECT 1 FROM companies_clean cc WHERE cc.cui = mrc.cui AND cc.country = 'RO'
)
AND (mrc.email IS NOT NULL AND mrc.email != '');

-- Final RO coverage
SELECT
  COUNT(*) total,
  COUNT(email) FILTER (WHERE email IS NOT NULL AND email!='') as direct_email,
  COUNT(enriched_email) FILTER (WHERE enriched_email IS NOT NULL AND enriched_email!='') as enriched_email,
  COUNT(phone) FILTER (WHERE phone IS NOT NULL AND phone!='') as with_phone
FROM companies_clean WHERE country='RO';
