# IDEAS — Code, Scrapers & Data Inventory (2026-04-12)

Synced on both LOCAL (`D:\MEMORY\IDEAS\`) and RASPIBIG (`/opt/ACTIVE/IDEAS/`)

---

## 1. ASOCIATII — Romanian NGO Registry
**Status:** FROZEN | **Data:** 90K+ NGOs across 42 counties

### Code (4 scripts)
| Script | What it does |
|--------|-------------|
| `generate_ong_registry.py` | Generates full NGO registry from source data |
| `generate_ong_shortlist.py` | Creates filtered shortlist (5,000 top NGOs) |
| `deploy_ong_to_raspibig.py` | Deploys data to raspibig PostgreSQL |
| `raspibig_ong_ingest_remote.py` | Remote ingestion script for raspibig |

### Data (49 CSVs)
| File | What it contains |
|------|-----------------|
| `ONG_ACTIVE.csv` | All active Romanian NGOs |
| `ONG_REGISTRU_NATIONAL.csv` | National registry extract |
| `ONG_SHORTLIST_5000.csv` | Top 5,000 NGOs filtered |
| `ONG_SUMAR_JUDETE.csv` | Summary by county |
| `ONG_SUMAR_LOCALITATI.csv` | Summary by city |
| `JUDETE_ORASE_RO.csv` | Romania regions/cities (4,706 rows) |
| `ong_pe_judete/ong_active_*.csv` | 42 county-specific files (alba through vrancea) |

---

## 2. CHINA — Trade Data & Manufacturing
**Status:** RESEARCH | **Data:** Manufacturers + economic indicators

### Scrapers (3 scripts)
| Script | What it scrapes |
|--------|----------------|
| `scrapers/made_in_china.py` | Made-in-China.com manufacturer listings |
| `scrapers/nbs_china_api.py` | China National Bureau of Statistics API (GDP, CPI, exports) |
| `scrapers/un_comtrade.py` | UN Comtrade international trade statistics |

### Data (8 CSVs)
| File | What it contains |
|------|-----------------|
| `data/manufacturers/electronics_20260322.csv` | Electronics manufacturers |
| `data/manufacturers/machinery_20260322.csv` | Industrial machinery companies |
| `data/nbs/china_trade_2020_2024.csv` | China trade stats 2020-2024 |
| `data/nbs/gdp_20260322.csv` | GDP data |
| `data/nbs/cpi_20260322.csv` | Consumer price index |
| `data/nbs/industrial_output_20260322.csv` | Industrial output |
| `data/nbs/exports_total_20260322.csv` | Total exports |
| `data/opendata/chinese_ie_sample.csv` | Import/export company sample |

---

## 3. COOPERATIVA BUSINESS — EU Export Cooperative
**Status:** FROZEN (needs co-founder) | **Data:** 140 producers + EU buyers

### Code (2 scripts)
| Script | What it does |
|--------|-------------|
| `scripts/week1_consolidate_producers.py` | Consolidates 140 producer records |
| `scripts/week1_segment_buyers.py` | Segments EU hypermarket/diaspora buyers |

### Data (4 CSVs)
| File | What it contains |
|------|-----------------|
| `data_working/cooperatives_full.csv` | All cooperatives |
| `data_working/master_producers_consolidated.csv` | 140 producers master list |
| `data_working/hypermarket_targets_25emails.csv` | 25 EU hypermarket contacts |
| `data_working/italy_diaspora_shops_sample.csv` | Italian diaspora shops |

---

## 4. DATING — fdating.com Search
**Status:** PLANNED | **Data:** None yet

No code or data yet. Plan saved in `FDATING_SEARCH.md`.

---

## 5. FOOD — HORECA + Supermarkets + SEAP
**Status:** ACTIVE | **Data:** 28K HORECA emails, SEAP winners, food industry

### Code (25 scripts in SUPERMARKETS_CLAUDE/CODE/)
| Script | What it does |
|--------|-------------|
| `create_db.py` | Initialize food industry database |
| `consolidate.py` | Merge all food data sources |
| `segment_and_analyze.py` | Segment companies by type/size |
| `enrich_food_raspibig.py` | Enrich contacts from raspibig DB |
| `deep_enrich_raspibig.py` | Deep enrichment (phone, email, ANAF) |
| `fuzzy_enrich_raspibig.py` | Fuzzy name matching for enrichment |
| `enrich_from_db.py` | DB-based contact enrichment |
| `enrich_master_index.py` | Master index enrichment |
| `enrich_seap_winners.py` | Enrich 3,030 SEAP food winners |
| `ultimate_enrich_raspibig.py` | Final enrichment pass |
| `web_email_finder.py` | Scrape websites for email addresses |
| `query_food_contacts.py` | Query enriched contacts |
| `scan_all_sources.py` | Scan all data sources for food companies |
| `seap_extract.py` | Extract SEAP food procurement data |
| `seap_cross_match.py` | Cross-match SEAP with company DB |
| `seap_food_alerts.py` | Alert on new food tenders |
| `seap_alert_dispatcher.py` | Dispatch tender alerts |
| `faliment_cross_match.py` | Cross-match food companies with insolvency |
| `faliment_opportunities.py` | Find bankrupt food asset opportunities |
| `campaign_dashboard.py` | Campaign visualization dashboard |
| `campaign_export.py` | Export campaign-ready CSVs |
| `campaign_templates.py` | Email templates for food outreach |
| `shared_utils.py` | Shared utility functions |
| `sync_to_raspibig.cmd` | Windows sync script |
| `sync_to_raspibig.ps1` | PowerShell sync script |

### Exploratory (11 scripts in CODE/exploratory/)
| Script | What it does |
|--------|-------------|
| `ddg_email_search.py` | DuckDuckGo email finder |
| `inspect_all_dbs.py` | Inspect all PostgreSQL databases |
| `scan_all_pg_dbs.py` | Scan all PG databases for food tables |
| `scan_big_csvs.py` | Scan large CSVs for food data |
| `search_liquidators.py` | Find liquidator contacts |
| `listafirme_cui_lookup.py` | ListaFirme.ro CUI lookup |
| `test_listafirme*.py` (4) | ListaFirme scraper iterations |
| `test_web_finder.py` | Test web email finder |

### Data (23 CSVs)
| File | What it contains |
|------|-----------------|
| `HORECA_28K_UNIQUE_EMAILS.csv` | **28K HORECA contacts** (20K RO, 5.6K NO, 800 BG, 350 DK) |
| `DATA/ALL_SUPERMARKET_CHAINS.csv` | All EU supermarket chains |
| `DATA/SUPERMARKETS_RO.csv` | Romanian supermarkets |
| `DATA/HORECA_RO.csv` | RO hotels/restaurants/catering |
| `DATA/DISTRIBUTORS_RO.csv` | RO food distributors |
| `DATA/DAIRY_RO.csv` | RO dairy companies |
| `DATA/COLD_STORAGE_RO.csv` | RO cold storage facilities |
| `DATA/MEAT_PROCESSORS_RO.csv` | RO meat processors |
| `DATA/LOGISTICS_RO.csv` | RO logistics companies |
| `DATA/WHOLESALE_EUROPE.csv` | EU wholesale distributors |
| `DATA/MASTER_CLEAN.csv` | Cleaned master food database |
| `DATA/ROMANIA_FOOD_DISTRIBUTION_CONTACTS.csv` | RO food distribution contacts |
| `DATA/masterdb_food_companies.csv` | Master DB food companies |
| `DATA/romanian_farms_raspibig.csv` | Romanian farms from raspibig |
| `DATA/romanian_food_processors_database.csv` | Food processors |
| `DATA/romanian_wholesale_distributors.csv` | Wholesale distributors |
| `DATA/romanian_agricultural_cooperatives_comprehensive_database.csv` | Agricultural cooperatives |
| `DATA/romanian_chamber_of_commerce_database.csv` | Chamber of commerce data |
| `DATA/seap_food_winners_all.csv` | All SEAP food winners |
| `DATA/seap_food_winners_enriched.csv` | Enriched SEAP winners (3,030) |
| `DATA/seap_food_winners_unique.csv` | Deduplicated SEAP winners |
| `DATA/seap_food_winners_with_cui.csv` | SEAP winners with CUI |
| `DATA/seap_food_overlap.csv` | SEAP overlap analysis |
| `DATA/insolvent_contacts_flagged.csv` | Insolvent food companies flagged |
| `DATA/CAMPAIGN_SEGMENTS/TIER0_SEAP_WINNERS.csv` | Campaign tier 0 |
| `DATA/CAMPAIGN_SEGMENTS/TIER1_CHAINS.csv` | Campaign tier 1 |
| `DATA/CAMPAIGN_SEGMENTS/TIER2_DISTRIBUTORS.csv` | Campaign tier 2 |
| `DATA/CAMPAIGN_SEGMENTS/TIER3_HORECA_BUCHAREST.csv` | Campaign tier 3 |
| `DATA/CAMPAIGN_SEGMENTS/ACQUISITION_TARGETS.csv` | Acquisition targets |

---

## 6. FRESKON — Trade Fair Exhibitors
**Status:** ACTIVE | **Data:** Exhibitor list

### Data (1 CSV)
| File | What it contains |
|------|-----------------|
| `freskon_exhibitors.csv` | European trade fair exhibitor contacts |

---

## 7. GUMROAD — Data Product Sales
**Status:** READY | **Data:** Product descriptions + templates

No code. Contains `/descriptions/` and `/products/` with templates for selling datasets.

---

## 8. LEGUME MASINI DE SORTAT LEGUME — Vegetable Sorting Machines
**Status:** RESEARCH

### Code (1 scraper)
| Script | What it scrapes |
|--------|----------------|
| `scrape_competitors.py` | Competitor sorting machine companies |

---

## 9. LEO CASA BUZAU — Property Rental (Buzau County)
**Status:** DATA READY (waiting for Leo) | **Data:** 34K+ companies

### Data (11 CSVs — multiple enrichment stages)
| File | What it contains |
|------|-----------------|
| `buzau_potrivite_companies_FINAL.csv` | Matched companies for rental |
| `LEO_BUZAU_FINAL_ENRICHED.csv` | Final enriched version |
| `LEO_BUZAU_WITH_EMAIL.csv` | Companies with email contacts |
| `leo_anaf_enriched.csv` | ANAF registry enriched |
| `leo_enriched.csv` / `leo_enriched_v2.csv` | Enrichment iterations |
| `leo_final.csv` / `leo_final_enriched.csv` | Final versions |
| `leo_max_enriched.csv` / `leo_ultimate.csv` | Maximum enrichment |
| `leo_with_headers.csv` | Clean headers version |

---

## 10. LLM — Email Classifier & Responder
**Status:** ACTIVE | **Data:** Training data, labels DB

### Code (7 scripts)
| Script | What it does |
|--------|-------------|
| `email_responder.py` | Automated email response system |
| `gmail_drafter.py` | Gmail draft generator |
| `train_classifier.py` | Train sklearn email classifier (94.5% accuracy) |
| `import_labels_to_pg.py` | Import labels to PostgreSQL |
| `response_templates.py` | Response template library |
| `test_local.py` | Local testing framework |
| `deploy.sh` | Deploy to raspibig |

### Data (5 files)
| File | What it contains |
|------|-----------------|
| `labels.db` | SQLite label database |
| `config.json` | Configuration |
| `training_data/manual_labels_batch1.json` | Training batch 1 |
| `training_data/manual_labels_batch2.json` | Training batch 2 |
| `training_data/seen_message_ids.json` | Processed message tracking |
| `training_data/collector_stats.json` | Collection statistics |

---

## 11. MERCOSUR — Latin America Trade Intelligence
**Status:** ACTIVE | **Data:** 22 sector campaigns, embassy contacts, Brazil CNPJ

### Scrapers (40+ scripts)

**Government APIs (5):**
| Script | What it scrapes |
|--------|----------------|
| `government/apex_brasil.py` | Brazil export promotion agency |
| `government/argentina_exporta.py` | Argentina export directory |
| `government/prochile.py` | Chile export promotion |
| `government/rediex_paraguay.py` | Paraguay export/investment |
| `government/uruguay_xxi.py` | Uruguay investment/export |

**Company Registries (4):**
| Script | What it scrapes |
|--------|----------------|
| `registries/argentina_afip.py` | Argentina tax registry |
| `registries/brazil_cnpj.py` | Brazil company registry (CNPJ) |
| `registries/chile_sii.py` | Chile tax service |
| `registries/uruguay_dgi.py` | Uruguay tax service |

**Trade Associations (6):**
| Script | What it scrapes |
|--------|----------------|
| `associations/abiec_beef.py` | Brazilian beef exporters |
| `associations/abemel_honey.py` | Brazilian honey exporters |
| `associations/ibram_mining.py` | Brazilian mining association |
| `associations/ipcva_argentina.py` | Argentine meat institute |
| `associations/sada_honey_ar.py` | Argentine honey association |
| `associations/wines_argentina.py` | Argentine wine exporters |

**Trade Shows (5):**
| Script | What it scrapes |
|--------|----------------|
| `tradeshows/apas_show.py` | APAS food show (Brazil) |
| `tradeshows/expoaladi.py` | ALADI trade expo |
| `tradeshows/fenavinho.py` | Wine fair |
| `tradeshows/fispal.py` | FISPAL food show (Brazil) |
| `tradeshows/mercoagro.py` | MercoAgro agribusiness |

**Directories (4):**
| Script | What it scrapes |
|--------|----------------|
| `directories/connectamericas.py` | ConnectAmericas IDB directory |
| `directories/dnb_latam.py` | D&B Latin America |
| `directories/kompass_latam.py` | Kompass directory |
| `directories/trademap.py` | ITC Trade Map |

**Working/Production (14):**
| Script | What it does |
|--------|-------------|
| `working/brazil_producers.py` | Scrape Brazilian producers |
| `working/argentina_producers.py` | Scrape Argentine producers |
| `working/chile_producers.py` | Scrape Chilean producers |
| `working/paraguay_producers.py` | Scrape Paraguayan producers |
| `working/uruguay_producers.py` | Scrape Uruguayan producers |
| `working/brazil_comex.py` | Brazil trade data (Comex) |
| `working/connectamericas_web.py` | Web scrape ConnectAmericas |
| `working/deep_scraper.py` | Deep website scraping |
| `working/mass_scraper.py` | Mass parallel scraping |
| `working/scrape_websites.py` | Scrape company websites |
| `working/scrape_all_websites.py` | Batch website scraping |
| `working/enrich_contacts.py` | Contact enrichment |
| `working/sector_enricher.py` | Sector-based enrichment |
| `working/consolidate_all.py` / `final_merge.py` | Data consolidation |

**Orchestration (5):**
| Script | What it does |
|--------|-------------|
| `parallel/orchestrator.py` | Parallel scraper orchestrator |
| `parallel/merger.py` | Merge parallel results |
| `parallel/worker_*.py` (5) | Specialized workers (associations, enricher, govapis, registries, tradeshows, websites) |
| `run_all.py` | Run all scrapers |
| `gentle_runner.py` | Rate-limited runner |

**Enrichment (6):**
| Script | What it does |
|--------|-------------|
| `TOTAL_SCRAPER/enrich_all_brazil.py` | Enrich all Brazil data |
| `TOTAL_SCRAPER/enrich_brazil_cnpj.py` | CNPJ-based enrichment |
| `TOTAL_SCRAPER/enrich_exporters.py` | Exporter enrichment |
| `TOTAL_SCRAPER/enrich_gentle.py` | Gentle rate-limited enrichment |
| `TOTAL_SCRAPER/test_all_scrapers.py` | Test suite |
| `VENTAS_EN_EUROPA/brazil_major_cnpj_corrected.py` | CNPJ correction |

**Embassy Outreach (2):**
| Script | What it does |
|--------|-------------|
| `embassy_outreach/send_embassy_letters.py` | Send letters to embassies |
| `embassy_outreach/send_mercosur_bucuresti.py` | Contact Mercosur embassies in Bucharest |

**Infrastructure (3):**
| Script | What it does |
|--------|-------------|
| `TOTAL_SCRAPER/cron_scrapers.sh` | Cron job for scheduled scraping |
| `TOTAL_SCRAPER/download_opendata.sh` | Download open data sources |
| `MERCOSUR2/VSCODE/inventory.py` | Data inventory tool |

### Data (50+ CSVs)

**Sector Campaigns (22 CSVs in BACKUP_20260321/campaigns/):**
agrifood, aluminum, beef, cleantech, coffee, copper, fruits, honey, lithium, lumber, machinery, minerals, niobium, poultry, pulp_paper, salmon, seafood, shrimp, soy, steel, sugar, wine + `eu_beef_meat_buyers.csv`

**Enriched Exporters (8 in BACKUP_20260321/data/):**
beef, honey, lithium, niobium (raw + enriched versions)

**Brazil Deep Data (11 in TOTAL_SCRAPER/data/brazil/):**
brazil_all_enriched, brazil_exporters_full, brazil_winners, brazil_producers, brazil_cnpja, connectamericas, dadosgov, transparencia, sample_cnpj

**Ventas en Europa (14 CSVs):**
mercosur_producers_all/clean, productores_mercosur, argentina_exporters, brazil_associations/states/cnpja/major, abiec_members_deep, latam_extra_emails, campana_productores, small_producers_emails

**Other (5):**
chile_exports, uruguay_exp, connectamericas_exporters, mercosur_ted_sample (3 versions), embassy contacts

---

## 12. NATO — Military Procurement
**Status:** ACTIVE

### Code (5 scripts)
| Script | What it does |
|--------|-------------|
| `OPENCODE/scripts/analyze_seap_market.py` | Analyze SEAP military procurement |
| `OPENCODE/scripts/cap_matchmaker.py` | Match capabilities to requirements |
| `OPENCODE/scripts/cap_monitor.py` | Monitor capability changes |
| `OPENCODE/scripts/phase1_tracker.py` | Track Phase 1 progress |
| `OPENCODE/scripts/quick_setup.py` | Quick setup for NATO pipeline |

---

## 13. PRODUS MONTAN — Mountain Products (680 producers)
**Status:** ACTIVE | **Data:** 1,331 producers, organic agriculture

### Code (15 scripts)
| Script | What it does |
|--------|-------------|
| `CODE/produs_montan_parse.py` | Parse RNPM data |
| `CODE/create_produs_montan_db.py` | Create PostgreSQL database |
| `CODE/generate_catalog.py` | Generate HTML product catalog |
| `CODE/deploy_catalog.py` | Deploy catalog to A2 Hosting |
| `CODE/generate_woocommerce_csv.py` | Export to WooCommerce format |
| `CODE/campaign_cos_legume.py` | Vegetable basket campaign |
| `CODE/publish_2026_post.py` | Publish WordPress post |
| `CODE/update_post_contact.py` | Update contact info on posts |
| `CODE/check_enrichment.py` | Verify enrichment quality |
| `CODE/check_phones.py` | Validate phone numbers |
| `CODE/show_clean_sample.py` / `show_phones.py` | Data inspection |
| `CODE/test_html.py` / `test_phone_format.py` | Testing |

### Scrapers (8 scripts)
| Script | What it scrapes |
|--------|----------------|
| `CODE/SCRAPER/scrape_produsmontan.py` | RNPM mountain product registry |
| `CODE/SCRAPER/fetch.py` | Fetch RNPM pages |
| `CODE/SCRAPER AGRICULTURA ECOLOGICA/CODE/scraper.py` | Organic agriculture registry |
| `CODE/SCRAPER AGRICULTURA ECOLOGICA/CODE/scraper_v2.py` | Organic scraper v2 |
| `CODE/SCRAPER AGRICULTURA ECOLOGICA/CODE/clean_data.py` | Clean scraped data |
| `CODE/SCRAPER AGRICULTURA ECOLOGICA/CODE/contact_enricher.py` | Enrich organic producer contacts |
| `CODE/SCRAPER AGRICULTURA ECOLOGICA/CODE/to_ascii.py` | Convert diacritics |
| `CODE/SCRAPER AGRICULTURA ECOLOGICA/CODE/deploy_to_pis.sh` | Deploy to Raspberry Pi |

### Data (17 CSVs + 3 JSONs)
| File | What it contains |
|------|-----------------|
| `DATA/rnpm_producers_1331.csv` | 1,331 mountain producers |
| `DATA/rnpm_producers_no_email_354.csv` | 354 producers without email |
| `DATA/PRODUS MONTAN PRODUCATORI.csv` | Producer master list |
| `DATA/RNPM 10.07.2023 CARNE FISIER LUCRU.csv` | Meat producers |
| `DATA/cooperative_functionale.csv` | Functional cooperatives |
| `DATA/cooperative_top50_alimentare_montane.csv` | Top 50 food cooperatives |
| `DATA/cooperative_top50_enriched.csv` | Enriched top 50 |
| `DATA/woo_products.csv` | WooCommerce product export |
| `DATA/DATE EXTRASE/rnpm email.csv` | Extracted emails |
| `DATA/DATE EXTRASE/contact rnpm telefon*.csv` | Extracted phones (2 files) |
| `mountain_producers.csv` | Root-level producer list |
| `CODE/SCRAPER/rnpm_producers_2026-03-07.csv` | Scrape snapshot Mar 7 |
| `CODE/SCRAPER/rnpm_producers_2026-03-11.csv` | Scrape snapshot Mar 11 |
| `CODE/SCRAPER/rnpm_fresh_2026-03-07.csv` | Fresh produce Mar 7 |
| Organic: `producers.csv`, `producers_clean.csv`, `producers_enriched.csv` | Organic producer pipeline |
| Organic: `producers.json`, `enrichment_stats.json`, `stats.json` | Organic metadata |

---

## 14. TRASABILITATE PRODUS ALIMENTAR — Food Traceability SaaS
**Status:** FROZEN (awaiting Kaufland) | **Data:** Target clients

### Code (7 scripts)
| Script | What it does |
|--------|-------------|
| `analyze_targets.py` | Analyze potential SaaS clients |
| `PRODUS TRASABIL/backend/app.py` | FastAPI backend |
| `PRODUS TRASABIL/backend/init_db.py` | Database initialization |
| `PRODUS TRASABIL/cli/trasabilitate.py` | CLI tool |
| `PRODUS TRASABIL/consolidate_documents.py` | Document consolidation |
| `PRODUS TRASABIL/scripts/seed_demo.py` | Seed demo data |
| `PRODUS TRASABIL/scripts/deploy.sh` | Deployment script |
| `PRODUS TRASABIL/tests/test_api.py` | API tests |

### Data (1 CSV)
| File | What it contains |
|------|-----------------|
| `TARGET_CLIENTS.csv` | Potential SaaS clients |

---

## 15. UNIFIED DB USAGE — Database Helper Tools
**Status:** REFERENCE

### Code (2 scripts)
| Script | What it does |
|--------|-------------|
| `company_lookup.py` | Look up companies in PostgreSQL |
| `db_helper.py` | Database connection helper |

---

## TOTALS

| Category | Count |
|----------|-------|
| **Project scripts** | 120+ |
| **Scrapers** | 55+ |
| **Data CSVs** | 150+ |
| **JSON/DB files** | 15+ |
| **Active projects** | 8 (FOOD, MERCOSUR, NATO, PRODUS MONTAN, LLM, ASOCIATII, CHINA, UNIFIED DB) |
| **Frozen** | 4 (COOPERATIVA, TRASABILITATE, LEO CASA, DATING) |
| **Ready to launch** | 2 (GUMROAD, FRESKON) |
