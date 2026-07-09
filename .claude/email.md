# email.md — Unified Email Architecture

All email sending flows through raspibig orchestrator. Laptop = dev/config mgmt. Raspi = validation layer.

## Three-System Division

### Laptop (D:\MEMORY\CODE\CAMPAIGNS/)

**Dev sandbox + config management.** No live sends.

```
CAMPAIGNS/
├── CODE/senders/          — local test senders (e.g., campaign_primarii.py)
├── EMAIL/CODE/            — config builders, utilities, Mailrelay integration
│   ├── email_accounts.py  — Brevo/Gmail/Zoho credential mgmt
│   ├── send_mailrelay.py  — Mailrelay SDK wrapper
│   ├── verify_mailrelay.py — health check
│   └── patch_*.py         — config patches (applied before raspibig deploy)
├── EMAIL PERSONAL/CODE/   — DB enrichment pipeline (steps 1-46)
├── HARGHITA/              — RO regional campaign configs
└── EMAIL/                 — Brevo templates (HTML)
```

**Workflow:**
1. Build/test campaign config locally (email_accounts.py, patch_*.py)
2. Verify with send_mailrelay.py (no live send, dry-run only)
3. SCP config to raspibig: `scp "D:/MEMORY/CODE/CAMPAIGNS/EMAIL/..." tudor@192.168.100.21:/opt/ACTIVE/EMAIL/`
4. Never send from laptop

**Key files:**
- `email_accounts.py` — references 13 Brevo senders, Gmail creds, Zoho warmup accounts
- `send_mailrelay.py` — Mailrelay API (2,666/day budget)
- `send_db.py` (copy of raspibig's DB layer) — local testing only

---

### Raspibig (192.168.100.21:/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/)

**Production email orchestrator. All live sends here.**

#### Core Stack (1.5K lines total)

| Module | Lines | Responsibility |
|--------|-------|-----------------|
| `send_campaign.py` | 19K | Main orchestrator loop (sector/template dispatch, rate limiting, state mgmt) |
| `send_config.py` | ~250 | Global config, sector dicts, DB mapping, logger setup |
| `send_db.py` | ~350 | PostgreSQL integration, contact fetching, log recording |
| `send_providers.py` | ~450 | Brevo, Gmail, Zoho, A2, Postfix abstraction layer |
| `send_utils.py` | ~300 | Template expansion, HMAC signing, business hours check, failure handling |

#### Data Flow

```
send_campaign.py (main loop)
├── load send_config.py (sectors, limits, DB config)
├── for sector in SECTORS:
│   ├── get contacts from send_db.py
│   ├── apply rules (engagement, greylisting, bounce check)
│   └── dispatch to send_providers.py (Brevo/Gmail/Zoho/Postfix/A2)
├── track in send_log table
└── state.json (daily counts, sender cooldown, exhaustion)
```

#### Providers (send_providers.py)

| Provider | Method | Capacity | Use Case |
|----------|--------|----------|----------|
| **Brevo** | REST API | 270/sender/day × 13 accounts | Primary (corporate targets) |
| **Postfix+DKIM** | Postfix→Brevo SMTP relay | Unlimited | Signed mail (sensitive domains) |
| **Gmail** | SMTP TLS | 235/day | Fallback, warmup accounts |
| **Zoho** | SMTP TLS | 50→250/day (warmup) | Secondary fallback |
| **A2 Hosting** | Custom SMTP | 30/day | Legacy campaigns |
| **Mailrelay** | REST API | 2,666/day | expatsinromania.org only |

**Selection logic:**
```python
if cfg.get("sender_type") == "mailrelay":
    send_mailrelay()
elif cfg.get("sender_type") == "gmail_only":
    send_gmail()
elif cfg.get("use_postfix"):
    send_postfix()  # via rspamd DKIM milter
else:
    send_brevo()    # default
```

#### Postfix + DKIM (on raspibig, LIVE)

**Architecture:** Campaign → Postfix:25 → rspamd milter:11332 (sign) → Brevo SMTP:587

Key config:
- **rspamd 4.0.1** — `/etc/rspamd/local.d/dkim_signing.conf`, selector `mail2026`
- **DKIM keys** — `/etc/rspamd/dkim/{domain}.key` (28 domains)
- **Postfix** — satellite relay, `relayhost=[smtp-relay.brevo.com]:587` (loopback-only)
- **sasl_passwd** — per-sender Brevo creds (postmap'd), ~9 senders
- **DNS** — 27/28 domains have `mail2026._domainkey.{domain}` TXT record

**When to use Postfix:**
```json
{"use_postfix": true}  # in sector config → signs all mail
```

DNS check (1 missing):
```bash
ssh tudor@192.168.100.21 'dig +short mail2026._domainkey.cifn.info TXT'
```

---

### Raspi (192.168.100.20:/opt/SKILLS/)

**Email validation + enrichment layer. No sending.**

| Module | Purpose |
|--------|---------|
| `email_validator.py` | MX check, format validation, corporate vs consumer |
| `email_mx_verifier.py` | Per-email MX lookup cache |
| `email_campaign_tracker.py` | Global send tracker (dedup across campaigns) |
| `sender_utils.py` | Shared utilities (bounce analysis, enrichment) |

**Accessed by:** raspibig's send_campaign.py (via import or API call)

---

## Campaign Execution

### Sector Config Structure (send_config.py → SECTORS dict)

```python
SECTORS = {
    "DELIVERY_RO_2026": {
        "enabled": True,
        "sender": "office@mivromania.info",
        "sender_type": "brevo",  # or "gmail_only", "zoho", "postfix", "mailrelay"
        "sender_key": "BREVO_API_KEY",
        "daily_limit": 100,
        "template_num": 1,
        "reply_to": "manpower.dristor@gmail.com",
        "use_postfix": False,
        "business_hours": "08:00-18:00",
    },
    "HARGHITA_PHASE_3": {
        "enabled": True,
        "sender": "recruitment@...",
        "daily_limit": 100,
        "template_num": 3,
        "rotating_templates": [1, 2, 3],  # cycle through templates
        "cooldown_days": 14,
        "stop_conditions": ["SENDER_BLOCKED", "BOUNCE_HIGH"],
    },
    ...
}
```

### Execution (from raspibig)

```bash
# Single sector
python3 /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/send_campaign.py DELIVERY_RO_2026 --limit 100

# All sectors
python3 /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/send_campaign.py

# Test (no send)
python3 /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/send_campaign.py HARGHITA_PHASE_1 --dry-run
```

---

## Monitoring + Health

**Health check script needed** — see `email-limits.md` for metrics.

Current manual checks:
- Brevo bounce % — inspect send_log, calculate `bounced / sent`
- Gmail quota — check `/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/logs/`
- Postfix status — `ssh tudor@192.168.100.21 'postfix status'`

---

## Deploy Pattern (Laptop → Raspibig)

```bash
# 1. Build + test config on laptop (NO send)
python D:\MEMORY\CODE\CAMPAIGNS\EMAIL\CODE\email_accounts.py  # verify senders
python D:\MEMORY\CODE\CAMPAIGNS\EMAIL\CODE\send_mailrelay.py --dry-run  # validate

# 2. SCP to raspibig
scp "D:/MEMORY/CODE/CAMPAIGNS/EMAIL/CODE/send_config_*.py" tudor@192.168.100.21:/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/

# 3. SSH to raspibig, deploy
ssh tudor@192.168.100.21
cd /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/
python3 send_campaign.py SECTOR_NAME --limit 10 --dry-run  # verify
python3 send_campaign.py SECTOR_NAME --limit 50  # live

# 4. Monitor
tail -f logs/sector_name_*.log
```

---

## Files + Directories

| Path | Purpose |
|------|---------|
| `D:\MEMORY\CODE\CAMPAIGNS\EMAIL\CODE\` | Laptop config mgmt (never send) |
| `D:\MEMORY\CODE\CAMPAIGNS\EMAIL\` | Brevo templates (HTML) |
| `/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/` | Raspibig orchestrator (ALL sends) |
| `/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/logs/` | Send logs per sector per day |
| `/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/state/` | `{sector}.json` — daily counts, cooldowns |
| `/opt/ACTIVE/EMAIL/.env` | Credentials (Brevo API keys, Gmail passwords) |
| `/etc/rspamd/dkim/` | DKIM private keys (raspibig) |
| `/etc/postfix/sasl_passwd` | SMTP relay credentials (raspibig) |

---

## Safety Rules

**From CLAUDE.md + campaigns.md — enforceable:**

- ✓ Bounce threshold 30% — check BEFORE every send (3 locations: send_campaign.py line ~158, ~300, ~400)
- ✓ Test sends pollute Brevo stats — never test on live senders
- ✓ One sender per campaign
- ✓ All apply links → `https://interjob.ro/apply.html`
- ✓ GDPR: HMAC-signed unsubscribe links in ALL templates, `privacy.html` LIVE on interjob.ro
- ✓ Never auto-publish to WordPress — draft only
- ✓ Postfix signing: always enable for sensitive domains (legal, gov, corp)
- ✓ Never add `skip_cooldown: true` — violates 14-day anti-spam rule

---

## Next: Phase 2 Consolidation Plan

See `.claude/email-consolidation.md` for code refactor.
