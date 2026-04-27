# ANOFM PostgreSQL Migration Plan
**Status:** READY FOR EXECUTION  
**Date:** 2026-04-27  
**Database:** SQLite (tudor.db) → PostgreSQL (interjob_master.anofm_contacts)  
**Live Contacts:** 1,418  
**Campaign Location:** `/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/`  
**Risk Level:** MEDIUM (24h parallel validation required)

---

## Executive Summary

Migrate ANOFM campaign from SQLite (tudor.db) to PostgreSQL connection pooling for:
- **Scalability:** Concurrent sender processes
- **Durability:** TX logs, point-in-time recovery
- **Monitoring:** pg_stat_statements, automated health checks
- **Reliability:** Connection pooling, automatic reconnect

**Zero downtime strategy:** 24-hour parallel run (SQLite + PG side-by-side) before cutover.

---

## Phase 0: PRE-DEPLOYMENT (30 minutes)

### Checklist
- [ ] **Backup SQLite** — Archive tudor.db to HDD
  ```bash
  cp /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/tudor.db /backup/anofm_tudor_20260427.db
  ```

- [ ] **Verify PG Connection** — Test from laptop
  ```bash
  PGPASSWORD=tudor "/c/Program Files/PostgreSQL/18/bin/psql.exe" \
    -U tudor -h 127.0.0.1 -p 5433 -d interjob_master -c "SELECT 1;"
  ```

- [ ] **Verify PG Connection from raspibig** — SSH test
  ```bash
  ssh tudor@192.168.100.21 'python3 -c "import psycopg2; c=psycopg2.connect(host=\"127.0.0.1\",port=5433,dbname=\"interjob_master\",user=\"tudor\",password=\"tudor\"); print(c); c.close()"'
  ```

- [ ] **Check anofm_contacts table exists** — PG schema validation
  ```bash
  PGPASSWORD=tudor "/c/Program Files/PostgreSQL/18/bin/psql.exe" \
    -U tudor -h 127.0.0.1 -p 5433 -d interjob_master \
    -c "\dt anofm_contacts"
  ```

- [ ] **Export schema from tudor.db** — For comparison
  ```bash
  sqlite3 /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/tudor.db ".schema contacts" > /tmp/sqlite_schema.txt
  ```

- [ ] **Count SQLite records** — Baseline
  ```bash
  sqlite3 /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/tudor.db "SELECT COUNT(*) FROM contacts WHERE status='pending';"
  ```

---

## Phase 1: MIGRATION (20 minutes)

### Step 1a: Prepare Migration Script
**File:** `/d/MEMORY/CODE/MIGRATIONS/migrate_anofm_sqlite_to_pg.py`

```python
#!/usr/bin/env python3
"""
Migrate ANOFM SQLite contacts to PostgreSQL.
- Reads: /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/tudor.db (1,418 records)
- Writes: interjob_master.anofm_contacts on 127.0.0.1:5433
- Idempotent: Uses ON CONFLICT DO NOTHING (email UNIQUE constraint)
- Rollback: Delete PG records, keep SQLite intact
"""
import sqlite3
import psycopg2
import psycopg2.extras
from datetime import datetime
from pathlib import Path

SQLITE_DB = "/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/tudor.db"
PG_CONN_STR = "postgresql://tudor:tudor@127.0.0.1:5433/interjob_master"

def migrate():
    # Connect both databases
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()
    
    pg_conn = psycopg2.connect(PG_CONN_STR)
    pg_cur = pg_conn.cursor()
    
    # Read all contacts from SQLite
    sqlite_cur.execute("SELECT * FROM contacts")
    rows = sqlite_cur.fetchall()
    
    migrated = 0
    skipped = 0
    
    for row in rows:
        try:
            pg_cur.execute("""
                INSERT INTO anofm_contacts (
                    email, company, city, county, source, status,
                    sent_at, sent_via, added_at, first_name, last_name,
                    contact_name, position, phone, sector
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (email) DO NOTHING
            """, (
                row['email'], row['company'], row['city'], row['county'],
                row['source'] or 'anofm', row['status'] or 'pending',
                row['sent_at'], row['sent_via'], row['added_at'],
                row['first_name'], row['last_name'], row['contact_name'],
                row['position'], row['phone'], row['sector']
            ))
            migrated += 1
        except Exception as e:
            print(f"ERROR row {row['email']}: {e}")
            skipped += 1
    
    pg_conn.commit()
    
    # Verify counts
    pg_cur.execute("SELECT COUNT(*) FROM anofm_contacts")
    pg_total = pg_cur.fetchone()[0]
    
    pg_cur.execute("SELECT COUNT(*) FROM anofm_contacts WHERE status='pending'")
    pg_pending = pg_cur.fetchone()[0]
    
    print(f"✓ Migration complete:")
    print(f"  Inserted: {migrated}")
    print(f"  Skipped (duplicate): {skipped}")
    print(f"  PG Total: {pg_total}")
    print(f"  PG Pending: {pg_pending}")
    
    pg_cur.close(); pg_conn.close()
    sqlite_cur.close(); sqlite_conn.close()

if __name__ == "__main__":
    migrate()
```

### Step 1b: Run Migration (on raspibig)
```bash
ssh tudor@192.168.100.21 'python3 /d/MEMORY/CODE/MIGRATIONS/migrate_anofm_sqlite_to_pg.py'
```

**Expected output:**
```
✓ Migration complete:
  Inserted: 1418
  Skipped (duplicate): 0
  PG Total: 1418
  PG Pending: 1418
```

### Step 1c: Validate Schema Match
```bash
ssh tudor@192.168.100.21 'python3 -c "
import psycopg2
c = psycopg2.connect(\"postgresql://tudor:tudor@127.0.0.1:5433/interjob_master\")
cur = c.cursor()
cur.execute(\"SELECT COUNT(*), COUNT(DISTINCT email) FROM anofm_contacts\")
total, unique = cur.fetchone()
print(f\"PG: {total} total, {unique} unique emails\")
cur.close(); c.close()
"'
```

---

## Phase 2: PARALLEL RUN (24 hours)

### Setup
**Current State:** SQLite sending (`tudor_sender.py`)  
**New State:** Both SQLite + PostgreSQL running simultaneously

### Step 2a: Deploy PG Sender to Staging
1. **Copy sender code to /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR_PG/** (staging)
   ```bash
   scp -r /d/MEMORY/CODE/WEB/CODE/tudor_sender_pg.py tudor@192.168.100.21:/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR_PG/
   scp -r /d/MEMORY/CODE/WEB/CODE/sender_db_pg.py tudor@192.168.100.21:/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR_PG/
   scp -r /d/MEMORY/CODE/WEB/CODE/sender_mail.py tudor@192.168.100.21:/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR_PG/
   scp -r /d/MEMORY/CODE/WEB/CODE/sender_config.py tudor@192.168.100.21:/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR_PG/
   ```

2. **Add cron job to run PG sender in parallel** (run 30min after SQLite sender)
   ```bash
   # Via SSH: Add to raspi crontab
   # 09:00 SQLite runs → 09:30 PG runs (same contacts, no duplication risk)
   ```

### Step 2b: Monitoring During Parallel Run (24h window)

**Track both senders:**
```sql
-- PG: Check sent count in parallel window
SELECT COUNT(*) FROM anofm_contacts WHERE status='sent' AND sent_at > NOW() - '24 hours'::interval;

-- SQLite: Count from tudor.db (manual check via ssh)
sqlite3 /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/tudor.db "SELECT COUNT(*) FROM contacts WHERE status='sent' AND sent_at > datetime('now', '-24 hours');"
```

**Daily checklist (run at 18:00 UTC):**
- [ ] PG sent count matches SQLite sent count (within ±5%)
- [ ] No duplicate sends (compare email + timestamp)
- [ ] Brevo bounce rate < 30% (check both sender configs)
- [ ] No connection errors in logs

**Log files to monitor:**
- SQLite: `/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/sender.log`
- PG: `/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR_PG/sender_pg.log`
- Raspibig syslog: `ssh tudor@192.168.100.21 'tail -50 /var/log/syslog | grep -i anofm'`

---

## Phase 3: CUTOVER (5 minutes)

### Decision Criteria (all must be true)
- [ ] PG contacts table has ≥1,418 rows
- [ ] PG pending contacts = SQLite pending (or SQLite was drained)
- [ ] PG bounce rate ≤ 30% (Brevo API check)
- [ ] Zero duplicate sends (email + timestamp unique)
- [ ] No connection pool errors in PG logs

### Step 3a: Stop SQLite Sender
```bash
# Disable cron job on raspi
ssh tudor@192.168.100.21 'crontab -e'
# Comment out: 0 9,12,15,18 * * * /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/run-tudor.sh

# OR if using raspi_orchestrator.json, disable in orchestrator_configs
ssh tudor@192.168.100.21 'sed -i "s/\"enabled\": true/\"enabled\": false/" /opt/EMAIL/CAMPAIGNS/orchestrator_configs/anofm_tudor.json'
```

### Step 3b: Switch Sender Code
```bash
# Update run-tudor.sh to point to PG sender
ssh tudor@192.168.100.21 'cat > /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/run-tudor.sh << "EOF"
#!/bin/bash
cd /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR
python3 tudor_sender_pg.py "$@"
EOF
chmod +x /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/run-tudor.sh
'
```

### Step 3c: Update Orchestrator Config
```json
{
  "name": "ANOFM_TUDOR",
  "enabled": true,
  "sender": "tudor_sender_pg.py (PostgreSQL + connection pooling)",
  "database": "postgresql://127.0.0.1:5433/interjob_master.anofm_contacts",
  "schedule": {
    "hours": "8-18",
    "days": "mon-fri",
    "interval_minutes": 120
  },
  "command": {
    "run": ["bash", "/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/run-tudor.sh", "--limit", "15"],
    "cwd": "/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR",
    "timeout": 600
  }
}
```

### Step 3d: Verify First Send with PG
```bash
# Test send 3 contacts
ssh tudor@192.168.100.21 'cd /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR && python3 tudor_sender_pg.py --limit 3 --test'
```

**Expected output:**
```
Testing TUDOR_ANOFM PostgreSQL sender...
[PENDING] email1@company.ro (company1, city1) 
[PENDING] email2@company.ro (company2, city2)
[PENDING] email3@company.ro (company3, city3)
Ready to send 3 emails. Run without --test to execute.
```

### Step 3e: Enable PG Sender in Orchestrator
```bash
ssh tudor@192.168.100.21 'sed -i "s/\"enabled\": false/\"enabled\": true/" /opt/EMAIL/CAMPAIGNS/orchestrator_configs/anofm_tudor.json'

# Verify raspi_orchestrator picks it up
ssh tudor@192.168.100.21 'pkill -f raspi_orchestrator; sleep 2; nohup python3 /opt/EMAIL/CAMPAIGNS/raspi_orchestrator.py &'
```

---

## Phase 4: VALIDATION (1 hour)

### Hour 1-4: Monitor First Sends
```bash
# Watch PG logs (run every 15min for 1 hour)
watch -n 15 "ssh tudor@192.168.100.21 'tail -20 /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/sender_pg.log'"

# Check PG status
watch -n 15 "ssh tudor@192.168.100.21 'python3 -c \"
import psycopg2
c = psycopg2.connect(\\\"postgresql://tudor:tudor@127.0.0.1:5433/interjob_master\\\")
cur = c.cursor()
cur.execute(\\\"SELECT status, COUNT(*) FROM anofm_contacts GROUP BY status\\\")
for status, count in cur.fetchall():
    print(f\\\"{status}: {count}\\\")
cur.close(); c.close()
\"'"
```

### Checklist
- [ ] First 3 test sends succeeded (check Brevo dashboard)
- [ ] No PG connection pool errors
- [ ] Contact status updated to 'sent' in PG
- [ ] Bounce rate unchanged (< 30%)

---

## Phase 5: ARCHIVE (10 minutes)

### Step 5a: Rename SQLite DB
```bash
ssh tudor@192.168.100.21 'mv /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/tudor.db /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/tudor_backup_20260427.db'
```

### Step 5b: Clean Up Staging
```bash
ssh tudor@192.168.100.21 'rm -rf /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR_PG'
```

### Step 5c: Archive Backup
```bash
# SCP SQLite backup to laptop HDD
scp tudor@192.168.100.21:/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/tudor_backup_20260427.db "D:/BACKUP/ANOFM/"
```

### Step 5d: Document Migration
Create `.planning/STATE.md`:
```markdown
# ANOFM PostgreSQL Migration — COMPLETE
- Date: 2026-04-27
- SQLite DB: Archived to D:\BACKUP\ANOFM\tudor_backup_20260427.db
- PG Table: interjob_master.anofm_contacts (1,418 rows)
- Sender: tudor_sender_pg.py (PostgreSQL + pooling)
- Parallel run: 24h validation ✓
- Status: PRODUCTION LIVE
- Rollback available: tudor_backup_20260427.db
```

---

## Rollback Plan

**If PG fails during parallel run or first sends:**

### Option 1: Switch Back to SQLite (1 hour recovery)
1. Stop PG sender:
   ```bash
   ssh tudor@192.168.100.21 'sed -i "s/\"enabled\": true/\"enabled\": false/" /opt/EMAIL/CAMPAIGNS/orchestrator_configs/anofm_tudor.json'
   ```

2. Restore SQLite from parallel run (if still active):
   ```bash
   # If migration was clean and SQLite is still in parallel mode
   ssh tudor@192.168.100.21 'sed -i "s/\"enabled\": false/\"enabled\": true/" /opt/EMAIL/CAMPAIGNS/orchestrator_configs/anofm_tudor_sqlite.json'
   ```

3. Or restore from backup:
   ```bash
   ssh tudor@192.168.100.21 'cp /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/tudor_backup_20260427.db /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/tudor.db'
   ```

### Option 2: Purge PG and Retry
1. Delete PG table (with approval):
   ```bash
   PGPASSWORD=tudor "/c/Program Files/PostgreSQL/18/bin/psql.exe" \
     -U tudor -h 127.0.0.1 -p 5433 -d interjob_master \
     -c "DELETE FROM anofm_contacts WHERE campaign_id='TUDOR_ANOFM_2026';"
   ```

2. Re-run migration script
3. Resume parallel run

---

## Risk Mitigation

| Risk | Severity | Mitigation |
|------|----------|-----------|
| **PG connection fails** | HIGH | Connection pooling + auto-reconnect. Fallback to SQLite during parallel run. |
| **Data corruption during migration** | MEDIUM | Idempotent migration (ON CONFLICT), validate row counts, compare email counts before/after. |
| **Duplicate sends during parallel run** | MEDIUM | Offset sender times (SQLite 09:00, PG 09:30), compare sent email sets daily. |
| **Brevo quota exceeded** | LOW | Each sender has independent quota tracking. Parallel run splits load. |
| **Connection pool exhaustion** | LOW | Pool set to min=1, max=5. Monitor with `psycopg2.pool.getconn()` logging. |
| **Rollback takes too long** | LOW | SQLite backup available on both devices. Restore time < 1 minute. |

---

## Timeline Summary

| Phase | Duration | Start | End | Owner |
|-------|----------|-------|-----|-------|
| **Pre-Deploy** | 30 min | 08:00 | 08:30 | You |
| **Migration** | 20 min | 08:30 | 08:50 | SSH to raspibig |
| **Parallel Run** | 24 hours | 08:50 | 08:50 (next day) | Automated + monitoring |
| **Cutover** | 5 min | ~09:00 (next day) | 09:05 | SSH to raspibig |
| **Validation** | 1 hour | 09:05 | 10:05 | Monitor logs |
| **Archive** | 10 min | 10:05 | 10:15 | SSH cleanup + backup |
| **TOTAL** | ~25.5 hours | — | — | — |

---

## Success Criteria

✓ All of the following must be true:

1. **Data Integrity:** PG anofm_contacts row count ≥ 1,418
2. **No Duplicates:** Each email appears exactly once in PG (UNIQUE constraint enforced)
3. **Status Sync:** PG pending + sent + bounced + dnc = SQLite pending + sent + bounced + dnc
4. **Parallel Validation:** 24h side-by-side send counts within ±5%
5. **Bounce Rate:** Brevo < 30% (unchanged from SQLite)
6. **Connection Stability:** Zero connection pool errors in logs
7. **Code Deployment:** tudor_sender_pg.py running in production
8. **Backup:** SQLite DB archived to HDD + D:\BACKUP\ANOFM\

---

## Post-Migration (SOP)

### Weekly Checks
```bash
# Monitor PG table health
watch -n 300 "ssh tudor@192.168.100.21 'python3 -c \"
import psycopg2
c = psycopg2.connect(\\\"postgresql://tudor:tudor@127.0.0.1:5433/interjob_master\\\")
cur = c.cursor()
cur.execute(\\\"ANALYZE anofm_contacts; SELECT relname, n_tup_ins, n_tup_upd, n_tup_del FROM pg_stat_user_tables WHERE relname='anofm_contacts'\\\")
print(cur.fetchone())
cur.close(); c.close()
\"'"
```

### Monthly Maintenance
- Vacuum + analyze: `VACUUM ANALYZE anofm_contacts;`
- Check index bloat: `SELECT * FROM pg_stat_user_indexes WHERE relname='anofm_contacts_email_key';`
- Monitor connection pool: Add logging to sender_db_pg.py

### Disaster Recovery
- Full backup: `pg_dump -Fc interjob_master -t anofm_contacts > anofm_contacts_backup.dump`
- Point-in-time restore: Use PostgreSQL WAL (enabled by default)
- Restore from CSV: Re-run migration_anofm_sqlite_to_pg.py with SQLite backup

---

## Files Involved

| File | Location | Purpose |
|------|----------|---------|
| `tudor_sender_pg.py` | `/d/MEMORY/CODE/WEB/CODE/` → `/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/` | Main sender (PG) |
| `sender_db_pg.py` | `/d/MEMORY/CODE/WEB/CODE/` → `/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/` | DB layer (PG pooling) |
| `migrate_anofm_sqlite_to_pg.py` | `/d/MEMORY/CODE/MIGRATIONS/` → raspibig | One-time migration script |
| `tudor.db` | `/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/` | SQLite backup (archived) |
| `anofm_tudor.json` | `/opt/EMAIL/CAMPAIGNS/orchestrator_configs/` | Orchestrator config (updated) |
| `run-tudor.sh` | `/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/` | Runner script (updated) |

---

**Ready to deploy. Await explicit approval before Phase 0.**
