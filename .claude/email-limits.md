# email-limits.md — Centralized Caps, Rules, Thresholds

All hard limits, soft thresholds, cooldown periods, and business rules. Single source of truth.

## Daily + Hourly Caps

### Per-Provider Limits

| Provider | Capacity | Interval | Notes | Config Key |
|----------|----------|----------|-------|-----------|
| Brevo (1 sender) | 270 | Day | × 13 accounts = 3,510/day total | `BREVO_API_KEY` |
| Gmail (personal) | 235 | Day | Fallback only | `GMAIL_SENDERS` list |
| Gmail (corporate) | 150 | Day | Warmup accounts | `GMAIL_CAP_PER_SENDER` |
| Zoho (warmup) | 50→250 | Day | +5/day automatic warmup | `ZOHO_DAILY_LIMIT` env |
| A2 Hosting | 30 | Day | Legacy campaigns only | Hard-coded in send_a2() |
| Mailrelay | 2,666 | Day | expatsinromania.org only | `send_mailrelay()` check |
| Postfix (unlimited) | — | — | Via Brevo SMTP relay, no direct cap | Routed through Brevo |

### Per-Sector Daily Limits

Hardcoded in `send_config.py → SECTORS → [sector] → daily_limit`:

```python
SECTORS = {
    "DELIVERY_RO_2026": {"daily_limit": 100, ...},       # 562 companies, 6-day campaign
    "HARGHITA_PHASE_1": {"daily_limit": 10, ...},        # 6 companies, testing
    "HARGHITA_PHASE_2": {"daily_limit": 20, ...},        # 18 companies
    "HARGHITA_PHASE_3": {"daily_limit": 100, ...},       # 770 companies
    "FI_TED_CONSTRUCTION": {"daily_limit": 80, ...},     # EU procurement
    "ANOFM": {"daily_limit": 290, ...},                  # 8,546 contacts, multi-sector
    # ... 16 more sectors
}
```

**Total daily capacity:** ~2,500/day (across all sectors, Brevo-first routing)

---

## Bounce + Complaint Thresholds

### Hard Stops (Auto-halt campaign)

| Metric | Threshold | Action | Recovery |
|--------|-----------|--------|----------|
| **Bounce %** | >30% | Stop sector, set `sender_blocked_until` | Manual review + 24h wait |
| **Complaint %** | >1% | Set `sender_blocked_until` | Manual review + FBL investigation |
| **Hard bounce** | >50% of batch | Pause, move to DNC | Purge list, reset sender |
| **Unsubscribe %** | >5% per 1K sends | Flag sector for review | List quality audit |

### Check Points (in send_campaign.py)

```python
# Line ~158: pre-send check (brevo_pre_check)
if bounce_rate > 0.30:
    logger.error(f"Bounce rate {bounce_rate:.1%} > 30%, halting.")
    state['sender_blocked_until'] = (now + 24h).isoformat()
    return 0  # STOP

# Line ~300: mid-batch check (every MID_BATCH_CHECK_INTERVAL = 1 send)
if total_sent % 10 == 0:
    current_bounce = brevo_mid_check(sender)
    if current_bounce > 0.30:
        logger.error("Live bounce check: halt.")
        break

# Line ~400: post-batch analytics
if total_bounced / total_sent > 0.30:
    state['exhausted_until'] = next_month.isoformat()
```

**Where to check manually (3 locations):**
1. `send_log` table — `SELECT bounced, total FROM send_log WHERE sector = '...' ORDER BY date DESC LIMIT 1`
2. Brevo dashboard — Campaigns → Statistics → Bounce %
3. send_campaign.py logs — `grep "bounce_rate\|Bounce" logs/*`

---

## Cooldown + Exhaustion Rules

### Anti-Spam 14-Day Cooldown (MANDATORY)

| Rule | Definition | Enforcement |
|------|-----------|-------------|
| **Minimum gap** | 14 days between sends to same company | `col_last_contacted` in DB + cooldown_days in config |
| **Sector-level** | Same sector, different template, still counts | Global tracker or `companies_clean.last_contacted` |
| **Cross-campaign** | SOV Consulting (DELIVERY_RO) in Feb can't be hit again until Mar 15 | `master_emails.last_contacted` |
| **Skip bypass** | NEVER set `skip_cooldown: true` | Security rule, violates anti-spam law |

**Example config:**
```python
{
    "HARGHITA_PHASE_3": {
        "cooldown_days": 14,
        "stop_conditions": ["COOLDOWN_BLOCKED", "SENDER_BLOCKED", "BOUNCE_HIGH"],
    }
}
```

### Exhaustion Rules

| Condition | Trigger | State Flag | Recovery |
|-----------|---------|-----------|----------|
| **Daily limit reached** | `daily_count >= daily_limit` | Resume next day (auto-reset) | —— |
| **Sector exhausted** | All eligible contacts sent, no new list | `exhausted_until` → end of month | Manual re-import |
| **Sender blocked** | Bounce >30%, complaint >1% | `sender_blocked_until` → 24h later | Manual Brevo review |
| **Business hours** | Outside `business_hours` window (e.g., "08:00-18:00") | Skip sector for this run | Resume next scheduled window |

---

## Gmail + Zoho Warmup

### Gmail Warmup (Automatic)

```python
GMAIL_SENDERS = [
    {"email": "gmail1@...", "limit": 50, "env_pass": "GMAIL_PASS_1"},
    {"email": "gmail2@...", "limit": 100, "env_pass": "GMAIL_PASS_2"},
    # ... rotate through available senders
]
```

**Quota tracking:**
```python
state['gmail_daily'][sender_email] = count  # resets daily
if state['gmail_daily'].get(sender_email, 0) >= cfg['daily_limit']:
    skip this sender
```

### Zoho Warmup (+5/day automatic)

```bash
/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/zoho_warmup.py  # cron daily @ midnight
# transport.work@zohomail.com — starts 50/day, +5/day auto-increment
# workers.europe@zohomail.eu — same pattern
```

Limits:
- transport.work: 50 → 55 → 60 ... → 250/day (cap)
- workers.europe: 50 → 55 → 60 ... → 250/day (cap)

**Env vars:**
```bash
export ZOHO_EMAIL_1="transport.work@zohomail.com"
export ZOHO_PASS_1="..."
export ZOHO_EMAIL_2="workers.europe@zohomail.eu"
export ZOHO_PASS_2="..."
export ZOHO_DAILY_LIMIT=50  # starting limit
```

---

## MX Verification + Bounce Analysis

### Pre-Send MX Check

**When:** Corporate domain (not gmail, yahoo, outlook, hotmail, icloud, live)

**How:**
```python
if not is_consumer(email):
    valid, reason = verify_mx(email)
    if not valid:
        log_dnc(email, reason)  # skip send
        continue
```

**Skip:** Consumer domains (Gmail, Yahoo, etc.) skip MX check to save time

### Bounce Classification

| Type | Cause | Recovery | DNC Action |
|------|-------|----------|-----------|
| **Hard bounce** | Invalid address, account closed | No retry | Add to DNC forever |
| **Soft bounce** | Mailbox full, greylisting | Retry 2-3×, then DNC | Add to DNC if persists |
| **Complaint** | User marked as spam (ISP feedback loop) | No send, suppress | Add to DNC + FBL review |
| **Block** | Sender reputation issue | Rotate sender | Investigate Brevo logs |

**Bounce tracking (send_log table):**
```sql
SELECT sector, sent, bounced, bounced::float / sent AS bounce_rate
FROM send_log
WHERE sector = '...'
ORDER BY date DESC
LIMIT 10;
```

---

## Postfix + DKIM Configuration

### DKIM Selector + Keys

| Domain | Key | Selector | TXT Record | Status |
|--------|-----|----------|-----------|--------|
| factoryjobs.eu | `/etc/rspamd/dkim/factoryjobs.eu.key` | `mail2026` | `dig mail2026._domainkey.factoryjobs.eu` | ✓ Live |
| careworkers.eu | ✓ | `mail2026` | ✓ | ✓ Live |
| ... (25 more) | ✓ | `mail2026` | ✓ | ✓ Live |
| cifn.info | ✗ | — | MISSING | ✗ Pending (grem01.gazduire.ro cPanel `uamkawbd`) |

### When to Enable Postfix Signing

**Enable `use_postfix: true` if:**
- Domain is sensitive (legal, finance, gov, medical)
- Campaign targets corporate (non-Gmail) domains
- Sender reputation is critical

**Example:**
```python
{
    "EU_LEGAL_CONTRACTS": {
        "sender": "contracts@careworkers.eu",
        "use_postfix": True,  # ← DKIM signs all mail
        "sender_type": "brevo",  # ← but still routes via Brevo SMTP
    }
}
```

**Flow:** Campaign → Postfix:25 → rspamd (sign) → Brevo SMTP:587 → recipient

---

## Rate Limiting + Delays

### Send Delays (Hardcoded in send_campaign.py)

| Stage | Delay | Reason |
|-------|-------|--------|
| Per-send random | 180–240s | Brevo + email provider throttle |
| Between batches | 30–60s | Rate limit recovery |
| Mid-batch check | Every 10 sends | Monitor bounce, adjust on-the-fly |

### Request Rate (API)

| Provider | Limit | Enforcement |
|----------|-------|------------|
| Brevo API | 5 req/s (per key) | Backoff + retry in send_brevo() |
| Gmail SMTP | 150 msg/hr (per sender) | Per-sender quota tracking |
| Zoho SMTP | 50 msg/hr (initial) | ZOHO_DAILY_LIMIT env var |

---

## Business Hours + Schedule

### Sector-Level Business Hours

```python
{
    "HARGHITA_PHASE_3": {
        "business_hours": "08:00-18:00",  # only send in this window
        "timezone": "Europe/Bucharest",    # local time
    },
    "EU_PROCUREMENT": {
        "business_hours": "08:00-17:00",   # EU-wide standard
    },
}
```

**Check in code:**
```python
if not check_business_hours(cfg, dry_run=False):
    logger.info(f"Outside business hours, skipping {sector}")
    return 0
```

### Cron Schedule (Examples)

```bash
# ANOFM 3×/day @ 08:40, 12:40, 16:40 (after scraper finishes at :30)
40 8,12,16 * * * /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/send_campaign.py ANOFM --limit 290

# HARGHITA Phase 3 @ 10:00 daily (30/day)
0 10 * * * /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/send_campaign.py HARGHITA_PHASE_3 --limit 30

# Zoho warmup @ 00:00 daily (+5/day)
0 0 * * * /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/zoho_warmup.py
```

---

## Rollback + State Management

### State File Location

```bash
/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/state/{sector}.json
```

**Example (DELIVERY_RO_2026):**
```json
{
    "daily_count": 75,
    "total_sent": 562,
    "last_run": "2026-04-27T16:30:00",
    "last_reset": "2026-04-27",
    "sender_blocked_until": null,
    "exhausted_until": null,
    "gmail_daily": {"gmail1@...": 50},
    "brevo_gmail_daily": 0,
    "zoho_daily": 0,
    "transient_retries": {}
}
```

### Manual State Reset

```bash
# Reset single sector
rm /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/state/delivery_ro_2026.json

# Reset all
rm /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/state/*.json
```

---

## Monitoring Commands

```bash
# Bounce rate (manual check)
ssh tudor@192.168.100.21
psql -h 127.0.0.1 -U tudor -d interjob_master -c "
  SELECT sector, sent, bounced, ROUND(100.0 * bounced / sent, 1) AS bounce_pct
  FROM send_log
  WHERE date = CURRENT_DATE
  ORDER BY bounce_pct DESC;
"

# Latest send logs
tail -50 /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/logs/*

# Gmail quota status
grep -h "Gmail\|gmail" /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/logs/* | tail -20

# Postfix status
postfix status || echo "Postfix not running"

# Brevo API key validity (spot-check)
curl -s https://api.brevo.com/v3/account -H "api-key: $BREVO_API_KEY" | jq '.plan'
```

---

## Emergency Procedures

### Halt All Campaigns (Immediate)

```bash
ssh tudor@192.168.100.21
rm /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/state/*.json  # resets all sectors
pkill -f send_campaign.py  # kill running processes
```

### Investigate High Bounce Rate

1. Check send_log for last 24h:
```sql
SELECT sector, COUNT(*), bounced, ROUND(100.0 * bounced / COUNT(*), 1) AS pct
FROM send_log
WHERE date >= NOW() - '1 day'::interval
GROUP BY sector, bounced
ORDER BY pct DESC;
```

2. Review sector config:
   - Invalid email format? → Run dedup script
   - Scraper bug? → Check source data
   - Brevo issue? → Check API response codes in logs

3. Rotate sender (if reputation issue):
```python
cfg["sender"] = "alternate@domain.com"
```

4. Resume after fix:
```bash
python3 send_campaign.py SECTOR --limit 10  # test 10 sends
# if OK:
python3 send_campaign.py SECTOR --limit 100  # resume normal
```

---

## Revision History

- **2026-04-27** — Initial consolidation from campaigns.md + send_config.py
- See `git log .claude/email-limits.md` for all changes
