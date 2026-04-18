-- Step 10: Lead scoring system
-- Score = email_quality(0-40) + ted_wins(0-20) + employees(0-20) + revenue(0-10) + not_insolvent(10)

UPDATE companies_clean SET lead_score = (
  -- Email quality (max 40)
  CASE
    WHEN (email IS NOT NULL AND email != '') OR (enriched_email IS NOT NULL AND enriched_email != '') THEN
      CASE
        WHEN EXISTS (
          SELECT 1 FROM master_emails me
          WHERE LOWER(me.email) = LOWER(COALESCE(enriched_email, email))
          AND me.quality_tier = 1
        ) THEN 40
        WHEN EXISTS (
          SELECT 1 FROM master_emails me
          WHERE LOWER(me.email) = LOWER(COALESCE(enriched_email, email))
          AND me.quality_tier = 2
        ) THEN 25
        ELSE 15
      END
    ELSE 0
  END
  +
  -- TED wins (max 20)
  CASE
    WHEN COALESCE(ted_wins,0) >= 10 THEN 20
    WHEN COALESCE(ted_wins,0) >= 5  THEN 15
    WHEN COALESCE(ted_wins,0) >= 1  THEN 10
    ELSE 0
  END
  +
  -- Employees (max 20)
  CASE
    WHEN COALESCE(employees_count,0) >= 250 THEN 20
    WHEN COALESCE(employees_count,0) >= 50  THEN 15
    WHEN COALESCE(employees_count,0) >= 10  THEN 10
    WHEN COALESCE(employees_count,0) >= 1   THEN 5
    ELSE 0
  END
  +
  -- Revenue (max 10)
  CASE
    WHEN COALESCE(revenue,0) >= 10000000 THEN 10
    WHEN COALESCE(revenue,0) >= 1000000  THEN 7
    WHEN COALESCE(revenue,0) >= 100000   THEN 4
    ELSE 0
  END
  +
  -- Not insolvent (10)
  CASE WHEN COALESCE(is_insolvent, false) = false THEN 10 ELSE 0 END
);

-- Distribution
SELECT
  CASE
    WHEN lead_score >= 60 THEN 'A (60+)'
    WHEN lead_score >= 40 THEN 'B (40-59)'
    WHEN lead_score >= 20 THEN 'C (20-39)'
    ELSE 'D (<20)'
  END AS tier,
  COUNT(*) AS companies,
  COUNT(COALESCE(email,enriched_email)) FILTER (WHERE COALESCE(email,'') != '' OR COALESCE(enriched_email,'') != '') AS contactable
FROM companies_clean
GROUP BY 1 ORDER BY 1;
