-- Step 1: DB-internal email quality filter
-- Adds quality_tier column and marks emails based on existing data
-- Run: psql -U tudor -h 127.0.0.1 -p 5433 -d interjob_master -f step1_db_filter.sql

-- Add columns if not exist
ALTER TABLE master_emails ADD COLUMN IF NOT EXISTS is_dnc BOOLEAN DEFAULT false;
ALTER TABLE master_emails ADD COLUMN IF NOT EXISTS dnc_reason TEXT;
ALTER TABLE master_emails ADD COLUMN IF NOT EXISTS quality_tier INTEGER; -- 1=best, 2=ok, 3=suspect, 4=bad

-- 1. Mark bounced
UPDATE master_emails SET is_dnc=true, dnc_reason='bounced'
WHERE is_bounced=true AND is_dnc IS DISTINCT FROM true;

-- 2. Mark DNC from main list
UPDATE master_emails me SET is_dnc=true, dnc_reason='dnc_list'
FROM dnc_list d WHERE LOWER(me.email)=LOWER(d.email) AND me.is_dnc IS DISTINCT FROM true;

-- 3. Mark DNC from all country DNC tables
UPDATE master_emails me SET is_dnc=true, dnc_reason='country_dnc'
WHERE LOWER(me.email) IN (
    SELECT LOWER(email) FROM austria_dnc UNION ALL
    SELECT LOWER(email) FROM be_dnc UNION ALL
    SELECT LOWER(email) FROM bg_dnc UNION ALL
    SELECT LOWER(email) FROM czechia_dnc UNION ALL
    SELECT LOWER(email) FROM denmark_dnc UNION ALL
    SELECT LOWER(email) FROM finland_dnc UNION ALL
    SELECT LOWER(email) FROM france_dnc UNION ALL
    SELECT LOWER(email) FROM germany_dnc UNION ALL
    SELECT LOWER(email) FROM isc_dnc UNION ALL
    SELECT LOWER(email) FROM italy_dnc UNION ALL
    SELECT LOWER(email) FROM netherlands_dnc UNION ALL
    SELECT LOWER(email) FROM no_dnc UNION ALL
    SELECT LOWER(email) FROM norway_dnc UNION ALL
    SELECT LOWER(email) FROM poland_dnc UNION ALL
    SELECT LOWER(email) FROM romania_dnc UNION ALL
    SELECT LOWER(email) FROM spain_dnc UNION ALL
    SELECT LOWER(email) FROM ted_campaign_dnc
)
AND me.is_dnc IS DISTINCT FROM true;

-- 4. Flag bad format (no @ or no dot after @)
UPDATE master_emails SET is_dnc=true, dnc_reason='bad_format'
WHERE (email NOT LIKE '%@%' OR email NOT LIKE '%@%.%')
AND is_dnc IS DISTINCT FROM true;

-- 5. Flag generic/role-based prefixes
UPDATE master_emails SET is_generic=true
WHERE LOWER(email) ~ '^(noreply|no-reply|donotreply|postmaster|mailer-daemon|abuse|spam|webmaster|hostmaster|support|help|contact|info|office|admin|sales|marketing|hr|jobs|careers|hello|team|service|billing|newsletter|unsubscribe|bounces|reply)@'
AND is_generic IS DISTINCT FROM true;

-- 6. Assign quality tiers
-- Tier 1: MX valid, not DNC, not generic, not bounced
-- Tier 2: MX valid, not DNC, generic OK
-- Tier 3: MX unknown, not DNC
-- Tier 4: DNC / bounced / bad format

UPDATE master_emails SET quality_tier =
    CASE
        WHEN is_dnc=true OR is_bounced=true THEN 4
        WHEN mx_valid=true AND is_generic=false THEN 1
        WHEN mx_valid=true AND is_generic=true  THEN 2
        WHEN mx_valid IS NULL OR mx_valid=false  THEN 3
        ELSE 3
    END;

-- Summary report
SELECT
    quality_tier,
    COUNT(*) AS count,
    ROUND(COUNT(*)*100.0/SUM(COUNT(*)) OVER(), 1) AS pct
FROM master_emails
GROUP BY quality_tier
ORDER BY quality_tier;
