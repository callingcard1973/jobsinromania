# IDEAS — Inventar Cod, Scrapere si Date (2026-04-12)

Sincronizat pe LOCAL (`D:\MEMORY\IDEAS\`) si RASPIBIG (`/opt/ACTIVE/IDEAS/`)

---

## 1. ASOCIATII — Registru ONG-uri Romania
**Status:** INGHETAT | **Date:** 90K+ ONG-uri in 42 judete

### Cod (4 scripturi)
| Script | Ce face |
|--------|---------|
| `generate_ong_registry.py` | Genereaza registrul complet ONG |
| `generate_ong_shortlist.py` | Filtreaza top 5.000 ONG-uri |
| `deploy_ong_to_raspibig.py` | Trimite datele in PostgreSQL pe raspibig |
| `raspibig_ong_ingest_remote.py` | Ingestie date pe raspibig |

### Date (49 CSV-uri)
| Fisier | Ce contine |
|--------|-----------|
| `ONG_ACTIVE.csv` | Toate ONG-urile active din Romania |
| `ONG_REGISTRU_NATIONAL.csv` | Extras registru national |
| `ONG_SHORTLIST_5000.csv` | Top 5.000 filtrate |
| `ONG_SUMAR_JUDETE.csv` | Sumar pe judete |
| `ONG_SUMAR_LOCALITATI.csv` | Sumar pe localitati |
| `JUDETE_ORASE_RO.csv` | Judete si orase Romania (4.706 randuri) |
| `ong_pe_judete/ong_active_*.csv` | 42 fisiere pe judet (alba pana la vrancea) |

---

## 2. CHINA — Date Comerciale si Manufacturieri
**Status:** CERCETARE | **Date:** Producatori + indicatori economici

### Scrapere (3 scripturi)
| Script | Ce scrapeaza |
|--------|-------------|
| `scrapers/made_in_china.py` | Listari producatori Made-in-China.com |
| `scrapers/nbs_china_api.py` | API Biroul National Statistica China (PIB, IPC, exporturi) |
| `scrapers/un_comtrade.py` | Statistici comert international UN Comtrade |

### Date (8 CSV-uri)
| Fisier | Ce contine |
|--------|-----------|
| `data/manufacturers/electronics_20260322.csv` | Producatori electronice |
| `data/manufacturers/machinery_20260322.csv` | Producatori utilaje industriale |
| `data/nbs/china_trade_2020_2024.csv` | Comert China 2020-2024 |
| `data/nbs/gdp_20260322.csv` | Date PIB |
| `data/nbs/cpi_20260322.csv` | Indice preturi consum |
| `data/nbs/industrial_output_20260322.csv` | Productie industriala |
| `data/nbs/exports_total_20260322.csv` | Exporturi totale |
| `data/opendata/chinese_ie_sample.csv` | Esantion companii import/export |

---

## 3. COOPERATIVA BUSINESS — Cooperativa Export UE
**Status:** INGHETAT (nevoie de co-fondator) | **Date:** 140 producatori + cumparatori UE

### Cod (2 scripturi)
| Script | Ce face |
|--------|---------|
| `scripts/week1_consolidate_producers.py` | Consolideaza 140 producatori |
| `scripts/week1_segment_buyers.py` | Segmenteaza cumparatori hipermarket/diaspora |

### Date (4 CSV-uri)
| Fisier | Ce contine |
|--------|-----------|
| `data_working/cooperatives_full.csv` | Toate cooperativele |
| `data_working/master_producers_consolidated.csv` | Lista master 140 producatori |
| `data_working/hypermarket_targets_25emails.csv` | 25 contacte hipermarket UE |
| `data_working/italy_diaspora_shops_sample.csv` | Magazine diaspora Italia |

---

## 4. DATING — Cautare fdating.com
**Status:** PLANIFICAT | **Date:** Inca nu

Fara cod sau date. Plan salvat in `FDATING_SEARCH.md`.

---

## 5. FOOD — HORECA + Supermarketuri + SEAP
**Status:** ACTIV | **Date:** 28K emailuri HORECA, castigatori SEAP, industria alimentara

### Cod (25 scripturi in SUPERMARKETS_CLAUDE/CODE/)
| Script | Ce face |
|--------|---------|
| `create_db.py` | Initializeaza baza de date industrie alimentara |
| `consolidate.py` | Combina toate sursele de date alimentare |
| `segment_and_analyze.py` | Segmenteaza companii dupa tip/dimensiune |
| `enrich_food_raspibig.py` | Imbogateste contacte din raspibig DB |
| `deep_enrich_raspibig.py` | Imbogatire profunda (telefon, email, ANAF) |
| `fuzzy_enrich_raspibig.py` | Potrivire fuzzy pentru imbogatire |
| `enrich_from_db.py` | Imbogatire bazata pe DB |
| `enrich_master_index.py` | Imbogatire index master |
| `enrich_seap_winners.py` | Imbogateste 3.030 castigatori SEAP alimentari |
| `ultimate_enrich_raspibig.py` | Trecere finala imbogatire |
| `web_email_finder.py` | Scrapeaza site-uri web pentru adrese email |
| `query_food_contacts.py` | Interogheaza contacte imbogatite |
| `scan_all_sources.py` | Scaneaza toate sursele de date alimentare |
| `seap_extract.py` | Extrage date achizitii publice SEAP |
| `seap_cross_match.py` | Potriveste SEAP cu DB companii |
| `seap_food_alerts.py` | Alerte licitatii alimentare noi |
| `seap_alert_dispatcher.py` | Trimite alerte licitatii |
| `faliment_cross_match.py` | Potriveste companii alimentare cu insolventa |
| `faliment_opportunities.py` | Gaseste oportunitati active falimentare |
| `campaign_dashboard.py` | Panou vizualizare campanii |
| `campaign_export.py` | Export CSV-uri pregatite de campanie |
| `campaign_templates.py` | Sabloane email pentru outreach alimentar |
| `shared_utils.py` | Functii utilitare partajate |

### Scripturi exploratorii (11 in CODE/exploratory/)
| Script | Ce face |
|--------|---------|
| `ddg_email_search.py` | Cautare email prin DuckDuckGo |
| `inspect_all_dbs.py` | Inspecteaza toate bazele PostgreSQL |
| `scan_all_pg_dbs.py` | Scaneaza toate DB-urile PG pentru tabele alimentare |
| `scan_big_csvs.py` | Scaneaza CSV-uri mari pentru date alimentare |
| `search_liquidators.py` | Gaseste contacte lichidatori |
| `listafirme_cui_lookup.py` | Cautare CUI pe ListaFirme.ro |
| `test_listafirme*.py` (4) | Iteratii scraper ListaFirme |
| `test_web_finder.py` | Test cautare email web |

### Date (23+ CSV-uri)
| Fisier | Ce contine |
|--------|-----------|
| `HORECA_28K_UNIQUE_EMAILS.csv` | **28K contacte HORECA** (20K RO, 5.6K NO, 800 BG, 350 DK) |
| `DATA/ALL_SUPERMARKET_CHAINS.csv` | Toate lanturile de supermarketuri UE |
| `DATA/SUPERMARKETS_RO.csv` | Supermarketuri Romania |
| `DATA/HORECA_RO.csv` | Hoteluri/restaurante/catering RO |
| `DATA/DISTRIBUTORS_RO.csv` | Distribuitori alimentari RO |
| `DATA/DAIRY_RO.csv` | Companii lactate RO |
| `DATA/COLD_STORAGE_RO.csv` | Depozite frigorifice RO |
| `DATA/MEAT_PROCESSORS_RO.csv` | Procesatori carne RO |
| `DATA/LOGISTICS_RO.csv` | Companii logistica RO |
| `DATA/WHOLESALE_EUROPE.csv` | Distribuitori en-gros UE |
| `DATA/MASTER_CLEAN.csv` | Baza date master curatata |
| `DATA/seap_food_winners_enriched.csv` | Castigatori SEAP imbogatiti (3.030) |
| `DATA/seap_food_winners_all.csv` | Toti castigatorii SEAP alimentari |
| `DATA/insolvent_contacts_flagged.csv` | Companii insolvente marcate |
| `DATA/CAMPAIGN_SEGMENTS/TIER0-3` | Segmente campanie (4 fisiere) |

---

## 6. FRESKON — Expozanti Targuri Comerciale
**Status:** ACTIV

### Date (1 CSV)
| Fisier | Ce contine |
|--------|-----------|
| `freskon_exhibitors.csv` | Contacte expozanti targuri europene |

---

## 7. GUMROAD — Vanzare Pachete Date
**Status:** GATA | **Date:** Descrieri produse + sabloane

Fara cod. Contine `/descriptions/` si `/products/` cu sabloane pentru vanzare date.

---

## 8. LEGUME MASINI DE SORTAT — Utilaje Sortare Legume
**Status:** CERCETARE

### Cod (1 scraper)
| Script | Ce scrapeaza |
|--------|-------------|
| `scrape_competitors.py` | Companii concurente utilaje sortare |

---

## 9. LEO CASA BUZAU — Inchiriere Proprietati (Judetul Buzau)
**Status:** DATE GATA (asteptam Leo) | **Date:** 34K+ companii

### Date (11 CSV-uri — etape multiple imbogatire)
| Fisier | Ce contine |
|--------|-----------|
| `buzau_potrivite_companies_FINAL.csv` | Companii potrivite pentru inchiriere |
| `LEO_BUZAU_FINAL_ENRICHED.csv` | Versiune finala imbogatita |
| `LEO_BUZAU_WITH_EMAIL.csv` | Companii cu contacte email |
| `leo_anaf_enriched.csv` | Imbogatite din registru ANAF |
| `leo_enriched*.csv` (variante) | Iteratii imbogatire |
| `leo_final*.csv` (variante) | Versiuni finale |

---

## 10. LLM — Clasificator Email si Raspunsuri Automate
**Status:** ACTIV | **Date:** Date antrenament, baza etichete

### Cod (7 scripturi)
| Script | Ce face |
|--------|---------|
| `email_responder.py` | Sistem raspunsuri email automate |
| `gmail_drafter.py` | Generator ciorne Gmail |
| `train_classifier.py` | Antreneaza clasificator sklearn (94.5% acuratete) |
| `import_labels_to_pg.py` | Importa etichete in PostgreSQL |
| `response_templates.py` | Biblioteca sabloane raspuns |
| `test_local.py` | Framework testare locala |
| `deploy.sh` | Deploy pe raspibig |

### Date (5 fisiere)
| Fisier | Ce contine |
|--------|-----------|
| `labels.db` | Baza date etichete SQLite |
| `config.json` | Configurare |
| `training_data/manual_labels_batch1-2.json` | Date antrenament (2 loturi) |
| `training_data/seen_message_ids.json` | Urmarire mesaje procesate |
| `training_data/collector_stats.json` | Statistici colectare |

---

## 11. MERCOSUR — Informatii Comerciale America Latina
**Status:** ACTIV | **Date:** 22 campanii sectoriale, contacte ambasade, CNPJ Brazilia

### Scrapere (40+ scripturi)

**API-uri Guvernamentale (5):** apex_brasil, argentina_exporta, prochile, rediex_paraguay, uruguay_xxi
**Registre Companii (4):** argentina_afip, brazil_cnpj, chile_sii, uruguay_dgi
**Asociatii Comerciale (6):** abiec_beef, abemel_honey, ibram_mining, ipcva_argentina, sada_honey_ar, wines_argentina
**Targuri Comerciale (5):** apas_show, expoaladi, fenavinho, fispal, mercoagro
**Directoare (4):** connectamericas, dnb_latam, kompass_latam, trademap
**Producatori pe Tara (5):** brazil, argentina, chile, paraguay, uruguay
**Imbogatire (6):** enrich_all_brazil, enrich_brazil_cnpj, enrich_exporters, enrich_gentle, etc.
**Orchestrare (5):** orchestrator, merger, workeri specializati, run_all, gentle_runner
**Ambasade (2):** send_embassy_letters, send_mercosur_bucuresti

### Date (50+ CSV-uri)
- **22 campanii sectoriale:** agrifood, aluminum, beef, cleantech, coffee, copper, fruits, honey, lithium, lumber, machinery, minerals, niobium, poultry, pulp_paper, salmon, seafood, shrimp, soy, steel, sugar, wine
- **Exportatori imbogatiti:** beef, honey, lithium, niobium (raw + enriched)
- **Date profunde Brazilia:** brazil_all_enriched, brazil_exporters_full, brazil_winners, CNPJ
- **Vanzari in Europa:** mercosur_producers_all/clean, argentina_exporters, brazil_cnpja
- **Altele:** chile_exports, uruguay_exp, conectamericas, mostre TED, contacte ambasade

---

## 12. NATO — Achizitii Militare
**Status:** ACTIV

### Cod (5 scripturi)
| Script | Ce face |
|--------|---------|
| `analyze_seap_market.py` | Analizeaza achizitii SEAP militare |
| `cap_matchmaker.py` | Potriveste capacitati cu cerinte |
| `cap_monitor.py` | Monitorizare schimbari capacitati |
| `phase1_tracker.py` | Urmarire progres Faza 1 |
| `quick_setup.py` | Configurare rapida pipeline NATO |

---

## 13. PRODUS MONTAN — Produse de Munte (680 producatori)
**Status:** ACTIV | **Date:** 1.331 producatori, agricultura ecologica

### Cod (15 scripturi)
| Script | Ce face |
|--------|---------|
| `produs_montan_parse.py` | Parseaza date RNPM |
| `create_produs_montan_db.py` | Creeaza baza PostgreSQL |
| `generate_catalog.py` | Genereaza catalog HTML produse |
| `deploy_catalog.py` | Deploy catalog pe A2 Hosting |
| `generate_woocommerce_csv.py` | Export format WooCommerce |
| `campaign_cos_legume.py` | Campanie cosuri legume |
| `publish_2026_post.py` | Publica articol WordPress |
| `update_post_contact.py` | Actualizeaza info contact pe posturi |
| `check_enrichment.py` | Verifica calitate imbogatire |
| `check_phones.py` | Valideaza numere telefon |

### Scrapere (8 scripturi)
| Script | Ce scrapeaza |
|--------|-------------|
| `SCRAPER/scrape_produsmontan.py` | Registru RNPM produse montane |
| `SCRAPER/fetch.py` | Descarca pagini RNPM |
| `SCRAPER AGRICULTURA ECOLOGICA/CODE/scraper.py` | Registru agricultura ecologica |
| `SCRAPER AGRICULTURA ECOLOGICA/CODE/scraper_v2.py` | Scraper v2 ecologic |
| `SCRAPER AGRICULTURA ECOLOGICA/CODE/clean_data.py` | Curata date scrapate |
| `SCRAPER AGRICULTURA ECOLOGICA/CODE/contact_enricher.py` | Imbogateste contacte producatori eco |
| `SCRAPER AGRICULTURA ECOLOGICA/CODE/to_ascii.py` | Converteste diacritice |
| `SCRAPER AGRICULTURA ECOLOGICA/CODE/deploy_to_pis.sh` | Deploy pe Raspberry Pi |

### Date (17 CSV-uri + 3 JSON-uri)
| Fisier | Ce contine |
|--------|-----------|
| `DATA/rnpm_producers_1331.csv` | 1.331 producatori montani |
| `DATA/rnpm_producers_no_email_354.csv` | 354 producatori fara email |
| `DATA/PRODUS MONTAN PRODUCATORI.csv` | Lista master producatori |
| `DATA/RNPM 10.07.2023 CARNE FISIER LUCRU.csv` | Producatori carne |
| `DATA/cooperative_functionale.csv` | Cooperative functionale |
| `DATA/cooperative_top50_alimentare_montane.csv` | Top 50 cooperative alimentare |
| `DATA/cooperative_top50_enriched.csv` | Top 50 imbogatite |
| `DATA/woo_products.csv` | Export produse WooCommerce |
| `mountain_producers.csv` | Lista producatori la radacina |
| Organic: `producers.csv`, `producers_clean.csv`, `producers_enriched.csv` | Pipeline producatori eco |

---

## 14. TRASABILITATE PRODUS ALIMENTAR — SaaS Trasabilitate
**Status:** INGHETAT (asteptam Kaufland)

### Cod (7 scripturi)
| Script | Ce face |
|--------|---------|
| `analyze_targets.py` | Analizeaza clienti potentiali SaaS |
| `backend/app.py` | Backend FastAPI |
| `backend/init_db.py` | Initializare baza date |
| `cli/trasabilitate.py` | Instrument linie comanda |
| `scripts/seed_demo.py` | Populeaza date demo |
| `scripts/deploy.sh` | Script deployment |
| `tests/test_api.py` | Teste API |

### Date (1 CSV)
| Fisier | Ce contine |
|--------|-----------|
| `TARGET_CLIENTS.csv` | Clienti potentiali SaaS |

---

## 15. UNIFIED DB USAGE — Utilitare Baza de Date
**Status:** REFERINTA

### Cod (2 scripturi)
| Script | Ce face |
|--------|---------|
| `company_lookup.py` | Cauta companii in PostgreSQL |
| `db_helper.py` | Helper conexiune baza date |

---

## TOTALURI

| Categorie | Numar |
|-----------|-------|
| **Scripturi proiect** | 120+ |
| **Scrapere** | 55+ |
| **CSV-uri date** | 150+ |
| **Fisiere JSON/DB** | 15+ |
| **Proiecte active** | 8 (FOOD, MERCOSUR, NATO, PRODUS MONTAN, LLM, ASOCIATII, CHINA, UNIFIED DB) |
| **Inghetate** | 4 (COOPERATIVA, TRASABILITATE, LEO CASA, DATING) |
| **Gata de lansare** | 2 (GUMROAD, FRESKON) |
