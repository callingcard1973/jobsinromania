# CLAUDE.md — SILOZURI (Storage & Silos Directory)

**v1.0 | 2026-06-14**

---

## PROJECT OVERVIEW

**Goal:** Build a master directory of all agricultural storage facilities (silozuri) in Romania with contact info (email, phone, address, manager names).

**Use cases:**
1. Lead generation — sell to silo operators (storage optimization, grain trading, agri consultancy)
2. Supply chain mapping — know where product flows (for buyers/sellers/cooperatives)
3. Market intelligence — silo capacity by county = production indicators
4. B2B outreach — coordinate aggregation (e.g., cooperative grain sales)

---

## DATA SOURCES

| Source | Type | Coverage | Status |
|--------|------|----------|--------|
| ANAF (National Agency) | Gov registry | All commercial entities | ✅ Available (DSVSA has ag companies) |
| County Ag Directorates (DAJ) | Gov registry | By county | 🔍 To scrape |
| Google Maps / Apple Maps | Search engine | Partial | 🔍 To verify |
| MADR Databases | Ministry | Cooperatives, grain traders | ✅ MADR census exists |
| LinkedIn / Facebook | Social | Operator profiles | 🔍 To verify |
| Local business sites | Web | Ad hoc listings | 🔍 To crawl |

**Primary source:** ANAF + MADR census (most reliable, government-backed).

---

## DATA SCHEMA

```csv
silo_id, name, county, city, address, phone, email, manager_name, manager_phone, manager_email, 
capacity_tonnes, grain_types, owned_by_coop, website, source, last_verified_date
```

---

## SCRAPING STRATEGY

1. **ANAF CAEN lookup** — Search ANAF registry for CAEN codes related to grain/storage (01.13, 01.30, 49.40)
2. **DAJ county pages** — Each county has a Directorate of Agriculture with licensed operators
3. **Google/Apple** — Verify geo-location and cross-reference contact info
4. **LinkedIn** — Find operator profiles + manager details
5. **Dedup** — Email + phone + name key

---

## TOOL SELECTION

- **ro-contact-extract skill** — Auto-loads; use for PDF registries, web directories
- **MCP query** — Run PostgreSQL enrichment queries (join with master_emails, companies_clean)
- **Bash scraping** — County DAJ websites (if HTML-based)
- **Agent** — Parallel scraping (3-4 counties simultaneously)

---

## TIMELINE

- **Phase 1 (Now)** — Validate data sources, identify top 5-10 counties by silo density
- **Phase 2** — Build scraper for ANAF + DAJ
- **Phase 3** — Enrich with Google/LinkedIn verification
- **Phase 4** — Dedup, QA, publish master CSV

---

## CONSTRAINTS & NOTES

- ⚠️ **Privacy:** Phone/email from public registries only (ANAF is public; GDPR-compliant)
- ⚠️ **Rate limiting:** DAJ websites may have throttling; use 2-3s delays
- ⚠️ **Language:** ANAF/DAJ pages in Romanian; may need translation for business_name parsing
- ✅ **Budget:** Zero scraping cost (public data)

---

## Next Step

Use `ro-contact-extract` skill or Agent to:
1. Query ANAF for grain storage CAEN codes (01.13.20, 01.30.30, 49.40.51)
2. Identify top 5 counties by silo count
3. Download first batch of contact data
