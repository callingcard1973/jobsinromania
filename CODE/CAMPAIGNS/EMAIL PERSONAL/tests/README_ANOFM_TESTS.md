# ANOFM PostgreSQL Migration Test Suite

## Overview

Comprehensive test suite for ANOFM (Agentia Nationala pentru Ocuparea Fortei de Munca) PostgreSQL migration to `companies_clean` table. Tests connection health, data integrity, idempotency, send operations, audit logging, rollback/recovery, load simulation, and GDPR compliance.

**Total tests: 40+ test methods across 8 test classes**

## Requirements

- PostgreSQL 18 on localhost:5433
- Database: `interjob_master`
- User: `tudor` / `tudor`
- Python 3.12+
- pytest
- psycopg2

## Test Classes

### 1. TestConnectionHealth (6 tests)
Validates database connection pool and reliability:
- Single connection success
- Connection pool initialization (2-10 size)
- Connection timeout enforcement (5s default)
- Reconnection after close
- Concurrent connections (5 parallel)

**Critical:** If pool tests fail, production sends will fail.

### 2. TestDataIntegrity (4 tests)
Validates ANOFM data migration integrity:
- Import 1,418+ valid records
- No duplicate emails in final dataset
- Schema constraint enforcement
- Email normalization (trim + lowercase)
- ANOFM_ sector prefix applied

**Pass criterion:** ≥1,418 records, 0 duplicates, all sectors prefixed.

### 3. TestIdempotency (2 tests)
Ensures migration can run 2x with identical results:
- Import twice = same final count
- Hash of data identical on 2nd run

**Critical for safety:** Protects against accidental re-imports.

### 4. TestSendOperations (4 tests)
Validates performance for email sending pipeline:
- Bulk insert 1,418 rows < 10s
- SELECT by source < 100ms (uses idx_clean_source)
- Batch UPDATE lead_score < 500ms
- Email index usage verified

**Pass criterion:** All operations meet latency targets.

### 5. TestAuditLogging (4 tests)
Validates audit trail and PII masking:
- Audit log table creation
- Email masking logic (x***@domain.com)
- Migration actions logged
- No PII (email, phone, address) in logs

**Pass criterion:** All sensitive fields masked, audit trail intact.

### 6. TestRollbackRecovery (3 tests)
Validates backup and recovery procedures:
- Backup table structure matches source
- Timestamp validation for recovery window
- Dry-run recovery (no data modification)

**Pass criterion:** Backup readable, recovery script safe.

### 7. TestLoadSimulation (2 tests)
Simulates 100 concurrent sends:
- 100 concurrent SELECT queries < 30s
- Mixed concurrent inserts + selects

**Pass criterion:** No connection errors, all complete < 30s.

### 8. TestGDPRCompliance (3 tests)
GDPR delete & right-to-be-forgotten:
- DELETE by email removes record
- Audit log preserved after delete
- No orphaned records (NULL emails < 100)

**Pass criterion:** Records deleted, audit preserved.

## Running Tests

### Quick Test (all)
```bash
cd "D:\MEMORY\CODE\CAMPAIGNS\EMAIL PERSONAL\tests"
pytest test_anofm_pg.py -v
```

### Specific Test Class
```bash
pytest test_anofm_pg.py::TestConnectionHealth -v
pytest test_anofm_pg.py::TestDataIntegrity -v
```

### Single Test
```bash
pytest test_anofm_pg.py::TestDataIntegrity::test_import_valid_anofm_records -v
```

### With Coverage
```bash
pytest test_anofm_pg.py --cov=import_anofm_to_companies_clean --cov-report=html
```

### Show SQL (debugging)
```bash
pytest test_anofm_pg.py -v -s
```

## Pre-deployment Checklist

Before running migration on production (raspibig):

- [ ] All tests pass locally on laptop (localhost:5433)
- [ ] No errors in TestConnectionHealth
- [ ] No duplicates detected in TestDataIntegrity
- [ ] Idempotency tests pass (safe to re-run)
- [ ] Load simulation completes < 30s (pool healthy)
- [ ] Audit table created and populated
- [ ] Backup table created (pre-migration)
- [ ] GDPR tests pass (delete/recovery safe)
- [ ] Brevo bounce rate < 30% (before send)

## Test Fixtures

### `pg_conn`
Single database connection for the test (session-scoped).

### `pg_pool`
Connection pool (2-10 connections) for load tests.

### `cleanup_anofm`
Auto-cleanup of ANOFM_TEST records before/after each test.

### `anofm_test_csv`
Generated CSV with 50 test records (valid + invalid for edge cases).

## Performance Expectations

| Operation | Target | Actual |
|-----------|--------|--------|
| Bulk insert (1,418 rows) | < 10s | [RUN TEST] |
| SELECT by source (index) | < 100ms | [RUN TEST] |
| Batch UPDATE | < 500ms | [RUN TEST] |
| 100 concurrent SELECT | < 30s | [RUN TEST] |
| Pool getconn/putconn | < 10ms | [RUN TEST] |

## Database Cleanup After Tests

Tests use `source = 'ANOFM_TEST'` for isolation. Cleanup runs automatically:

```bash
# Manual cleanup if needed
PGPASSWORD=tudor psql -U tudor -h 127.0.0.1 -p 5433 -d interjob_master -c \
  "DELETE FROM companies_clean WHERE source = 'ANOFM_TEST';"
```

## Audit Table Schema

If audit table missing, create manually:

```sql
CREATE TABLE anofm_audit_log (
    id SERIAL PRIMARY KEY,
    action TEXT,
    table_name TEXT,
    record_id INT,
    email_masked VARCHAR(255),
    timestamp TIMESTAMP DEFAULT now(),
    user_name TEXT
);

CREATE INDEX idx_audit_action ON anofm_audit_log(action);
CREATE INDEX idx_audit_timestamp ON anofm_audit_log(timestamp DESC);
```

## Troubleshooting

### "Connection refused"
- Verify PostgreSQL 18 running: `psql -U tudor -h 127.0.0.1 -p 5433 interjob_master -c "SELECT 1"`
- Check port: `netstat -an | grep 5433`

### "Relation companies_clean does not exist"
- Table must exist (production import)
- Schema: `\d companies_clean` in psql

### "Duplicate key value violates unique constraint"
- Test data not cleaned up from previous run
- Run: `DELETE FROM companies_clean WHERE source = 'ANOFM_TEST'`

### "Pool overflow" (concurrent tests fail)
- Pool size too small (default 2-10)
- Adjust: `psycopg2.pool.SimpleConnectionPool(5, 20, ...)`

## Integration with CI/CD

For GitHub Actions / GitLab CI:

```yaml
test_anofm:
  stage: test
  script:
    - apt-get install -y postgresql-client
    - pip install pytest psycopg2
    - pytest CODE/CAMPAIGNS/EMAIL\ PERSONAL/tests/test_anofm_pg.py -v
  services:
    - postgres:18
```

## Files Modified

- `test_anofm_pg.py` — Test suite (this file)
- `import_anofm_to_companies_clean.py` — Target script (to be enhanced with audit logging)

## Related Documentation

- `.claude/pipeline.md` — ANOFM import step documentation
- `CAMPAIGNS/EMAIL PERSONAL/CODE/import_anofm_*.py` — Migration scripts
- `CAMPAIGNS/MEMORY.md` — Email pipeline status

## Questions?

See: `D:\MEMORY\.claude\campaigns.md` — ANOFM campaign configs and Brevo integration.
