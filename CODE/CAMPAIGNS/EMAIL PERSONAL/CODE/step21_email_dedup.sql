-- Step 21: Email deduplication across all campaign tables
-- Find emails already sent to, add to DNC to prevent double-sending

-- Count total sent per email across all logs
CREATE TEMP TABLE sent_counts AS
SELECT LOWER(email) AS email, COUNT(*) AS times_sent,
  STRING_AGG(DISTINCT campaign, ', ') AS campaigns
FROM (
  SELECT email, campaign FROM norway_send_log WHERE status='sent' AND email IS NOT NULL
  UNION ALL SELECT email, campaign FROM romania_send_log WHERE status='sent' AND email IS NOT NULL
  UNION ALL SELECT email, campaign FROM denmark_send_log WHERE status='sent' AND email IS NOT NULL
  UNION ALL SELECT email, campaign FROM bg_send_log WHERE status='sent' AND email IS NOT NULL
  UNION ALL SELECT email, campaign FROM be_send_log WHERE status='sent' AND email IS NOT NULL
  UNION ALL SELECT email, campaign FROM no_send_log WHERE status='sent' AND email IS NOT NULL
  UNION ALL SELECT email, campaign FROM jobfairs_send_log WHERE status='sent' AND email IS NOT NULL
) all_sent
GROUP BY LOWER(email);

-- Report: emails sent to 3+ campaigns
SELECT COUNT(*) AS over_contacted FROM sent_counts WHERE times_sent >= 3;
SELECT COUNT(*) AS duplicate_domains FROM (
  SELECT SPLIT_PART(email,'@',2) AS domain, COUNT(DISTINCT email) AS emails
  FROM sent_counts
  GROUP BY domain HAVING COUNT(DISTINCT email) >= 5
) sub;

-- Add heavily contacted to DNC
INSERT INTO dnc_list (email, reason, source)
SELECT email, 'over_contacted', 'dedup_audit'
FROM sent_counts
WHERE times_sent >= 5
  AND email NOT IN (SELECT LOWER(email) FROM dnc_list)
ON CONFLICT (email) DO NOTHING;

-- Also deduplicate master_emails: mark quality_tier=4 if in DNC
UPDATE master_emails SET quality_tier=4, is_dnc=true, dnc_reason='over_contacted'
WHERE LOWER(email) IN (SELECT email FROM sent_counts WHERE times_sent >= 5)
  AND quality_tier != 4;

SELECT 'DNC updated with over-contacted emails' AS status;
SELECT COUNT(*) AS total_dnc FROM dnc_list;

DROP TABLE sent_counts;
