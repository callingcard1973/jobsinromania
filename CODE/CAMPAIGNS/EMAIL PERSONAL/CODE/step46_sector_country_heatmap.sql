-- Step 46: Sector x Country heatmap
-- Shows WHERE to focus next campaign: most contactable high-score companies
-- Score = contactable * avg_lead_score (opportunity mass)

COPY (
SELECT
  COALESCE(standard_sector, 'unknown') AS sector,
  country,
  COUNT(*) AS total_companies,
  COUNT(*) FILTER (
    WHERE COALESCE(email,'') != '' OR COALESCE(enriched_email,'') != ''
  ) AS contactable,
  ROUND(AVG(lead_score)) AS avg_score,
  COUNT(*) FILTER (WHERE lead_score >= 60) AS tier_a,
  COUNT(*) FILTER (WHERE lead_score >= 40 AND lead_score < 60) AS tier_b,
  COUNT(*) FILTER (WHERE ted_wins > 0) AS has_ted_wins,
  -- opportunity mass: contactable companies weighted by avg score
  ROUND(
    COUNT(*) FILTER (
      WHERE COALESCE(email,'') != '' OR COALESCE(enriched_email,'') != ''
    ) * AVG(lead_score) / 100.0
  ) AS opportunity_score
FROM companies_clean
WHERE (is_insolvent IS NULL OR is_insolvent = false)
  AND (is_agency IS NULL OR is_agency = false)
  AND country IN ('NO','SE','DK','FI','PL','RO','DE','FR','BG','CZ','HU','AT','NL','BE','IT')
GROUP BY standard_sector, country
HAVING COUNT(*) FILTER (
  WHERE COALESCE(email,'') != '' OR COALESCE(enriched_email,'') != ''
) >= 10
ORDER BY opportunity_score DESC NULLS LAST
LIMIT 100
) TO 'D:/MEMORY/EMAIL PERSONAL/DATA/heatmap_sector_country.csv' CSV HEADER;

-- Print top 30 to screen
SELECT
  COALESCE(standard_sector, 'unknown') AS sector,
  country,
  COUNT(*) FILTER (
    WHERE COALESCE(email,'') != '' OR COALESCE(enriched_email,'') != ''
  ) AS contactable,
  ROUND(AVG(lead_score)) AS avg_score,
  ROUND(
    COUNT(*) FILTER (
      WHERE COALESCE(email,'') != '' OR COALESCE(enriched_email,'') != ''
    ) * AVG(lead_score) / 100.0
  ) AS opportunity_score
FROM companies_clean
WHERE (is_insolvent IS NULL OR is_insolvent = false)
  AND (is_agency IS NULL OR is_agency = false)
  AND country IN ('NO','SE','DK','FI','PL','RO','DE','FR','BG','CZ','HU','AT','NL','BE','IT')
GROUP BY standard_sector, country
HAVING COUNT(*) FILTER (
  WHERE COALESCE(email,'') != '' OR COALESCE(enriched_email,'') != ''
) >= 10
ORDER BY opportunity_score DESC NULLS LAST
LIMIT 30;
