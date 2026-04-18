-- Step 27: Follow-up scheduler
-- Sets followup_at = sent_at + 7 days on all send logs
-- Exports overdue follow-ups (followup_at < NOW() and not yet responded)

-- Set followup_at where NULL
UPDATE norway_send_log SET followup_at = sent_at + INTERVAL '7 days'
WHERE followup_at IS NULL AND status='sent';

UPDATE romania_send_log SET followup_at = sent_at + INTERVAL '7 days'
WHERE followup_at IS NULL AND status='sent';

UPDATE denmark_send_log SET followup_at = sent_at + INTERVAL '7 days'
WHERE followup_at IS NULL AND status='sent';

-- Overdue follow-ups: sent 7+ days ago, no response, not in DNC
COPY (
  SELECT 'NO' AS country, email, company, campaign, sent_at, followup_at,
    CURRENT_DATE - sent_at::date AS days_since_sent
  FROM norway_send_log
  WHERE followup_at < NOW()
    AND status = 'sent'
    AND email NOT IN (SELECT LOWER(email) FROM dnc_list)
    AND LOWER(email) NOT IN (SELECT LOWER(sender_email) FROM campaign_responses)
  UNION ALL
  SELECT 'RO', email, company, campaign, sent_at, followup_at,
    CURRENT_DATE - sent_at::date
  FROM romania_send_log
  WHERE followup_at < NOW()
    AND status = 'sent'
    AND email NOT IN (SELECT LOWER(email) FROM dnc_list)
    AND LOWER(email) NOT IN (SELECT LOWER(sender_email) FROM campaign_responses)
  UNION ALL
  SELECT 'DK', email, company, campaign, sent_at, followup_at,
    CURRENT_DATE - sent_at::date
  FROM denmark_send_log
  WHERE followup_at < NOW()
    AND status = 'sent'
    AND email NOT IN (SELECT LOWER(email) FROM dnc_list)
    AND LOWER(email) NOT IN (SELECT LOWER(sender_email) FROM campaign_responses)
  ORDER BY days_since_sent DESC
) TO 'D:/MEMORY/EMAIL PERSONAL/followup_overdue.csv' CSV HEADER;

SELECT 'Follow-up CSV exported' AS status;
