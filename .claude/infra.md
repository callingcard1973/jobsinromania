# infra.md — Infrastructure, DB, Services

## Machine IPs

| Machine | IP | Role |
|---------|-----|------|
| laptop | 192.168.100.25 | dev, LM Studio :1234, PG18 :5433 |
| raspibig | 192.168.100.21 | campaigns, email, automation, Telegram |
| raspi | 192.168.100.20 | scrapers, APIs, DB, VPN |
| minipc | 192.168.100.33 | standby, Ollama qwen2.5:14b :11434 |

Tailscale: raspibig=100.124.99.56, laptop=100.81.18.34 (DNS disabled on raspibig: `tailscale set --accept-dns=false`)

## PostgreSQL (laptop)

- PG18 port 5433, data on D:\DATABASES\pgdata18
- Connect: `PGPASSWORD=tudor "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U tudor -h 127.0.0.1 -p 5433 -d interjob_master`

## Key Tables

| Table | Rows | Purpose |
|-------|------|---------|
| `companies_clean` | 33M | Master company DB, enriched |
| `master_emails` | 1.03M | Emails, quality_tier 1-4 |
| `ted_awards` | 6.2M | EU procurement winners |
| `tenders` | 5.1M | EU tenders |
| `seap_ro_awards` | growing | RO SEAP procurement |
| `solonet_orders` | live | Worker placement orders |
| `master_applicants` | 758+ | Worker applicants |

## LLM Stack

- Laptop: Jan-v3.5-4B (fast mode) + Qwen3-8B (batch), port 1234
- Raspibig: Ollama qwen3-4b + qwen2.5:1.5b + llama3.2:3b
- LLM params: temp 0.6, top_k 20, repeat_penalty 1.1
- LLM task feeder: `llm-task-feeder.service` on raspibig, `/opt/ACTIVE/llm_task_feeder.py`

## Raspibig Services

| Service | Port | Script |
|---------|------|--------|
| Campaign orchestrator | — | `/opt/ACTIVE/EMAIL/CAMPAIGNS/orchestrator.py` |
| Unified campaign sender | — | `/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/send_campaign.py` |
| Dashboard | 8096 | `/opt/ACTIVE/INFRA/` |
| ANAF API | 5050 | `INFRA/FASTAPI/anaf_api.py` |
| Bot + watchdog | — | `/opt/ACTIVE/INFRA/SKILLS/bot_watchdog.py` |
| Portainer | 9000 | Docker management |
| Uptime Kuma | 3002 | Service monitor |
| ntfy | 5080 | Push notifications |
| Stirling PDF | 8080 | PDF ops |
| Heimdall | 5005 | Services dashboard |
| Vaultwarden | 8889 | Passwords |

## Raspibig Optimization (LIVE)

- Ollama RE-ENABLED: qwen3-4b, qwen2.5:1.5b, llama3.2:3b
- PostgreSQL VACUUM: 2 AM (off-peak)
- Log rotation: 14-day EU funding, 7-day PG, 4-week email
- Docker: stopped+disabled (save 34% CPU — `sudo systemctl start docker` to restore)
- Node-RED: restart limits configured
- Health check: `python3 /opt/ACTIVE/INFRA/SKILLS/raspibig_health_check.py`

## VPN (raspi)

ProtonVPN WireGuard at `/etc/wireguard/proton-nl.conf` — routes only Zoho SMTP traffic.
```bash
ssh tudor@192.168.100.20 'sudo wg show proton-nl'
ssh tudor@192.168.100.20 'sudo wg-quick down proton-nl && sudo wg-quick up proton-nl'
```

## Deploy Patterns

```bash
# SCP to raspibig
scp "D:/MEMORY/CODE/path/script.py" tudor@192.168.100.21:/opt/ACTIVE/path/

# SSH command
ssh tudor@192.168.100.21 'python3 /opt/ACTIVE/path/script.py'
```

## raspibig Legacy Dirs (/opt/ACTIVE/)

| Dir | What |
|-----|------|
| `A2_SITE_DEPLOYER/` | Deploy sites to cPanel + SEO |
| `ARTICLES/` | LLM articles → 11 languages → deploy |
| `EMAIL_BRAIN/` | 19 inboxes, classify, route workers, solonet orders, CV vault |
| `SITE_PAGES/` | Local mirror of all site HTML |
| `EBRD/` | campaign_builder, contractor_finder, procurement_monitor, ted_scraper |
| `JAN.AI/` | LLM Task Feeder (autonomous batch processing) |
| `CV/` | CV scanner, web UI, file watcher |
