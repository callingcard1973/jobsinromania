-- Step 17: Liquidator contacts campaign list
-- Pitch: "your clients' workers need new jobs — we place them"
-- High niche, zero competition, liquidators manage 1M+ RO insolvencies

-- Quality check
SELECT
  COUNT(*) total,
  COUNT(liquidator_email) FILTER (WHERE liquidator_email IS NOT NULL AND liquidator_email!='') with_email,
  COUNT(liquidator_phone) FILTER (WHERE liquidator_phone IS NOT NULL AND liquidator_phone!='') with_phone,
  COUNT(DISTINCT liquidator_email) FILTER (WHERE liquidator_email IS NOT NULL AND liquidator_email!='') unique_emails
FROM insolvency;

-- Top liquidators by caseload
SELECT
  liquidator_name,
  liquidator_email,
  liquidator_phone,
  COUNT(*) AS cases,
  MAX(date_filed) AS latest_case
FROM insolvency
WHERE liquidator_email IS NOT NULL AND liquidator_email != ''
  AND liquidator_email NOT IN (SELECT email FROM dnc_list)
GROUP BY liquidator_name, liquidator_email, liquidator_phone
ORDER BY cases DESC
LIMIT 20;

-- Export top 500 liquidators by caseload
\copy (
  SELECT
    liquidator_name AS name,
    liquidator_email AS email,
    liquidator_phone AS phone,
    COUNT(*) AS cases_managed,
    MAX(date_filed) AS latest_case,
    COUNT(DISTINCT sector) AS sectors
  FROM insolvency
  WHERE liquidator_email IS NOT NULL AND liquidator_email != ''
    AND liquidator_name IS NOT NULL AND liquidator_name != ''
    AND liquidator_email NOT IN (SELECT email FROM dnc_list)
  GROUP BY liquidator_name, liquidator_email, liquidator_phone
  ORDER BY cases_managed DESC
  LIMIT 500
) TO 'D:/MEMORY/EMAIL PERSONAL/liquidator_contacts.csv' CSV HEADER;
