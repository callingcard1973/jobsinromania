-- Step 11: Phone campaign exports
-- NO, RO, PL — name + phone + sector, sorted by lead_score

-- NO phone list (top 10K by score)
\copy (
  SELECT name, phone, city, sector_name, employees_count, lead_score
  FROM companies_clean
  WHERE country='NO'
    AND phone IS NOT NULL AND phone != ''
    AND (is_insolvent IS NULL OR is_insolvent=false)
  ORDER BY lead_score DESC NULLS LAST
  LIMIT 10000
) TO 'D:/MEMORY/EMAIL PERSONAL/phone_NO_top10k.csv' CSV HEADER;

-- RO phone list
\copy (
  SELECT name, phone, city, sector_name, employees_count, lead_score
  FROM companies_clean
  WHERE country='RO'
    AND phone IS NOT NULL AND phone != ''
    AND (is_insolvent IS NULL OR is_insolvent=false)
  ORDER BY lead_score DESC NULLS LAST
  LIMIT 10000
) TO 'D:/MEMORY/EMAIL PERSONAL/phone_RO_top10k.csv' CSV HEADER;

-- PL phone list
\copy (
  SELECT name, phone, city, sector_name, employees_count, lead_score
  FROM companies_clean
  WHERE country='PL'
    AND phone IS NOT NULL AND phone != ''
    AND (is_insolvent IS NULL OR is_insolvent=false)
  ORDER BY lead_score DESC NULLS LAST
) TO 'D:/MEMORY/EMAIL PERSONAL/phone_PL_all.csv' CSV HEADER;

-- BG phone list
\copy (
  SELECT name, phone, city, sector_name, employees_count, lead_score
  FROM companies_clean
  WHERE country='BG'
    AND phone IS NOT NULL AND phone != ''
    AND (is_insolvent IS NULL OR is_insolvent=false)
  ORDER BY lead_score DESC NULLS LAST
  LIMIT 10000
) TO 'D:/MEMORY/EMAIL PERSONAL/phone_BG_top10k.csv' CSV HEADER;

-- Summary counts
SELECT country, COUNT(*) as phone_contacts
FROM companies_clean
WHERE phone IS NOT NULL AND phone != ''
  AND (is_insolvent IS NULL OR is_insolvent=false)
  AND country IN ('NO','RO','PL','BG')
GROUP BY country ORDER BY phone_contacts DESC;
