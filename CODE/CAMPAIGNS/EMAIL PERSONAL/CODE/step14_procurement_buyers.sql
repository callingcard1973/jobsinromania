-- Step 14: Procurement buyer targeting from ted_awards
-- These are orgs that BUY labor/services — best recruitment prospects

-- Top buyers by country with contact count
SELECT
  iso_country_code AS country,
  cae_name AS buyer,
  cae_town AS city,
  COUNT(*) AS contracts_bought,
  MAX(year) AS last_active
FROM ted_awards
WHERE cae_name IS NOT NULL AND cae_name != ''
GROUP BY iso_country_code, cae_name, cae_town
HAVING COUNT(*) >= 3
ORDER BY contracts_bought DESC
LIMIT 50;

-- Export buyers not already in companies_clean as enrichment targets
\copy (
  SELECT DISTINCT
    ta.iso_country_code AS country,
    ta.cae_name AS name,
    ta.cae_town AS city,
    ta.cae_address AS address,
    COUNT(*) AS contracts_bought,
    MAX(ta.year) AS last_active_year
  FROM ted_awards ta
  WHERE ta.cae_name IS NOT NULL
    AND ta.iso_country_code IN ('NO','RO','PL','BG','DE','FR','GB','FI','DK','SE')
    AND NOT EXISTS (
      SELECT 1 FROM companies_clean cc
      WHERE LOWER(TRIM(cc.name)) = LOWER(TRIM(ta.cae_name))
      AND TRIM(cc.country) = ta.iso_country_code
    )
  GROUP BY ta.iso_country_code, ta.cae_name, ta.cae_town, ta.cae_address
  HAVING COUNT(*) >= 2
  ORDER BY contracts_bought DESC
) TO 'D:/MEMORY/EMAIL PERSONAL/procurement_buyers_new.csv' CSV HEADER;

SELECT 'Exported procurement buyers not in companies_clean' AS status;
