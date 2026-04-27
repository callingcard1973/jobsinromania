# ANOFM Test Suite Setup Guide

## Prerequisites

- **Python:** 3.12+ (tested on 3.13)
- **PostgreSQL:** 18 on localhost:5433
- **Database:** `interjob_master` with table `companies_clean`
- **User:** tudor / tudor

## Installation Steps

### 1. Install Test Dependencies

```bash
cd "D:\MEMORY\CODE\CAMPAIGNS\EMAIL PERSONAL\tests"

# Option A: Using pip
pip install -r requirements.txt

# Option B: Using uv (faster)
uv pip install -r requirements.txt
```

### 2. Verify PostgreSQL Connection

```bash
# Test connection locally
PGPASSWORD=tudor "/c/Program Files/PostgreSQL/18/bin/psql.exe" \
  -U tudor -h 127.0.0.1 -p 5433 -d interjob_master -c "SELECT 1"

# Expected output: "1"
```

### 3. Run Quick Sanity Check

```bash
cd "D:\MEMORY\CODE\CAMPAIGNS\EMAIL PERSONAL\tests"

# Run a single test
python -m pytest test_anofm_pg.py::TestConnectionHealth::test_single_connection_success -v
```

If you see:
```
PASSED                                                               [100%]
```

✓ Setup is complete.

## Running Tests

### Full Suite (all 28+ tests)
```bash
python -m pytest test_anofm_pg.py -v
```

### Fast Suite (skip load tests)
```bash
python -m pytest test_anofm_pg.py -v -m "not slow"
```

### By Category

```bash
# Connection health
python -m pytest test_anofm_pg.py -v -k "Connection"

# Data integrity
python -m pytest test_anofm_pg.py -v -k "Integrity"

# Idempotency
python -m pytest test_anofm_pg.py -v -k "Idempotency"

# Send operations
python -m pytest test_anofm_pg.py -v -k "Send"

# Audit logging
python -m pytest test_anofm_pg.py -v -k "Audit"

# Recovery procedures
python -m pytest test_anofm_pg.py -v -k "Recovery"

# Load simulation
python -m pytest test_anofm_pg.py -v -k "Load"

# GDPR compliance
python -m pytest test_anofm_pg.py -v -k "GDPR"
```

### Helper Script

```bash
# All tests
python run_anofm_tests.py

# Fast (skip slow tests)
python run_anofm_tests.py --fast

# Specific category
python run_anofm_tests.py --only connection

# With HTML report
python run_anofm_tests.py --html
# Opens: test_report.html

# Verbose + output
python run_anofm_tests.py -vv --show-output

# Exit on first failure
python run_anofm_tests.py -x

# Parallel (4 workers)
python run_anofm_tests.py -n 4
```

## Test Output Examples

### Success
```
test_anofm_pg.py::TestConnectionHealth::test_single_connection_success PASSED
test_anofm_pg.py::TestDataIntegrity::test_import_valid_anofm_records PASSED
...
======================== 28 passed in 12.34s ========================
```

### Failure Diagnostic
```
FAILED test_anofm_pg.py::TestConnectionHealth::test_single_connection_success
Traceback:
    psycopg2.OperationalError: FATAL: password authentication failed for user "tudor"

ACTION: Verify DB credentials in DB_CONFIG or set POSTGRES_* env vars
```

## Environment Variables

Override DB credentials via env vars:

```bash
set POSTGRES_HOST=127.0.0.1
set POSTGRES_PORT=5433
set POSTGRES_DB=interjob_master
set POSTGRES_USER=tudor
set POSTGRES_PASSWORD=tudor

python -m pytest test_anofm_pg.py -v
```

Or in `.env` file:

```
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5433
POSTGRES_DB=interjob_master
POSTGRES_USER=tudor
POSTGRES_PASSWORD=tudor
```

Then:

```bash
# Install python-dotenv
pip install python-dotenv

# Tests auto-load .env
python -m pytest test_anofm_pg.py -v
```

## Database Cleanup

Tests use `source = 'ANOFM_TEST'` for isolation. Auto-cleanup runs after each test.

**Manual cleanup if needed:**

```sql
-- Delete test records
DELETE FROM companies_clean WHERE source IN ('ANOFM_TEST', 'ANOFM_BACKUP_TEST');

-- Delete test emails
DELETE FROM companies_clean WHERE email LIKE 'test-%@test.ro'
  OR email LIKE 'bulk_%@test.ro'
  OR email LIKE 'concurrent_%@test.ro';

-- Audit cleanup
DELETE FROM anofm_audit_log WHERE timestamp > now() - interval '1 hour';
```

## Common Issues & Solutions

### Error: "password authentication failed"
```
SOLUTION:
1. Verify PostgreSQL password: SET PGPASSWORD=tudor
2. Test manually: psql -U tudor -h 127.0.0.1 -p 5433 interjob_master
3. Check if user exists: \du in psql
```

### Error: "Relation companies_clean does not exist"
```
SOLUTION:
1. Verify table exists: \d companies_clean in psql
2. Connect to correct database: -d interjob_master
3. Table must be pre-existing (production import)
```

### Error: "Pool overflow" (concurrent tests hang)
```
SOLUTION:
1. Increase pool size: SimpleConnectionPool(5, 20, ...)
2. Check max_connections in PostgreSQL: SHOW max_connections;
3. Kill idle connections: SELECT pg_terminate_backend(pid) FROM pg_stat_activity
```

### Error: "Duplicate key value violates unique constraint"
```
SOLUTION:
1. Clean up test data: DELETE FROM companies_clean WHERE source = 'ANOFM_TEST'
2. Check for lingering records from previous run
3. Verify cleanup_anofm fixture is running
```

### Tests run very slowly (>30s)
```
SOLUTION:
1. Check PostgreSQL performance: EXPLAIN ANALYZE SELECT...
2. Verify indexes exist: idx_clean_source, idx_clean_email
3. Check disk space: df -h / (>10GB recommended)
4. Monitor connections: SELECT * FROM pg_stat_activity
```

## Test Data

Tests generate synthetic data:
- `anofm_test.csv`: 50 records (10% invalid for edge cases)
- Email patterns: `test-*@test.ro`, `bulk_*@test.ro`, etc.
- Sectors: `ANOFM_productie`, `ANOFM_comert`, etc.

All test data uses `source = 'ANOFM_TEST'` for easy cleanup.

## Reports & Metrics

### HTML Report
```bash
python -m pytest test_anofm_pg.py --html=report.html --self-contained-html
# Opens in browser: report.html
```

### Coverage Report
```bash
python -m pytest test_anofm_pg.py --cov=. --cov-report=html
# Check: htmlcov/index.html
```

### JUnit XML (for CI/CD)
```bash
python -m pytest test_anofm_pg.py --junit-xml=results.xml
# Parse: results.xml for CI integration
```

## Pre-Deployment Checklist

Before running migration on production (raspibig):

- [ ] `python -m pytest test_anofm_pg.py -v` all pass locally
- [ ] No TestConnectionHealth failures (pool health)
- [ ] No TestDataIntegrity failures (duplicates, schema)
- [ ] TestIdempotency passes (safe to re-run)
- [ ] TestLoadSimulation < 30s (pool can handle 100 concurrent)
- [ ] TestAuditLogging passes (audit trail intact)
- [ ] TestRollbackRecovery passes (backup + recovery safe)
- [ ] TestGDPRCompliance passes (delete + audit preserved)
- [ ] Brevo bounce rate < 30% (checked before send)

## Continuous Integration

### GitHub Actions
```yaml
name: ANOFM Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:18
        env:
          POSTGRES_PASSWORD: tudor
          POSTGRES_USER: tudor
          POSTGRES_DB: interjob_master
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.13"

      - name: Install dependencies
        run: pip install -r "CODE/CAMPAIGNS/EMAIL PERSONAL/tests/requirements.txt"

      - name: Run tests
        run: pytest "CODE/CAMPAIGNS/EMAIL PERSONAL/tests/test_anofm_pg.py" -v
        env:
          POSTGRES_HOST: localhost
          POSTGRES_PORT: 5432
          POSTGRES_USER: tudor
          POSTGRES_PASSWORD: tudor
          POSTGRES_DB: interjob_master
```

## Performance Baseline

Expected timings (laptop, localhost:5433):

| Test | Target | Status |
|------|--------|--------|
| Connection pool (5 conn) | < 500ms | ✓ |
| Bulk insert (1,418 rows) | < 10s | [Run test] |
| SELECT by source (index) | < 100ms | [Run test] |
| Batch UPDATE | < 500ms | [Run test] |
| 100 concurrent SELECT | < 30s | [Run test] |

## Support

**Troubleshooting:** See README_ANOFM_TESTS.md → "Troubleshooting" section

**Questions:** Check `.claude/campaigns.md` for ANOFM campaign setup details.

**Issues:** Email: manpower.dristor@gmail.com
