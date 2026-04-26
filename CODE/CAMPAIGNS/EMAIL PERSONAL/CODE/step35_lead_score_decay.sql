-- Step 35: Lead score decay for stale procurement buyers
-- Companies last active in TED 2020 shouldn't score same as 2023

-- Add last_ted_year column if not exists
ALTER TABLE companies_clean ADD COLUMN IF NOT EXISTS last_ted_year INTEGER;

-- Populate from ted_awards
UPDATE companies_clean cc
SET last_ted_year = sub.last_year
FROM (
  SELECT
    LOWER(REGEXP_REPLACE(win_name,'[^a-zA-Z0-9]','','g')) AS name_key,
    win_country_code AS country,
    MAX(year::integer) AS last_year
  FROM ted_awards
  WHERE win_name IS NOT NULL AND win_name != ''
  GROUP BY name_key, country
) sub
WHERE LOWER(REGEXP_REPLACE(cc.name,'[^a-zA-Z0-9]','','g')) = sub.name_key
  AND TRIM(cc.country) = sub.country;

-- Also from procurement buyers
UPDATE companies_clean cc
SET last_ted_year = sub.last_year
FROM (
  SELECT
    LOWER(REGEXP_REPLACE(cae_name,'[^a-zA-Z0-9]','','g')) AS name_key,
    iso_country_code AS country,
    MAX(year::integer) AS last_year
  FROM ted_awards
  WHERE cae_name IS NOT NULL
  GROUP BY name_key, country
) sub
WHERE LOWER(REGEXP_REPLACE(cc.name,'[^a-zA-Z0-9]','','g')) = sub.name_key
  AND TRIM(cc.country) = sub.country
  AND (cc.last_ted_year IS NULL OR sub.last_year > cc.last_ted_year);

-- Apply decay: older = lower score
UPDATE companies_clean
SET lead_score = GREATEST(0, lead_score +
  CASE
    WHEN last_ted_year >= 2023 THEN 5   -- boost recent
    WHEN last_ted_year = 2022  THEN 0
    WHEN last_ted_year = 2021  THEN -5
    WHEN last_ted_year = 2020  THEN -10
    WHEN last_ted_year <= 2019 THEN -15
    ELSE 0
  END
)
WHERE last_ted_year IS NOT NULL;

SELECT last_ted_year, COUNT(*), ROUND(AVG(lead_score)) avg_score
FROM companies_clean
WHERE last_ted_year IS NOT NULL
GROUP BY last_ted_year ORDER BY last_ted_year DESC;
