-- Step 36: IT/tech sector campaign builder
-- Target: software companies, IT consultancies, tech firms across EU
-- High salary = higher placement fee

-- IT companies with email by country
SELECT country,
  COUNT(*) AS it_companies,
  COUNT(COALESCE(email,enriched_email)) FILTER (
    WHERE COALESCE(email,'')!='' OR COALESCE(enriched_email,'')!=''
  ) AS contactable,
  ROUND(AVG(lead_score)) AS avg_score
FROM companies_clean
WHERE LOWER(COALESCE(sector_name,'')) ~ '(software|it |tech|digital|program|datap|informatica|telecom)'
  AND (is_insolvent IS NULL OR is_insolvent=false)
GROUP BY country ORDER BY contactable DESC LIMIT 15;

-- Export IT campaign CSV
COPY (
  SELECT name,
    COALESCE(NULLIF(email,''), enriched_email) AS email,
    phone, city, country, sector_name,
    employees_count, revenue, ted_wins, lead_score, website
  FROM companies_clean
  WHERE LOWER(COALESCE(sector_name,'')) ~ '(software|it |tech|digital|program|datap|informatica|telecom)'
    AND (email IS NOT NULL AND email!='' OR enriched_email IS NOT NULL AND enriched_email!='')
    AND (is_insolvent IS NULL OR is_insolvent=false)
    AND country IN ('NO','SE','DK','FI','PL','RO','DE','FR')
  ORDER BY lead_score DESC NULLS LAST
  LIMIT 10000
) TO 'D:/MEMORY/EMAIL PERSONAL/campaign_IT_europe_10000.csv' CSV HEADER;

SELECT 'IT campaign exported' AS status;
