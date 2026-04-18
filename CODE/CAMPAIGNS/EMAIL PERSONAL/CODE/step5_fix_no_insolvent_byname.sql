-- Step 5b: Fix is_insolvent for NO companies — match by normalized name
-- CUI not populated for NO in companies_clean, so use name match

UPDATE companies_clean cc
SET is_insolvent = true
FROM no_companies_full nf
WHERE LOWER(TRIM(cc.name)) = LOWER(TRIM(nf.navn))
  AND cc.country = 'NO'
  AND (nf.konkurs = 'J' OR nf.underavvikling = 'J')
  AND (cc.is_insolvent IS NULL OR cc.is_insolvent = false);

SELECT
  COUNT(*) FILTER (WHERE is_insolvent=true) AS insolvent,
  COUNT(*) AS total,
  ROUND(COUNT(*) FILTER (WHERE is_insolvent=true) * 100.0 / COUNT(*), 1) AS pct
FROM companies_clean WHERE country='NO';
