-- Step 38: Detect and flag staffing/recruitment agencies in companies_clean
-- Agencies = competitors for employer campaigns, targets for partner pitch

ALTER TABLE companies_clean ADD COLUMN IF NOT EXISTS is_agency boolean DEFAULT false;

-- Flag by name keywords (multilingual)
UPDATE companies_clean
SET is_agency = true
WHERE is_agency = false
  AND LOWER(name) ~ '(recruit|staffing|manpower|interim|work\s*force|placement|headhunt|personal\s*verm|tijdelijk|uitzend|arbeitsverm|interimat|detasare|agentie\s*munc|agentia\s*de\s*munc|agence\s*emploi|emploi\s*temp|vikar|bemanning|bemannings|vikariat|henkilost|rekrytoint|personalverm|job\s*agenc|employment\s*agenc|labour\s*supp|labour\s*hire|hr\s*consul|human\s*resource|personnel\s*consul)';

-- Flag by sector
UPDATE companies_clean
SET is_agency = true
WHERE is_agency = false
  AND LOWER(COALESCE(sector_name,'')) ~ '(temp\s*agenc|staffing|recruitment|human\s*resource|personal\s*vermittlung|uitzendbureau|agence\s*emploi)';

SELECT
  is_agency,
  COUNT(*) AS companies,
  COUNT(COALESCE(email, enriched_email)) FILTER (
    WHERE COALESCE(email,'') != '' OR COALESCE(enriched_email,'') != ''
  ) AS contactable
FROM companies_clean
GROUP BY is_agency;

-- Top agency countries
SELECT country, COUNT(*) AS agencies
FROM companies_clean
WHERE is_agency = true
GROUP BY country ORDER BY agencies DESC LIMIT 10;
