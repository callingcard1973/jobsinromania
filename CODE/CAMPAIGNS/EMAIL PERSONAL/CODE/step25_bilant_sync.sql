-- Step 25: Sync bilant_years latest financials → companies_clean

UPDATE companies_clean cc
SET
  revenue = b.cifra_afaceri,
  employees_count = COALESCE(cc.employees_count, b.nr_angajati)
FROM bilant_years b
WHERE cc.cui = b.cui
  AND cc.country = 'RO'
  AND b.year = (SELECT MAX(year) FROM bilant_years)
  AND b.cifra_afaceri > 0
  AND (cc.revenue IS NULL OR cc.revenue = 0 OR b.cifra_afaceri > cc.revenue);

-- Re-score RO after revenue update
UPDATE companies_clean SET lead_score = LEAST(100,
  COALESCE(lead_score,0) +
  CASE WHEN revenue >= 10000000 THEN 5
       WHEN revenue >= 1000000  THEN 3
       WHEN revenue >= 100000   THEN 1
       ELSE 0 END
)
WHERE country='RO' AND revenue > 0;

-- Report
SELECT
  COUNT(*) total,
  COUNT(revenue) FILTER (WHERE revenue > 0) with_revenue,
  COUNT(employees_count) FILTER (WHERE employees_count > 0) with_employees,
  ROUND(AVG(lead_score)) avg_score
FROM companies_clean WHERE country='RO';
