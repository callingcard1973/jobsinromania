-- Step 6: Enrich companies_clean NO from no_companies_full (94 cols)
-- Syncs: email, phone, employees, website, sector from richer source

-- Update email where missing in companies_clean
UPDATE companies_clean cc
SET
  email = COALESCE(NULLIF(cc.email,''), nf.epostadresse),
  phone = COALESCE(NULLIF(cc.phone,''), COALESCE(nf.telefon, nf.mobil)),
  website = COALESCE(NULLIF(cc.website,''), nf.hjemmeside),
  employees_count = COALESCE(cc.employees_count, NULLIF(nf.antallansatte,'')::integer),
  sector = COALESCE(NULLIF(cc.sector,''), nf.naeringskode1_kode),
  sector_name = COALESCE(NULLIF(cc.sector_name,''), nf.naeringskode1_beskrivelse)
FROM no_companies_full nf
WHERE cc.cui = nf.organisasjonsnummer
  AND cc.country = 'NO'
  AND (
    (cc.email IS NULL OR cc.email = '') AND (nf.epostadresse IS NOT NULL AND nf.epostadresse != '')
    OR (cc.phone IS NULL OR cc.phone = '') AND (nf.telefon IS NOT NULL OR nf.mobil IS NOT NULL)
    OR (cc.website IS NULL OR cc.website = '') AND (nf.hjemmeside IS NOT NULL AND nf.hjemmeside != '')
    OR cc.employees_count IS NULL AND nf.antallansatte IS NOT NULL
  );

-- Report improvement
SELECT
  COUNT(*) total,
  COUNT(email) FILTER (WHERE email IS NOT NULL AND email!='') as has_email,
  COUNT(phone) FILTER (WHERE phone IS NOT NULL AND phone!='') as has_phone,
  COUNT(website) FILTER (WHERE website IS NOT NULL AND website!='') as has_website,
  COUNT(employees_count) FILTER (WHERE employees_count IS NOT NULL) as has_employees
FROM companies_clean WHERE country='NO';
