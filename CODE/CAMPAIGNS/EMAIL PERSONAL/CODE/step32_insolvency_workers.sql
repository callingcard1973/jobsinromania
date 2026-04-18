-- Step 32: Insolvency company_email → worker outreach pipeline
-- Closing companies = workers need jobs NOW. Pitch: "we place your workers."

-- Quality check
SELECT status, COUNT(*) FROM insolvency
WHERE company_email IS NOT NULL AND company_email!=''
GROUP BY status ORDER BY COUNT(*) DESC LIMIT 10;

-- Export: closing companies with email, not in DNC
COPY (
  SELECT
    i.company_name AS name,
    i.company_email AS email,
    i.company_phone AS phone,
    i.sector,
    i.status,
    i.date_filed,
    CURRENT_DATE - i.date_filed AS days_in_insolvency,
    i.liquidator_email
  FROM insolvency i
  WHERE i.company_email IS NOT NULL AND i.company_email!=''
    AND i.company_email NOT IN (SELECT email FROM dnc_list)
    AND i.status IS NOT NULL
  ORDER BY i.date_filed DESC NULLS LAST
  LIMIT 5000
) TO 'D:/MEMORY/EMAIL PERSONAL/insolvency_worker_targets.csv' CSV HEADER;

SELECT 'Exported insolvency worker pipeline' AS status;
