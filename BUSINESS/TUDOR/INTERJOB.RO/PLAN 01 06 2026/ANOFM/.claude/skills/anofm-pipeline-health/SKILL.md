---
name: anofm-pipeline-health
description: Comprehensive health check of entire ANOFM pipeline on raspi (timers, DB, scraper, ingest, campaign, disk). Generates health score (0–100), trends, alerts, and remediation recommendations. Used for daily monitoring, debugging failures, auditing system state, or triggering automated recovery.
---

# Skill: anofm-pipeline-health

**Domain:** System observability, metrics aggregation, trend detection  
**Target:** raspi (192.168.100.20), systemd, PostgreSQL, file system  
**Input:** none  
**Output:** health_score (0–100), component status, alerts, recommendations, full report

---

## When to Use

- **Daily health check:** "Is the pipeline healthy? What's the status?"
- **Debugging failures:** "Why did the scraper stop? Show me all metrics."
- **Trending:** "Is bounce rate getting worse? What's the pattern?"
- **Alerts:** "Tell me if anything is critical"
- **Post-incident:** "Verify everything is back to normal"

---

## How It Works

### Step 1: Collect Timer Metrics
```bash
ssh tudor@192.168.100.20

# Timer status
systemctl status anofm-scraper.timer --no-pager
systemctl status anofm-ingest.timer --no-pager
systemctl status anofm-audience-rebuild.timer --no-pager

# Scheduled vs actual
systemctl list-timers anofm-* --no-pager

# Extract: enabled/disabled, last trigger, next trigger, failures
# If last_run_status != 0, increment failure_count
```

### Step 2: Collect Database Metrics
```sql
-- Row count (should be ~16,429)
SELECT COUNT(*) FROM ij_jobs WHERE source='anofm';

-- Daily growth
SELECT COUNT(*) FROM ij_jobs WHERE source='anofm' AND uploaded_at >= NOW() - INTERVAL '1 day';

-- Dedup ratio (should be close to 100% unique)
SELECT COUNT(DISTINCT content_hash) FROM ij_jobs WHERE source='anofm';

-- Check for corruption (nulls in required fields)
SELECT COUNT(*) FROM ij_jobs WHERE source='anofm' AND company IS NULL;
SELECT COUNT(*) FROM ij_jobs WHERE source='anofm' AND job_title IS NULL;
```

### Step 3: Collect Disk Metrics
```bash
# CSV storage size
du -sh /opt/ACTIVE/ANOFM_DATA/

# Percentage used (overall /opt)
df /opt | tail -1 | awk '{print $5}'

# Alert if > 90%
```

### Step 4: Collect Log Metrics
```bash
# Recent errors
journalctl -u anofm-scraper.service -n 5 --no-pager | grep -i error
journalctl -u anofm-ingest.service -n 5 --no-pager | grep -i error

# Scraper runtime (from systemd log)
journalctl -u anofm-scraper.service -1 | grep -i "finished\|failed"
```

### Step 5: Collect Campaign Metrics
```bash
# Total emails sent
wc -l /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/sent.csv

# Sent today (last 24h)
grep "$(date +%Y-%m-%d)" /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/sent.csv | wc -l

# DNC size
wc -l /opt/ACTIVE/EMAIL/CAMPAIGNS/dnc_bounces.txt

# Bounce rate
dnc_growth = dnc_size_now - dnc_size_previous
bounce_rate = (dnc_growth / emails_sent) * 100
```

### Step 6: Calculate Health Score
```python
score = 100

# Timer health
if timer_disabled: score -= 20
if timer_failures > 0: score -= (timer_failures * 10)

# Database health
if row_count < 16000: score -= 20  # Corruption suspect
if nulls_in_required_fields > 0: score -= 10

# Disk health
if disk_usage > 90%: score -= 15
if disk_usage > 95%: score = 0  # Critical

# Campaign health
if bounce_rate > 25%: score -= (bounce_rate - 20)  # Penalty for rate > 20%
if daily_sends < 100 and day > 0: score -= 10  # Low activity

# Service availability
if any_service_down: score = 0  # Critical
```

### Step 7: Trend Analysis
```python
# Load historical metrics from _workspace/health_history.json
# Compare current to previous runs (7-day moving average)

trend = {
  'row_count': 'stable' | 'declining' | 'spiking',
  'bounce_rate': 'stable' | 'trending_up' | 'trending_down',
  'uptime': 'stable' | 'degrading' | 'improving',
  'send_rate': 'stable' | 'declining' | 'spiking'
}

# Alert if trend_direction is concerning
```

### Step 8: Generate Alerts
```python
alerts = []

# Critical
if score < 50:
  if timer_failures > 0:
    alerts.append("CRITICAL: Timer failure detected. Check systemd logs.")
  if row_count < 16000:
    alerts.append("CRITICAL: Database row count anomaly. Possible data loss.")
  if disk_usage > 95%:
    alerts.append("CRITICAL: Disk nearly full. Cleanup urgent.")

# Warning
if 50 <= score < 75:
  if bounce_rate > 25%:
    alerts.append(f"WARNING: Bounce rate {bounce_rate:.1f}%. Review DNC quality.")
  if disk_usage > 80%:
    alerts.append(f"WARNING: Disk usage {disk_usage}%. Schedule cleanup.")
  if daily_sends < 100:
    alerts.append("WARNING: Low send activity today. Check campaign status.")

# Info
if score >= 75:
  if bounce_rate > 20%:
    alerts.append(f"INFO: Bounce rate {bounce_rate:.1f}%. Monitor trend.")
  if row_count > 20000:
    alerts.append(f"INFO: Row count {row_count}. List growth on track.")
```

### Step 9: Generate Recommendations
```python
recommendations = []

if timer_failures > 0:
  recommendations.append("sudo systemctl restart anofm-ingest.timer")

if bounce_rate > 25:
  recommendations.append("Consider list cleaning or audience segmentation.")

if disk_usage > 90:
  recommendations.append("rm /opt/ACTIVE/ANOFM_DATA/csv/*-??-*.csv  # Archive old CSVs")

if row_count < 16000:
  recommendations.append("Verify ingest logs: sudo journalctl -u anofm-ingest.service")

if daily_sends < 100:
  recommendations.append("Check campaign timer: sudo systemctl status anofm-*.timer")

# Add "no action needed" if all clear
if len(recommendations) == 0:
  recommendations.append("Pipeline healthy. Continue current schedule.")
```

### Step 10: Generate Report
```json
{
  "timestamp": "2026-06-21T16:30:00Z",
  "pipeline": "anofm-raspi",
  "health_score": 85,
  "status": "HEALTHY",
  "components": {
    "timers": {
      "status": "OK",
      "enabled": ["scraper", "ingest", "audience-rebuild"],
      "failures": 0,
      "next_run": "2026-06-21T18:25:00Z"
    },
    "database": {
      "status": "OK",
      "row_count": 16429,
      "daily_growth": 200,
      "nulls_in_required_fields": 0,
      "dedup_ratio": 100.0
    },
    "scraper": {
      "status": "OK",
      "last_rows": 7222,
      "trend": "stable",
      "last_run": "2026-06-21T12:30:00Z"
    },
    "ingest": {
      "status": "OK",
      "rows_ingested": 7222,
      "success_rate": 99.5,
      "last_run": "2026-06-21T13:00:00Z"
    },
    "campaign": {
      "status": "OK",
      "sent_today": 142,
      "daily_cap": 150,
      "bounce_rate": 3.2,
      "dnc_size": 53
    },
    "disk": {
      "status": "OK",
      "usage_percent": 76,
      "csv_storage_gb": 45
    }
  },
  "trends": {
    "row_count": "stable",
    "bounce_rate": "trending_up (2.1% → 3.2%)",
    "uptime": "stable",
    "send_rate": "stable"
  },
  "alerts": [
    "Bounce rate trending up (2.1% → 3.2% week-on-week). Monitor next 3 days."
  ],
  "recommendations": [
    "Continue current schedule. No action needed.",
    "Review audience quality if bounce rate continues trending up."
  ],
  "next_check": "2026-06-21T20:30:00Z"
}
```

---

## Health Score Reference

| Score | Status | Action |
|-------|--------|--------|
| 90–100 | Excellent | No action. Monitor routine. |
| 75–89 | Good | Investigate alerts. Plan remediation. |
| 50–74 | Fair | Address alerts. Escalate if worsening. |
| 0–49 | Poor | Critical issues. May need manual intervention. |

---

## Error Handling

| Scenario | Action |
|----------|--------|
| SSH fails | Retry once. Report network issue. |
| DB unreachable | Health score = 0 (critical). |
| Metrics file missing | Skip that metric. Continue. Report warning. |
| Disk full (100%) | Health score = 0. Emergency alert. |

---

## Command Examples

```bash
# Full health check
python3 /opt/ACTIVE/INFRA/SKILLS/anofm_pipeline_health.py

# Quick status (no detailed metrics)
systemctl list-timers anofm-* && psql anofm_db -c "SELECT COUNT(*) FROM ij_jobs;"

# Check logs for errors
journalctl -u anofm-*.service --since "24 hours ago" | grep -i error

# Disk usage
df -h /opt && du -sh /opt/ACTIVE/ANOFM_DATA/
```

---

## Performance Notes

- Full health check: <10 sec (most time is DB queries + SSH)
- Can run every 30 min without overhead
- Report stored in `_workspace/pipeline_health_report.json`
- Historical data kept in `_workspace/health_history.json` (30-day rolling window)

---

## Alerts & Notifications

**Critical (health score < 50):**
- Email to tudor@... (future: integrate Telegram/Slack)

**Warning (50–75):**
- Log to `/opt/ACTIVE/INFRA/LOGS/anofm_health.log`

**Info (75+):**
- Silent (log only)

---

## Future Enhancements

- Auto-remediation (restart failed timers, cleanup disk)
- Telegram/Slack notifications for alerts
- Grafana dashboard integration
- Predictive alerts (if bounce_rate = +0.5% per day, alert in 3 days when > 25%)
