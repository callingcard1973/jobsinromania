# Session Handoff - 7-8 April 2026

## What Was Built (2 days)

### 1. Unified Email Pipeline
- `email_pipeline.py` (252 lines) - scans 30 IMAP accounts, classifies with sklearn, routes to orders/applicants/contacts/bounces/handovers
- `email_accounts.py` (108 lines) - 30 accounts: 15 A2 + 11 Gmail + 2 Yahoo + 2 Zoho
- Replaces 6 old scripts (reply_detector, reply_classifier, email_organizer, gmail_reply_detector, response_contacts, collect_orders)
- Cron 2h on raspibig + Node-RED "Email Pipeline" tab
- Outputs: orders.csv, applicants.csv, contacts.csv, handovers.csv, bounces.log

### 2. Campaign Dashboard
- `https://192.168.100.21/campaigns/` (Caddy HTTPS reverse proxy → Flask port 8097)
- 6 files: dashboard_app, dashboard_shared, dashboard_campaigns, dashboard_upload, dashboard_senders, dashboard_stats
- Features: campaign CRUD, CSV upload, template viewer/editor, sender inventory with utilization, stats from all DBs
- systemd service: `campaign-dashboard.service` (auto-restart)

### 3. Campaign Infrastructure
- 55 campaign configs across Romania + EU
- 22 A2 domains with DKIM VALID
- All templates personalized + export/Franta/detasare pitch
- All campaigns verified: 0 issues
- Corporate = Brevo/A2 only, Gmail max 40/day = personal only

### 4. ANOFM Campaign (NOT STARTED - needs approval)
- Config: `ROMANIA/configs/anofm.json`
- DB: `anofm.jobs` - 52,893 remaining (after sector + EU reservations)
- 13 sectors enabled: 9 Brevo corporate (2,319/day) + 4 Gmail personal (160/day) = 2,479/day
- Randomize fix applied (was alphabetical)
- ~21 days to complete

### 5. EU Proiecte Campaign (NOT STARTED - needs template)
- Config: `ROMANIA/configs/eu_proiecte.json`
- DB: `european_funds.proiecte` - 15,932 unique emails
- Placeholder template - user writes via dashboard
- Rolling: scraper feeds new projects → auto-sent

### 6. Sector Campaigns
| Campaign | Contacts | Sender CORPORATE | Status |
|----------|----------|-----------------|--------|
| RO Curierat | 2,751 | horecaworkers2026.com (A2) | SENDING (47 today) |
| RO Construction | 4,058 | buildjobs.eu (Brevo) | STARTED |
| RO Agricultura | 6,558 | agroevolution.com | configured, not started |
| RO Confectii | 667 | cumparlegume.com (disabled) | needs new sender |
| RO Lemn | 468 | farmworkers.eu | configured, not started |
| RO Horeca | 9,603 | careworkers.eu (disabled) | needs reactivation |

### 7. TED EU (10 countries)
- All CORPORATE: buildjobs.eu 27/day each (disabled by user)
- All PERSONAL: 10 Gmail 40/day each (some still sending)

### 8. Data Cleanup Done
- HARGHITA CSVs fixed (phone prefix + .co → .com, 1,033 emails fixed)
- All Brevo keys cleaned (926 hard bounces unblocked, 1,058 to DNC)
- Bounce rate pre-check changed to 7-day window
- 5 old overlapping services archived (email-classifier, reply-classifier, llm-email-processor, unified-email-processor)
- Raspi ANOFM campaigns disabled (consolidated to raspibig)

### 9. 10 Automation Scripts (deployed, NOT on cron - needs approval)
telegram_comanda_alert, auto_reply_comanda, retrigger_handover, campaign_dashboard, enrich_bounced_corporate, a2_warmup, dedup_cross_campaigns, campaign_analytics, anofm_fresh_import, orders_to_sheet

### 10. Zoho Warmup
- workers.europe@zohomail.eu: warmup 5/day +5/day (cron 9:23 daily)
- transport.work@zohomail.com: 30/day (PROFESIONISTI)

## Credentials Quick Reference

### A2 Hosting
- cPanel: loaiidil @ nl1-cl8-ats1.a2hosting.com:2083
- API token: 9QEJ4ANOPHXZ0YE34NEWDAKA1UXZPKNX
- Email password (all domains): pADVouA01bYUkfpE

### PostgreSQL (raspibig)
- user: tudor, password: tudor
- DBs: interjob_master, romania_emails, anofm, european_funds, email_sender

### Brevo API Keys (in /opt/ACTIVE/EMAIL/CAMPAIGNS/.env)
- 20 keys: buildjobs, factoryjobs, warehouseworkers, interjob, mivromania, mivromania_online, careworkers, nepalezi, expatsinromania, horecaworkers2026_eu, horecaworkers2026_com, electricjobs, meatworkers, cumparlegume, agroevolution, seicarescu, bppltd, farmworkers, mechanicjobs, horecaworkers

### Gmail (app passwords in /opt/EMAIL/.env)
- manpower.dristor: tbdh pycf vbxo eung
- manpowerdristor: LOCKED (needs new app password!)
- elena.manpower.dristor: wmfnpikkcierkmrq
- expatsinromania: hxdn mukn jloe shkk
- cumparlegume: iggy urti wmze znqo
- casafaurbucuresti: zlfb mbqf xiki mcbw
- fruitnature4: mosv ghia ptwc xasr (DO NOT USE for sending)
- vegetablesbucharest: filr iqdc rklp cbyu
- fructexportromania: wqkp hejw nooo ztpv
- icralbucuresti: lqni pfzf ovyv otdu
- carteledeapel: dqzw ensj tmlb jrgj
- manpowersearchromania: xibc xpuz qxfm caei (verify - may be different env var)

### Zoho
- transport.work@zohomail.com: JKkdxGS3szvC (smtp.zoho.com:587)
- workers.europe@zohomail.eu: Mu59U3Lfa3Dw (smtp.zoho.eu:587)

### Telegram Bot
- Token: 8546618948:AAG0neoQA-kNq0M2GrZX7J-dGXNvEJEOK9w

### Alibaba Cloud DirectMail
- App ID: 4195410055503316452
- Verified: interjob.ro, cifn.eu

## Key Rules (in memory)
1. Corporate emails → Brevo/A2 only. Gmail → personal only.
2. Gmail max 40/day per account.
3. Nothing starts without explicit user approval.
4. fruitnature4@gmail.com: DO NOT USE for sending.
5. Sector campaigns have priority over ANOFM.
6. Virgil ≠ Lucian (different people at BP&P).
7. Max 250 lines per script.
8. cifn.info: expired domain, removed.
9. Business hours 8-18 Mon-Fri, gentle delays 360-600s.
10. All campaigns are ours (not just Romania).

## Pending Actions
1. START ANOFM (user approval)
2. START remaining RO campaigns (user approval)
3. Write EU_PROIECTE template (user does via dashboard)
4. Fix manpowerdristor app password (browser login)
5. Enable 10 automation crons (user approval)
6. Create more Zoho accounts (browser, user does)
7. Telegram COMANDA notifications (script ready, not activated)
8. A2 SMTP warmup for remaining 21 domains
