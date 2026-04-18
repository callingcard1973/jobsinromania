-- Step 7: Cross-ref TED winners → companies_clean
-- Increments ted_wins counter on companies that won EU contracts
-- Match by normalized name + country

-- Reset then recount ted_wins
UPDATE companies_clean SET ted_wins = 0 WHERE ted_wins IS NULL;

-- Match winners to companies by normalized name + country
WITH ted_counts AS (
  SELECT
    LOWER(REGEXP_REPLACE(win_name, '[^a-zA-Z0-9]', '', 'g')) AS name_key,
    win_country_code AS country,
    COUNT(*) AS wins
  FROM ted_awards
  WHERE win_name IS NOT NULL AND win_name != ''
    AND win_country_code IS NOT NULL
  GROUP BY name_key, country
)
UPDATE companies_clean cc
SET ted_wins = COALESCE(cc.ted_wins, 0) + tc.wins
FROM ted_counts tc
WHERE LOWER(REGEXP_REPLACE(cc.name, '[^a-zA-Z0-9]', '', 'g')) = tc.name_key
  AND TRIM(cc.country) = tc.country;

-- Report top TED winners now linked
SELECT name, country, ted_wins, email, sector_name
FROM companies_clean
WHERE ted_wins > 0
ORDER BY ted_wins DESC
LIMIT 20;

-- Summary
SELECT country, COUNT(*) as companies_with_ted, SUM(ted_wins) as total_wins
FROM companies_clean
WHERE ted_wins > 0
GROUP BY country ORDER BY total_wins DESC LIMIT 10;
