# Cooperative Food Distribution Contacts -- Romania

## Purpose

Contact database for a chamber of commerce of cooperatives distributing fresh produce, dairy, meat, and processed food in Romania. Full food product range requiring DSVSA veterinary permits.

## File Structure

```
SUPERMARKETS CLAUDE/
  CLAUDE.md
  COOPERATIVE_DISTRIBUTION_STRATEGY.md   -- 12 distribution channels + regulatory
  ideas.txt                              -- Business ideas + next steps
  CODE/
    shared_utils.py                      -- normalize(), DB configs, CSV I/O, stats
    enrich_master_index.py               -- Build master lookup index from interjob_master
    seap_extract.py                      -- Extract food winners from SEAP via SSH
    seap_cross_match.py                  -- Cross-match SEAP winners vs food_distribution
    faliment_opportunities.py            -- Bankrupt food company acquisition targets
    consolidate.py                       -- Merge, deduplicate, categorize all sources
    create_db.py                         -- Create food_distribution PG DB + import
    enrich_from_db.py                    -- 4-pass enrichment from interjob_master
    query_food_contacts.py               -- Query interjob_master by category/county
    seap_food_alerts.py                  -- SEAP food tender report + buyers/winners
    seap_alert_dispatcher.py             -- Cron-ready SEAP tender alerts via Brevo
    faliment_cross_match.py              -- Insolvency flagging + stats
    campaign_templates.py                -- Email templates for tier-based outreach
    campaign_dashboard.py                -- Campaign readiness status display
    campaign_export.py                   -- Export segmented contact lists to CSV
    segment_and_analyze.py               -- Tier segmentation + geographic heatmaps
    exploratory/                         -- Test/debug scripts (11 files)
  DATA/
    SUPERMARKETS_RO.csv                  -- 15,134 supermarkets & retailers
    DISTRIBUTORS_RO.csv                  -- 5,115 food distributors
    COLD_STORAGE_RO.csv                  -- 160 cold chain facilities
    MEAT_PROCESSORS_RO.csv               -- 4,469 meat processing plants
    DAIRY_RO.csv                         -- 18,719 dairy producers
    LOGISTICS_RO.csv                     -- 4,994 food logistics
    HORECA_RO.csv                        -- 18,303 hotels/restaurants/catering
    ALL_SUPERMARKET_CHAINS.csv           -- 137 major chain contacts
    WHOLESALE_EUROPE.csv                 -- 591 EU wholesalers
    MASTER_CLEAN.csv                     -- 19,062 deduplicated master
    masterdb_food_companies.csv          -- 210K master DB extract
    ROMANIA_FOOD_DISTRIBUTION_CONTACTS.csv -- 32,545 consolidated output
    seap_food_winners_unique.csv         -- 4,728 SEAP food tender winners
    seap_food_winners_all.csv            -- 47,309 food tenders (full)
    seap_food_overlap.csv                -- 108 cross-matches (SEAP vs our DB)
    insolvent_contacts_flagged.csv       -- 1,969 insolvent contacts flagged
```

## Quick Start

```bash
# Consolidate all sources
python CODE/consolidate.py

# Create DB + import
python CODE/create_db.py

# Enrich from interjob_master
python CODE/enrich_from_db.py

# SEAP food tender alerts
python CODE/seap_food_alerts.py

# Insolvency cross-match
python CODE/faliment_cross_match.py

# Query by category
python CODE/query_food_contacts.py --category supermarket --email-only
```

## Database

- **food_distribution** on raspibig:5432 -- 32,545 contacts, 20,795 with email
- **interjob_master** -- source for enrichment (43.8M companies, 5.1M tenders)

## Key Findings (2026-03-07)

- 47,309 Romanian food tenders (CPV 15*/03*), 2 billion RON total value
- 4,728 unique SEAP food winners, 932 public buyers
- 5,367 bankrupt food companies (acquisition targets)
- 1,969 of our contacts are insolvent (1,824 with email -- remove from campaigns)
