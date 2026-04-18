-- Step 26: Sector normalization → 10 standard buckets
-- Maps Norwegian/Romanian/Polish/etc sector names to standard_sector column

ALTER TABLE companies_clean ADD COLUMN IF NOT EXISTS standard_sector TEXT;

UPDATE companies_clean SET standard_sector =
  CASE
    WHEN LOWER(COALESCE(sector_name,'')) ~ '(construct|bygg|oppf|civil|roads|build|lucrari|constructii|instalat)' THEN 'construction'
    WHEN LOWER(COALESCE(sector_name,'')) ~ '(transport|logistic|freight|spediti|courier|delivery|kurier|frakt|spedit)' THEN 'transport'
    WHEN LOWER(COALESCE(sector_name,'')) ~ '(manufactur|fabrica|produc|industrial|usine|fabricat|prelucrare|metalurg|prelucrari)' THEN 'manufacturing'
    WHEN LOWER(COALESCE(sector_name,'')) ~ '(agri|farm|food|vegetab|fruit|legum|lapte|carne|apicol|cereale|zooteh|horticultura)' THEN 'agriculture'
    WHEN LOWER(COALESCE(sector_name,'')) ~ '(hotel|restaurant|horeca|cater|food service|ospitalitate|turism|pensiune|cafe)' THEN 'hospitality'
    WHEN LOWER(COALESCE(sector_name,'')) ~ '(health|care|medical|nursing|hospital|spital|sanatate|clinic|farma|stomatolog)' THEN 'healthcare'
    WHEN LOWER(COALESCE(sector_name,'')) ~ '(software|it |tech|digital|program|datap|informatica|telecom|telecomunic)' THEN 'it'
    WHEN LOWER(COALESCE(sector_name,'')) ~ '(retail|comer|wholesale|handel|magazin|vanzare|supermarkt|detailh)' THEN 'retail'
    WHEN LOWER(COALESCE(sector_name,'')) ~ '(clean|facility|janitor|menaj|curatenie|reinigung|entretien|service cladiri)' THEN 'facility'
    WHEN LOWER(COALESCE(sector_name,'')) ~ '(electric|install|plumb|hvac|mechanical|sanitare|termice|electrice)' THEN 'trades'
    ELSE 'other'
  END
WHERE sector_name IS NOT NULL;

-- Distribution
SELECT standard_sector, COUNT(*) AS companies,
  COUNT(COALESCE(email,enriched_email)) FILTER (WHERE COALESCE(email,'')!='' OR COALESCE(enriched_email,'')!='') AS contactable
FROM companies_clean
WHERE standard_sector IS NOT NULL
GROUP BY standard_sector ORDER BY companies DESC;
