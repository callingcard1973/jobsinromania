-- Step 15: Active tender buyers — companies scaling NOW, need workers immediately

SELECT
  country,
  buyer_name,
  COUNT(*) AS tender_count,
  SUM(value) AS total_value,
  MAX(date_published) AS latest_tender,
  MIN(cpv_code) AS sample_cpv
FROM tenders
WHERE date_published >= NOW() - INTERVAL '180 days'
  AND buyer_name IS NOT NULL AND buyer_name != ''
GROUP BY country, buyer_name
ORDER BY tender_count DESC, total_value DESC NULLS LAST
LIMIT 30;

-- Export active tender buyers as campaign targets
\copy (
  SELECT
    t.country,
    t.buyer_name AS name,
    COUNT(*) AS tenders_last_6mo,
    SUM(t.value) AS total_value_eur,
    MAX(t.date_published) AS last_tender_date,
    COALESCE(cc.email, cc.enriched_email) AS email,
    cc.phone,
    cc.city
  FROM tenders t
  LEFT JOIN companies_clean cc
    ON LOWER(TRIM(cc.name)) = LOWER(TRIM(t.buyer_name))
    AND TRIM(cc.country) = t.country
  WHERE t.date_published >= NOW() - INTERVAL '180 days'
    AND t.buyer_name IS NOT NULL
  GROUP BY t.country, t.buyer_name, cc.email, cc.enriched_email, cc.phone, cc.city
  HAVING COUNT(*) >= 2
  ORDER BY tenders_last_6mo DESC
) TO 'D:/MEMORY/EMAIL PERSONAL/active_tender_buyers.csv' CSV HEADER;
