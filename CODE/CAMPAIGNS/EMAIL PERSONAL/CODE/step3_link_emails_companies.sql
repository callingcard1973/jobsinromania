-- Step 3: Link master_emails → companies_clean via domain matching
-- Matches business-domain emails to companies by website domain
-- Updates enriched_email on companies_clean
-- Run: psql -U tudor -h 127.0.0.1 -p 5433 -d interjob_master -f step3_link_emails_companies.sql

-- Build temp index: extract domain from company website
CREATE TEMP TABLE company_domains AS
SELECT
  id,
  country,
  REGEXP_REPLACE(
    REGEXP_REPLACE(LOWER(website), '^https?://(www\.)?', ''),
    '/.*$', ''
  ) AS website_domain
FROM companies_clean
WHERE website IS NOT NULL AND website != ''
  AND enriched_email IS NULL;

CREATE INDEX idx_tmp_domain ON company_domains(website_domain);

-- Match emails to companies by domain
UPDATE companies_clean cc
SET enriched_email = me.email
FROM company_domains cd
JOIN (
  SELECT DISTINCT ON (domain) domain, email, quality_tier
  FROM master_emails
  WHERE quality_tier IN (1,2)
    AND domain NOT IN ('gmail.com','hotmail.com','yahoo.com','yahoo.co.uk','yahoo.fr',
      'yahoo.de','yahoo.no','yahoo.pl','outlook.com','hotmail.fr','hotmail.de',
      'live.com','icloud.com','aol.com','abv.bg','wp.pl','orange.fr','mail.ru',
      'gmx.de','gmx.net','web.de','free.fr','laposte.net','wanadoo.fr','t-online.de')
  ORDER BY domain, quality_tier ASC
) me ON me.domain = cd.website_domain
WHERE cd.id = cc.id
  AND cc.enriched_email IS NULL;

-- Report results
SELECT
  country,
  COUNT(*) FILTER (WHERE enriched_email IS NOT NULL) as newly_enriched,
  COUNT(*) total
FROM companies_clean
WHERE country IN ('NO','RO','PL','FR','DE','GB','BG','UA','CZ')
GROUP BY country
ORDER BY newly_enriched DESC;

DROP TABLE company_domains;
