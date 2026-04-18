-- Step 24: Warm leads follow-up list
-- INTERESTED responses with days since reply, not yet followed up

COPY (
  SELECT
    cr.sender_email AS email,
    cr.campaign,
    cr.created_at AS responded_at,
    CURRENT_DATE - cr.created_at::date AS days_since_response,
    cr.category,
    cc.name AS company_name,
    cc.country,
    cc.city,
    cc.sector_name,
    cc.phone,
    cc.employees_count,
    cc.lead_score
  FROM campaign_responses cr
  LEFT JOIN companies_clean cc
    ON LOWER(COALESCE(cc.email,'')) = LOWER(cr.sender_email)
    OR LOWER(COALESCE(cc.enriched_email,'')) = LOWER(cr.sender_email)
  WHERE cr.category IN ('INTERESTED','REPLY')
    AND cr.sender_email NOT IN (SELECT LOWER(email) FROM dnc_list)
  ORDER BY days_since_response ASC
) TO 'D:/MEMORY/EMAIL PERSONAL/warm_leads_followup.csv' CSV HEADER;

-- Summary
SELECT category, COUNT(*) as count,
  ROUND(AVG(CURRENT_DATE - created_at::date)) as avg_days_old
FROM campaign_responses
WHERE category IN ('INTERESTED','REPLY','NOT_INTERESTED')
GROUP BY category ORDER BY count DESC;
