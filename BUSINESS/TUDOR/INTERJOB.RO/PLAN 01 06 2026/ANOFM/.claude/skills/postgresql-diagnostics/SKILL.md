---
name: postgresql-diagnostics
description: Diagnose and fix PostgreSQL connection issues on remote servers (socket vs TCP, PGHOST misconfiguration, cluster path errors, permission issues). SSH-based diagnosis via plink. Used when psql fails with "Invalid data directory" or connection refused, testing database connectivity, recovering from crashed clusters, or verifying PostgreSQL health.
---

# Skill: postgresql-diagnostics

**Domain:** PostgreSQL troubleshooting, connection debugging  
**Target:** Remote PostgreSQL servers (via SSH + plink)  
**Input:** Server IP, username, database name, error message  
**Output:** Root cause analysis, connection test results, remediation steps

---

## When to Use

- **Connection fails:** "psql: Invalid data directory for cluster" or connection refused
- **Socket vs TCP confusion:** psql works with `-h localhost` but not without it
- **Environment misconfiguration:** PGHOST/PGDATA/PGUSER not set correctly
- **Cluster path errors:** "data directory for cluster 17 main" issues
- **Permission problems:** psql works as postgres but not as regular user
- **Health verification:** Test a remote DB is working before deploying apps

---

## How It Works

### Step 1: Check PostgreSQL Process Status

```bash
ssh user@server
ps aux | grep postgres | grep -v grep
# Should show: postgres main server + worker processes
```

**What to look for:**
- `/usr/lib/postgresql/XX/bin/postgres -D /var/lib/postgresql/XX/main`
- Multiple worker processes (checkpointer, walwriter, autovacuum)
- If none found → PostgreSQL not running

### Step 2: Test Connection as postgres superuser

```bash
sudo -u postgres psql -c "SELECT version();"
# Should return: PostgreSQL X.X (Debian ...)
```

**Success = DB is running.** If fails, check:
- Systemd status: `systemctl status postgresql`
- Data directory permissions: `ls -ld /var/lib/postgresql/XX/main`
- Log file: `/var/log/postgresql/postgresql-XX-main.log`

### Step 3: Test Connection as Regular User

```bash
psql -h localhost dbname -c "SELECT 1;"
# Try without -h (socket):
psql dbname -c "SELECT 1;"
```

**Result determines root cause:**

| Command | Result | Issue |
|---------|--------|-------|
| `psql -h localhost ...` | ✅ Works | Socket misconfigured (socket version fails) |
| `psql ...` (no `-h`) | ❌ Fails | Socket path wrong or PGHOST env var needed |
| Both fail | ❌ Fails | TCP or authentication issue |

### Step 4: Check Environment Variables

```bash
echo $PGHOST
echo $PGDATA
echo $PGUSER
# If empty or wrong, that's the problem
```

**Expected values:**
```
PGHOST=localhost (or IP if remote)
PGDATA=/var/lib/postgresql/XX/main
PGUSER=postgres (or specific user)
```

### Step 5: Diagnose Root Cause

**Common issues:**

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Invalid data directory for cluster 17 main` | PGHOST not set → tries Unix socket | `export PGHOST=localhost` |
| `Connection refused` | PostgreSQL not running | `systemctl start postgresql` |
| `role "user" does not exist` | User not created in DB | `sudo -u postgres createuser user` |
| `permission denied for socket /var/run/postgresql/.s.PGSQL.5432` | Socket permissions wrong | `chmod 777 /var/run/postgresql/` |
| `FATAL: remaining connection slots are reserved for superuser` | DB connection limit reached | Check active connections, kill idle ones |

### Step 6: Apply Fix

**If socket issue (most common):**
```bash
# Permanent fix (add to ~/.bashrc)
echo 'export PGHOST=localhost' >> ~/.bashrc
source ~/.bashrc

# Verify
psql -c "SELECT COUNT(*) FROM ij_jobs;"
```

**If PostgreSQL not running:**
```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
sudo systemctl status postgresql
```

**If authentication issue:**
```bash
# Check pg_hba.conf
sudo cat /etc/postgresql/17/main/pg_hba.conf | grep -E "^(local|host)"

# Typical fix: add "trust" or "md5" auth for local user
# Restart: sudo systemctl restart postgresql
```

### Step 7: Verify Fix

```bash
# Full connectivity test
psql -h localhost dbname << 'EOF'
SELECT version();
SELECT COUNT(*) FROM information_schema.tables;
BEGIN; SELECT 1; ROLLBACK;
EOF
```

**Success criteria:**
- ✅ Version query returns PostgreSQL version
- ✅ Table count query succeeds
- ✅ BEGIN/ROLLBACK executes (transactions work)

---

## Troubleshooting Examples

### Example 1: Socket Issue (Most Common)

**Error:**
```
$ psql anofm_db -c "SELECT 1;"
Error: Invalid data directory for cluster 17 main
```

**Diagnosis:**
```bash
$ ps aux | grep postgres
postgres  1046 ... postgres -D /var/lib/postgresql/17/main  # ✅ Running

$ sudo -u postgres psql anofm_db -c "SELECT 1;"
 ?column? 
----------
        1  # ✅ Works as postgres
```

**Root cause:** Regular user psql tries Unix socket (which doesn't exist), but PostgreSQL is running fine on TCP.

**Fix:**
```bash
export PGHOST=localhost
psql anofm_db -c "SELECT 1;"  # ✅ Works now
```

### Example 2: PostgreSQL Not Running

**Error:**
```
$ psql anofm_db
psql: error: could not connect to server: Connection refused
```

**Diagnosis:**
```bash
$ ps aux | grep postgres
# No postgres process found

$ systemctl status postgresql
● postgresql.service - PostgreSQL RDBMS
  Active: inactive (dead)  # ❌ Not running
```

**Fix:**
```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
systemctl status postgresql  # Should show: active (running)
```

### Example 3: Role Doesn't Exist

**Error:**
```
$ psql -U wronguser anofm_db
psql: error: role "wronguser" does not exist
```

**Fix:**
```bash
# Create user
sudo -u postgres createuser tudor
sudo -u postgres psql -c "ALTER USER tudor WITH PASSWORD 'password';"

# Or connect with existing user
psql -U postgres anofm_db
```

---

## Performance Notes

- Full diagnosis: ~10–30 seconds (includes SSH overhead)
- Most issues fixable in <5 minutes
- Socket issue (PGHOST): <1 minute fix
- PostgreSQL restart: 5–10 seconds downtime
- If DB in use, kills connections: notify users first

---

## Prevention

**Best practices to avoid these issues:**

1. **Set PGHOST in ~/.bashrc** at account creation:
   ```bash
   echo 'export PGHOST=localhost' >> ~/.bashrc
   ```

2. **Test connectivity after deployment:**
   ```bash
   psql dbname -c "SELECT COUNT(*) FROM information_schema.tables;" 
   ```

3. **Monitor PostgreSQL uptime:**
   ```bash
   systemctl is-active postgresql  # Should return "active"
   ```

4. **Keep connection pools alive:**
   - Use connection pooling (pgbouncer) for apps
   - Monitor idle connections: `SELECT count(*) FROM pg_stat_activity WHERE state='idle';`

---

## Integration with Harness

In ANOFM harness:
- **Phase 4 (Ingest Monitor)** uses this skill to validate DB before ingesting
- **Phase 6 (Health Checker)** uses this to verify PostgreSQL health
- **Fallback:** If PostgreSQL issue detected, health score reduced, alert generated

**Sample health check integration:**
```bash
#!/bin/bash
export PGHOST=localhost
psql anofm_db -c "SELECT 1;" > /dev/null 2>&1
if [ $? -eq 0 ]; then
  echo "database: OK"
else
  echo "database: FAILED (see postgresql-diagnostics skill)"
  exit 1
fi
```
