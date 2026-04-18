-- Step 5: Fix is_insolvent on companies_clean
-- RO: match by CUI against insolvency table
-- NO: match by org number against no_companies_full where konkurs='J'

-- RO: mark insolvent by CUI
UPDATE companies_clean cc
SET is_insolvent = true
FROM insolvency i
WHERE cc.cui = i.cui
  AND cc.country = 'RO'
  AND (cc.is_insolvent IS NULL OR cc.is_insolvent = false);

-- NO: mark bankrupt companies
UPDATE companies_clean cc
SET is_insolvent = true
FROM no_companies_full nf
WHERE cc.cui = nf.organisasjonsnummer
  AND cc.country = 'NO'
  AND nf.konkurs = 'J'
  AND (cc.is_insolvent IS NULL OR cc.is_insolvent = false);

-- Also mark under liquidation (NO)
UPDATE companies_clean cc
SET is_insolvent = true
FROM no_companies_full nf
WHERE cc.cui = nf.organisasjonsnummer
  AND cc.country = 'NO'
  AND nf.underavvikling = 'J'
  AND (cc.is_insolvent IS NULL OR cc.is_insolvent = false);

-- Report
SELECT country,
  COUNT(*) FILTER (WHERE is_insolvent=true) AS insolvent,
  COUNT(*) AS total,
  ROUND(COUNT(*) FILTER (WHERE is_insolvent=true) * 100.0 / COUNT(*), 1) AS pct
FROM companies_clean
WHERE country IN ('RO','NO')
GROUP BY country;
