# ANOFM PostgreSQL Migration Planning

**Status:** READY FOR EXECUTION  
**Date Created:** 2026-04-27  
**Total Duration:** 25.5 hours (mostly automated)  
**Risk Level:** MEDIUM (mitigated by 24h parallel validation)

## Three Documents

### 1. **ANOFM_PG_MIGRATION_PLAN.md** — Master Plan
- Executive summary + rationale
- 5 phases with detailed procedures
- Risk mitigation table
- Success criteria
- Rollback procedures
- **Read this first** for understanding

### 2. **ANOFM_STATE.md** — Current Status
- Current situation (SQLite operational, 1,418 contacts)
- What's being migrated (SQLite → PostgreSQL)
- Completed tasks & blockers
- Timeline & approval checkpoint
- **Reference during execution for status**

### 3. **ANOFM_EXECUTION_CHECKLIST.md** — Step-by-Step SOP
- Checkbox format for each phase
- Expected outputs for verification
- Record sheet for metrics
- Go/No-Go decisions at each phase
- Sign-off lines for approvals
- **Use this to execute the migration**

## Quick Start

**If approved, execute in this order:**

```
Phase 0: PRE-DEPLOYMENT (30 min)
  └─ Backup SQLite, verify connections, validate schemas

Phase 1: MIGRATION (20 min)
  └─ Run migrate_anofm_sqlite_to_pg.py, validate data

Phase 2: PARALLEL RUN (24 hours, automated)
  └─ Both SQLite + PG sending, daily monitoring @ 18:00 UTC

Phase 3: CUTOVER (5 min)
  └─ Switch sender code to PG, restart orchestrator

Phase 4: VALIDATION (1 hour)
  └─ Monitor first sends, verify bounce rate, check pool health

Phase 5: ARCHIVE (10 min)
  └─ Backup SQLite, clean staging, document recovery SOP
```

## Key Files

| File | Location | Purpose |
|------|----------|---------|
| `migrate_anofm_sqlite_to_pg.py` | `/d/MEMORY/CODE/MIGRATIONS/` | One-time migration script |
| `tudor_sender_pg.py` | `/d/MEMORY/CODE/WEB/CODE/` | PG-based sender |
| `sender_db_pg.py` | `/d/MEMORY/CODE/WEB/CODE/` | PG DB layer (pooling) |
| `tudor.db` | `/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/` | SQLite (to be archived) |
| `anofm_tudor.json` | `/opt/EMAIL/CAMPAIGNS/orchestrator_configs/` | Campaign config (to be updated) |

## Success Criteria

All must be true:

1. ✓ PG anofm_contacts ≥ 1,418 rows
2. ✓ No duplicate emails (UNIQUE constraint)
3. ✓ Status distribution matches SQLite
4. ✓ 24h parallel validation within ±5% send count
5. ✓ Brevo bounce rate < 30%
6. ✓ Zero connection pool errors
7. ✓ tudor_sender_pg.py running in production
8. ✓ SQLite archived to D:\BACKUP\ANOFM\

## Approval Checkpoint

**Before Phase 0, confirm:**

- [ ] Migration plan reviewed & accepted
- [ ] raspibig PostgreSQL stable (no issues in 7 days)
- [ ] No other campaigns scheduled during 24h parallel window
- [ ] SCP/SSH access to raspibig working
- [ ] PostgreSQL backup current

**Status: ⏳ AWAITING USER DECISION**

---

**Next Step:** User approves → Execute ANOFM_EXECUTION_CHECKLIST.md in order
