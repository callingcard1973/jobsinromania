---
name: infrastructure-health
description: "Monitor INTERJOB.RO infrastructure — raspibig CPU/memory/disk, PostgreSQL health, cron job status, systemd services. Real-time alerts on thresholds. Use when checking system health, monitoring cron jobs, investigating slow queries, diagnosing service failures, or generating infrastructure reports."
---

# Infrastructure Health Skill

**Purpose:** Real-time health monitoring for INTERJOB.RO — detect bottlenecks, alert on failures, track SLA compliance.

**Monitored systems:**
- **Raspibig** (192.168.100.21) — CPU, memory (6/64GB alert), disk (450/465GB alert), uptime
- **PostgreSQL** — Active queries, connection pool (80/100 alert), replication lag (if any)
- **Systemd services** — campaign-orchestrator, hermes, marm, email-poller, dlm-poller
- **Cron jobs** — 37 active jobs, last run status, next scheduled time
- **Network** — SSH latency, DNS resolution

**Alert thresholds:**
| Metric | Warning | Critical |
|--------|---------|----------|
| CPU usage | 70% | 85% |
| Memory | 80% | 90% |
| Disk | 85% | 95% |
| Connections | 75 | 90 |
| Query time | 30s | 60s |
| Cron failure streak | 2 consecutive | 5+ consecutive |

**Alert channels:**
- Email: fruitnature4@gmail.com
- Telegram: @expatsinromania_news channel (-1003830000766)
- Dashboard: port 8096 (health widget)

**Outputs:**
- Health status JSON — `{cpu, memory, disk, connections, services, crons, last_check, alert_count}`
- Alert events — timestamp, severity (warning/critical), metric, recommendation
- Daily digest — email summary at 06:00 UTC
- Health trend CSV — for 30-day SLA tracking

**Query optimizations:**
- Cache SSH connection via ControlMaster (15 min persistence)
- Batch psql queries (single connection)
- Run every 5 minutes (not per-request)
- Store last state locally, alert only on state changes

**Error handling:**
- SSH timeout >30s → mark infrastructure "unreachable", alert ops
- DNS failure → retry 2x then mark as "network issue"
- Failed query → use last known value, flag as stale (age in hours)
- Service unknown → investigate via systemctl, update monitoring rules
