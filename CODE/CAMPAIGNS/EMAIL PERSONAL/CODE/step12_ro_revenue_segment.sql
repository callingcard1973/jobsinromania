-- Step 12: RO revenue segmentation from bilant_years
-- Find companies with growing cifra_afaceri 3 consecutive years → premium leads
-- Boost lead_score for growing companies

-- Companies with 3yr consecutive growth
WITH growth AS (
  SELECT
    b1.cui,
    b1.cifra_afaceri AS y1,
    b2.cifra_afaceri AS y2,
    b3.cifra_afaceri AS y3,
    ROUND((b3.cifra_afaceri - b1.cifra_afaceri) * 100.0 / NULLIF(b1.cifra_afaceri, 0), 1) AS growth_pct
  FROM bilant_years b1
  JOIN bilant_years b2 ON b1.cui = b2.cui AND b2.year = b1.year + 1
  JOIN bilant_years b3 ON b1.cui = b3.cui AND b3.year = b1.year + 2
  WHERE b1.year = (SELECT MAX(year)-2 FROM bilant_years)
    AND b2.cifra_afaceri > b1.cifra_afaceri
    AND b3.cifra_afaceri > b2.cifra_afaceri
    AND b1.cifra_afaceri > 0
)
UPDATE companies_clean cc
SET lead_score = LEAST(100, COALESCE(cc.lead_score, 0) +
  CASE
    WHEN g.growth_pct >= 50 THEN 20
    WHEN g.growth_pct >= 20 THEN 15
    WHEN g.growth_pct >= 10 THEN 10
    ELSE 5
  END
)
FROM growth g
WHERE cc.cui = g.cui AND cc.country = 'RO';

-- Top growing RO companies with contact
SELECT cc.name, cc.city, cc.sector_name, cc.employees_count,
  b.cifra_afaceri AS latest_revenue, cc.lead_score,
  COALESCE(NULLIF(cc.email,''), cc.enriched_email) AS email
FROM companies_clean cc
JOIN bilant_years b ON cc.cui = b.cui AND b.year = (SELECT MAX(year) FROM bilant_years)
WHERE cc.country='RO'
  AND cc.lead_score >= 50
  AND (cc.email IS NOT NULL AND cc.email != '' OR cc.enriched_email IS NOT NULL AND cc.enriched_email != '')
  AND (cc.is_insolvent IS NULL OR cc.is_insolvent=false)
ORDER BY cc.lead_score DESC, b.cifra_afaceri DESC
LIMIT 20;
