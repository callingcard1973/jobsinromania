# Next Steps & Additional Opportunities

## COMPLETED (Phase 1 + Phase 3)

| Task | Output | Records |
|------|--------|---------|
| Sector matcher | sector_matcher.py | 303K matches |
| Lithium campaign | campaign_lithium.csv | 493 buyers |
| Niobium campaign | campaign_niobium.csv | 497 buyers |
| Beef campaign | campaign_beef.csv | 493 buyers |
| Honey campaign | campaign_honey.csv | 491 buyers |
| Brazilian scrapers | apex_brasil_scraper.py | Ready |
| Data sources doc | DATA_SOURCES.md | 10+ APIs |
| **Canada-EU matcher** | **canada_eu_matcher.py** | **136K matches** |
| Seafood campaign | campaign_seafood.csv | 492 buyers |
| Aluminum campaign | campaign_aluminum.csv | 486 buyers |
| Lumber campaign | campaign_lumber.csv | 487 buyers |
| Minerals campaign | campaign_minerals.csv | 492 buyers |
| Clean Tech campaign | campaign_cleantech.csv | 498 buyers |
| Agri-food campaign | campaign_agrifood.csv | 489 buyers |
| Machinery campaign | campaign_machinery.csv | 490 buyers |

---

## PHASE 2: EXPAND COMMODITIES (Week 1-2)

### 1. Wine & Spirits (Romanian GIs)

15 Romanian products protected under EU-Mercosur:
- Palinca, Tuica Zetea, Vinars Tarnave/Vrancea
- Wines: Cotnari, Dealu Mare, Murfatlar, etc.

**Action:**
```bash
# Add wine sector to matcher
python3 sector_matcher.py --commodity wine --campaign
```

**CPV codes:** 159 (beverages), 155 (alcoholic)
**Target:** Brazil wine importers ($518M/yr market)

### 2. Coffee & Cocoa (Reverse - EU buys from Mercosur)

Brazil is world's #1 coffee exporter.

**Action:** Build coffee_suppliers.py
**Target:** EU coffee roasters, retailers

### 3. Soy & Sugar

Major Mercosur exports, new quotas under agreement.

**CPV codes:** 156 (grain products), 157 (animal feed)
**Target:** EU food processors, animal feed producers

### 4. Machinery (EU -> Mercosur)

EU machinery gets 14-20% tariff cuts.

**Action:** Reverse matcher - find EU machinery exporters, match to Mercosur buyers
**Target:** German/Italian machinery manufacturers

---

## PHASE 3: CANADA OPPORTUNITIES (COMPLETED 2026-03-21)

Tudor is Canadian - dual access advantage.

### 1. CETA Matcher (Canada-EU) - DONE

Built `/opt/ACTIVE/DB/GLOBAL/CANADA/scripts/canada_eu_matcher.py`:
- 7 sectors: seafood, aluminum, lumber, minerals, cleantech, agrifood, machinery
- 29 Canadian suppliers (seed data)
- 33,233 EU buyers matched
- 136,636 total potential matches

**Campaign files:**
```
/mnt/hdd/GLOBAL_DOWNLOADS/canada_eu/matches/
├── campaign_seafood_20260321.csv   (492 buyers)
├── campaign_aluminum_20260321.csv  (486 buyers)
├── campaign_lumber_20260321.csv    (487 buyers)
├── campaign_minerals_20260321.csv  (492 buyers)
├── campaign_cleantech_20260321.csv (498 buyers)
├── campaign_agrifood_20260321.csv  (489 buyers)
└── campaign_machinery_20260321.csv (490 buyers)
```

**Quick commands:**
```bash
python3 /opt/ACTIVE/DB/GLOBAL/CANADA/scripts/canada_eu_matcher.py --stats
python3 /opt/ACTIVE/DB/GLOBAL/CANADA/scripts/canada_eu_matcher.py --commodity all --campaign
```

### 2. CPTPP Arbitrage (TODO)

Canada has access to:
- Japan (vehicles, electronics)
- Vietnam (textiles, electronics)
- Australia (minerals, food)

**Opportunity:** Source from CPTPP, re-export to EU under CETA

### 3. Canadian Company Registration (TODO)

Register Tudor Trade Inc. (Canada) for:
- CETA preferential access
- Canadian banking
- Dual invoicing (CAD/EUR)

---

## PHASE 4: AUTOMATION (Week 3-4)

### 1. Weekly Matching Pipeline

```bash
# Cron: Every Monday 6 AM
0 6 * * 1 /opt/ACTIVE/DB/GLOBAL/MERCOSUR/scripts/weekly_match.sh
```

Tasks:
- Refresh TED winners data
- Run all commodity matches
- Generate campaign CSVs
- Send summary to Telegram

### 2. Supplier Enrichment Pipeline

Crawl supplier websites for contact info:
```bash
python3 /opt/ACTIVE/INFRA/SKILLS/website_enricher.py \
  /mnt/hdd/GLOBAL_DOWNLOADS/mercosur_lithium/lithium_suppliers.json
```

### 3. Auto-Campaign Triggers

When new matches > 100:
- Auto-generate campaign CSV
- Notify via Telegram
- Queue for review

---

## PHASE 5: NEW MARKETS (Month 2+)

### 1. UK Post-Brexit

UK-Mercosur negotiations ongoing.
Build uk_mercosur_matcher.py when deal announced.

### 2. African Continental Free Trade Area (AfCFTA)

55 African countries, $3.4T GDP.
Opportunity: Broker EU-Africa trade.

### 3. India-EU FTA

Negotiations active. India = 1.4B consumers.
Prepare india_eu_matcher.py framework.

### 4. Gulf Cooperation Council (GCC)

EU-GCC FTA negotiations resumed.
UAE, Saudi, Qatar = high-value markets.

---

## REVENUE PROJECTIONS

### Conservative (Year 1)

| Quarter | Deals | Avg Size | Commission | Revenue |
|---------|-------|----------|------------|---------|
| Q1 | 2 | EUR 50K | 5% | EUR 5K |
| Q2 | 5 | EUR 75K | 4% | EUR 15K |
| Q3 | 8 | EUR 100K | 3.5% | EUR 28K |
| Q4 | 10 | EUR 150K | 3% | EUR 45K |
| **Year 1** | **25** | - | - | **EUR 93K** |

### Aggressive (with Canada + automation)

| Year | Deals | Revenue |
|------|-------|---------|
| Year 1 | 40 | EUR 150K |
| Year 2 | 100 | EUR 400K |
| Year 3 | 200 | EUR 800K |

---

## IMMEDIATE ACTIONS (This Week)

### Priority 1: Test Campaign
```bash
# Take 100 lithium buyers, send test email
head -101 /mnt/hdd/GLOBAL_DOWNLOADS/mercosur_matches/campaign_lithium_20260321.csv > test_campaign.csv
```

### Priority 2: Email Template
Create "Secure Mercosur supply chain" template:
- Subject: EU-Mercosur: Secure {commodity} supply before May 2026
- Body: Tariff savings, supplier list, call-to-action

### Priority 3: Enrich Suppliers
Get contact emails for top 10 lithium suppliers:
```bash
python3 /opt/ACTIVE/INFRA/SKILLS/website_enricher.py \
  --input /mnt/hdd/GLOBAL_DOWNLOADS/mercosur_lithium/lithium_suppliers.json \
  --output lithium_enriched.csv
```

### Priority 4: Canada Research
```bash
# Search Canadian exporters
python3 scrapers/canada/canada_exporters.py --sector seafood
```

---

## FILES CREATED

```
/opt/ACTIVE/IDEAS/MERCOSUR/OPENCODE/
├── CLAUDE.md                    # Project guide
├── SYNTHESIS.md                 # Full analysis & plan
├── DATA_SOURCES.md              # APIs & data sources
├── NEXT_STEPS.md                # This file
├── scrapers/
│   ├── mercosur/
│   │   ├── apex_brasil_scraper.py
│   │   ├── connectamericas_scraper.py
│   │   └── brazil_exporters.py
│   └── canada/                  # TODO
├── data/                        # Scraped data
└── campaigns/                   # Email templates

/opt/ACTIVE/DB/GLOBAL/MERCOSUR/
├── scripts/
│   ├── sector_matcher.py        # Main matcher
│   ├── mercosur_all.py          # Orchestrator
│   ├── lithium_suppliers.py
│   ├── niobium_suppliers.py
│   ├── beef_exporters.py
│   └── honey_exporters.py
└── CLAUDE.md

/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_*/
├── lithium_suppliers.json       # 24 suppliers
├── niobium_suppliers.json       # 8 suppliers
├── beef_exporters.json          # 22 suppliers
├── honey_exporters.json         # 20 suppliers
└── mercosur_matches/
    ├── campaign_lithium_20260321.csv
    ├── campaign_niobium_20260321.csv
    ├── campaign_beef_20260321.csv
    └── campaign_honey_20260321.csv
```
