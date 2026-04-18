# EMAIL - Unified Email Pipeline + Campaign Management

## Universal Rules
1. **Corporate emails → Brevo/A2 SMTP only. Gmail → personal domains only.**
2. **Gmail max 40/day per account.** No exceptions.
3. **Brevo and A2 SMTP can send simultaneously** on the same campaign (different senders).
4. **A2 SMTP warmup**: start at 50/day per domain, increase gradually.
5. **Never start sending without explicit user approval.**
6. **fruitnature4@gmail.com**: DO NOT USE for any sending.
7. **Sector campaigns have priority over ANOFM.** ANOFM only sends to unreserved emails.
8. **cifn.info**: expired domain, removed from everything.
9. **Virgil ≠ Lucian**: two different people at BP&P Partners.
10. **Business hours**: 8-18 Mon-Fri, gentle delays 360-600s on all campaigns.

## Pipeline
```
32 IMAP accounts → sklearn classifier → route:
  Scans INBOX + Spam/Junk folder (readonly, never marks as read)
  campaign_reply/inquiry → LLM extract → orders.csv
  application (personal) → applicants.csv
  bounce (personal domain) → DNC + delete from inbox (INBOX only)
  bounce (corporate, blocked) → delete bounce only, keep for retry
  handover → handovers.csv + new contact
  partner reply → contacts.csv
  unsubscribe → DNC
Spam folder auto-detected per provider:
  Gmail=[Gmail]/Spam | A2=INBOX.SPAM | Yahoo=Bulk | Zoho=Spam
```

## Campaign Structure
- Romania: `/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/` (configs/ + templates/)
- EU TED: `/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/` (*_ted_construction.json)
- All symlinked to orchestrator via `UNIFIED/configs/`

## ANOFM (14 sectors, 2,479/day enabled)
Config: `ROMANIA/configs/anofm.json` | DB: `anofm.jobs` | 62,782 sendable | ~25 days
- Brevo corporate (9 senders): 2,319/day
- Gmail personal (4 × 40): 160/day
- Zoho yahoo (disabled): 30/day when enabled

## EU Proiecte Campaign — DISABLED, placeholder template
- DB: `european_funds.proiecte` (15,932 unique emails)
- Config: `ROMANIA/configs/eu_proiecte.json`, interjob.ro 50/day
- Template: `ROMANIA/templates/eu_proiecte/template1.txt` (replace via dashboard)
- Variables: {beneficiar}, {contact}, {judet}, {localitate}
- Rolling: scraper feeds new projects → auto-sent
- 15,932 emails reserved in ANOFM. ANOFM remaining: 52,893

## Active Campaigns (8 Apr 2026)
| Campaign | Sender | Method | /day | Status |
|----------|--------|--------|------|--------|
| TED 10 countries CORP | buildjobs.eu | Brevo | 27 each (270 total) | sending |
| TED 10 countries PERS | 10 Gmail | Gmail | 40 each (400 total) | sending |
| RO Curierat CORP | horecaworkers2026.com | A2 SMTP | 50 (warmup) | sending |
| RO Construction | buildjobs + manpowersearch | Brevo+Gmail | 57 | via orchestrator |
| ANOFM | 14 senders | Brevo+Gmail | 2,479 | **awaiting start** |
| RO Agricultura | agroevolution.com + fruitnature4 | Brevo | 290 | configured |
| RO Confectii | cumparlegume.com | Brevo | 290 | configured |
| RO Lemn | agroevolution.com | Brevo | 290 | configured |
| RO Horeca | careworkers.eu | Brevo | 290 | configured |

## Sender Allocation
### Brevo API (corporate only, 300/day each)
**10 WORKING** (tested 2026-04-09, total ~2,984/day):
| Domain | API Key | /day | Status |
|--------|---------|------|--------|
| buildjobs.eu | BREVO_BUILDJOBS | 300 | OK |
| bppltd.co.uk | BREVO_BPPLTD | 284 | OK |
| mivromania.com | BREVO_MIVROMANIA | 300 | OK |
| mivromania.online | BREVO_MIVROMANIA (same key) | 300 | OK |
| mivromania.info | BREVO_MIVROMANIA (same key) | 300 | OK (49.8% bounce risk) |
| seicarescu.com | BREVO_SEICARESCU | 300 | OK |
| agroevolution.com | BREVO_AGROEVOLUTION | 300 | OK |
| cumparlegume.com | BREVO_CUMPARLEGUME | 300 | OK |
| careworkers.eu | BREVO_CAREWORKERS | 300 | OK |
| horecaworkers2026.eu | BREVO_HORECAWORKERS2026_EU | 300 | OK |

**6 DEAD (401 — need key regeneration):**
interjob.ro, warehouseworkers.eu, expatsinromania.org, factoryjobs.eu, nepalezi.com, electricjobs.eu, horecaworkers2026.com

**Note:** mivromania.online + mivromania.info share the BREVO_MIVROMANIA key (same Brevo account, 3 senders on 1 key). SMTP key `bskcH7QxDYmRB8o` is dead — use API only.

### Resend API (interjob.ro only, 100/day)
- Key: working (tested 2026-04-09)
- Sender: `noreply@interjob.ro` (1 domain on free tier)

### Mailrelay API (expatsinromania.org, 80K/month)
- API key working, SMTP password stale
- Account under review after first test send (clears 24-48h)

### Mailjet API — BLOCKED (account suspended)
### Elastic Email — test-only (needs paid plan)

### A2 SMTP (corporate, warmup 50/day)
| Domain | Campaign | /day |
|--------|----------|------|
| horecaworkers2026.com | RO Curierat CORPORATE | 50 |
| 21 other domains | available (DKIM valid, warmup needed) |

### Gmail (personal only, max 40/day each)
| Account | Campaigns | /day |
|---------|-----------|------|
| manpowersearchromania | ANOFM + RO Construction | 40 |
| pamintstrabun | ANOFM + TED FI | 40 |
| casafaurbucuresti | ANOFM + TED AT | 40 |
| elena.manpower.dristor | ANOFM + TED DE | 40 |
| cumparlegume | TED FR | 40 |
| fructexportromania | TED ES | 40 |
| carteledeapel | TED IT | 40 |
| vegetablesbucharest | TED PL | 40 |
| expatsinromania | TED SE | 40 |
| icralbucuresti | TED CZ | 40 |
| manpowerdristor | **LOCKED** (needs new app password) |
| fruitnature4 | **DO NOT USE** |

### Zoho SMTP
| Account | Campaign | /day |
|---------|----------|------|
| transport.work@zohomail.com | PROFESIONISTI + ANOFM Yahoo (disabled) | 30 |
| workers.europe@zohomail.eu | warmup only | 5 (+5/day) |

## Automation
- Pipeline: cron 2h on raspibig + Node-RED (scans INBOX + spam folders, readonly mode)
- Orchestrator: auto-starts campaigns at business hours
- ROMANIA launcher: cron 8:07 AM Mon-Fri
- Zoho warmup: cron 9:23 daily
- ANOFM import: cron 2x/day
- Brevo cleanup: `/opt/ACTIVE/INFRA/SKILLS/clean_all_brevo.py`
- DKIM setup: `/opt/ACTIVE/INFRA/SKILLS/a2_dkim_setup.py`
- Verification: `/opt/ACTIVE/INFRA/SKILLS/verify_all_campaigns.py`

## GDPR Compliance (2026-04-14) — ALL CAMPAIGNS
- **Privacy policy:** https://interjob.ro/privacy.html (Romanian, Art 6(1)(f) legitimate interest)
- **Unsubscribe:** https://interjob.ro/unsubscribe.php (HMAC-signed one-click, secret: interjob_unsub_2026_xK9m)
- **send_utils.py:** `{unsubscribe_url}` (now HMAC-signed), `{privacy_url}`, `{gdpr_footer_ro}`, `{gdpr_footer_en}`
- **Unsub sync:** cron :30 every hour, `/opt/ACTIVE/EMAIL/PROCESSORS/sync_unsubscribes.py` (A2 CSV → DNC tables)
- **Mailrelay:** DISABLED on recruitment_agencies + eu_projects_info (2026-04-14)

## DKIM/SPF Status
- 22 A2 domains: all DKIM VALID
- 5 domains SPF propagating (horecaworkers, meatworkers, mechanicjobs, farmworkers, mivromania.online)
- cifn.info: removed (expired)
