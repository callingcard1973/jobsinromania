-- Step 44: GDPR consent tracking
-- Basis: TED/ANOFM public data = legitimate interest (B2B)
-- DE/FR/IT require stricter handling

ALTER TABLE companies_clean ADD COLUMN IF NOT EXISTS gdpr_basis text;
ALTER TABLE companies_clean ADD COLUMN IF NOT EXISTS gdpr_basis_date date;

-- Legitimate interest: public procurement data
UPDATE companies_clean
SET gdpr_basis = 'legitimate_interest',
    gdpr_basis_date = CURRENT_DATE
WHERE gdpr_basis IS NULL
  AND source IN ('ted_procurement_buyers','ted_winners','anofm','ebrd_contractors');

-- Public registry: legitimate interest
UPDATE companies_clean
SET gdpr_basis = 'legitimate_interest',
    gdpr_basis_date = CURRENT_DATE
WHERE gdpr_basis IS NULL
  AND source IN ('no_registry','se_registry','dk_registry','fi_registry',
                 'ro_anaf','anofm','master_romania');

-- Enriched pattern emails: weaker basis, mark separately
UPDATE companies_clean
SET gdpr_basis = 'pattern_enriched',
    gdpr_basis_date = CURRENT_DATE
WHERE gdpr_basis IS NULL
  AND enriched_email IS NOT NULL AND enriched_email != ''
  AND (email IS NULL OR email = '');

-- Remaining: unknown
UPDATE companies_clean
SET gdpr_basis = 'unknown',
    gdpr_basis_date = CURRENT_DATE
WHERE gdpr_basis IS NULL;

-- High-risk countries requiring extra care
SELECT
  country,
  gdpr_basis,
  COUNT(*) AS companies
FROM companies_clean
WHERE country IN ('DE','FR','IT','AT','CH','NL','BE')
GROUP BY country, gdpr_basis
ORDER BY country, companies DESC;

-- Summary
SELECT gdpr_basis, COUNT(*) FROM companies_clean GROUP BY gdpr_basis ORDER BY COUNT(*) DESC;
