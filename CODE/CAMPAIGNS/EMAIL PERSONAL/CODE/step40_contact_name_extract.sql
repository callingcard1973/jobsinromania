-- Step 40: Extract contact first name from email address
-- john.smith@co.com -> "John", j.smith@co.com -> null (too short), info@co.com -> null (generic)

ALTER TABLE companies_clean ADD COLUMN IF NOT EXISTS contact_first_name text;

-- Generic prefixes to skip
CREATE TEMP TABLE generic_prefixes AS
SELECT unnest(ARRAY[
  'info','contact','office','mail','post','admin','hello','sales','support',
  'hr','jobs','careers','work','team','service','noreply','no-reply',
  'kontakt','bureau','reception','sekretariat','redaktion','presse',
  'buchung','anfrage','bestellung','angebot','info1','info2','webmaster',
  'marketing','commercial','direction','accueil','emploi','recrutement'
]) AS prefix;

UPDATE companies_clean cc
SET contact_first_name = initcap(split_part(local_part, '.', 1))
FROM (
  SELECT id,
    LOWER(split_part(COALESCE(NULLIF(email,''), enriched_email), '@', 1)) AS local_part
  FROM companies_clean
  WHERE (email IS NOT NULL AND email != '' OR enriched_email IS NOT NULL AND enriched_email != '')
    AND contact_first_name IS NULL
) sub
WHERE cc.id = sub.id
  AND length(split_part(sub.local_part, '.', 1)) >= 3
  AND split_part(sub.local_part, '.', 1) NOT IN (SELECT prefix FROM generic_prefixes)
  AND sub.local_part ~ '^[a-z]+\.[a-z]'  -- must be firstname.something pattern
  AND split_part(sub.local_part, '.', 2) != '';  -- must have second part

DROP TABLE generic_prefixes;

SELECT
  COUNT(*) FILTER (WHERE contact_first_name IS NOT NULL) AS with_name,
  COUNT(*) FILTER (WHERE contact_first_name IS NULL AND (email IS NOT NULL AND email!='' OR enriched_email IS NOT NULL AND enriched_email!='')) AS without_name,
  COUNT(*) AS total
FROM companies_clean;

-- Sample extracted names
SELECT contact_first_name, COALESCE(email, enriched_email) AS email, country
FROM companies_clean
WHERE contact_first_name IS NOT NULL
ORDER BY random() LIMIT 20;
