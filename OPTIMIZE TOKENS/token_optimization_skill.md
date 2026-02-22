# Token Optimization Supervisor Skill

**Name**: token-optimization
**Type**: Monitoring & Reporting
**Trigger**: Manual or scheduled (daily audits, weekly dashboards)

## Description

Supervise and monitor the token optimization system across all 3 machines (laptop, raspibig, raspi). Provides:
- **Health checks**: Detect anomalies, verify cron jobs, check file compliance
- **Trend analysis**: Weekly reports on token savings and optimization progress
- **Automated fixes**: Detect new bloat and consolidation drift, auto-trigger corrections
- **Actionable reports**: Supervisor briefings with recommendations

## Quick Start

### Health Check
```bash
python D:\MEMORY\OPTIMIZE TOKENS\token_optimization_supervisor.py --check
```
Output: System status (HEALTHY/DEGRADED), metrics, warnings, recommendations

### Weekly Report
```bash
python D:\MEMORY\OPTIMIZE TOKENS\token_optimization_supervisor.py --report
```
Output: Detailed supervisor report with trend analysis and recommendations

## Supervised Components

1. **Daily Audits** (raspibig + raspi + laptop)
   - Monitored: Cron job execution, log freshness, bloat detection
   - Alert: If audit >48 hours old, or files exceed 50-line limit

2. **Weekly Dashboard** (Mondays)
   - Monitored: Report generation, trend analysis, recommendations
   - Alert: If weekly report missing or tokens saved declining >50%

3. **Infrastructure Consolidation**
   - Monitored: New duplication, reference drift
   - Alert: If infrastructure refs duplicate, costing >100 tokens wasted

4. **Token Tracking**
   - Monitored: Baseline drift, tool weight accuracy
   - Alert: If baseline increases >20% from expected

5. **Remote Machines**
   - Monitored: Script deployment, cron job sync, log directories
   - Alert: If scripts missing or versions diverge

## System Outputs

- **Health status**: GREEN (healthy) / YELLOW (warnings) / RED (alerts)
- **Metrics dashboard**: Files audited, bloat count, tokens saved
- **Trend reports**: Weekly PDF with graphs and analysis
- **Anomaly detection**: Automatic alerts for >50% token savings drop
- **Recommendations**: Actionable steps to maintain optimization

## Integration with Claude Code

### SessionStart Hook
Automatically runs light health check when Claude Code starts:
```json
{
  "hooks": {
    "PostToolUse": {
      "command": "python D:\\MEMORY\\OPTIMIZE TOKENS\\token_monitor.py"
    }
  }
}
```

### Manual Invocation
Call from any Claude Code session to check system health:
```bash
/token-optimization check
```

## Key Metrics Tracked

| Metric | Normal | Warning | Alert |
|--------|--------|---------|-------|
| Audit age | <24h | 24-48h | >48h |
| Files bloated | 0 | 1-5 | >5 |
| Token savings trend | stable/up | declining | down >50% |
| Cron job status | scheduled | delayed | failed |
| Infrastructure duplication | 0 | <5 items | >5 items |
| Machine sync | synchronized | 1h behind | >24h behind |

## Deployment

### On Laptop (Windows)
- Manual: `python D:\MEMORY\OPTIMIZE TOKENS\token_optimization_supervisor.py --check`
- Scheduled: Can be added to Task Scheduler

### On raspibig + raspi (Linux)
- Manual: SSH and run supervisor script
- Scheduled: Cron job (can be added)

## Example Report Output

```
TOKEN OPTIMIZATION SUPERVISOR REPORT
Generated: 2026-02-23T14:30:00

System Status: HEALTHY

HEALTH METRICS:
  latest_audit_age_hours: 2.1
  files_audited: 278
  files_bloated: 0
  tokens_saved_total: 4670
  infrastructure_duplication: 0

WARNINGS: None

RECOMMENDATIONS:
  [OK] System operating normally - no action required

NEXT ACTIONS:
  - Daily (9 AM UTC): Auto-audit runs (randomized 0-59 min delay)
  - Weekly (Mondays): Dashboard report generated
  - Quarterly: Deep audit of all 277 CLAUDE.md files
```

## Emergency Commands

**Force immediate health check:**
```bash
python D:\MEMORY\OPTIMIZE TOKENS\token_optimization_supervisor.py --check
```

**Trigger corrective actions:**
```bash
python D:\MEMORY\OPTIMIZE TOKENS\claude_md_optimizer.py --apply
python D:\MEMORY\OPTIMIZE TOKENS\consolidate_infrastructure.py --apply
```

**Reset audit counter:**
```bash
python D:\MEMORY\OPTIMIZE TOKENS\token_monitor.py --reset
```

## Monitoring Schedule

- **Every tool call**: token_monitor.py runs (PostToolUse hook)
- **Daily 9 AM UTC**: Randomized audit (0-59 min delay)
- **Weekly Mondays**: Dashboard report generated
- **Weekly Fridays**: Remote machine sync verification
- **Monthly 1st**: Infrastructure consolidation review
- **Quarterly**: Deep audit of all files

## Success Metrics

- ✓ 0 bloated files (all ≤50 lines)
- ✓ 40-50% token reduction sustained
- ✓ All 3 machines synchronized
- ✓ Weekly trend reports generated
- ✓ <1 alert/month (anomalies rare)
- ✓ Audit completion time <30 minutes
