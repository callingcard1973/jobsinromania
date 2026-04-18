# Change: cleanup-and-shared-utils

## Intent
Extract duplicated code into shared module, fix bugs, organize test files.

## Scope
- Create `CODE/shared_utils.py` with normalize(), DB connections, CSV I/O
- Fix SQL injection in `query_food_contacts.py`
- Fix KeyError in `ultimate_enrich_raspibig.py`
- Move 5 test files to `CODE/tests/`
- Update all 12+ scripts to import from shared_utils

## Approach
Bottom-up: create shared module first, then update each script to use it.

## Rollback
Revert commit. No DB changes, no data changes.

## Affected Modules
- CODE/shared_utils.py (NEW)
- CODE/query_food_contacts.py (bug fix)
- CODE/ultimate_enrich_raspibig.py (bug fix)
- CODE/enrich_from_db.py, enrich_seap_winners.py, deep_enrich_raspibig.py,
  enrich_food_raspibig.py, fuzzy_enrich_raspibig.py, scan_all_sources.py (dedup)
- CODE/create_db.py, faliment_cross_match.py, seap_food_alerts.py (DB dedup)
