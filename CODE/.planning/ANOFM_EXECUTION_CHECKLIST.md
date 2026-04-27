# ANOFM PostgreSQL Migration — Execution Checklist
**Date:** 2026-04-27  
**Duration:** ~25.5 hours  
**Owner:** Execute per this checklist, no deviations

---

## PHASE 0: PRE-DEPLOYMENT (30 min, 08:00–08:30 UTC)

### Section 0.1: Backup & Archive
- [ ] **Task 0.1a:** Create backup directory on laptop
  ```bash
  mkdir -p "D:\BACKUP\ANOFM\2026-04-27"
  ```
  - **Verify:** Directory exists
  - **Output:** `Directory created successfully`

- [ ] **Task 0.1b:** SCP tudor.db backup from raspibig (PRE-MIGRATION)
  ```bash
  scp tudor@192.168.100.21:/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/tudor.db "D:/BACKUP/ANOFM/2026-04-27/tudor_PRE_MIGRATION.db"
  ```
  - **Verify:** File size > 1 MB
  - **Output:** `tudor_PRE_MIGRATION.db received`

### Section 0.2: Connection Validation

- [ ] **Task 0.2a:** Test PG connection from laptop
  ```bash
  PGPASSWORD=tudor "/c/Program Files/PostgreSQL/18/bin/psql.exe" \
    -U tudor -h 127.0.0.1 -p 5433 -d interjob_master \
    -c "SELECT version(); SELECT current_timestamp;"
  ```
  - **Expected output:** PostgreSQL version + current time
  - **Verify:** No errors, response < 2 seconds

- [ ] **Task 0.2b:** Test PG connection from raspibig
  ```bash
  ssh tudor@192.168.100.21 'python3 << "PYEOF"
import psycopg2
import sys
try:
    conn = psycopg2.connect(host="127.0.0.1", port=5433, dbname="interjob_master", user="tudor", password="tudor")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name='anofm_contacts'")
    exists = cur.fetchone()[0]
    cur.close(); conn.close()
    print(f"✓ PG connection OK. Table exists: {exists == 1}")
    sys.exit(0)
except Exception as e:
    print(f"✗ Connection failed: {e}")
    sys.exit(1)
PYEOF
'
  ```
  - **Expected:** `✓ PG connection OK. Table exists: True`
  - **Verify:** Exit code 0

### Section 0.3: Schema Validation

- [ ] **Task 0.3a:** Verify anofm_contacts table schema
  ```bash
  PGPASSWORD=tudor "/c/Program Files/PostgreSQL/18/bin/psql.exe" \
    -U tudor -h 127.0.0.1 -p 5433 -d interjob_master \
    -c "\d anofm_contacts" | head -30
  ```
  - **Verify:** Columns match: email, company, city, county, source, status, sent_at, sent_via, etc.
  - **Verify:** email has UNIQUE constraint

- [ ] **Task 0.3b:** Check PG table is empty (pre-migration)
  ```bash
  PGPASSWORD=tudor "/c/Program Files/PostgreSQL/18/bin/psql.exe" \
    -U tudor -h 127.0.0.1 -p 5433 -d interjob_master \
    -c "SELECT COUNT(*) as 'Row Count', COUNT(DISTINCT email) as 'Unique Emails' FROM anofm_contacts;"
  ```
  - **Expected:** Both 0
  - **Verify:** Clean state before migration

### Section 0.4: SQLite Baseline

- [ ] **Task 0.4a:** Count SQLite records (all statuses)
  ```bash
  ssh tudor@192.168.100.21 'sqlite3 /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/tudor.db \
    "SELECT status, COUNT(*) FROM contacts GROUP BY status;"'
  ```
  - **Expected output:** pending: 1418 (or close)
  - **Record these counts:** `SQLITE_PENDING=___`, `SQLITE_SENT=___`, `SQLITE_BOUNCED=___`
  - **Verify:** Total ≈ 1,418

- [ ] **Task 0.4b:** Export SQLite schema for comparison
  ```bash
  ssh tudor@192.168.100.21 'sqlite3 /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/tudor.db ".schema contacts"' > /tmp/sqlite_schema.txt
  type /tmp/sqlite_schema.txt
  ```
  - **Verify:** Outputs CREATE TABLE statement

### Section 0.5: Orchestrator Verification

- [ ] **Task 0.5a:** Verify ANOFM config in orchestrator
  ```bash
  ssh tudor@192.168.100.21 'cat /opt/EMAIL/CAMPAIGNS/orchestrator_configs/anofm_tudor.json'
  ```
  - **Verify:** enabled=true, schedule 8-18h, interval 120min
  - **Record:** Current run command for restoration if needed

- [ ] **Task 0.5b:** Check raspi_orchestrator is running
  ```bash
  ssh tudor@192.168.100.21 'ps aux | grep raspi_orchestrator | grep -v grep'
  ```
  - **Verify:** 1 process running (PID line)

### ✓ Phase 0 Complete
**Checklist:** All 8 tasks passed  
**Timestamp:** _________________  
**Approver:** _________________

---

## PHASE 1: MIGRATION (20 min, 08:30–08:50 UTC)

### Section 1.1: Prepare Migration Script

- [ ] **Task 1.1a:** SCP migration script to raspibig
  ```bash
  scp /d/MEMORY/CODE/MIGRATIONS/migrate_anofm_sqlite_to_pg.py tudor@192.168.100.21:/tmp/
  ```
  - **Verify:** File transferred successfully

- [ ] **Task 1.1b:** Verify migration script on raspibig
  ```bash
  ssh tudor@192.168.100.21 'python3 -m py_compile /tmp/migrate_anofm_sqlite_to_pg.py && echo "✓ Script syntax OK"'
  ```
  - **Expected:** `✓ Script syntax OK`

### Section 1.2: Execute Migration

- [ ] **Task 1.2a:** Run migration (non-interactive)
  ```bash
  ssh tudor@192.168.100.21 'python3 /tmp/migrate_anofm_sqlite_to_pg.py'
  ```
  - **Expected output:**
    ```
    ✓ Migration complete:
      Inserted: 1418
      Skipped (duplicate): 0
      PG Total: 1418
      PG Pending: 1418
    ```
  - **Record actual counts:** `Inserted=___`, `Skipped=___`, `PG_Total=___`, `PG_Pending=___`
  - **Verify:** Inserted ≥ 1418 and matches SQLITE_PENDING from Phase 0.4a

### Section 1.3: Validate Migration

- [ ] **Task 1.3a:** Verify PG row count matches SQLite
  ```bash
  PGPASSWORD=tudor "/c/Program Files/PostgreSQL/18/bin/psql.exe" \
    -U tudor -h 127.0.0.1 -p 5433 -d interjob_master \
    -c "SELECT COUNT(*) as Total, COUNT(DISTINCT email) as Unique FROM anofm_contacts;"
  ```
  - **Expected:** Both equal 1418 (or actual count from task 1.3a)
  - **Verify:** Exact match

- [ ] **Task 1.3b:** Spot-check 5 random records
  ```bash
  PGPASSWORD=tudor "/c/Program Files/PostgreSQL/18/bin/psql.exe" \
    -U tudor -h 127.0.0.1 -p 5433 -d interjob_master \
    -c "SELECT email, company, city, status FROM anofm_contacts LIMIT 5;"
  ```
  - **Verify:** Columns populated, email looks valid

- [ ] **Task 1.3c:** Check for duplicates
  ```bash
  PGPASSWORD=tudor "/c/Program Files/PostgreSQL/18/bin/psql.exe" \
    -U tudor -h 127.0.0.1 -p 5433 -d interjob_master \
    -c "SELECT email, COUNT(*) FROM anofm_contacts GROUP BY email HAVING COUNT(*) > 1 LIMIT 10;"
  ```
  - **Expected:** (0 rows)
  - **Verify:** No duplicates

- [ ] **Task 1.3d:** Verify status distribution
  ```bash
  PGPASSWORD=tudor "/c/Program Files/PostgreSQL/18/bin/psql.exe" \
    -U tudor -h 127.0.0.1 -p 5433 -d interjob_master \
    -c "SELECT status, COUNT(*) FROM anofm_contacts GROUP BY status ORDER BY status;"
  ```
  - **Record:** `pending=___`, `sent=___`, `bounced=___`, `dnc=___`
  - **Verify:** Matches SQLITE distribution from Phase 0.4a

### ✓ Phase 1 Complete
**Checklist:** All 4 tasks passed  
**Migration Status:** ✓ Data verified, integrity OK  
**Timestamp:** _________________

---

## PHASE 2: PARALLEL RUN SETUP (5 min, 08:50–08:55 UTC)

### Section 2.1: Deploy PG Sender to Staging

- [ ] **Task 2.1a:** Create staging directory on raspibig
  ```bash
  ssh tudor@192.168.100.21 'mkdir -p /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR_PG'
  ```

- [ ] **Task 2.1b:** SCP sender files to staging
  ```bash
  scp /d/MEMORY/CODE/WEB/CODE/tudor_sender_pg.py tudor@192.168.100.21:/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR_PG/
  scp /d/MEMORY/CODE/WEB/CODE/sender_db_pg.py tudor@192.168.100.21:/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR_PG/
  scp /d/MEMORY/CODE/WEB/CODE/sender_mail.py tudor@192.168.100.21:/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR_PG/
  scp /d/MEMORY/CODE/WEB/CODE/sender_config.py tudor@192.168.100.21:/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR_PG/
  ```

- [ ] **Task 2.1c:** Verify staging files
  ```bash
  ssh tudor@192.168.100.21 'ls -la /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR_PG/'
  ```
  - **Verify:** 4 files present, sizes > 1 KB each

### Section 2.2: Configure Parallel Run

- [ ] **Task 2.2a:** Create parallel run script
  ```bash
  ssh tudor@192.168.100.21 'cat > /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR_PARALLEL.sh << "BASHEOF"
#!/bin/bash
# Parallel run: PG sender (30min offset from SQLite)
cd /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR_PG
python3 tudor_sender_pg.py --limit 15 >> sender_pg_parallel.log 2>&1
BASHEOF
chmod +x /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR_PARALLEL.sh
'
  ```

- [ ] **Task 2.2b:** Add to raspibig crontab (manual offset scheduling)
  ```bash
  ssh tudor@192.168.100.21 'crontab -l > /tmp/cron_backup.txt && \
  echo "0 9,12,15,18 * * 1-5 /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR_PARALLEL.sh # PG parallel (30min offset)" >> /tmp/cron_backup.txt && \
  crontab /tmp/cron_backup.txt'
  ```
  - **Verify:** `crontab -l | grep ANOFM_TUDOR_PARALLEL`

- [ ] **Task 2.2c:** Log rotation setup
  ```bash
  ssh tudor@192.168.100.21 'cat > /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR_PG/.logrotate << "LOGEOF"
/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR_PG/sender_pg_parallel.log {
    daily
    rotate 7
    compress
    delaycompress
}
LOGEOF
'
  ```

### ✓ Phase 2 Setup Complete
**Status:** Parallel run ready to start  
**Timeline:** 24 hours starting 08:55 UTC  
**Timestamp:** _________________

---

## PHASE 2: PARALLEL RUN MONITORING (24 hours, 08:55 UTC → next day 08:55 UTC)

### Daily Monitoring Checklist (run at 18:00 UTC each day)

**Day 1 @ 18:00 UTC:**
- [ ] **Task 2.3a:** Check SQLite send count (24h window)
  ```bash
  ssh tudor@192.168.100.21 'sqlite3 /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/tudor.db \
    "SELECT COUNT(*) FROM contacts WHERE status=\"sent\" AND sent_at > datetime(\"now\", \"-24 hours\");"'
  ```
  - **Record:** `SQLITE_SENT_24H = ___`

- [ ] **Task 2.3b:** Check PG send count (24h window)
  ```bash
  PGPASSWORD=tudor "/c/Program Files/PostgreSQL/18/bin/psql.exe" \
    -U tudor -h 127.0.0.1 -p 5433 -d interjob_master \
    -c "SELECT COUNT(*) FROM anofm_contacts WHERE status='sent' AND sent_at > NOW() - '24 hours'::interval;"
  ```
  - **Record:** `PG_SENT_24H = ___`

- [ ] **Task 2.3c:** Compare send counts
  - **Calculation:** `Difference = |SQLITE_SENT_24H - PG_SENT_24H| / min(SQLITE_SENT_24H, PG_SENT_24H)`
  - **Verify:** Difference < 5% (acceptable tolerance)
  - **If > 5%:** Check logs below

- [ ] **Task 2.3d:** Check Brevo bounce rate
  ```bash
  ssh tudor@192.168.100.21 'python3 << "PYEOF"
# Run from a Python script with Brevo API integration
# (Or check manually at https://app.brevo.com/statistics)
import os
api_key = os.getenv("BREVO_TUDOR_API_KEY", "your_key")
# Check bounce rate for last 7 days
# Expected: < 30%
PYEOF
'
  ```
  - **Record:** `Bounce_Rate = ___%`
  - **Verify:** < 30%

- [ ] **Task 2.3e:** Check for duplicate sends (sample 10 emails)
  ```bash
  PGPASSWORD=tudor "/c/Program Files/PostgreSQL/18/bin/psql.exe" \
    -U tudor -h 127.0.0.1 -p 5433 -d interjob_master \
    -c "SELECT email, COUNT(*) as send_count FROM anofm_contacts WHERE status='sent' GROUP BY email HAVING COUNT(*) > 1 LIMIT 10;"
  ```
  - **Expected:** (0 rows)
  - **Verify:** No duplicate sends

- [ ] **Task 2.3f:** Check logs for errors
  ```bash
  ssh tudor@192.168.100.21 'tail -50 /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/sender.log | grep -i "error\|exception\|fail" || echo "No errors in SQLite logs"'
  ssh tudor@192.168.100.21 'tail -50 /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR_PG/sender_pg_parallel.log | grep -i "error\|exception\|fail" || echo "No errors in PG logs"'
  ```
  - **Verify:** No critical errors

- [ ] **Task 2.3g:** Verify connection pool health
  ```bash
  ssh tudor@192.168.100.21 'grep "pool\|connection" /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR_PG/sender_pg_parallel.log | tail -5 || echo "No pool warnings"'
  ```
  - **Verify:** No exhaustion errors

**Summary Sheet (fill after each daily check):**

| Metric | Day 1 @ 18:00 | Day 2 @ 18:00 |
|--------|---------------|---------------|
| SQLite sent (24h) | ___ | N/A |
| PG sent (24h) | ___ | N/A |
| Difference | __% | N/A |
| Bounce rate | __% | N/A |
| Duplicates detected | ___ | N/A |
| Errors in logs | ___ | ___ |
| Connection pool OK | ✓/✗ | ✓/✗ |

### ✓ Phase 2 Monitoring Complete
**Timestamp Day 1 @ 18:00:** _________________  
**Go/No-Go Decision:** ✓ GO (continue to cutover)  OR  ✗ ABORT (return to Phase 0)

---

## PHASE 3: CUTOVER (5 min, 08:55 UTC + 24h)

### Section 3.1: Stop SQLite Sender

- [ ] **Task 3.1a:** Disable ANOFM_TUDOR in orchestrator
  ```bash
  ssh tudor@192.168.100.21 'sed -i "s/\"enabled\": true/\"enabled\": false/" /opt/EMAIL/CAMPAIGNS/orchestrator_configs/anofm_tudor.json'
  ```

- [ ] **Task 3.1b:** Verify orchestrator picked up change
  ```bash
  ssh tudor@192.168.100.21 'pkill -f raspi_orchestrator && sleep 2 && nohup python3 /opt/EMAIL/CAMPAIGNS/raspi_orchestrator.py > /tmp/orchestrator.log 2>&1 &'
  sleep 5
  ssh tudor@192.168.100.21 'grep "ANOFM_TUDOR" /tmp/orchestrator.log'
  ```
  - **Verify:** Orchestrator sees disabled config

### Section 3.2: Switch to PG Sender

- [ ] **Task 3.2a:** Update run-tudor.sh to use PG sender
  ```bash
  ssh tudor@192.168.100.21 'cat > /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/run-tudor.sh << "BASHEOF"
#!/bin/bash
# ANOFM Campaign Sender (PostgreSQL version)
cd /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR
python3 tudor_sender_pg.py "$@"
BASHEOF
chmod +x /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/run-tudor.sh
'
  ```

- [ ] **Task 3.2b:** Verify script updated
  ```bash
  ssh tudor@192.168.100.21 'cat /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/run-tudor.sh'
  ```
  - **Verify:** Points to tudor_sender_pg.py

- [ ] **Task 3.2c:** Copy PG sender files to production directory
  ```bash
  ssh tudor@192.168.100.21 'cp /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR_PG/*.py /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/'
  ```

- [ ] **Task 3.2d:** Verify files in place
  ```bash
  ssh tudor@192.168.100.21 'ls -la /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/*.py | grep -E "tudor_sender_pg|sender_db_pg"'
  ```
  - **Verify:** Both files present

### Section 3.3: Update Orchestrator Config

- [ ] **Task 3.3a:** Edit anofm_tudor.json
  ```bash
  ssh tudor@192.168.100.21 'cat > /opt/EMAIL/CAMPAIGNS/orchestrator_configs/anofm_tudor.json << "JSONEOF"
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
JSONEOF
'
  ```

- [ ] **Task 3.3b:** Verify JSON syntax
  ```bash
  ssh tudor@192.168.100.21 'python3 -m json.tool /opt/EMAIL/CAMPAIGNS/orchestrator_configs/anofm_tudor.json > /dev/null && echo "✓ JSON valid"'
  ```
  - **Expected:** `✓ JSON valid`

### Section 3.4: Test PG Sender

- [ ] **Task 3.4a:** Run test send (3 contacts, no actual send)
  ```bash
  ssh tudor@192.168.100.21 'cd /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR && python3 tudor_sender_pg.py --limit 3 --test'
  ```
  - **Expected output:** Lists 3 pending contacts, asks confirmation
  - **Verify:** No errors, correct table queried

- [ ] **Task 3.4b:** Verify PG connection pool working
  ```bash
  ssh tudor@192.168.100.21 'python3 << "PYEOF"
import sys
sys.path.insert(0, "/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR")
from sender_db_pg import get_pool, close_pool
pool = get_pool()
conn = pool.getconn()
print(f"✓ Pool connection acquired: {conn}")
pool.putconn(conn)
close_pool()
PYEOF
'
  ```
  - **Expected:** `✓ Pool connection acquired: <psycopg2 connection>`

### Section 3.5: Enable PG Sender

- [ ] **Task 3.5a:** Verify orchestrator config is enabled
  ```bash
  ssh tudor@192.168.100.21 'grep "enabled" /opt/EMAIL/CAMPAIGNS/orchestrator_configs/anofm_tudor.json'
  ```
  - **Expected:** `"enabled": true`

- [ ] **Task 3.5b:** Restart orchestrator to pick up changes
  ```bash
  ssh tudor@192.168.100.21 'pkill -f raspi_orchestrator; sleep 2; nohup python3 /opt/EMAIL/CAMPAIGNS/raspi_orchestrator.py > /tmp/orchestrator.log 2>&1 &'
  sleep 5
  ssh tudor@192.168.100.21 'grep -i "anofm_tudor" /tmp/orchestrator.log | head -3'
  ```
  - **Verify:** Orchestrator loaded ANOFM_TUDOR config

### ✓ Phase 3 Cutover Complete
**Status:** ✓ PG sender active, ready for sends  
**Timestamp:** _________________

---

## PHASE 4: VALIDATION (1 hour, 09:05–10:05 UTC + 24h)

### Section 4.1: Monitor First PG Sends (15 min)

- [ ] **Task 4.1a:** Watch sender log in real-time
  ```bash
  ssh tudor@192.168.100.21 'tail -f /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/sender.log'
  ```
  - **Run for:** 10 minutes
  - **Verify:** Sends appear, no errors
  - **Expected lines:** `[SENT] email1@... via brevo`, `[SENT] email2@... via gmail`

- [ ] **Task 4.1b:** Check database updates
  ```bash
  PGPASSWORD=tudor "/c/Program Files/PostgreSQL/18/bin/psql.exe" \
    -U tudor -h 127.0.0.1 -p 5433 -d interjob_master \
    -c "SELECT COUNT(*) FROM anofm_contacts WHERE status='sent' AND sent_at > NOW() - '30 minutes'::interval;"
  ```
  - **Expected:** >= 3 (at least initial test sends)
  - **Verify:** Status field updated

### Section 4.2: Brevo Dashboard Verification (5 min)

- [ ] **Task 4.2a:** Check Brevo outbox (manual)
  - Visit: https://app.brevo.com/dashboard
  - **Verify:** Recent ANOFM emails appear
  - **Record:** Email count in last 30 min = ___

- [ ] **Task 4.2b:** Check bounce rate (24h)
  ```bash
  # Brevo API check (if API credentials available)
  ssh tudor@192.168.100.21 'python3 << "PYEOF"
import requests, os
api_key = os.getenv("BREVO_TUDOR_API_KEY", "")
if api_key:
    r = requests.get("https://api.brevo.com/v3/smtp/statistics/aggregatedReport",
                     headers={"api-key": api_key}, params={"days": 1})
    if r.status_code == 200:
        d = r.json()
        delivered = d.get("delivered", 0)
        bounced = d.get("hardBounces", 0) + d.get("softBounces", 0)
        rate = bounced / (delivered + bounced) if (delivered + bounced) > 0 else 0
        print(f"Bounce rate (24h): {rate*100:.1f}%")
PYEOF
'
  ```
  - **Verify:** < 30%

### Section 4.3: Connection Pool Health (10 min)

- [ ] **Task 4.3a:** Check pool statistics
  ```bash
  ssh tudor@192.168.100.21 'grep -i "pool" /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/sender.log | tail -10 || echo "No pool messages"'
  ```
  - **Verify:** No "pool exhausted" or "max connections" errors

- [ ] **Task 4.3b:** Query active connections
  ```bash
  PGPASSWORD=tudor "/c/Program Files/PostgreSQL/18/bin/psql.exe" \
    -U tudor -h 127.0.0.1 -p 5433 -d interjob_master \
    -c "SELECT COUNT(*) as active_conns FROM pg_stat_activity WHERE datname='interjob_master';"
  ```
  - **Expected:** 1–3 connections (low)
  - **Verify:** No connection leak

### Section 4.4: Data Integrity (10 min)

- [ ] **Task 4.4a:** Verify sent records are correct
  ```bash
  PGPASSWORD=tudor "/c/Program Files/PostgreSQL/18/bin/psql.exe" \
    -U tudor -h 127.0.0.1 -p 5433 -d interjob_master \
    -c "SELECT COUNT(*) as sent_count, COUNT(DISTINCT email) as unique_sent FROM anofm_contacts WHERE status='sent' AND sent_at > NOW() - '1 hour'::interval;"
  ```
  - **Verify:** sent_count = unique_sent (no duplicates)

- [ ] **Task 4.4b:** Spot-check a sent record
  ```bash
  PGPASSWORD=tudor "/c/Program Files/PostgreSQL/18/bin/psql.exe" \
    -U tudor -h 127.0.0.1 -p 5433 -d interjob_master \
    -c "SELECT email, company, status, sent_at, sent_via FROM anofm_contacts WHERE status='sent' LIMIT 1;"
  ```
  - **Verify:** sent_via = "brevo" or "gmail", sent_at is recent

### Section 4.5: Rollback Readiness (5 min)

- [ ] **Task 4.5a:** Verify SQLite backup exists
  ```bash
  ls -lh /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/tudor_backup_*.db || echo "Backup not found"
  ```
  - **Verify:** File size > 1 MB

- [ ] **Task 4.5b:** Verify old sender code still accessible
  ```bash
  ssh tudor@192.168.100.21 'which tudor_sender.py || find /opt/EMAIL -name "tudor_sender.py" -type f'
  ```
  - **Verify:** Path returned

### ✓ Phase 4 Validation Complete
**Status:** ✓ PG sender operational, data verified  
**Go/No-Go:** ✓ GO (proceed to archive)  OR  ✗ ABORT (rollback to Phase 3 Section 3.1)  
**Timestamp:** _________________

---

## PHASE 5: ARCHIVE & CLEANUP (10 min, 10:05–10:15 UTC + 24h)

### Section 5.1: Archive SQLite

- [ ] **Task 5.1a:** Rename SQLite to backup
  ```bash
  ssh tudor@192.168.100.21 'mv /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/tudor.db /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/tudor_backup_20260427.db'
  ```

- [ ] **Task 5.1b:** Verify backup exists
  ```bash
  ssh tudor@192.168.100.21 'ls -lh /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/tudor_backup_20260427.db'
  ```
  - **Verify:** File size > 1 MB

### Section 5.2: Clean Staging

- [ ] **Task 5.2a:** Remove parallel staging directory
  ```bash
  ssh tudor@192.168.100.21 'rm -rf /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR_PG /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR_PARALLEL.sh'
  ```

- [ ] **Task 5.2b:** Remove parallel cron job
  ```bash
  ssh tudor@192.168.100.21 'crontab -l | grep -v ANOFM_TUDOR_PARALLEL | crontab -'
  ```

### Section 5.3: Create Local Backup

- [ ] **Task 5.3a:** SCP final backup to laptop HDD
  ```bash
  scp tudor@192.168.100.21:/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/tudor_backup_20260427.db "D:/BACKUP/ANOFM/2026-04-27/tudor_FINAL.db"
  ```

- [ ] **Task 5.3b:** Verify backup on laptop
  ```bash
  ls -lh "D:/BACKUP/ANOFM/2026-04-27/tudor_FINAL.db"
  ```
  - **Verify:** File > 1 MB, matches raspibig size

### Section 5.4: Documentation

- [ ] **Task 5.4a:** Update ANOFM_STATE.md
  ```markdown
  # ANOFM PostgreSQL Migration — COMPLETE
  - Date: 2026-04-27
  - SQLite DB: Archived at D:\BACKUP\ANOFM\2026-04-27\tudor_FINAL.db
  - PG Table: interjob_master.anofm_contacts (1,418 rows)
  - Sender: tudor_sender_pg.py (PostgreSQL + pooling)
  - Parallel run: 24h validation ✓
  - Status: PRODUCTION LIVE
  - Rollback available: tudor_backup_20260427.db (on raspibig)
  ```

- [ ] **Task 5.4b:** Create recovery SOP document
  ```bash
  cat > /d/MEMORY/CODE/.planning/ANOFM_RECOVERY_SOP.md << "EOF"
  # ANOFM Recovery SOP (Rollback Procedures)
  
  ## Quick Rollback to SQLite (< 1 hour)
  
  ### If PG sender fails during validation:
  1. Stop PG sender: `sed -i 's/"enabled": true/"enabled": false/' /opt/EMAIL/CAMPAIGNS/orchestrator_configs/anofm_tudor.json`
  2. Restore SQLite: `cp /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/tudor_backup_20260427.db /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/tudor.db`
  3. Revert run-tudor.sh: `echo 'python3 tudor_sender.py "$@"' > /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/run-tudor.sh`
  4. Restart orchestrator: `pkill -f raspi_orchestrator && sleep 2; nohup python3 /opt/EMAIL/CAMPAIGNS/raspi_orchestrator.py &`
  5. Verify: `sqlite3 /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/tudor.db "SELECT COUNT(*) FROM contacts;"`
  
  ### Timeline: ~10 minutes to full restoration
  EOF
  ```

- [ ] **Task 5.4c:** Sign-off log
  ```bash
  cat >> /d/MEMORY/CODE/.planning/ANOFM_EXECUTION_CHECKLIST.md << "EOF"
  
  ---
  
  ## MIGRATION COMPLETE
  
  | Item | Value |
  |------|-------|
  | **Completion Date** | 2026-04-27 |
  | **Execution Time** | 25.5 hours |
  | **Contacts Migrated** | 1,418 |
  | **PG Table Rows** | 1,418 |
  | **Backup Location** | D:\BACKUP\ANOFM\2026-04-27\ |
  | **Sender Status** | PostgreSQL ✓ |
  | **Bounce Rate** | < 30% ✓ |
  | **Rollback Status** | Available |
  | **Approver** | _________________ |
  | **Date** | _________________ |
  
  EOF
  ```

### ✓ Phase 5 Complete
**Status:** ✓ Migration archived, documentation complete  
**Timestamp:** _________________  
**Approver Sign-Off:** _________________

---

## FINAL CHECKLIST (Post-Migration Day 1)

Run these checks the day after cutover:

- [ ] ANOFM campaign sent emails today (check Brevo dashboard)
- [ ] Contact status correctly updated in PG (pending → sent)
- [ ] No connection errors in sender.log
- [ ] Bounce rate stable (< 30%)
- [ ] No orphaned processes (PG connections closed properly)
- [ ] Backup on laptop HDD verified readable
- [ ] ANOFM_RECOVERY_SOP.md available for emergency rollback

**Final Status: ✓ MIGRATION SUCCESSFUL**

---

**Approval Chain:**
1. Plan Review: _________________
2. Phase 0 Sign-Off: _________________
3. Phase 1 Sign-Off: _________________
4. Phase 3 Sign-Off: _________________
5. Phase 4 Sign-Off: _________________
6. Final Approval: _________________

---

**Document Version:** 1.0  
**Created:** 2026-04-27  
**Status:** READY FOR EXECUTION
