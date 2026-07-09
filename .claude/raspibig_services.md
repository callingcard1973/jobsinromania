# Raspibig Critical Services Status

**Last Updated:** 2026-04-28 08:45 EEST

## Services Health

| Service | Status | Uptime | Role | Log |
|---------|--------|--------|------|-----|
| rspamd | ✅ ACTIVE | 10d | Spam filtering | systemd journal |
| email-health-check.timer | ✅ ACTIVE | 20min | Campaign monitoring | `/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/logs/` |
| email-auto-organize.timer | ✅ ACTIVE | 8min | Email sorting | `/opt/ACTIVE/EMAIL/EMAIL_CLASSIFIER/DATA/training_data/auto_organize.log` |
| llm-email-processor | ✅ ACTIVE | 13min | Email classification+response | `/opt/EMAIL/LINKMIND/logs/smart_email_processor.log` |
| email-action-api | ✅ ACTIVE | 17d | Email API | systemd journal |
| email-health-dashboard | ✅ ACTIVE | 27d | Health UI | systemd journal |
| unified-orchestrator | ✅ ACTIVE | 8d | Campaign sender | systemd journal |

## Resources

- **Memory:** 5.8GB/15GB (available: 10GB)
- **Swap:** 3.0GB/8.4GB (37% — monitor)
- **Disk:** 82G/235G (37% — healthy)
- **Processes:** 420 (stable)

## Quick Checks

```bash
# Check rspamd
rspamc stat

# Run health check manually
cd /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED && python3 health_monitor.py --telegram

# Check LLM processor logs
tail -20 /opt/EMAIL/LINKMIND/logs/smart_email_processor.log

# Check auto-organize logs
tail -20 /opt/ACTIVE/EMAIL/EMAIL_CLASSIFIER/DATA/training_data/auto_organize.log

# Monitor swap
free -h
```

## Known Issues

1. Campaign sends: 0 in last 24h (verify configs active)
2. LLM model: lfm2.5-1.2b has timeout issues (consider qwen2.5)
3. Swap: 37% used (was 93% before cleanup)

## Disabled Services (Not Needed)

- spamd (replaced by rspamd)
- llama-server (broken model path, use laptop)
- ollama (disabled)
- legacy email services (responder, classifier, collector)

---

Run cleanup checks weekly. Alert if swap >60% or rspamd errors appear.
