# Telegram Alert Notifier System

## Overview
Complete Telegram notification system for Prometheus Alertmanager. Receives critical infrastructure alerts and forwards them to Telegram in real-time.

## Components

### 1. Alertmanager Configuration
**Location:** `/etc/prometheus/alertmanager.yml`

Configured with:
- Webhook receiver for Telegram notifications on `http://localhost:8081/webhook`
- Alert grouping by alertname, cluster, and service
- 10s group wait and group interval for fast notifications
- 1h repeat interval for ongoing alerts
- Critical alerts repeated every 15 minutes

### 2. Telegram Notifier Service
**Location:** `/opt/ACTIVE/INFRA/ALERTS/telegram_notifier.py`

Features:
- Flask-based webhook receiver (port 8081)
- Receives Prometheus alert JSON payloads
- Formats alerts with severity icons and detailed information
- Health check endpoint at `/health`
- Placeholder configuration for Telegram bot token and chat ID

### 3. Systemd Service
**Location:** `/etc/systemd/system/telegram-alerts.service`

Configuration:
- Runs as `tudor` user
- Auto-restarts on failure
- Depends on prometheus-alertmanager
- Logs to journal (journalctl)

## Installation

Files are deployed to raspibig:
```bash
# Service is enabled and running
sudo systemctl status telegram-alerts
sudo systemctl enable telegram-alerts

# Check service logs
journalctl -u telegram-alerts -f
```

## Configuration

### Step 1: Get Telegram Bot Token
1. Create a bot with @BotFather on Telegram
2. Get the token (format: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

### Step 2: Get Chat ID
1. Message your bot
2. Visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Find your chat_id in the response

### Step 3: Update Configuration
Edit `/opt/ACTIVE/INFRA/ALERTS/telegram_notifier.py`:
```python
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID_HERE"
```

Restart service:
```bash
sudo systemctl restart telegram-alerts
```

## Alert Examples

### Critical Alert (Port 8081)
When a critical alert fires:
```
🚨 FIRING

Alert: InstanceDown
Severity: CRITICAL
Instance: localhost:9090
Summary: Instance localhost:9090 is down
Description: Instance localhost:9090 has been down for more than 2 minutes
Time: 2026-04-04 16:18:30
```

### Warning Alert
```
⚠️ FIRING

Alert: HighMemoryUsage
Severity: WARNING
Instance: raspibig:9100
Summary: High memory usage on raspibig:9100
Description: Memory usage is above 90% on raspibig:9100
Time: 2026-04-04 16:18:45
```

## Alert Rules
Active alert rules in `/etc/prometheus/rules/critical_alerts.yml`:
- InstanceDown: any instance down for 2+ minutes
- HighMemoryUsage: >90% for 5+ minutes
- DiskSpaceLow: >85% usage for 5+ minutes
- PostgreSQLDown: database not responding for 1+ minute
- HighDatabaseConnections: >80 active connections for 5+ minutes

## Testing

Health check:
```bash
curl http://localhost:8081/health
```

Send test alert:
```bash
curl -X POST http://localhost:8081/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "alerts":[{
      "status":"firing",
      "labels":{
        "alertname":"TestAlert",
        "severity":"warning",
        "instance":"test:9090"
      },
      "annotations":{
        "summary":"Test alert",
        "description":"This is a test notification"
      }
    }]
  }'
```

## Monitoring

View service logs:
```bash
journalctl -u telegram-alerts -n 50 --no-pager
journalctl -u telegram-alerts -f
```

Check service status:
```bash
systemctl status telegram-alerts
sudo systemctl restart telegram-alerts
sudo systemctl stop telegram-alerts
```

Check port binding:
```bash
lsof -i :8081
netstat -tlnp | grep 8081
```

## Troubleshooting

**Service won't start:**
```bash
journalctl -u telegram-alerts -n 30
# Check Flask/Python errors
```

**Telegram messages not sending:**
- Verify bot token in `/opt/ACTIVE/INFRA/ALERTS/telegram_notifier.py`
- Verify chat_id is correct
- Check service logs: `journalctl -u telegram-alerts -f`
- Test endpoint: `curl http://localhost:8081/health`

**Port already in use:**
```bash
# Find process using port 8081
lsof -i :8081
# Change port in telegram_notifier.py and alertmanager.yml
```

## Files Summary

| File | Location | Purpose |
|------|----------|---------|
| telegram_notifier.py | /opt/ACTIVE/INFRA/ALERTS/ | Flask webhook service |
| telegram-alerts.service | /etc/systemd/system/ | Systemd service unit |
| alertmanager.yml | /etc/prometheus/ | Alertmanager config |
| critical_alerts.yml | /etc/prometheus/rules/ | Alert rule definitions |

## Integration

Alertmanager → telegram_notifier.py → Telegram Bot → Chat

1. Prometheus evaluates alert rules
2. Alertmanager receives alerts
3. Webhook notifier receives at /webhook
4. Formats and sends to Telegram
5. User receives instant notification

## Status (2026-04-04)

✓ Configuration updated
✓ Service created and deployed
✓ Port 8081 configured
✓ Health check working
✓ Test webhook successful
✓ Ready for token configuration
