# ABOUT BUSINESSES — operating reference

**Reconstructed 2026-06-25 from sourced memory + root CLAUDE.md** (the canonical folder was missing; rebuilt from sourced material only — no fabrication). Single source of truth for *the business entities*. Read before substantive work. Do NOT duplicate elsewhere.

The ecosystem: **AgroEvolution + InterJob + FarmWorkers** — B2B2C recruitment marketplace + agri-land marketplace + EU wholesale data + a Romanian-producer supermarket (Hambarul Romanesc). Everything is evaluated by business value: traffic, leads, revenue, data quality, market intelligence, operational efficiency, competitive edge. Source: root CLAUDE.md Strategic Directive.

---

## InterJob.ro

**Model:** B2B2C recruitment marketplace — clients → verified specialists. Pay-per-lead + subscriptions. Start vertical: **architects** (OAR verification), expandable to engineers, designers, constructors. Source: `PLAN 01 06 2026/CLAUDE.md`.

**Differentiators:** full Romanian localization, city/category SEO, mobile-first, OAR verification.

**Revenue targets:** Y1 360K RON · Y2 1.26M RON · Y3 3M RON. MVP budget ~9K EUR. Roadmap: MVP → reviews/chat/premium → mobile/SMS/AI → vertical + geographic expansion. Source: `PLAN 01 06 2026/CLAUDE.md`.

**Apply link:** https://interjob.ro/apply.html

**11 job boards (.eu domains)** — sector-specific job catalogs (bilingual RO/EN, PDF + HTML), sourced from `ij_jobs` PostgreSQL on raspibig:
- buildjobs.eu, careworkers.eu, electricjobs.eu, factoryjobs.eu, farmworkers.eu, horecaworkers.eu, internaltransfers.eu, meatworkers.eu, mechanicjobs.eu, warehouseworkers.eu
- **agroevolution.eu** — agri-land / EN (the 11th domain; see AgroEvolution below)

Source: `interjob-catalog` skill, `web-publish` skill, `interjob_harnesses_scrapers_web_rural_2026_06_24`. Catalog example: factoryjobs.eu (PDF 5.6MB + HTML, ~350 jobs), `phase3_job_catalog_handoff_2026_06_11`.

**Job data sources:** ANOFM, EURES, plus RSS. Daily pipeline → catalogs (`pipeline-orchestrator`). Master harness coordinates 9 agents + 4 daily-roundup skills; daily cycle 00:30 pipeline → 06:00 campaigns + digest → 09:00 roundup → Mon 07:00 weekly report. Source: `PLAN 01 06 2026/CLAUDE.md`, `interjob_master_harness_2026_06_23`.

---

## AgroEvolution (.com RO + .eu EN)

**Model:** agricultural-land marketplace. **~9,658 land listings**, 41 county pages, interactive map. Also hosts vegetable selling (no separate veg domain). Source: `madr_agroevolution_complete`, `project_agroevolution_vegetables`.

**Tech:** PrestaShop on A2 Hosting (cPanel deploy, Smarty cache rule). Land data from MADR (CSV → PostgreSQL → SEO pages; 41 county pages + `/pretul-terenurilor/` monthly). Source: `project_agroevolution_cpanel`, `project_agroevolution_prices`.

**agroevolution.eu** = newer EN-facing agri-land domain, wired into the InterJob SCRAPERS → PROPRIETATI RURALE (EN catalogs) → WEB deploy chain. Source: `interjob_harnesses_scrapers_web_rural_2026_06_24`.

**Buyer side:** food wholesalers / distributors AgroEvolution sells produce to — 479 email-keyed leads built (DSVSA × master_emails + ANSVSA food). Source: `wholesale_buyer_leads_2026_06_11`.

**Status note:** generation largely done, deployment lagging — TERENURI + WHOLESALE catalogs built but several never pushed live. Source: `agroevolution_not_done_2026_06_11`.

---

## FarmWorkers (farmworkers.eu)

**Model:** agricultural worker recruitment — connect farm workers (RO, BG, PL) with employers (NL, DE, DK, FR, UK). Revenue per source: €50–200/mo employer listings + 10% placement fees; Y1 target €75K–250K, 10K+ workers, 200+ employers (from FarmWorkers business proposal). Source: `FARMWORKERS_BUSINESS_PROPOSAL.md`, `farmworkers_eu_business_proposal`.

**Tech:** zero-token site (HTML5 + jobs.json + vanilla JS, SFTP deploy). CV pipeline live on raspibig (Gmail + applicant CVs → extract → HTML → farmworkers.eu/candidates/, cron). Telegram bot (9 commands). Status: ~90% ready, with documented fixes. Source: `farmworkers_eu_complete_delivery`, `farmworkers_cv_pipeline_2026_05_30`, `farmworkers_eu_website_zero_token_2026_05_30`.

Also functions as the agricultural-recruitment arm of the InterJob ecosystem (farmworkers.eu is one of the 11 job boards).

---

## ExpatsInRomania.org

**Model:** relocation funnel + Romania news empire. WordPress (audited: taxonomy + plugin prune, hardening). Source: `expatsinromania_audit_2026_05_23`.

**Automation:** `press_review.py` posts daily Romania press review to WordPress + Facebook (Expats in Romania page) at 08:50 UTC, 11 RSS sources. `city_news_aggregator` posts to Mastodon (@expatsinromania) + Telegram (@expatsinromania_news) at 09:30 UTC. Source: `news_empire_integration_2026_06_07`, `revista_presei_press_review_2026_06_04`.

---

## Hambarul Romanesc

**Model:** Romanian-producer-first supermarket. Pilot = **București Sector 1**. **15,500 origin-verified producers** (DSVSA / VIA-PROFI / SILOZURI); 2,665 CUI-verified via ONRC full registry. Bilingual business plan (PLAN_DE_AFACERI_RO + BUSINESS_PLAN_EN). Funding ask **~€500k Y1**. Source: `hambarul_supermarket_harness_2026_06_24`.

**Harness:** 9 agents + 9 skills + orchestrator (built + run end-to-end). Branch `hambarul-romanesc-harness`. CUI gate red→amber (~100 verifications needed to open).

**Note:** external/legacy domain `hambarulromanesc.ro` referenced in `claude-api_backdoor_incident_2026_06_11` (security follow-up) — relationship to the supermarket launch not confirmed in sources; mark **unknown**.

---

## Cross-cutting

**Norway construction campaign (LIVE):** cold B2B to **14,740** Norwegian construction firms (NACE 41/42/43, official Brønnøysund), offering RO/EEA workers. Sender buildjobs.eu/Brevo, warmup ramp 50→100→150→200/day. Data = 154,984 official Brønnøysund companies. Source: `norway_construction_campaign_2026_06_20`, `norway-sector-campaign` skill.

**EU wholesale data (CumparLegume / AgroEvolution buyers):** 9+ production scrapers, 735 vendors; 27+ markets across waves; €500K–€3M revenue potential. Source: `european_wholesale_markets_complete_inventory_2026_06_18`.

**Email campaign engine:** shared orchestrator on raspibig (port 8096 dashboard), 11 InterJob campaigns + sector campaigns, sender.py + campaigns.json single source of truth. Reusable across all businesses. Source: `email_campaigns_orchestrator_2026_06_12`, `campaign_dashboard_final_2026_06_13`.

---

## Boundaries (HARD)

- GitHub-synced file: **no secrets/keys/passwords, no PII, no legal/personal cases** (LUCIU / BILIE / ASOC PROP live in `PERSONAL/`, not here).
- Source every claim; mark unknowns. Never invent revenue numbers — use only sourced figures.
- Lead hygiene: do not suppress leads on temporal negative signals. Source: `feedback_temporal_signals`.
