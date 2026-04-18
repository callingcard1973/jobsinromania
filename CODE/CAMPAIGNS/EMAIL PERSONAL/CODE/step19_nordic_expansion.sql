-- Step 19: Nordic expansion — import DK/FI/SE into companies_clean

-- Check columns
SELECT column_name FROM information_schema.columns WHERE table_name='se_companies' LIMIT 10;

-- Import DK (12K emails)
INSERT INTO companies_clean (name, country, city, email, phone, website, source, lead_score, is_insolvent, is_agency)
SELECT
  company_name, 'DK',
  company_city,
  email_1,
  NULL, company_website,
  'dk_companies', 0, false, false
FROM dk_companies
WHERE email_1 IS NOT NULL AND email_1 != ''
  AND NOT EXISTS (
    SELECT 1 FROM companies_clean cc
    WHERE LOWER(cc.name) = LOWER(company_name) AND cc.country='DK'
  )
ON CONFLICT DO NOTHING;

-- Import FI (10K emails)
INSERT INTO companies_clean (name, country, email, source, lead_score, is_insolvent, is_agency)
SELECT name, 'FI', email, 'fi_companies', 0, false, false
FROM fi_companies
WHERE email IS NOT NULL AND email != ''
  AND NOT EXISTS (
    SELECT 1 FROM companies_clean cc
    WHERE LOWER(cc.name) = LOWER(fi_companies.name) AND cc.country='FI'
  )
ON CONFLICT DO NOTHING;

-- Report
SELECT country, COUNT(*) total, COUNT(email) FILTER (WHERE email IS NOT NULL AND email!='') with_email
FROM companies_clean
WHERE country IN ('DK','FI','SE','NO')
GROUP BY country ORDER BY total DESC;
