# DATABASE INVENTORY — 2026-03-15

Complete inventory of all PostgreSQL databases on raspibig and raspi.

---

## RASPIBIG (192.168.100.21) — 19 Databases

### 1. interjob_master (107 GB) — MASTER DATABASE
Primary business intelligence database. **VERIFIED 2026-03-15**

| Table | Size | Records | Purpose |
|-------|------|---------|---------|
| companies | 82 GB | **178.8M** | Companies from 42 countries |
| de_companies | 4.8 GB | - | German companies |
| fr_companies | 4.6 GB | - | French companies |
| master_romania_companies | 4.4 GB | - | Romania master |
| ted_awards | 3.5 GB | **6.2M** | EU TED procurement winners |
| uk_companies | 2.3 GB | - | UK companies |
| tenders | 1.3 GB | **5.1M** | EU-wide tenders |
| no_companies_full | 640 MB | - | Norway companies |
| cz_companies | 615 MB | - | Czech companies |
| bilant_years | 368 MB | - | Financial data |
| ted_contracts | 250 MB | - | TED contracts |
| ie_companies | 211 MB | - | Ireland companies |
| bg_ted_notices | 185 MB | - | Bulgaria TED |
| insolvency | 177 MB | **1.03M** | Bankrupt companies |
| ong_registry_mj | 129 MB | 150K | Romanian NGOs |
| contacts | 106 MB | **555K** | All with email |
| agencies | - | **148K** | Recruitment agencies |
| romania_campaign | 74 MB | 372K | Campaign contacts |

---

### 2. romania (9.3 GB) — ROMANIA BUSINESS INTEL
| Table | Size | Records | Purpose |
|-------|------|---------|---------|
| companies | 7.4 GB | 4.95M | All Romanian companies |
| contacts | 1 GB | 8.2M | Contact records |
| procurement | 588 MB | 2.1M | Public procurement |
| ong_registry_mj | 129 MB | 150K | NGO registry |
| tenders | 107 MB | - | Romanian tenders |
| food_companies_master | 24 MB | - | Food sector |
| specialists | 5.4 MB | - | Professional contacts |
| ong_shortlist_5000_mj | 4 MB | 5K | Top NGOs |
| ecologic_producers | 3.9 MB | - | Eco producers |
| dnc | 2.3 MB | - | Do-not-contact |
| mountain_producers | 520 KB | 1,331 | Produs Montan |

---

### 3. opendata (7.3 GB) — BULK OPEN DATA
| Table | Size | Records | Purpose |
|-------|------|---------|---------|
| companies | 6 GB | 17.7M | EU companies bulk |
| contacts | 1.2 GB | 8.2M | Contact records |
| faliment | 189 MB | 222K | Insolvency records |

---

### 4. csv_raw (5.3 GB) — RAW CSV IMPORTS
- **1,275 tables** (unprocessed imports)
- Historical scraper outputs
- Needs processing/deduplication

---

### 5. eures (504 MB) — EURES JOB PORTAL
| Table | Size | Purpose |
|-------|------|---------|
| scraped_urls | 245 MB | Scraped job URLs |
| dsvsa_companies | 196 MB | Food safety companies |
| campaign_contacts | 21 MB | Campaign targets |
| contacts | 19 MB | EURES contacts |
| employer_emails | 6.7 MB | Employer data |
| anofm_employers | 2 MB | ANOFM employers |

---

### 6. bulgaria_emails (325 MB) — BULGARIA B2B
| Table | Size | Records | Purpose |
|-------|------|---------|---------|
| ted_notices | 186 MB | 63K | TED procurement |
| companies_registry | 58 MB | 27K | Company registry |
| companies | 51 MB | 143K | All companies |
| ukazatelite | 13 MB | - | Directory |
| eu_subsidy | 2.6 MB | - | EU subsidies |
| agencies | 2.5 MB | - | Recruitment agencies |
| ksb_builders | 2.1 MB | - | Construction |

---

### 7. romania_emails (248 MB) — CAMPAIGN CONTACTS
| Table | Size | Records | Purpose |
|-------|------|---------|---------|
| contacts_backup | 179 MB | - | Backup |
| contacts | 59 MB | 82K | Active contacts |
| dnc | 176 KB | - | Do-not-contact |
| send_log | 64 KB | - | Send history |

---

### 8. norway_emails (244 MB) — NORWAY CAMPAIGN
| Table | Size | Records | Purpose |
|-------|------|---------|---------|
| norway_emails | 232 MB | 155K | Norway contacts |
| lucian_horeca | 4 MB | - | HORECA segment |
| norway_send_log | 296 KB | - | Send history |

---

### 9. scraper (131 MB) — SCRAPER STATE
| Table | Purpose |
|-------|---------|
| anofm_jobs | ANOFM job listings |
| scraped_jobs | All scraped jobs |
| scraped_urls | URL tracking |
| employer_emails | Employer contacts |
| campaign_runs | Campaign tracking |
| worker_states | Scraper workers |

---

### 10. food_distribution (45 MB) — FOOD SECTOR
| Table | Size | Purpose |
|-------|------|---------|
| contacts | 17 MB | Food contacts |
| dairy_ro | 6.2 MB | Dairy companies |
| supermarkets_ro | 5.6 MB | Supermarkets |
| horeca_ro | 3 MB | HORECA |
| distributors_ro | 2 MB | Distributors |
| logistics_ro | 1.4 MB | Logistics |
| meat_processors_ro | 1.3 MB | Meat processors |
| wholesale_europe | 160 KB | EU wholesale |

---

### 11. email_sender (26 MB) — SEND LOGS
| Table | Size | Purpose |
|-------|------|---------|
| send_log | 7.6 MB | Send history |
| global_sends | 6 MB | All sends |
| campaign_replies | 2.1 MB | Reply tracking |
| campaign_contacts | 1.9 MB | Campaign targets |
| applications | 120 KB | Job applications |

---

### 12. denmark_emails (15 MB)
Danish company contacts for campaigns.

### 13. moldova (13 MB)
Moldovan company data.

### 14. norway (12 MB)
Additional Norway data.

### 15. eures_scraper (12 MB)
EURES scraper state.

### 16. cifn_eu (8 MB) — EU FUNDING PORTAL
| Table | Size | Purpose |
|-------|------|---------|
| calls | 536 KB | 510 EU funding calls |

### 17. business_intelligence (8 MB)
BI analytics data.

### 18. carbon_credits (7 MB)
Agricultural carbon credit data.

---

## RASPI (192.168.100.20) — 12 Databases

### 1. csv_raw (6.4 GB) — RAW IMPORTS
- **3,018 tables** (more than raspibig!)
- Recent imports include:
  - th_data_2022 (412 MB)
  - eurostat_temp_turnover (355 MB)
  - general_master_50 (232 MB)
  - SEAP achizitii directe (multiple, 180-220 MB each)
  - poland_contacts (multiple, 184-190 MB each)
  - sweden_contacts (172 MB)

### 2. master_db (3.6 GB)
Master database (appears empty/migrated).

### 3. eures (268 MB)
EURES scraper data (Southern/Eastern Europe).

### 4. romania (32 MB)
Romanian company subset.

### 5. scraper (18 MB)
Scraper state and logs.

### 6. jobscraper (17 MB)
Job scraping data.

### 7. email_sender (13 MB)
Email send logs (raspi sends).

### 8. ofn_db (12 MB)
Open Food Network data.

### 9. listmonk (9 MB)
Listmonk email marketing.

### 10. bounce_processor (8 MB)
Bounce processing and tracking.

### 11. freescout (7 MB)
FreeScout helpdesk.

---

## SUMMARY STATISTICS

### By Machine
| Machine | Databases | Total Size | Tables |
|---------|-----------|------------|--------|
| raspibig | 19 | ~130 GB | 1,400+ |
| raspi | 12 | ~10 GB | 3,100+ |

### Key Record Counts (VERIFIED 2026-03-15)
| Asset | Records | Location |
|-------|---------|----------|
| EU Companies | **178.8M** | interjob_master.companies |
| TED Awards | **6.2M** | interjob_master.ted_awards |
| EU Tenders | **5.1M** | interjob_master.tenders |
| Romania Companies | 4.95M | romania.companies |
| Opendata Companies | 17.7M | opendata.companies |
| All Contacts (RO) | 8.2M | romania.contacts |
| Romania Procurement | 2.1M | romania.procurement |
| Insolvency | **1.03M** | interjob_master.insolvency |
| Contacts w/Email | **555K** | interjob_master.contacts |
| Romanian NGOs | 150K | interjob_master.ong_registry_mj |
| Norway Emails | 155K | norway_emails.norway_emails |
| Agencies | **148K** | interjob_master.agencies |
| Bulgaria Companies | 143K | bulgaria_emails.companies |
| Romania Campaign | 82K | romania_emails.contacts |
| Produs Montan | 1,331 | romania.mountain_producers |
| EU Funding Calls | 510 | cifn_eu.calls |

### Storage by Purpose
| Purpose | Size | Records | Location |
|---------|------|---------|----------|
| Company Intelligence | 82 GB | 178.8M | interjob_master.companies |
| TED Procurement | 3.5 GB | 6.2M | interjob_master.ted_awards |
| EU Tenders | 1.3 GB | 5.1M | interjob_master.tenders |
| Insolvency | 177 MB | 1.03M | interjob_master.insolvency |
| Romania Business | 9.3 GB | 4.95M | romania database |
| Open Data Archive | 7.3 GB | 17.7M | opendata database |
| Raw CSV Imports | 11.7 GB | 4,293 tables | csv_raw (both machines) |
| Campaign Contacts | 500 MB | 555K+ | *_emails databases |
| Recruitment Agencies | - | 148K | interjob_master.agencies |
| Food Sector | 45 MB | - | food_distribution |
| EU Funding | 8 MB | 510 calls | cifn_eu |

---

## REVENUE POTENTIAL BY DATABASE

### HIGH VALUE
1. **interjob_master** (107 GB) — EUR 50K-500K data sales potential
   - 178.8M companies, 6.2M TED awards, 5.1M tenders, 1.03M insolvency
2. **romania** (9.3 GB) — EUR 10K-50K, all Romanian B2B
3. **norway_emails** (244 MB) — EUR 5-15K/placement, 155K contacts
4. **bulgaria_emails** (325 MB) — EUR 3-5K/placement, 143K companies

### MEDIUM VALUE
5. **opendata** (7.3 GB) — EUR 5-20K, bulk EU data
6. **romania_emails** (248 MB) — Active campaigns, 82K contacts
7. **food_distribution** (45 MB) — EUR 500-5K, food sector
8. **eures** (504 MB) — Job portal contacts

### UTILITY
9. **email_sender** — Campaign analytics
10. **scraper** — Operational data
11. **cifn_eu** — Lead generation (510 EU calls)

---

## UNPROCESSED GOLD MINES

1. **ted_awards** — **6.2M** EU procurement winners
   - Script ready (ted_outreach_campaign.py)
   - EUR 150K+ potential per campaign
   - Massive untapped asset

2. **insolvency** — **1.03M** pan-European bankruptcies
   - Available workers, distressed assets
   - Cross-sell to accountants, executors

3. **csv_raw (raspibig)** — 1,275 tables, 5.3 GB
   - Historical scraper outputs
   - Needs deduplication and enrichment

4. **csv_raw (raspi)** — 3,018 tables, 6.4 GB
   - Recent imports (Poland, Sweden, SEAP)
   - Fresh data for campaigns

5. **ong_registry_mj** — 150K Romanian NGOs
   - Cross-sell accounting/legal services

6. **agencies** — **148K** recruitment agencies
   - Direct partnership targets

---

Generated: 2026-03-15
Machines: raspibig (192.168.100.21), raspi (192.168.100.20)
