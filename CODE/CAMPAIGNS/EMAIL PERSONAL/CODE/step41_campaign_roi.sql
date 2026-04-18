-- Step 41: Campaign ROI tracker
-- Links campaign_responses -> solonet_orders -> revenue by sector/country/template

-- View: response rate per campaign
CREATE OR REPLACE VIEW v_campaign_roi AS
SELECT
  cr.campaign,
  cr.sender_email,
  COUNT(*) AS total_responses,
  COUNT(*) FILTER (WHERE cr.category = 'INTERESTED') AS interested,
  COUNT(*) FILTER (WHERE cr.category = 'NOT_INTERESTED') AS rejected,
  COUNT(*) FILTER (WHERE cr.category = 'WORKER_APPLICATION') AS worker_apps,
  ROUND(100.0 * COUNT(*) FILTER (WHERE cr.category = 'INTERESTED') /
    NULLIF(COUNT(*), 0), 1) AS interest_pct,
  MIN(cr.created_at) AS first_response,
  MAX(cr.created_at) AS last_response
FROM campaign_responses cr
GROUP BY cr.campaign, cr.sender_email;

SELECT * FROM v_campaign_roi ORDER BY interested DESC;

-- Link to solonet revenue if table exists
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'solonet_orders') THEN
    RAISE NOTICE 'Solonet orders:';
  END IF;
END $$;

SELECT
  so.status,
  COUNT(*) AS orders,
  SUM(so.revenue_eur) AS total_eur,
  AVG(so.revenue_eur) AS avg_eur
FROM solonet_orders so
GROUP BY so.status
ORDER BY total_eur DESC NULLS LAST;

-- Best performing campaigns (interested rate)
SELECT campaign, interest_pct, interested, total_responses
FROM v_campaign_roi
WHERE total_responses >= 5
ORDER BY interest_pct DESC
LIMIT 10;
