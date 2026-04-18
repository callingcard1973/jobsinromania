-- Step 42: Phone campaign call list builder
-- Sorted by lead_score, includes call script snippet per sector

COPY (
  SELECT
    cc.name,
    cc.phone,
    cc.city,
    cc.country,
    cc.standard_sector AS sector,
    cc.employees_count,
    cc.lead_score,
    cc.ted_wins,
    cc.website,
    CASE cc.standard_sector
      WHEN 'construction'   THEN 'We place carpenters, electricians, welders for construction projects'
      WHEN 'manufacturing'  THEN 'We supply factory workers, machine operators, production staff'
      WHEN 'transport'      THEN 'We place truck drivers, warehouse staff, logistics workers'
      WHEN 'hospitality'    THEN 'We place cooks, waiters, hotel staff, housekeeping'
      WHEN 'healthcare'     THEN 'We place nurses, care assistants, medical support staff'
      WHEN 'agriculture'    THEN 'We place seasonal farm workers, harvest teams'
      WHEN 'it'             THEN 'We place software developers, IT support, system admins'
      ELSE 'We place qualified workers across multiple sectors'
    END AS call_script_hint
  FROM companies_clean cc
  WHERE cc.phone IS NOT NULL AND cc.phone != ''
    AND (cc.is_insolvent IS NULL OR cc.is_insolvent = false)
    AND (cc.is_agency IS NULL OR cc.is_agency = false)
    AND cc.country IN ('NO','RO','PL','BG','DK','SE','FI','DE')
  ORDER BY cc.lead_score DESC NULLS LAST, cc.ted_wins DESC NULLS LAST
  LIMIT 20000
) TO 'D:/MEMORY/EMAIL PERSONAL/DATA/phone_call_list_20k.csv' CSV HEADER;

-- Summary by country
SELECT country, COUNT(*) AS companies
FROM companies_clean
WHERE phone IS NOT NULL AND phone != ''
  AND (is_insolvent IS NULL OR is_insolvent = false)
  AND country IN ('NO','RO','PL','BG','DK','SE','FI','DE')
GROUP BY country ORDER BY companies DESC;

SELECT 'Phone call list exported' AS status;
