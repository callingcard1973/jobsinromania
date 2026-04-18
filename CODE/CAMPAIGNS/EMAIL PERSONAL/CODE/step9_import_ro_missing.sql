-- Step 9: Import 143K missing RO companies from master_romania_companies
-- Only companies with email, not already in companies_clean by CUI

INSERT INTO companies_clean (
  id, name, cui, country, city, address, phone, email, website,
  sector, sector_name, employees_count, revenue, source, source_file,
  lead_score, is_insolvent, is_agency, enriched_email
)
SELECT
  mrc.id,
  mrc.name,
  mrc.cui,
  'RO',
  mrc.city,
  mrc.address,
  mrc.phone,
  mrc.email,
  mrc.website,
  mrc.caen,
  mrc.caen_description,
  mrc.employees_count,
  mrc.revenue,
  'master_romania_companies',
  NULL,
  0,
  false,
  false,
  NULL
FROM master_romania_companies mrc
WHERE (mrc.email IS NOT NULL AND mrc.email != '')
  AND NOT EXISTS (
    SELECT 1 FROM companies_clean cc WHERE cc.cui = mrc.cui AND cc.country = 'RO'
  )
ON CONFLICT (id) DO NOTHING;

-- Report
SELECT
  COUNT(*) total,
  COUNT(email) FILTER (WHERE email IS NOT NULL AND email!='') as with_email,
  COUNT(phone) FILTER (WHERE phone IS NOT NULL AND phone!='') as with_phone
FROM companies_clean WHERE country='RO';
