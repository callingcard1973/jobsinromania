---
name: silozuri-orchestrator
description: Full silozuri enrichment + validation + campaign prep orchestrator. Coordinates 4 specialist agents: data-collector (MADR/ANAF parsing), data-enricher (contact backfill), data-analyst (quality validation), campaign-ready (segmentation). Use when the user says "enrich silozuri", "prepare silozuri campaigns", "validate silozuri data", "rebuild silozuri from scratch", "update silozuri pipeline", or when running automated daily/weekly silozuri maintenance. Always use this for silozuri domain work instead of calling individual agents/skills.
---

# SILOZURI Orchestrator

Master workflow: Collect → Enrich → Analyze → Segment → Campaign Ready

## Scope

**Do use orchestrator for:**
- "Enrich the silozuri data" (full pipeline)
- "Prepare silozuri for Brevo campaigns" (end-to-end)
- "Rebuild from MADR + ANAF sources" (collection + enrichment)
- "Validate and segment silozuri" (analysis + campaign prep)
- Scheduled daily/weekly updates

**Do NOT use orchestrator for:**
- Simple questions ("How many TIER_1 records?") → run data-analyst directly for analysis only
- Emergency edits to existing CSVs → use CSV tools directly
- Brevo send orchestration → use silozuri-campaign skill

---

## Workflow Architecture

**Execution mode:** Sub-agent (Sequential, no team communication)

**Data flow:**
```
Phase 0: Context Check
  ↓
Phase 1: Data Collector (MADR + ANAF parsing)
  ↓
Phase 2: Data Enricher (Contact backfill)
  ↓
Phase 3: Data Analyst (Quality validation + tier)
  ↓
Phase 4: Campaign Ready (Segmentation)
  ↓
Final: Summary + send plan
```

**Files:**
- Workspace: `_workspace/` (intermediate files, cleaned up after success)
- Output: `DATA/MASTER.csv`, `DATA/MASTER_TIER1_READY_TO_CALL.csv`, `BUYERS/cereal_buyers_romania.csv`

---

## Phase 0: Context Check

**Determine execution mode:**

1. **Initial run** (no `_workspace/` directory):
   - Run full pipeline: Collect → Enrich → Analyze → Segment
   
2. **Re-run with same data:**
   - If `_workspace/01_collector_raw_merged.csv` exists + user says "re-enrich" → Skip Collector, start at Enricher
   - If `_workspace/02_enricher_enriched.csv` exists + user says "re-analyze" → Skip Collector+Enricher, start at Analyst
   
3. **Partial update:**
   - If user provides new MADR files or enrichment sources → Run full pipeline (safest)

**Decision tree:**
```
if no _workspace/:
  → Full pipeline (Collect → Enrich → Analyze → Segment)
elif _workspace/01_collector_raw_merged.csv exists AND user says re-enrich:
  → Skip Collector, run Enrich → Analyze → Segment
elif _workspace/03_analyst_validated.csv exists AND user says re-segment:
  → Skip Collector+Enricher+Analyst, run Segment only
else:
  → Default to full pipeline (safest)
```

---

## Phase 1: Data Collector

**Agent:** `data-collector`  
**Skill:** `data-collector`

**Prompt to agent:**

```
Parse all MADR county Excel files (DATA/raw/MADR_*.xlsx) and ANAF od_firme.csv.
Merge and deduplicate. Output to _workspace/01_collector_raw_merged.csv.

Key rules:
- auth_code is the facility PK; never merge distinct auth_codes
- Dedup by: name core-match OR CUI match → distinct auth_code
- County normalization: Standardize RO diacritics
- Output schema: auth_code, name, phone, email, county, city, cui, caen, capacity_total_t, capacity_grains_t, capacity_oilseeds_t, _source

Report:
- Row counts per county
- Merge stats (MADR + ANAF)
- Dedup collisions
```

**Success criteria:**
- `_workspace/01_collector_raw_merged.csv` exists
- Row count: 13K+ records
- Schema matches expected columns

**Failure handling:**
- If Collector fails → Stop, report error (user must fix MADR files or re-run)

---

## Phase 2: Data Enricher

**Agent:** `data-enricher`  
**Skill:** `data-enricher`

**Input:** `_workspace/01_collector_raw_merged.csv`

**Prompt to agent:**

```
Enrich raw silos with phone, email, CUI via CUI-join.

Sources:
- raspibig DB public.companies_clean table (phone, email, county, CAEN) — via SSH/plink to 192.168.100.21
- raspibig DB public.master_emails table (email lookup) — via SSH/plink
- DATA/raw/ANAF/od_firme.csv (CUI + county fallback)

Rules:
- Fill only blank fields (never overwrite)
- Normalize phones to E.164 format (+40...)
- CUI-join: use first match per CUI
- Blank detection: NaN, empty string, whitespace-only

Output: _workspace/02_enricher_enriched.csv + coverage report
```

**Success criteria:**
- `_workspace/02_enricher_enriched.csv` exists
- Coverage improved (email %, phone %, county %)
- Report shows fields filled per source

**Failure handling:**
- If Enricher fails → Output best-effort CSV + error log (continue to Analyst)

---

## Phase 3: Data Analyst

**Agent:** `data-analyst`  
**Skill:** `data-analyst`

**Input:** `_workspace/02_enricher_enriched.csv`

**Prompt to agent:**

```
Validate data quality and assign tiers.

Tier rules:
- TIER_1: CUI ✓ AND (phone ✓ OR email ✓)
- TIER_2: CUI ✓ AND (no contact)
- TIER_3: CUI ✗ AND (phone ✓ OR email ✓)
- TIER_4: No CUI, no phone, no email

Quality checks:
- Capacity validation (numeric, > 0, < 1B, components consistent)
- County consistency (RO official list)
- Phone/email format (E.164 or empty)
- Contact flags: NO_CUI, NO_PHONE, NO_EMAIL, NO_CONTACT, CLEAN

Output: _workspace/03_analyst_validated.csv (with _quality_tier, _issues columns) + report
Save: DATA/MASTER.csv (canonical)
```

**Success criteria:**
- `_workspace/03_analyst_validated.csv` exists
- _quality_tier column populated (TIER_1-4)
- _issues column has flags
- Report shows tier breakdown + coverage %

**Failure handling:**
- If Analyst fails → Output best-effort CSV (continue to Campaign Ready)

---

## Phase 4: Campaign Ready

**Agent:** `campaign-ready`  
**Skill:** `campaign-ready`

**Input:** `_workspace/03_analyst_validated.csv`

**Prompt to agent:**

```
Segment validated data into campaign-ready CSVs.

Segments:
1. TIER_1 (808 rows) → DATA/MASTER_TIER1_READY_TO_CALL.csv
   - CUI ✓ AND (phone ✓ OR email ✓)
   - Use: Phone-first cold calls
   
2. Cereal buyers (7,934 rows) → BUYERS/cereal_buyers_romania.csv
   - CAEN in (4621, 4622) AND (phone ✓ OR email ✓)
   - Use: Supply-chain B2B
   
3. TIER_2 email (450 rows)
   - TIER_2 AND email ✓
   
4. TIER_3 phone (1,200 rows)
   - TIER_3 AND phone ✓

Brevo format:
- Columns: name, phone (E.164), email, county, city, auth_code, capacity_total_t, caen, _quality_tier
- UTF-8 encoding, no BOM
- No duplicate dedup (Brevo will handle)

Output:
- Campaign CSVs to DATA/ and BUYERS/
- Send plan recommendation to _workspace/04_campaign_segments.txt
  - Rates: TIER_1 50/day, CEREAL 100/day ramp, TIER_2 25/day
  - Timeline: 79 days (CEREAL rate-limiting)
```

**Success criteria:**
- `DATA/MASTER_TIER1_READY_TO_CALL.csv` exists (808 rows)
- `BUYERS/cereal_buyers_romania.csv` exists (7,934 rows)
- `_workspace/04_campaign_segments.txt` has send plan
- All CSVs valid Brevo format

**Failure handling:**
- If Campaign Ready fails → Output best-effort CSVs (user can review manually)

---

## Final: Summary + Cleanup

**On success:**

1. Report summary:
   - Data Collector: Parsed all MADR counties + ANAF, deduped to 13K+ records
   - Data Enricher: Enriched phone/email/CUI from raspibig DB + ANAF
   - Data Analyst: Validated quality, assigned tiers (TIER_1/2/3/4)
   - Campaign Ready: Segmented into campaign CSVs (TIER_1, Cereal buyers)
   
2. Output files ready:
   - DATA/MASTER.csv (canonical, tiered + validated)
   - DATA/MASTER_TIER1_READY_TO_CALL.csv (TIER_1 for phone calls)
   - BUYERS/cereal_buyers_romania.csv (cereal buyers, CAEN 4621/4622)
   
3. Next: Use silozuri-campaign skill to send to Brevo

2. Keep `_workspace/` directory (audit trail + fast re-run)

3. Report to user: Data ready, campaign CSVs exported, send plan available

**On failure (any phase):**

1. Report which phase failed + error details
2. Save error logs in `_workspace/`
3. Suggest:
   - Re-run just the failed phase (reuse earlier outputs)
   - Or re-run full pipeline from start
4. Keep `_workspace/` for debugging

---

## Triggering from User

**Use cases:**

1. **Initial enrichment:**
   - User: "Enrich silozuri data"
   - Orchestrator: Runs full pipeline (Collect → Enrich → Analyze → Segment)

2. **Re-enrich with new sources:**
   - User: "Re-enrich silozuri, I have new emails"
   - Orchestrator: Skips Collector (reuse raw), runs Enricher → Analyst → Campaign

3. **Re-analyze + segment:**
   - User: "Re-segment TIER_1, update campaign lists"
   - Orchestrator: Skips Collector+Enricher, runs Analyst → Campaign

4. **Full rebuild:**
   - User: "Rebuild silozuri from scratch" or "Parse new MADR files"
   - Orchestrator: Full pipeline (delete `_workspace/`, start fresh)

---

## Monitoring & Alerts

**Track:**
- Each phase duration (Collect: 2 min, Enrich: 5 min, Analyst: 3 min, Campaign: 1 min)
- Success/failure per phase
- Row counts before/after enrichment
- Coverage improvements

**Alert on:**
- Phase timeout (>30 min per phase = investigate)
- Row count drop (Enrich removes rows → investigate dedup)
- TIER_1 drops below 500 (coverage regression)

---

## Test Scenarios

See `silozuri-orchestrator` test section below.

---

## Test Scenarios (for validation)

**Scenario 1: Fresh run**
- Delete `_workspace/`
- User: "Enrich silozuri"
- Expected: Full pipeline, all phases succeed
- Verify: TIER_1 ≈808, Cereal ≈7,934

**Scenario 2: Re-enrich**
- Keep `_workspace/01_collector_raw_merged.csv`
- User: "Re-enrich with new emails"
- Expected: Skip Collector, run Enricher → Analyst → Campaign
- Verify: Coverage improves, TIER_1 increases

**Scenario 3: Re-segment**
- Keep `_workspace/03_analyst_validated.csv`
- User: "Update campaigns"
- Expected: Skip Collector+Enricher+Analyst, run Campaign only
- Verify: Output CSVs updated, send plan refreshed

**Scenario 4: Error recovery**
- Simulate Enricher failure (missing master_romania_companies.csv)
- Expected: Log error, output best-effort CSV, continue to Analyst
- Verify: Partial enrichment, coverage lower than normal

---

## References

- Agent definitions: `.claude/agents/{data-collector,data-enricher,data-analyst,campaign-ready}.md`
- Skills: `.claude/skills/{data-collector,data-enricher,data-analyst,campaign-ready}/SKILL.md`
- CLAUDE.md: Harness pointer + change log
