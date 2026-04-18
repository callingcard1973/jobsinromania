-- Step 22: Import 97K procurement buyers into companies_clean

CREATE TEMP TABLE procurement_import (
  country text, name text, city text, address text,
  contracts_bought integer, last_active_year integer
);

COPY procurement_import FROM 'D:/MEMORY/EMAIL PERSONAL/procurement_buyers_new.csv' CSV HEADER;

-- Generate IDs from current max
DO $$
DECLARE max_id INTEGER;
BEGIN
  SELECT COALESCE(MAX(id),0) INTO max_id FROM companies_clean;
  INSERT INTO companies_clean (id, name, country, city, address, source, lead_score, is_insolvent, is_agency)
  SELECT
    (max_id + ROW_NUMBER() OVER (ORDER BY pi.contracts_bought DESC))::integer,
    pi.name, pi.country, pi.city, pi.address,
    'ted_procurement_buyers',
    CASE WHEN pi.contracts_bought >= 100 THEN 60
         WHEN pi.contracts_bought >= 20  THEN 45
         WHEN pi.contracts_bought >= 5   THEN 30
         ELSE 20 END,
    false, false
  FROM procurement_import pi
  WHERE NOT EXISTS (
    SELECT 1 FROM companies_clean cc
    WHERE LOWER(TRIM(cc.name)) = LOWER(TRIM(pi.name))
      AND TRIM(cc.country) = pi.country
  );
END $$;

DROP TABLE procurement_import;

SELECT source, COUNT(*) FROM companies_clean WHERE source='ted_procurement_buyers' GROUP BY source;
SELECT country, COUNT(*) FROM companies_clean WHERE source='ted_procurement_buyers' GROUP BY country ORDER BY COUNT(*) DESC LIMIT 10;
