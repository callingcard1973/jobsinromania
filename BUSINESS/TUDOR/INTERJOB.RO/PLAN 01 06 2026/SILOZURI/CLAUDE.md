# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**v1.2 | 2026-06-23**

---

## HARNESS: SILOZURI DATA PIPELINE

**Goal:** Automated enrichment + validation + campaign-ready segmentation for 13K+ silo records.

**Trigger:** Use `silozuri-orchestrator` skill for any silozuri domain work:
- "Enrich silozuri data"
- "Prepare campaigns"
- "Validate coverage"
- "Rebuild from MADR sources"

**Architecture:** 4-agent sub-agent model
- `data-collector` — MADR county + ANAF parsing (ANAF optional if missing)
- `data-enricher` — Phone/email/CUI backfill via raspibig DB
- `data-analyst` — Quality validation + tier assignment
- `campaign-ready` — Segmentation for outreach

**Change History:**
| Date | Change | Reason |
|------|--------|--------|
| 2026-06-23 | Harness v1.0 added (4 agents + 5 skills, droid verified) | Automate full data pipeline |
| 2026-06-23 | ANAF optional (skip if missing) | od_firme.csv not present; enricher uses raspibig DB |
| 2026-06-26 | MADR 2025 refresh + enrich (tasks 1,2,5,6,10) | +2,814 noi silozuri (13,287→16,101); CUI 64→75%, phone 60→74%; market matrix; buyers email |
| 2026-06-26 | Skill `silozuri-market-intel` added (data-analyst) | Cross-match ONRC status/DSVSA/ANOFM → MASTER_INTELLIGENCE.csv; flag 5,995 `radiata` (dead) + 412 insolvent |

---

## CAMPAIGN STATUS: SILOZURI

**Contacts prepared:** 1,049 (with email)
**Contacts sent:** 0 (as of 2026-06-23, dry-run mode only)
**Daily limit:** 290/day via Brevo (office@cumparlegume.com)
**Last run:** 2026-06-20 13:42:59
**Status:** Ready but NOT LIVE (dry_run=True, cron disabled)

**See:** MEMORY.md for full campaign status + next steps

---

## PROJECT OVERVIEW

Master directory of Romanian agricultural storage facilities (silozuri) — 13,287 unique entities from 4 merged MADR/ANAF sources. Goal: B2B outreach to silo operators (lead-gen, supply-chain mapping, cooperative aggregation).

**Primary output:** `DATA/MASTER.csv` (14 cols) + `DATA/MASTER_TIER1_READY_TO_CALL.csv` (808 rows).

---

## CURRENT STATE

- **13,287 unique entities** — deduped, remediated 2026-06-14
- **Schema:** `auth_code, name, phone, email, county, city, cui, caen, capacity_total_t, capacity_grains_t, capacity_oilseeds_t, _source, _quality_tier, _issues`
- **`auth_code`** = MADR silo license code — the true facility key; never merge distinct auth_codes
- **Quality tiers:** TIER_1 808 (CUI+contact) · TIER_2 7,664 (CUI only) · TIER_3 2,294 (contact only) · TIER_4 2,521
- **Coverage:** CUI 63.8% · county 80.7% · city 65.3% · phone 22.4% · email 6.1%
- **48 rows** flagged `BAD_CAPACITY` (garbage parse values)
- **Backups:** `ARCHIVE/MASTER_pre_remediation_*.csv`

---

## SCRIPTS (`CODE/`)

Toate scripturile sunt în `CODE/`. Se rulează din root-ul SILOZURI:

```
cd "D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\SILOZURI"
python CODE\remediate_master.py
```

Path-urile din scripturi sunt **absolute** (ROOT hardcodat la SILOZURI root) — funcționează indiferent de unde se rulează.

### Pipeline activ

| Script | Scop |
|--------|------|
| `CODE\remediate_master.py` | **Rebuild canonic** — backfill CUI/county din ANAF, redenumire coloane, tiere, dedup |
| `CODE\analyze_master.py` | **QA read-only** — stats acoperire, tier breakdown, capacitate |
| `CODE\merge_masters.py` | Merge surse raw în master pre-remediere |
| `CODE\enrich_master.py` | Enrichment telefoane din `companies_clean` pe raspibig (SSH) |
| `CODE\enrich_email.py` | Enrichment emailuri din `master_emails` pe raspibig |
| `CODE\enrich_via_anaf_dsvsa.py` | Cross-reference lista ANAF DSVSA firme agro |
| `CODE\build_cereal_buyers.py` | Construiește `BUYERS/cereal_buyers_romania.csv` (CAEN 4621/4622) |

### Scripturi legacy (preced remedierea — păstrate pentru referință)

`CODE\build_master.py`, `CODE\enrich_anofm.py`, `CODE\enrich_anofm_final.py`, `CODE\enrich_cui.py`, `CODE\normalize_and_regulate.py`, `CODE\dump_anofm.sh`, `CODE\extract_silos_madr.py`, `CODE\parse_madr.py`, `CODE\parse_madr_correct.py`, `CODE\parse_all_43_counties.py`, `CODE\parse_all_formats.py`, `CODE\enrich_silos.py`, `CODE\final_interjob_match.py`

---

## DATA SOURCES

- `DATA/raw/ANAF/od_firme.csv` — ANAF open-data company registry (used for CUI + county backfill)
- `DATA/raw/` — Raw MADR county Excel files (source of silo licenses + capacity)
- `DATA/csv/` — Intermediate parsed CSVs before merge
- `BUYERS/` — Separate cereal buyers list (CAEN 4621/4622 from companies_clean)

---

## KEY INVARIANTS

- **Do NOT merge rows with different `auth_code` values** — each is a distinct licensed facility
- **Dedup key for cross-source merging:** (name core-match OR CUI match) AND distinct auth_code
- Phone normalization: E.164 `+40...` (strip non-digits, convert `0040→+40`, `07→+407`)
- Name matching: strip diacritics → uppercase → remove legal tokens (SRL, SA, PFA…) → compare core tokens
- ANAF enrichment source: local `od_firme.csv` (not ANAF API — API returns 0 matches)
- DB enrichment runs via SSH plink to raspibig `192.168.100.21` (see CLAUDE.md root for plink syntax)

---

## NEXT ENRICHMENT OPPORTUNITIES

1. **Google Places API** — fetch emails for TIER_2 (7,664 with CUI, no contact)
2. **raspibig `master_emails`** — already partially applied; re-run `enrich_email.py` after new email imports
3. **DAJ county pages** — web scrape county Agriculture Directorates for licensed operators
4. **LinkedIn** — manager names for top-50 operators by capacity

---

## OUTREACH READINESS

- **TIER_1 (808):** `DATA/MASTER_TIER1_READY_TO_CALL.csv` — phone-first cold calls
- **Brevo campaign:** use `email` column; integrate via brevo-sender agent
- **Phone-first strategy** — email plateau at ~6%; phone coverage 22% (post-enrichment up to 60% on subsets)
