# campaigns.md — Email Stack + Active Campaigns

## Email Sending Stack

| Provider | Capacity/day | Method | Notes |
|----------|-------------|--------|-------|
| Brevo API | 270/sender | Direct API | 13 sender accounts |
| Postfix+DKIM | unlimited | Postfix→Brevo SMTP | DKIM-signs all mail |
| Gmail SMTP | 235 | SMTP TLS | fallback |
| Zoho #1 | 50→250 warmup | smtp.zoho.com:587 | transport.work@zohomail.com, pw: JKkdxGS3szvC |
| Zoho #2 | 50→250 warmup | smtp.zoho.eu:587 | workers.europe@zohomail.eu, pw: Mu59U3Lfa3Dw |
| Mailrelay | 2,666/day | API | expatsinromania.org, 80K/mo |

## Postfix + DKIM (raspibig, LIVE)

Architecture: Campaign → Postfix :25 → rspamd milter :11332 (DKIM sign) → Brevo SMTP relay :587

- rspamd 4.0.1: `/etc/rspamd/local.d/dkim_signing.conf`, selector `mail2026`, keys in `/etc/rspamd/dkim/$domain.key`
- Postfix: satellite relay, `relayhost=[smtp-relay.brevo.com]:587`, loopback-only
- sasl_passwd: per-sender Brevo creds for 9 senders
- `"use_postfix": true` in sector config → routes via Postfix+DKIM
- 27/28 domains have `mail2026._domainkey.{domain}` DNS TXT
- cifn.info: DNS record needed on grem01.gazduire.ro (cPanel `uamkawbd`)

Key files:
```
/etc/rspamd/dkim/                        # 28 x {domain}.key + {domain}.txt
/etc/postfix/sasl_passwd                 # per-sender Brevo creds (postmap'd)
/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/send_providers.py   # send_postfix()
/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/send_campaign.py    # use_postfix branch ~line 158
```

## Active Campaigns (2026-04-18)

### DELIVERY_RO_2026
- 562 RO delivery/transport companies, 100/day, sender: office@mivromania.info
- Reply-To: manpower.dristor@gmail.com | Log: `/opt/ACTIVE/EMAIL/CAMPAIGNS/delivery_brevo.log`

### HARGHITA (all 3 phases parallel, no approval gates)
- Phase 1: 6 construction companies, 10/day
- Phase 2: 18 mixed (manufacturing/hospitality/logistics), 20/day
- Phase 3: 770 all Harghita companies, 100/day, rotating templates → €70-100K/mo projected

### Support Campaigns (Continuous)
- FI_TED_CONSTRUCTION: 80/day
- ANOFM Orchestrator: 7 sectors (orchestrator.py)
- NECALIFICATI: blue-collar placements

### ANOFM — 16 sectors LIVE (fixed 2026-04-18)
- Root cause was SENDER_BLOCKED permanent stop (now patched, 20 stop-condition fixes)
- 8,546 new contacts added, daily_digest cron 17:30
- 13 Brevo senders, 2,249/day capacity

### TUDOR_ANOFM Campaign (raspibig, LIVE 2026-04-22)
Dir: `/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_TUDOR_MIGRATED_TO_RASPI/`
DB: `tudor.db` (SQLite)

**Pipeline automat:**
- 08:30, 12:30, 16:30 → `daily_scrape.sh` (Docker ANOFM scraper)
- 08:40, 12:40, 16:40 → `anofm_feed.py` → importă CSV → pornește sender loop

**Reguli trimitere:**
- **LIFO** — contacte noi (id DESC) trimise primele
- **Corporate first** — domenii non-gmail/yahoo prioritizate în fiecare batch
- **Delay mereu** — 180-240s între orice trimitere (Brevo și Gmail)
- **MX verify** înainte de fiecare send corporate (skip consumer: gmail/yahoo/hotmail/outlook/live/icloud)
- **Bounce check Brevo** la fiecare 10 trimiteri — oprire dacă > 30%
- **Sectoare excluse (hold forever):** comert, horeca, vanzari, it, paza
- **Limite zilnice:** Brevo 290, Gmail 550, A2 30

**Sender args:** `--limit 9999 --brevo-limit 290 --gmail-per-run 1 --a2-limit 5 --force`

**Lockfile:** `.tudor_sender.lock` — previne instanțe duplicate

## Campaign Rules

- Bounce threshold: 30% — check before EVERY send (3 locations in send_campaign.py)
- Test sends pollute Brevo stats — never test on live senders
- One sender per campaign
- All apply links → interjob.ro/apply.html
- GDPR: HMAC-signed unsubscribe links in ALL campaigns, privacy.html LIVE on interjob.ro
- Never auto-publish articles to WordPress — draft only

## Zoho Warmup (+5/day automatic)

```bash
/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/zoho_warmup_cron.sh   # run daily at midnight
python3 /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/zoho_warmup.py # status
```

## Deploy

```bash
cd /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED && python3 send_campaign.py
```
