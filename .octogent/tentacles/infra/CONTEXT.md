# Infra Tentacle

## Scope
D:\MEMORY\CODE\INFRA\ — servers, tools, automation

## Key services on raspibig (192.168.100.21)
- telegram-unified-controller (37 commands, @raspibig_controller_bot)
- interjob-nanoclaw, interjob-governor, campaign-dashboard :8096
- response_tracker.py (19 inboxes, 5min), email_processor.py (10min)
- bot_watchdog.py (15min cron), heartbeat.py (30min)

## Key dirs
- INFRA\WEBPAGES\ — site HTML, WP management, cPanel deploy scripts
- INFRA\FASTAPI\ — ANAF API :5050, cifn API
- INFRA\SECOND_BRAIN\ — vault, morning digest, hooks
- INFRA\RALPH\ — queue.md autonomous coding loop

## A2 Hosting
Host: nl1-cl8-ats1.a2hosting.com, user: loaiidil
API only (no SSH). Docroot: ~/domainname/
28 domains (27 job/static, 7 WP)

## Rules
- Never SSH to A2 Hosting — cPanel UAPI only
- Never auto-publish WP articles — draft only
