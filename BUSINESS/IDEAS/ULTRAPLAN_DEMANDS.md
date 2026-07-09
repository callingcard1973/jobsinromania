# ULTRAPLAN — Demands Document
**Date:** 2026-04-10
**Author:** Tudor + Claude
**Objective:** Generate revenue from existing assets within 30 days

---

## SITUATION (What We Have)

### Data Assets (raspibig PostgreSQL)
- **17.7M companies** across 42 countries (opendata)
- **81 GB master companies table** (interjob_master)
- **15,932 EU funds project contacts** with email (european_funds.proiecte)
- **9,227 private EU beneficiaries** with email (european_funds.beneficiari_privati)
- **222,660 insolvency records** (opendata.faliment)
- **1.24M PNRR payment records** (pnrr.plati_pnrr — municipalities, not directly usable)
- **5.1M tenders** with pricing
- **106K recruitment agencies** with email

### Infrastructure
- **6,300 emails/day** capacity (Brevo 2,984 + Mailrelay 2,666 + Gmail 400 + Zoho 100 + Resend 100 + A2 50)
- **83 campaign configs** in orchestrator (most idle)
- **Actual send rate: ~400/day = 6% utilization**
- **28 domains** on A2 Hosting
- **56 IMAP accounts** monitored by poller
- **Automated pipeline**: poller (15min) → classifier → orders.csv → Telegram approval → email forward

### Responses Already Captured (as of 2026-04-10)
- **15 business leads** in orders.csv (April 7-9)
- **2 Norwegian construction companies** interested (Unik Byggmester, Larsen Maskin)
- **3 Asian manpower agencies** offering worker supply (Sri Lanka, Nepal x2)
- **4 Romanian companies** with actual worker ORDERS (EXPRESS AUTO FAI 4 workers, P&M CONSTRUCT 1, Corneliu Balasanu carpenters, AgroConcept technicians)
- **1 recruitment company** (DAROM) requesting commercial offer
- **1 international partner** (Binny Mobility, Sweden/Denmark — fleet operations)
- **1 steel company** (REIMERS STEEL) offering detachment partnership

### Problems Found & Fixed (2026-04-10)
- Telegram order forwarding was blocked (Markdown bug on underscore in email) — **FIXED**
- 10 IMAP accounts had wrong passwords in governor/JSON — **FIXED** (8 of 10)
- CPU health alerts spamming Telegram every 5 min — **FIXED** (threshold 16→32)
- Unified .env created at `/opt/ACTIVE/EMAIL/.env.unified`

---

## DEMANDS (What Must Happen)

### D1. Process the 15 existing leads (Day 0)
**Owner:** Tudor (manual)
- Open Telegram @raspi_n8n_alerts_bot
- APPROVE real orders (EXPRESS AUTO FAI, P&M CONSTRUCT, Balasanu, AgroConcept)
- Reply to DAROM with commercial offer (leads subscription: EUR 200-500/month)
- Connect Nepal/Sri Lanka agencies with Norway companies (both responded)
- Reply to REIMERS STEEL about detachment partnership terms
- **Expected:** 2-3 immediate placements, 1 partnership deal

### D2. Activate the 106K recruitment agencies campaign (Days 1-3)
**Owner:** Claude (code) + Tudor (template approval)
- Extract agencies with email from interjob_master
- Template: "We source RO/EE workers. You place. We split fee. Zero upfront cost."
- Add as campaign config in orchestrator
- Daily limit: 500/day (Mailrelay sender)
- **Expected:** 2-5% response rate = 2,100-5,300 replies over 30 days
- **Revenue:** EUR 500-5,000 per placement via agency network

### D3. AgroEvolution premium listings (Days 3-7)
**Owner:** Claude (code)
- Add "Promoveaza-ti produsele — TOP listing EUR 10/luna" to agroevolution.com map
- Create Stripe/payment link for EUR 10/month subscription
- Email 9,469 MADR producers: "Esti pe harta noastra. Vrei sa apari in TOP?"
- Campaign via orchestrator (Brevo sender, 300/day)
- **Expected:** 2% conversion = 190 subscribers = EUR 1,900/month recurring
- **Revenue:** EUR 1,900/month, starts Week 2

### D4. Insolvency alerts subscription (Days 7-14)
**Owner:** Claude (code)
- Cron job querying 222,660 insolvency records for new entries
- Landing page on cifn.eu with Stripe payment link
- Email 17K accountants + 1,850 auditors (extract from interjob_master by CAEN)
- EUR 19/month subscription for daily insolvency alerts
- **Expected:** 100-200 subscribers in 60 days
- **Revenue:** EUR 1,900-3,800/month recurring, zero competition in Romania

### D5. Sell data packages (Days 3-7)
**Owner:** Tudor (account setup) + Claude (CSV export)
- Create Gumroad or LemonSqueezy account
- Export 5 CSV packages from PostgreSQL:
  1. RO Construction Companies (117K) — EUR 499
  2. EU Procurement Winners (TED awards) — EUR 299
  3. Norway Companies (155K) — EUR 999
  4. RO Food Industry (69K enriched) — EUR 499
  5. EU Recruitment Agencies (106K) — EUR 4,999
- **Expected:** 3-10 sales in 30 days
- **Revenue:** EUR 900-15,000

### D6. Scale email capacity from 6% to 50% (Days 1-7)
**Owner:** Claude (config)
- Unpause Norway campaign (335K emails, only 972 sent)
- Enable all Bulgaria configs (79K+ contacts)
- Enable Romania sector campaigns (13 configs idle)
- Increase TED EU daily limits (10 countries configured)
- Enable A1 Transport campaigns (8 countries)
- **Target:** 3,000+ emails/day (from current 400)
- **Revenue:** More campaigns = more responses = more placements

### D7. Delecroix agricultural equipment commissions (Days 7-14)
**Owner:** Tudor (relationship)
- Get price list from Toubeaux (+33 6 08 09 97 20)
- Coordinate with Agri Alianta (0755 405 555, already contracted)
- Email MADR producers from AgroEvolution DB with Delecroix catalog
- **Revenue:** EUR 1,500/unit x 5-35 units/year = EUR 7,500-52,500/year

### D8. "Leads as a service" to responding agencies (Days 14-30)
**Owner:** Tudor (sales) + Claude (automation)
- Every agency that responds to D2 becomes a potential subscriber
- EUR 200/month = 20 verified employer leads
- EUR 500/month = 50 leads + sector filtering
- Pipeline already generates leads — just resell to multiple agencies
- **Revenue:** EUR 2,000-10,000/month recurring at 10-50 subscribers

---

## REVENUE PROJECTIONS

| Demand | Week 1 | Week 2 | Week 3 | Week 4 | Month 2+ |
|--------|--------|--------|--------|--------|----------|
| D1. Existing leads | EUR 0-2K | EUR 2-5K | — | — | �� |
| D2. 106K agencies | — | replies start | EUR 1-3K | EUR 2-5K | EUR 5-15K/mo |
| D3. AgroEvolution | — | EUR 200 | EUR 500 | EUR 1K | EUR 1.9K/mo |
| D4. Insolvency alerts | — | — | launch | EUR 400 | EUR 1.9-3.8K/mo |
| D5. Data packages | EUR 300 | EUR 500 | EUR 500 | EUR 500 | EUR 1-3K/mo |
| D6. Scale campaigns | more leads flowing into D1/D2/D8 pipeline |||
| D7. Delecroix | — | price list | outreach | — | EUR 600-4K/mo |
| D8. Leads service | — | — | — | EUR 400 | EUR 2-10K/mo |
| **TOTAL** | **EUR 300-2K** | **EUR 700-5.5K** | **EUR 2-4K** | **EUR 4-7K** | **EUR 13-38K/mo** |

---

## DEPENDENCIES

```
D1 (process leads) → no dependency, DO NOW
D6 (scale capacity) → no dependency, DO NOW
D2 (agencies) → needs template approval from Tudor
D5 (data packages) → needs Gumroad/LemonSqueezy account (Tudor)
D3 (AgroEvolution) → needs Stripe account (Tudor)
D4 (insolvency) → needs D3 Stripe + landing page
D7 (Delecroix) → needs Tudor to call Toubeaux
D8 (leads service) → needs D2 responses first
```

## BLOCKERS (Tudor Must Do, Cannot Be Automated)

1. **Approve 15 Telegram orders** — @raspi_n8n_alerts_bot, tap APROBA
2. **Create Stripe account** — for D3, D4 payments
3. **Create Gumroad/LemonSqueezy account** — for D5 data sales
4. **Call Toubeaux** — +33 6 08 09 97 20 for Delecroix price list
5. **Approve campaign templates** — before D2, D3 go live
6. **Reply to DAROM** — commercial offer for leads subscription

---

## SUCCESS CRITERIA

- **Week 1:** First EUR earned (data sale or placement deposit)
- **Week 2:** 3+ campaigns running at 500+/day each
- **Week 4:** EUR 5K+ total revenue, 2+ recurring subscriptions
- **Month 2:** EUR 10K+/month, agencies network active, leads service live
- **Month 3:** EUR 15-25K/month steady state
