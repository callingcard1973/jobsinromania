---
name: cron-job-automation
description: Set up reliable cron jobs with logging, error handling, and monitoring on remote servers. Handles crontab editing safely (backup before change), creates log directories, verifies execution, and tests schedule compliance. SSH-based via plink. Used when scheduling recurring tasks, setting up automated pipelines, adding cleanup jobs, or verifying cron execution.
---

# Skill: cron-job-automation

**Domain:** Cron job scheduling, task automation  
**Target:** Remote Linux servers (via SSH + plink)  
**Input:** Server IP, schedule (cron expression), command, log path  
**Output:** Crontab entry verified, log files ready, test execution passed

---

## When to Use

- **Set up recurring task:** "Run this command every day at 09:00"
- **Add cleanup job:** "Delete old files monthly"
- **Schedule pipeline:** "Scrape at 08:00, ingest at 09:00, report at 10:00"
- **Add monitoring:** "Check health every 6 hours"
- **Verify execution:** "Did the cron job actually run?"
- **Fix failed crons:** "Job ran but produced no output"

---

## How It Works

### Step 1: Backup Current Crontab

**Always backup before editing:**
```bash
crontab -l > ~/crontab.backup_$(date +%Y%m%d_%H%M%S)
echo "✓ Backup saved"
```

**Why:** If you accidentally corrupt the crontab syntax, you can restore from backup.

### Step 2: Prepare New Entry

**Cron format:**
```
MIN HOUR DOM MON DOW COMMAND

MIN:  0–59
HOUR: 0–23 (UTC)
DOM:  1–31 (day of month)
MON:  1–12 (month)
DOW:  0–7 (day of week, 0=Sun, 1=Mon, ...7=Sun)
```

**Common expressions:**

| Schedule | Expression | Example |
|----------|-----------|---------|
| Every day at 09:00 | `0 9 * * *` | Email campaign send |
| Mon–Fri at 09:00 | `0 9 * * 1-5` | Weekday business task |
| Every 6 hours | `0 */6 * * *` | Health check |
| Daily at midnight | `0 0 * * *` | Backup, cleanup |
| Monthly 1st at 00:00 | `0 0 1 * *` | Monthly report |
| Every 30 minutes | `*/30 * * * *` | Frequent polling |

**Key additions to command:**

1. **Environment variables** (if needed):
   ```bash
   0 9 * * 1-5 export PGHOST=localhost && cd /path && python3 script.py
   ```

2. **Logging** (REQUIRED):
   ```bash
   0 9 * * 1-5 python3 script.py >> /var/log/myjob.log 2>&1
   ```

3. **Error notification** (optional):
   ```bash
   0 9 * * 1-5 python3 script.py >> /var/log/myjob.log 2>&1 || echo "FAILED" | mail -s "Cron Error" admin@example.com
   ```

### Step 3: Create Log Directory

```bash
mkdir -p /var/log/myapp/
chmod 777 /var/log/myapp/  # Make writable by cron user
touch /var/log/myapp/myjob.log
```

### Step 4: Add Entry to Crontab

**Safe method (programmatically):**
```bash
# Load current crontab
crontab -l > /tmp/crontab.new

# Append new entry
cat >> /tmp/crontab.new << 'EOF'
0 9 * * 1-5 export PGHOST=localhost && python3 /opt/script.py >> /var/log/myjob.log 2>&1
EOF

# Install updated crontab
crontab /tmp/crontab.new
```

**Verify installation:**
```bash
crontab -l | grep "script.py"  # Should show your entry
```

### Step 5: Test Execution

**Verify cron can read/execute:**

1. **Check if entry appears:**
   ```bash
   crontab -l | grep "myjob"
   ```

2. **Check if next run is scheduled:**
   ```bash
   # On systems with `at` utility:
   atq  # Shows scheduled jobs
   # Or check syslog:
   tail -20 /var/log/syslog | grep CRON
   ```

3. **Test manual execution:**
   ```bash
   # Run the command directly to verify it works:
   export PGHOST=localhost && python3 /opt/script.py
   # Check output matches what's expected
   ```

4. **Verify logging:**
   ```bash
   tail -5 /var/log/myjob.log
   # Should show recent execution
   ```

### Step 6: Monitor Execution

**After cron job is scheduled:**

1. **Check log growth:**
   ```bash
   ls -lh /var/log/myjob.log
   # Size should increase after scheduled time
   ```

2. **Verify recent runs:**
   ```bash
   tail -20 /var/log/myjob.log
   # Should show timestamp, status, output
   ```

3. **Alert on failures:**
   ```bash
   tail -1 /var/log/myjob.log | grep -i error && echo "FAILED"
   ```

---

## Example: ANOFM Campaign Cron

**Real-world example from ANOFM deployment:**

```bash
# Goal: Send emails Mon-Fri at 09:00, 150/day, with logging

# Step 1: Backup
crontab -l > /tmp/crontab.backup

# Step 2: Prepare entry
ENTRY="0 9 * * 1-5 export PGHOST=localhost && cd /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI && python3 campaign_anofm_angajatori.py --limit 150 --delay 8 >> /opt/ACTIVE/INFRA/LOGS/anofm_campaign.log 2>&1"

# Step 3: Create log dir
mkdir -p /opt/ACTIVE/INFRA/LOGS
chmod 666 /opt/ACTIVE/INFRA/LOGS/anofm_campaign.log

# Step 4: Add to crontab
crontab -l > /tmp/crontab.new
echo "$ENTRY" >> /tmp/crontab.new
crontab /tmp/crontab.new

# Step 5: Verify
crontab -l | grep "campaign_anofm_angajatori"

# Step 6: Wait for 09:00 UTC, then check log
# tail -20 /opt/ACTIVE/INFRA/LOGS/anofm_campaign.log
```

**Log entry format (expected):**
```
2026-06-24 09:00:15 Starting ANOFM_ANGAJATORI campaign
2026-06-24 09:00:15 Loaded 1,470 candidates
2026-06-24 09:20:42 Sent 142 emails (rate: 8 sec/email)
2026-06-24 09:20:43 Collected 3 bounces from Brevo
2026-06-24 09:20:43 Updated DNC list (+3)
2026-06-24 09:20:43 Campaign complete - SUCCESS
```

---

## Troubleshooting Cron Jobs

### Problem: Cron Job Doesn't Run at Scheduled Time

**Diagnosis:**
```bash
# 1. Verify entry exists
crontab -l | grep "myjob"

# 2. Check if cron daemon is running
systemctl status cron
# or
systemctl status crond

# 3. Check system time (must be accurate)
date
timedatectl  # Check if NTP is enabled

# 4. Review syslog for cron errors
grep CRON /var/log/syslog | tail -20
```

**Fixes:**
- Entry missing? → Add it again (Step 4)
- Daemon not running? → `systemctl start cron`
- Time wrong? → `sudo timedatectl set-ntp true`
- Syntax error in crontab? → Check with `crontab -l` (cron won't run if syntax invalid)

### Problem: Cron Job Runs but Produces No Output

**Diagnosis:**
```bash
# 1. Check log file exists and is writable
ls -l /var/log/myjob.log
chmod 666 /var/log/myjob.log

# 2. Check if command path is absolute
crontab -l | grep "myjob"
# If it's "cd /path && ./script.py", it might fail
# Cron doesn't have shell context; must be absolute paths

# 3. Test manually with same environment cron uses
env -i HOME=$HOME /bin/sh -c '/opt/script.py >> /var/log/myjob.log 2>&1'
```

**Fixes:**
- Use absolute paths only: `/opt/script.py` NOT `./script.py`
- Set PATH at top of crontab: `PATH=/usr/bin:/bin`
- Redirect all output: `>> /var/log/myjob.log 2>&1` (stderr AND stdout)

### Problem: Cron Job Runs Too Often (Or Not Enough)

**Diagnosis:**
```bash
# Check cron expression
crontab -l | grep "myjob"

# Examples of common mistakes:
* * * * *          # WRONG: every minute (not intended)
0 * * * *          # CORRECT: hourly
0 */6 * * *        # CORRECT: every 6 hours
0 9 * * 1-5        # CORRECT: Mon-Fri at 09:00
```

**Fix:** Edit crontab with correct schedule (see table above for expressions).

---

## Safety Best Practices

1. **Always backup before editing:**
   ```bash
   crontab -l > ~/crontab.backup_$(date +%s)
   ```

2. **Use absolute paths only:**
   ```bash
   ✅ /opt/script.py
   ❌ ~/script.py
   ❌ ./script.py
   ❌ script.py
   ```

3. **Redirect all output:**
   ```bash
   ✅ command >> /var/log/job.log 2>&1
   ❌ command  (silent, can't debug)
   ```

4. **Set explicit environment:**
   ```bash
   ✅ export PGHOST=localhost && command
   ❌ command  (missing env vars)
   ```

5. **Test command before scheduling:**
   ```bash
   # Run manually first
   /opt/script.py
   # Then add to cron
   ```

6. **Monitor logs regularly:**
   ```bash
   tail -20 /var/log/job.log  # After scheduled time
   # Look for errors, timing issues, output gaps
   ```

---

## Crontab Limits & Gotchas

| Limit | Issue | Solution |
|-------|-------|----------|
| Max command length | Very long commands may be truncated | Use shell script wrapper instead |
| No shell context | `cd`, `~`, pipes may fail | Use absolute paths, full paths to commands |
| No user interaction | `read`, `sudo` prompts will hang | Use passwordless sudo or pre-auth |
| Email notification | Cron sends output to mbox (can fill disk) | Redirect to file explicitly |
| File permissions | Cron user can't write to restricted files | Create log dir with 777 permissions |
| Large output | Logging 100MB/day can fill disk | Implement log rotation (logrotate) |

---

## Integration with Harness

**In ANOFM harness:**
- Campaign sends scheduled daily (Mon-Fri 09:00)
- Health checks scheduled every 6 hours
- Both log to files monitored by orchestrator

**Adding new scheduled task to ANOFM:**
```bash
# Example: Weekly report (Sunday 18:00)
0 18 * * 0 export PGHOST=localhost && python3 /opt/ANOFM/weekly_report.py >> /opt/ACTIVE/INFRA/LOGS/anofm_weekly.log 2>&1
```

---

## Quick Reference

**Add a cron job:**
```bash
crontab -l > /tmp/crontab.backup
echo "0 9 * * 1-5 /opt/script.py >> /var/log/job.log 2>&1" | crontab -
crontab -l | tail -1
```

**Remove a cron job:**
```bash
crontab -l > /tmp/crontab.new
sed -i '/script.py/d' /tmp/crontab.new
crontab /tmp/crontab.new
```

**Check if cron ran:**
```bash
tail -10 /var/log/job.log
tail -20 /var/log/syslog | grep CRON
```
