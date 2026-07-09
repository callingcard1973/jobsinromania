# Verification: cleanup-and-shared-utils

## Changes Made

### 1. Created `CODE/shared_utils.py` (112 lines)
- `normalize()` — single source of truth for Romanian company name normalization
- `DB_MASTER`, `DB_FOOD` — centralized DB connection configs
- `get_master_conn()`, `get_food_conn()` — connection helpers
- `load_enriched()`, `save_enriched()` — CSV I/O with sort
- `apply_match()` — enrichment field setter with KeyError guard
- `print_stats()` — standardized stats + source breakdown output
- `SEAP_COLS` — shared column list

### 2. Bug Fixes
- **SQL injection** in `query_food_contacts.py:43` — county parameter now uses `%s` placeholder
- **KeyError** in `ultimate_enrich_raspibig.py:104` — added `cui not in enriched` guard

### 3. Deduplication (12 files updated)
Replaced inline `normalize()` with `from shared_utils import normalize`:
- `enrich_from_db.py`, `enrich_seap_winners.py`, `deep_enrich_raspibig.py`
- `enrich_food_raspibig.py`, `fuzzy_enrich_raspibig.py`, `scan_all_sources.py`
- `ultimate_enrich_raspibig.py`, `faliment_cross_match.py`, `seap_food_alerts.py`

Replaced inline DB configs with `from shared_utils import DB_MASTER, DB_FOOD`:
- `query_food_contacts.py`, `create_db.py`, `enrich_from_db.py`
- `enrich_seap_winners.py`, `faliment_cross_match.py`, `seap_food_alerts.py`

Replaced inline CSV I/O + stats with shared helpers:
- `ultimate_enrich_raspibig.py`, `deep_enrich_raspibig.py`
- `fuzzy_enrich_raspibig.py`, `scan_all_sources.py`

### 4. Removed unused imports
- `unicodedata` removed from 4 files (now only in shared_utils)
- `re` removed from 2 files (no longer used after normalize extraction)

## Line Count Reduction

| File | Before | After | Saved |
|------|--------|-------|-------|
| ultimate_enrich_raspibig.py | 249 | 186 | 63 |
| deep_enrich_raspibig.py | 286 | 241 | 45 |
| fuzzy_enrich_raspibig.py | 168 | 122 | 46 |
| scan_all_sources.py | 296 | 244 | 52 |
| enrich_food_raspibig.py | 254 | 235 | 19 |
| enrich_from_db.py | 390 | 368 | 22 |
| enrich_seap_winners.py | 367 | 347 | 20 |
| **Total saved** | | | **267** |
| shared_utils.py (new) | 0 | 112 | — |
| **Net reduction** | | | **155** |

## Still Over 250 Lines (future work)
- `enrich_from_db.py` (368) — split enrich/stats/export into separate files
- `enrich_seap_winners.py` (347) — split extract/enrich into separate files
- `faliment_cross_match.py` (336) — split flag/opportunities/export
- `seap_food_alerts.py` (309) — split report/buyers/winners/overlap
