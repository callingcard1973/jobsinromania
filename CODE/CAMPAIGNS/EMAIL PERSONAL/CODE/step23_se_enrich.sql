-- Step 23: SE email enrichment from se_companies table

SELECT column_name FROM information_schema.columns
WHERE table_name='se_companies' ORDER BY ordinal_position LIMIT 15;

-- Check se_companies email coverage
SELECT COUNT(*) total,
  COUNT(email) FILTER (WHERE email IS NOT NULL AND email!='') with_email
FROM se_companies;

-- Sync emails to companies_clean SE
UPDATE companies_clean cc
SET
  email = COALESCE(NULLIF(cc.email,''), sc.email),
  phone = COALESCE(NULLIF(cc.phone,''), sc.phone),
  website = COALESCE(NULLIF(cc.website,''), sc.website)
FROM se_companies sc
WHERE (LOWER(TRIM(cc.name)) = LOWER(TRIM(sc.company_name))
    OR cc.cui = sc.company_org_number)
  AND cc.country = 'SE'
  AND sc.email IS NOT NULL AND sc.email != ''
  AND (cc.email IS NULL OR cc.email = '');

SELECT COUNT(*) total,
  COUNT(email) FILTER (WHERE email IS NOT NULL AND email!='') with_email
FROM companies_clean WHERE country='SE';
