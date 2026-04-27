# ANOFM PostgreSQL Migration Test Suite — Index

**Location:** `D:\MEMORY\CODE\CAMPAIGNS\EMAIL PERSONAL\tests\`  
**Git Commit:** 9d3b1650  
**Status:** ✓ READY FOR DEPLOYMENT  

## Start Here

### 1. If you're installing the test suite for the first time:
   → Read: **SETUP.md** (complete installation + verification guide)
   
### 2. If you're running tests before production deployment:
   → Read: **QUICK_REFERENCE.txt** (copy-paste commands)
   → Verify: Run `python -m pytest test_anofm_pg.py -v` locally

### 3. If you're deploying to production:
   → Read: **IMPLEMENTATION_GUIDE.md** (deployment workflow with 3 phases)
   → Verify: All local tests pass before raspibig deployment

### 4. If you want an overview of what's being tested:
   → Read: **README_ANOFM_TESTS.md** (test classes, coverage, checklist)

### 5. If you need to understand what was delivered:
   → Read: **DELIVERY_SUMMARY.md** (files, test breakdown, features)

## Files at a Glance

### Documentation (Read in this order)
1. **SETUP.md** ← Start here for installation & troubleshooting
2. **README_ANOFM_TESTS.md** ← Test overview & pre-deploy checklist
3. **IMPLEMENTATION_GUIDE.md** ← Deployment workflow (3 phases)
4. **QUICK_REFERENCE.txt** ← Quick command reference (copy-paste)
5. **DELIVERY_SUMMARY.md** ← What was delivered, test breakdown
6. **INDEX.md** ← This file

### Code Files
- **test_anofm_pg.py** (959 lines) — Main test suite, 28+ tests across 8 classes
- **conftest.py** (270 lines) — Pytest fixtures, DB config, auto-cleanup
- **run_anofm_tests.py** (182 lines) — CLI test runner with reporting
- **pytest.ini** — Test markers, timeouts, logging config
- **requirements.txt** — Dependencies (pytest, psycopg2, etc.)

## Quick Commands

```bash
# Install (one-time)
cd "D:\MEMORY\CODE\CAMPAIGNS\EMAIL PERSONAL\tests"
pip install -r requirements.txt

# Test connection
python -m pytest test_anofm_pg.py::TestConnectionHealth::test_single_connection_success -v

# Run all tests
python -m pytest test_anofm_pg.py -v

# Run fast (skip load tests)
python -m pytest test_anofm_pg.py -v -m "not slow"

# Run by category
python -m pytest test_anofm_pg.py::TestConnectionHealth -v
python -m pytest test_anofm_pg.py::TestDataIntegrity -v
python -m pytest test_anofm_pg.py::TestIdempotency -v

# Using runner script
python run_anofm_tests.py
python run_anofm_tests.py --fast
python run_anofm_tests.py --html
```

See **QUICK_REFERENCE.txt** for more commands.

## Test Classes (8 total, 28+ tests)

| Class | Tests | Purpose | Critical |
|-------|-------|---------|----------|
| TestConnectionHealth | 6 | Pool stability, reconnect, concurrent | ✓ YES |
| TestDataIntegrity | 4 | 1418+ records, no dupes, schema | ✓ YES |
| TestIdempotency | 2 | Run 2x = same result | ✓ SAFETY |
| TestSendOperations | 4 | Bulk insert/update/query performance | ✓ PERF |
| TestAuditLogging | 4 | Audit trail, PII masking | ✓ COMPLIANCE |
| TestRollbackRecovery | 3 | Backup table, recovery window, dry-run | ✓ RECOVERY |
| TestLoadSimulation | 2 | 100 concurrent SELECT < 30s | STRESS |
| TestGDPRCompliance | 3 | Delete by email, audit preserved | ✓ LEGAL |

## Pre-Deployment Checklist

```
☐ All tests pass locally: pytest test_anofm_pg.py -v
☐ Connection pool health (TestConnectionHealth)
☐ Data integrity (TestDataIntegrity) — ≥1418 records, 0 dupes
☐ Idempotency (TestIdempotency) — safe to re-run
☐ Load simulation (TestLoadSimulation) — < 30s
☐ Brevo bounce rate < 30% (CRITICAL)
☐ Backup table created
☐ Audit log table ready
```

See **README_ANOFM_TESTS.md** for full checklist.

## Deployment Phases

1. **Local validation** (laptop) — Run all tests, verify pass
2. **Pre-deploy checklist** — Test categories, verify bounce rate
3. **Production deployment** (raspibig) — Backup, migrate, verify

See **IMPLEMENTATION_GUIDE.md** for detailed workflow.

## Troubleshooting

Common issues:
- "Connection refused" → Check PostgreSQL is running on localhost:5433
- "Relation not found" → Verify companies_clean table exists
- "Duplicate key" → Clean test data: DELETE FROM companies_clean WHERE source = 'ANOFM_TEST'
- "Tests hang" → Kill idle connections or check disk space

See **SETUP.md** → "Troubleshooting" section for complete guide.

## Performance Targets

| Operation | Target |
|-----------|--------|
| Bulk insert (1418 rows) | < 10s |
| SELECT by source | < 100ms |
| Batch UPDATE | < 500ms |
| 100 concurrent SELECT | < 30s |

## Key Features

✓ 28+ test methods covering 8 domains  
✓ Safety-critical idempotency (run 2x = same result)  
✓ Auto-cleanup (test records isolated & deleted)  
✓ Connection pooling (validates 100 concurrent)  
✓ Audit compliance (PII masking, audit trail preserved)  
✓ GDPR ready (delete by email, no orphans)  
✓ Type-safe (100% type hints)  
✓ Well-documented (5 guides + quick reference = 46 KB)  
✓ Production-ready (deploy immediately after local validation)  

## File Sizes

| File | Size |
|------|------|
| test_anofm_pg.py | 31 KB |
| conftest.py | 7.8 KB |
| run_anofm_tests.py | 4.4 KB |
| README_ANOFM_TESTS.md | 6.4 KB |
| SETUP.md | 7.8 KB |
| IMPLEMENTATION_GUIDE.md | 12 KB |
| QUICK_REFERENCE.txt | 7.7 KB |
| DELIVERY_SUMMARY.md | 9.5 KB |
| pytest.ini | 1.4 KB |
| requirements.txt | 337 B |
| **Total** | **~88 KB** |

## Reading Guide by Role

### DevOps / Deployment Engineer
1. QUICK_REFERENCE.txt (commands)
2. IMPLEMENTATION_GUIDE.md (workflow)
3. README_ANOFM_TESTS.md (pre-deploy checklist)

### QA / Tester
1. README_ANOFM_TESTS.md (test overview)
2. SETUP.md (installation + running tests)
3. test_anofm_pg.py (test code)

### Backend Developer
1. SETUP.md (installation)
2. test_anofm_pg.py (test code & fixtures)
3. conftest.py (pytest config)
4. DELIVERY_SUMMARY.md (technical breakdown)

### Product / Project Manager
1. DELIVERY_SUMMARY.md (what was delivered)
2. README_ANOFM_TESTS.md (pre-deploy checklist)
3. QUICK_REFERENCE.txt (key commands)

## Related Documentation

- `.claude/campaigns.md` — ANOFM campaign setup, Brevo configs
- `.claude/pipeline.md` — DB pipeline steps 1-46, table schemas
- `CODE/CAMPAIGNS/EMAIL PERSONAL/CODE/import_anofm_*.py` — Migration scripts

## Next Steps

1. **Install:** Run `pip install -r requirements.txt`
2. **Test:** Run `python -m pytest test_anofm_pg.py -v`
3. **Review:** Check all tests pass (expect 28+ PASSED)
4. **Deploy:** Follow IMPLEMENTATION_GUIDE.md workflow

## Contact

- **Installation help:** See SETUP.md
- **Test failures:** See README_ANOFM_TESTS.md → Troubleshooting
- **Deployment questions:** See IMPLEMENTATION_GUIDE.md
- **Quick commands:** See QUICK_REFERENCE.txt
- **Email:** manpower.dristor@gmail.com

---

**Delivered:** 2026-04-27  
**Git Commit:** 9d3b1650  
**Status:** ✓ READY FOR DEPLOYMENT  
**Next Action:** Read SETUP.md or QUICK_REFERENCE.txt
