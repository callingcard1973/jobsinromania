---
name: report-generator
description: "Generate daily + weekly INTERJOB.RO reports — campaign KPIs, pipeline health, infrastructure status, lead quality, revenue signals, strategic blockers. Sends daily digest (06:00 UTC) + weekly stakeholder report (Monday 07:00 UTC). Use when generating reports, analyzing campaign trends, requesting blockers list, forecasting revenue, or stakeholder communication."
---

# Report Generator Skill

**Purpose:** Automated executive reporting for INTERJOB.RO — daily operational digest + weekly strategy review.

**Report types:**

### Daily Digest (06:00 UTC)
- Campaign metrics table (sends, bounce%, reply%, engagement per campaign)
- Pipeline health (data quality score, missing sources, anomalies)
- Infrastructure status (CPU/disk/connections, alerts from previous 24h)
- Blockers identified (numbered, with severity + action)
- Key metric trend (vs. last 7-day average)
- Forecast (today's expected volume, confidence)

### Weekly Stakeholder Report (Monday 07:00 UTC)
- Executive summary (status, key wins, blockers, forecast)
- Campaign analysis (performance per segment, optimization opportunities)
- Lead quality (engagement signals, conversion likelihood)
- Revenue impact (estimated leads, cost per lead, ROI signals)
- Infrastructure reliability (uptime %, incident summary)
- Recommendations (which campaigns to accelerate/pause, resource needs)
- Historical trends (7-day, 30-day moving averages)

**Data sources:**
- Campaign state: `/opt/ACTIVE/EMAIL/CAMPAIGNS/state.json` (daily counts)
- Bounce/reply logs: Campaign directories on raspibig
- Pipeline state: `pipeline_state.json` (from pipeline-orchestrator)
- Infrastructure metrics: `health_status.json` (from infrastructure-health)
- Company database: PostgreSQL (lead quality, engagement scoring)

**Calculations:**
- Bounce% = hard_bounces / sent
- Reply% = total_replies / sent
- Engagement% = (reply% + interested%) / sent
- Cost per lead = (campaign_cost / leads_generated)
- Lead quality = function(bounce%, reply_sentiment, company_health_signals)

**Output format:**
- Daily digest: HTML email (~1000 words)
- Weekly report: PDF (ReportLab) + HTML (~3000 words, embeds CSV tables)
- Blockers file: `latest_blockers.json` (for automation + human review)

**Error handling:**
- Incomplete data: use last known value + "as-of {date}" flag
- Failed query: escalate to pipeline-orchestrator / analytics
- Report generation timeout (>3 min): send partial report + error
- Data anomaly (bounce >30%): flag as unusual, recommend investigation

**Email recipients:**
- Daily digest: fruitnature4@gmail.com (Tudor)
- Weekly report: fruitnature4@gmail.com + optionally CC stakeholders
