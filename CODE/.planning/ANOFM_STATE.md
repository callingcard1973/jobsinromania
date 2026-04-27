# ANOFM PostgreSQL Migration — Current State
**Last Updated:** 2026-04-27 08:00 UTC  
**Status:** READY FOR APPROVAL  
**Phase:** Pre-Deployment

## Current Situation
- **Sender:** SQLite (tudor.db) at `/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/`
- **Live Contacts:** 1,418 pending
- **Campaign Schedule:** Mon-Fri 8-18h, every 2h (via raspi_orchestrator)
- **Sender Code:** `tudor_sender.py` + `sender_db.py` (SQLite)
- **Status:** OPERATIONAL (no issues)

## What's Being Migrated
- **Source:** SQLite file (tudor.db, 1.2 MB)
- **Target:** PostgreSQL table (interjob_master.anofm_contacts)
- **Database:** postgres://127.0.0.1:5433/interjob_master (tudor/tudor)
- **Code:** tudor_sender_pg.py + sender_db_pg.py (connection pooling)

## Migration Strategy
**Phases:**
1. **Pre-Deploy** (30 min) — Backup, verify connections, validate schemas
2. **Migrate** (20 min) — Run migration_anofm_sqlite_to_pg.py
3. **Parallel Run** (24h) — Both SQLite + PG sending simultaneously
4. **Cutover** (5 min) — Switch sender code to PG
5. **Validate** (1h) — Monitor first sends
6. **Archive** (10 min) — Backup SQLite to HDD

**Total Time:** ~25.5 hours (mostly unattended)

## Blockers
- [ ] Approval to proceed with migration
- [ ] Confirmation that raspibig PostgreSQL is stable (no recent restarts)
- [ ] Confirmation that parallel run schedule won't conflict with other campaigns

## Completed Tasks
- [x] Created migration plan (see ANOFM_PG_MIGRATION_PLAN.md)
- [x] Reviewed tudor_sender_pg.py code (ready to deploy)
- [x] Reviewed sender_db_pg.py code (connection pooling verified)
- [x] Analyzed current orchestrator_configs/anofm_tudor.json
- [x] Created rollback procedures (1-hour recovery)

## Next Steps
1. **AWAIT APPROVAL** — "Deploy the plan" or "Make changes and retry"
2. If approved → Phase 0 Pre-Deployment checklist
3. Run migration script → Phase 1
4. Monitor parallel run 24h → Phase 2
5. Cutover + validation → Phases 3-4
6. Archive + SOP docs → Phase 5

## Risks & Mitigations
| Risk | Severity | Status |
|------|----------|--------|
| PG connection pool exhaustion | LOW | Mitigated: pool min=1, max=5 |
| Data corruption during migration | MEDIUM | Mitigated: ON CONFLICT, validate row counts |
| Duplicate sends (parallel run) | MEDIUM | Mitigated: Offset sender times by 30min |
| Brevo bounce threshold exceeded | LOW | Mitigated: Independent quota per sender |
| Rollback takes too long | LOW | Mitigated: SQLite backup available < 1 min restore |

## Rollback Availability
- **Time to revert:** < 1 hour
- **Backup location:** `/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/tudor_backup_*.db`
- **Fallback sender:** tudor_sender.py (unchanged, available)
- **Data safety:** No data loss (SQLite untouched during migration)

## Approval Checkpoint
**Before proceeding, confirm:**
1. [ ] Migration plan reviewed and accepted
2. [ ] raspibig PostgreSQL is stable (no issues in last 7 days)
3. [ ] No other campaigns scheduled for 24h parallel run window
4. [ ] SCP/SSH access to raspibig working
5. [ ] PostgreSQL backup at 192.168.100.21 is current

**Approval Status:** ⏳ AWAITING USER DECISION

---

## Timeline
- **Plan Created:** 2026-04-27 08:00 UTC
- **Approval Window:** 2026-04-27 08:00–17:00 UTC (9 hours)
- **Est. Migration Start:** 2026-04-27 (on approval)
- **Est. Cutover:** 2026-04-28 ~09:00 UTC (24h later)
- **Est. Complete:** 2026-04-28 ~10:30 UTC
