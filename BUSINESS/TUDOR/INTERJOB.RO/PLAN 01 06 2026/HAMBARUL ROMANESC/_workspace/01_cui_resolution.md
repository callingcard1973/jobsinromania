# CUI Resolution — HAMBARUL ROMANESC supplier master

As-of: 2026-06-24. Source DB: `interjob_master.companies` on raspibig 192.168.100.21:5432 (laptop mirror 5433 was DOWN — connection refused).

## Method
- Matched no-CUI suppliers against `companies` (RO, numeric ANAF CUI: 117,679 rows) by normalized name (legal forms + diacritics stripped, uppercased). County not present in DB (only city/address) so match was name-driven; unique normalized-name candidate = `exact`, ambiguous = `low`.
- Backfilled SILOZURI_MASTER rows from `SILOZURI/DATA/MASTER.csv` (8,472 source CUIs + CAEN) by name+county.
- Origin verification: producer where DB sector text matched agri/processing keywords, or silo CAEN in 01/10/11.

## Results
- Total suppliers: 15,500
- No-CUI before: 14,749
- **Resolved: 53** — exact 49, high 2, low 2
- Still no CUI: 14,696 (cui blank, match_confidence=none)
- New `match_confidence` column added; pre-existing CUIs tagged `preexisting` (751).

### Resolved by category
cereals/grain 10, bakery 17, dairy 11, meat/charcuterie 11, preserves/conserve 1, +3 silo backfill.

### Unresolved by category
dairy 7,261 · cereals/grain 1,864 · bakery 1,861 · honey 1,454 · meat/charcuterie 1,109 · produce/vegetables 858 · eggs 168 · other/traditional 78 · preserves/conserve 38 · wine/tuica 5

### Unresolved by source
DSVSA_RO_REGISTRY 10,470 · SILOZURI_MASTER 1,864 · DAIRY_RO 304 · MEAT_PROCESSORS_RO 1,012 · VIA-PROFI 943 · ANSVSA_STARTER 65 · CONSERVE_FACTORIES 38

## Why yield is low
`companies` is construction/jobs/TED-skewed; agri-producer coverage is thin. Most unresolved rows are persons/PFA (VIA-PROFI) or DSVSA registry entities keyed on sanitary registration_number, names absent from the company DB. SILOZURI no-CUI rows genuinely lack CUI in their own source too.

## Recommended next step for the 14,696 unresolved
1. **ANAF bulk lookup** — the real gate. DSVSA registry rows carry sanitary `registration_number` + name + locality; resolve CUI via ANAF webservice (`webservicesp.anaf.ro` getInfo by name/locality) or the open `od_firme` ANAF dataset matched on name+locality. Highest-value path (covers ~10,470 DSVSA + 1,316 dairy/meat).
2. **VIA-PROFI (943)** — mostly individuals; CUI only obtainable via APIA/Registrul Comertului PFA lookup or web enrichment. Lower priority.
3. **SILOZURI (1,864)** — re-run silo enrichment / ANAF by name+county; partial.
Until CUI is verified per supplier the launch traceability gate stays OPEN for these categories.

---

## Pass 2 — Full RO company registry (2026-06-24)

**Registry used:** `D:\MEMORY\DATA\ACTIVE\ROMANIA_DB\master_romania_companies.csv` (full ONRC/ANAF export — name + cui + county + city + caen). Total rows 2,917,049; numeric-CUI rows indexed 2,805,504; unique normalized names 2,670,321. (raspibig `romania.companies` not reachable this session — password redacted; local PG 5432 auth failed; used the on-disk full registry CSV instead, which is the same data, far larger than the 117K jobs-DB subset of Pass 1.)

**Method:** normalized supplier name (strip SRL/SA/PFA/II/IF/COOP + diacritics, uppercase) → exact match on registry normalized name. Disambiguated by county/city when present. Confidence: `high` = unique geo-confirmed candidate; `exact` = all candidates share one CUI; `low` = ambiguous (<=3 candidates, first taken). Pulled `caen`; flagged CAEN 46.x (wholesale) — 105 hits to review.

**Newly resolved this pass: 1,861** — high 1,305 · exact 475 · low 81.
By category: bakery 892, meat/charcuterie 475, dairy 403, honey 33, cereals/grain 19, preserves/conserve 24, eggs 12, produce/vegetables 3.
CAEN backfilled on 1,833 rows. Wholesale-CAEN (46.x) flagged: 105 (origin re-review needed — possible resellers).

**Cumulative:** with CUI 2,665 / 15,500 (preexisting 751 + Pass 1 53 + Pass 2 1,861). Still blank 12,835.
Confidence tally: preexisting 751 · high 1,307 · exact 524 · low 83 · none 12,835.

**Still unresolved by category:** dairy 6,858 · cereals/grain 1,845 · honey 1,421 · bakery 969 · produce/vegetables 855 · meat/charcuterie 634 · eggs 156 · other/traditional 78 · preserves/conserve 14 · wine/tuica 5.
**By source:** DSVSA_RO_REGISTRY 9,258 · SILOZURI_MASTER 1,845 · VIA-PROFI 940 · MEAT_PROCESSORS_RO 610 · DAIRY_RO 168 · CONSERVE_FACTORIES 14.

**Why still ~12.8K unresolved:** DSVSA rows are keyed on sanitary registration_number with farm/holding names (often person names or holding names) absent from ONRC; SILOZURI rows lack CUI in their own source; VIA-PROFI are PFA/individuals. Next gate: ANAF webservice getInfo by name+locality for DSVSA, APIA/PFA lookup for VIA-PROFI.
