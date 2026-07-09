# Agent Inventory — 14 Autonomous Agents on Raspibig (2026-04-13)

> Zero tokens. Zero cost. 24/7. All report to Node-RED POST /enrichment-status.

## AGENTS LIST

| # | Agent | File | Cron | What |
|---|-------|------|------|------|
| 1 | Email Enrichment | email_enrichment_pipeline.py | 21:00-02:00 (5 jobs) | Scrape website→email, update DB |
| 3 | Tourism Collector | agent_tourism_collector.py | Mon 06:00 | Download SITUR, INFOTRAV, ATOL, Wikidata, OSM |
| 4 | Campaign Monitor | agent_campaign_launcher.py | L-V 09,13,17 | Status campaigns + master_emails |
| 5 | Cross-DB Enrichment | agent_cross_db_enrichment.py | Sun 20:00 | Copy emails between tables, zero HTTP |
| 6 | MX Validator | agent_mx_validator.py | Sat 18:00 | Validate email domains (50K/run) |
| 12 | ANAF CUI Lookup | agent_anaf_enrichment.py | L-V 14:00 | Romanian company data from ANAF API |
| 14 | Duplicate Detector | agent_duplicate_detector.py | Wed 19:00 | Match companies across tables, merge emails |
| 17 | TED Enricher | agent_ted_enricher.py | Daily 09:00 | TED winners → master_emails → all tables |
| 20 | Email Guesser | agent_email_guesser.py | Daily 19:00 | info@domain + MX verify = email without scraping |
| 27+30 | WHOIS/SOA Email | agent_whois_email.py | Daily 03:00 | Admin email from WHOIS + DNS SOA records |
| 28+29 | Sitemap Miner | agent_sitemap_miner.py | Daily 04:00 | Sitemap.xml → /contact pages → scrape emails |
| 34+36-38 | Warmth Scorer | agent_warmth_scorer.py | Daily 05:00 | Score leads, tag countries, audit quality |
| 32+33 | Registry Sync | agent_company_registry_sync.py | Tue 05:00 | Download Norway, Latvia, UK, EU registries |
| 35+22+31 | Auto Campaign | agent_auto_campaign_builder.py | Daily 07:00 | Auto-prepare campaigns when >500 emails/country |

## 24-HOUR SCHEDULE

```
03:00  WHOIS/SOA (5K domains)
04:00  Sitemap Miner (3K sites)
05:00  Warmth Scorer + Quality Auditor
05:00  Registry Sync (Tue only)
06:00  Tourism Collector (Mon only)
07:00  Auto Campaign Builder
09:00  TED Enricher + Campaign Monitor
13:00  Campaign Monitor
14:00  ANAF CUI (weekdays)
17:00  Campaign Monitor
18:00  MX Validator (Sat only)
19:00  Email Guesser + Duplicate Detector (Wed)
20:00  Cross-DB Enrichment (Sun)
21:00  Enrichment — Romania
22:00  Enrichment — Nordics
23:00  Enrichment — Central+South EU
00:30  Enrichment — Big tables
02:00  Enrichment — Bulgaria
```

## ALL FILES ON RASPIBIG

```
/opt/ACTIVE/FLIGHTS/
├── email_enrichment_pipeline.py    (Agent 1)
├── agent_tourism_collector.py      (Agent 3)
├── agent_campaign_launcher.py      (Agent 4)
├── agent_cross_db_enrichment.py    (Agent 5)
├── agent_mx_validator.py           (Agent 6)
├── agent_anaf_enrichment.py        (Agent 12)
├── agent_duplicate_detector.py     (Agent 14)
├── agent_ted_enricher.py           (Agent 17)
├── agent_email_guesser.py          (Agent 20)
├── agent_whois_email.py            (Agent 27+30)
├── agent_sitemap_miner.py          (Agent 28+29)
├── agent_warmth_scorer.py          (Agent 34+36-38)
├── agent_company_registry_sync.py  (Agent 32+33)
├── agent_auto_campaign_builder.py  (Agent 35+22+31)
├── scrape_emails_from_websites.py  (universal email scraper)
├── scrape_agencies.py              (Romanian agency scraper)
├── price_monitor.py                (flight price monitor)
├── enrichment/                     (state.json, batch CSVs)
├── logs/                           (all agent logs)
└── TOURISM_DATA/                   (downloaded datasets)
```

## NODE-RED MONITORING

All agents POST to: `http://localhost:1880/enrichment-status`
Read status: `GET http://192.168.100.21:1880/enrichment-status`
Tab: "Email Enrichment" in Node-RED dashboard

## KEY NUMBERS

- **83M+** website URLs without email in DB + CSVs
- **331,564** master_emails (deduped, growing daily)
- **+1,453,359** emails from email_1 backfill (done)
- **+21,864** emails from scraping (OSM + France + agencies)
- **41-64%** email find rate from website scraping
- **30 cron lines** for all agents
- **Zero tokens, zero cost**
