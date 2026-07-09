# Change: cleanup-phase2

## Intent

Complete codebase cleanup: split remaining oversize files, organize test/exploratory
scripts, and set up the SEAP tender alert dispatcher (highest-value quick win from ideas.txt).

## Scope

### 1. Split oversize files (mandatory — rule violation)
- `campaign_dashboard.py` (385 lines) — split tier logic from CLI/formatting
- `segment_and_analyze.py` (275 lines) — split analysis functions into module

### 2. Organize exploratory scripts
Move 11 test/debug/exploratory files (1,000+ lines) to `CODE/exploratory/`:
- `test_listafirme.py`, `test_listafirme2.py`, `test_listafirme3.py`, `test_listafirme4.py`
- `test_web_finder.py`
- `listafirme_cui_lookup.py`, `ddg_email_search.py`
- `search_liquidators.py`, `scan_big_csvs.py`, `scan_all_pg_dbs.py`, `inspect_all_dbs.py`

### 3. SEAP food tender alert dispatcher (ideas.txt item C)
- Create `seap_alert_dispatcher.py` — cron-ready script that:
  - Queries tenders table for NEW food tenders since last run
  - Cross-matches with cooperative member categories
  - Sends email alerts via Brevo to relevant members
- Uses existing infrastructure: SEAP scraper, email_sending_skill, Brevo

## Approach

Phase 1 (code cleanup): split files, move exploratory scripts — no functional changes.
Phase 2 (new feature): build dispatcher on existing seap_food_alerts + email infrastructure.

## Rollback
Revert commit. No DB schema changes.

## Affected Modules
- CODE/campaign_dashboard.py (split)
- CODE/segment_and_analyze.py (split)
- CODE/exploratory/ (new directory, 11 files moved)
- CODE/seap_alert_dispatcher.py (NEW)
