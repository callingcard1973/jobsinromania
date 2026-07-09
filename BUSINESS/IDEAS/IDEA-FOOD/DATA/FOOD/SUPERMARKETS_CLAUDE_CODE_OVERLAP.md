# Supermarkets Claude Code Overlap

## Scope
- This note compares the imported `SUPERMARKETS CLAUDE` codebase with the current FOOD code already in use.
- Comparison focus: operational role, overlap, and how the imported code should be used.

## Imported Workspace Role

Source: `D:/MEMORY/CLAUDE/SUPERMARKETS CLAUDE/CODE/`

Primary focus:
1. market-wide food contact consolidation
2. SEAP extraction and cross-match
3. buyer and winner alerts
4. database creation and enrichment
5. segmentation, campaign export, and insolvency filtering

Representative imported scripts:
- `seap_extract.py`
- `seap_cross_match.py`
- `seap_food_alerts.py`
- `seap_alert_dispatcher.py`
- `consolidate.py`
- `create_db.py`
- `enrich_from_db.py`
- `query_food_contacts.py`
- `faliment_cross_match.py`
- `campaign_export.py`

Additional imported coverage:
- enrichment pipelines: `deep_enrich_raspibig.py`, `ultimate_enrich_raspibig.py`, `enrich_seap_winners.py`
- market scanning: `scan_all_sources.py`, `web_email_finder.py`
- campaign support: `campaign_dashboard.py`, `campaign_templates.py`, `segment_and_analyze.py`
- exploratory research scripts under `CODE/exploratory/`

Operational interpretation:
- This workspace is a broad market-intelligence and enrichment toolkit.
- It is designed to discover, enrich, segment, and monitor food-sector opportunities across the market.

## Existing FOOD Code Role

Current operational code in FOOD focuses on narrower, active subprojects.

### Z.AI SUPERMARKETS
Primary focus:
1. create and populate a Romanian food-company database
2. export business-ready segment files
3. run utility-level database analysis for list packaging

Representative scripts:
- `setup_supermarkets_db.py`
- `import_supermarkets_data.py`
- `export_supermarkets_csv.py`
- `supermarkets_utils.py`

### PRODUSMONTAN
Primary focus:
1. parsing RNPM source files
2. importing producer/product data
3. generating and deploying the catalog
4. scraping produsmontan.ro
5. publishing and contact updates

Representative scripts:
- `produs_montan_parse.py`
- `create_produs_montan_db.py`
- `generate_catalog.py`
- `deploy_catalog.py`
- `publish_2026_post.py`
- `SCRAPER/scrape_produsmontan.py`

### ROMCONSERV
Primary focus:
1. single-campaign execution
2. template-based outreach to conserve and packaging contacts

Representative script:
- `send_campaign.py`

## Overlap Assessment

### Functional overlap
- `Z.AI SUPERMARKETS` and imported `SUPERMARKETS CLAUDE` both work on the food-company intelligence layer.
- Both can feed outreach and segmentation.
- Both can support downstream campaign work.

### Direct overlap by function
- Database foundation:
  - `Z.AI SUPERMARKETS` handles setup, import, export, and utility operations.
  - imported `SUPERMARKETS CLAUDE` also contains `create_db.py` and multiple enrichment paths.
  - conclusion: imported workspace extends the data layer, while Z.AI provides the cleaner starter scaffold.
- Segmentation and list packaging:
  - `export_supermarkets_csv.py` overlaps conceptually with `campaign_export.py` and `segment_and_analyze.py`.
  - conclusion: same commercial use case, different maturity levels.
- Enrichment and discovery:
  - imported workspace has the real depth here; Z.AI does not.
- SEAP and alerts:
  - imported workspace clearly owns this area; Z.AI does not.
- Operational campaign execution:
  - imported workspace prepares campaigns and exports.
  - active execution still sits elsewhere in FOOD, especially `ROMCONSERV/send_campaign.py`.

### Complementary areas
- `Z.AI SUPERMARKETS` is strongest for:
  - simple database bootstrap
  - understandable business packaging
  - fast creation of saleable list products
- Imported `SUPERMARKETS CLAUDE` code is strongest for:
  - SEAP extraction and monitoring
  - channel-wide contact consolidation
  - supplier and buyer segmentation
  - insolvency/risk filtering
- Existing FOOD code is strongest for:
  - Produs Montan producer pipeline
  - catalog generation
  - direct campaign execution for a specific segment

### Practical conclusion
- The imported code should not replace `PRODUSMONTAN` scripts.
- `Z.AI SUPERMARKETS` should not be merged file-by-file into imported `SUPERMARKETS CLAUDE`.
- It should be treated as the clean commercial packaging and starter-database layer.
- Imported `SUPERMARKETS CLAUDE` should be treated as the strategic market-intelligence and SEAP tooling layer around the current FOOD workspace.
- `ROMCONSERV` and `PRODUSMONTAN` remain operational subprojects; imported code broadens the buyer-access and procurement-intelligence side.

### Working split
1. Use `ZAI_SUPERMARKETS` when the task is simple list building, export packaging, and fast commercial data products.
2. Use `SUPERMARKETS_CLAUDE` when the task is enrichment, SEAP monitoring, insolvency filtering, or cross-source market intelligence.
3. Use `PRODUSMONTAN` and `ROMCONSERV` when the task is actual seller operations and campaign execution.

## Recommended Use
1. Keep `PRODUSMONTAN` code as the supply pipeline.
2. Keep `ROMCONSERV` code as the direct outreach runner for that niche.
3. Use `ZAI_SUPERMARKETS` for packaging lists and commercial database products.
4. Use imported `SUPERMARKETS CLAUDE` code for SEAP, channel analysis, master contact building, and campaign exports.
5. Avoid merging scripts blindly; prefer keeping both workspaces intact and assigning each one a clear role.