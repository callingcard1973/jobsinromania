# autoheal.md — Watchdog, Bots, Response Tracking, Solonet

## Architecture (2026-04-16)

- **One bot**: @raspibig_controller_bot — all interaction, 37 commands
- **Raspi**: zero telegram, zero email sending. Only scrapers + APIs + DB
- **Raspibig**: ALL telegram (5 bots), ALL email sending, ALL automation
- Watchdog v2 runs every 15 min via cron on both machines

## Raspibig Watchdog (`/opt/ACTIVE/INFRA/SKILLS/bot_watchdog.py`)

Checks: 11 services, bot 409 conflicts (auto deleteWebhook+restart), dashboard 8096, orchestrator, disk (auto-clean >85%), Ollama, response tracker cron, NanoClaw heartbeat, Caddy HTTPS.

## Raspi Watchdog (`/opt/ACTIVE/INFRA/SKILLS/bot_watchdog.py`)

Checks: 7 services, campaign orchestrator, disk, PostgreSQL query, Node-RED, Caddy, bot conflicts, raspibig reachability.

## Telegram Bot — @raspibig_controller_bot (37 commands)

```
/q /health /blockers /heal /nanoclaw    — overview + autoheal
/svc /restart /logs /errors /watchdog   — services
/campaigns /norway /bounce /send /stop_campaign  — campaigns
/solonet /send_solonet_X /solonet_placed_X <w> <eur>  — solonet
/process /approve_eXXX /skip_eXXX /queue  — email processing
/responses /workers /leads              — response tracking
/disk /mem /top /db /ollama /scrapers   — system
/ping /wake /kill /net /ssl /cron /temp /uptime /backup  — infra
```

## Response Tracker (`/opt/ACTIVE/INFRA/SKILLS/response_tracker.py`)

Scans 19 IMAP inboxes every 5 min. Classifies: INTERESTED, NOT_INTERESTED, WORKER_APPLICATION, REPLY, BOUNCE, AUTO_REPLY.
- Workers → applicant DB + auto-reply with apply form
- RO employer leads (.ro) → auto-create solonet order drafts

## Solonet Order Pipeline (`/opt/ACTIVE/INFRA/SKILLS/solonet_pipeline.py`)

Auto-creates draft orders from RO employer responses. Tudor approves via `/send_solonet_X` → email to solonet.vacancy@gmail.com.
- Tracks: draft→sent→responded→placed
- Auto follow-up after 3 days
- Revenue tracking via `/solonet_placed_X <workers> <eur>`
- DB: `interjob_master.solonet_orders` | No LLM tokens

## Email Processor (`/opt/ACTIVE/INFRA/SKILLS/email_processor.py`)

Every 10 min: sklearn classifier → Ollama qwen3-4b for draft reply if low confidence.
Telegram: `/approve_eXXX` or `/skip_eXXX`. Executor: `email_executor.py`

## Worker Router (`/opt/ACTIVE/INFRA/SKILLS/worker_router.py`)

Routes worker applications → `master_applicants.db` (758+ workers) + auto-reply.
Applications kept for Tudor, never forwarded to solonet.

## NanoClaw (`/opt/ACTIVE/INFRA/GOVERNOR/nanoclaw.py`)

Operations agent: 9 scrapers, TED data, disk, missed-run detection. LLM diagnosis on failure. Morning digest 07:00.

## Telegram Alerts Rule

Alerts = failure only. Never send for successful restarts/recoveries. Self-healing noise is useless.
