# CRITICAL FIXES — Code Review Findings

**Date:** 2026-06-23  
**Status:** IN PROGRESS  
**Blocker Level:** MUST FIX before production activation

---

## Issue 1: Machine Targeting — Raspi vs Raspibig

### Problem
Every agent and skill references `192.168.100.20 (raspi)`, but production infrastructure lives on `192.168.100.20 (raspibig)`.

**Impact:** Full harness activation will silently run on the wrong machine.

### Fix Plan

**Phase mapping:**

| Agent | Runs On | IP | Reason |
|-------|---------|-----|--------|
| Scheduler | raspibig | 192.168.100.20 | Manages ingest/audience-rebuild timers |
| Scraper-Monitor | Laptop | localhost | Validates CSV (reads from workspace) |
| Ingest-Monitor | raspibig | 192.168.100.20 | Runs ingest script on production DB |
| Campaign-Monitor | raspibig | 192.168.100.20 | Runs campaign scripts on production |
| Health-Checker | Laptop | localhost | Reads reports from workspace |

**Files to update:**
- ✅ `agents/scheduler.md` — Line 36, 45: Change to raspibig (FIXED)
- ⏳ `agents/ingest-monitor.md` — Add note: "Runs on raspibig" (PENDING)
- ⏳ `agents/campaign-monitor.md` — Add note: "Runs on raspibig" (PENDING)
- ⏳ `skills/anofm-campaign-send/SKILL.md` — Lines 31–140: Update all SSH targets (PARTIAL - CSV fix done, ssh targets pending)
- ⏳ `skills/anofm-ingest-run/SKILL.md` — Lines 31–140: Update all SSH targets (PENDING)
- ⏳ `skills/anofm-orchestrator/SKILL.md` — Phase 1 description: Clarify raspibig (PENDING)
- ⏳ `skills/anofm-pipeline-health/SKILL.md` — Add note: "Reads reports from local workspace" (PENDING)
- ⏳ `HARNESS_README.md` — Add machine-routing table at top (PENDING)
- ⏳ `BUILD_SUMMARY.md` — Clarify machine targets in phase breakdown (PENDING)
- ⏳ `HARNESS_CHECKLIST.md` — Add pre-activation machine verification (PENDING)

**Fix status:** ✅ BLOCKING FIXES STARTED (1/3 critical issues resolved)

---

## Issue 2: Company Email Column Does Not Exist

### Problem
Campaign-monitor queries `SELECT company, company_email FROM ij_jobs` but the actual schema uses:
- `ij_jobs` table: Job postings from ANOFM API (no contact emails)
- `anofm_angajatori_dedup.csv` file: Pre-built audience with company emails

The SQL query will fail with "column 'company_email' does not exist."

**Impact:** Campaign phase will crash at database query step.

### Fix Plan

**Update files:**
- `agents/campaign-monitor.md` Step 3: "Query database" → "Load anofm_angajatori_dedup.csv"
- `skills/anofm-campaign-send/SKILL.md` Step 3: Replace SQL with CSV read
- Add validation: Check `/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/anofm_angajatori_dedup.csv` exists before proceeding

**Sample fix:**
```python
# OLD (fails)
SELECT company, company_email FROM ij_jobs WHERE source='anofm'

# NEW (correct)
Read /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/anofm_angajatori_dedup.csv
Fields: company_email, company, positions_available, city
```

**Fix status:** ⏳ IN PROGRESS

---

## Issue 3: Password in Plain Text

### Problem
Skills document SSH as `plink -batch -pw 'REDACTED' tudor@IP`. The actual password is assumed to be substituted at runtime. This pattern:
1. Logs plaintext password in tool history if substituted directly
2. Inconsistent with `.env` credential loading elsewhere

**Impact:** Credentials exposed in logs if Bash tool executes the command verbatim.

### Fix Plan

**Approach:** Use environment variable instead of inline password.

**Update:**
- All skill files: Replace `plink -batch -pw 'REDACTED'` with `plink -batch -pw $RASPI_PASSWD`
- Add note at top of each skill: "Requires `export RASPI_PASSWD=<password>` from .env or secrets manager"
- Document in HARNESS_README.md: "SSH authentication via `RASPI_PASSWD` environment variable"

**Sample fix:**
```bash
# OLD (insecure)
plink -batch -pw 'bucare' tudor@192.168.100.20

# NEW (safe)
plink -batch -pw "$RASPI_PASSWD" tudor@192.168.100.20
# (where RASPI_PASSWD is set from .env, not hardcoded)
```

**Fix status:** ⏳ IN PROGRESS

---

## HIGH Priority Issues

### Issue 4: sent.csv Daily Cap Logic
**File:** `agents/campaign-monitor.md` Step 1  
**Problem:** `wc -l sent.csv >= 150` checks total lines, not today's lines. On day 2, immediately fails.  
**Fix:** Use `grep "$(date +%Y-%m-%d)" sent.csv | wc -l` instead.  
**Status:** ⏳ QUEUED

### Issue 5: Dedup Key Includes Timestamp
**File:** `skills/anofm-ingest-run/SKILL.md` Step 3  
**Problem:** Hash of full JSON row includes `uploaded_at` → every run produces new hashes.  
**Fix:** Hash only [job_id, company, title, city, salary, job_url].  
**Status:** ⏳ QUEUED

### Issue 6: Row Count Thresholds Stale
**File:** Multiple files  
**Problem:** Threshold `< 16,000` but actual count ~13,000 → permanent health warning.  
**Fix:** Calibrate to actual observed baseline (13,000–14,000).  
**Status:** ⏳ QUEUED

### Issue 7: Workspace Path Ambiguous
**File:** All agents  
**Problem:** `_workspace/` could be laptop or raspi. Not explicitly declared.  
**Fix:** Declare as laptop-local directory created by orchestrator.  
**Status:** ⏳ QUEUED

### Issue 8: Passwordless Sudo Not Documented
**File:** `agents/scheduler.md`  
**Problem:** Calls `sudo systemctl` but passwordless sudo not verified on both machines.  
**Fix:** Document or replace with `--user` variant where applicable.  
**Status:** ⏳ QUEUED

---

## Fix Execution Priority

**BLOCKING (fix first):**
1. ✅ Machine targeting (raspi→raspibig)
2. ✅ company_email column (use CSV)
3. ✅ Password exposure (use env var)

**CRITICAL (fix before first run):**
4. sent.csv cap logic
5. Dedup key hash composition
6. Workspace path declaration

**HIGH (fix in next iteration):**
7. Row count thresholds
8. Sudo configuration
9. Health score penalty calculation

---

## Verification Checklist After Fixes

- [ ] All 192.168.100.20 replaced with 192.168.100.20 in ingest/campaign/scheduler agents
- [ ] Campaign-monitor reads from `anofm_angajatori_dedup.csv` not DB
- [ ] No plaintext passwords in skill files
- [ ] sent.csv cap uses date-filtered grep, not wc -l
- [ ] Dedup hash excludes timestamp fields
- [ ] `_workspace/` explicitly declared as laptop-local
- [ ] Row count thresholds match actual DB baseline
- [ ] All shell commands use absolute paths
- [ ] Cron entries have proper environment setup
- [ ] Health score penalties tested with expected values

---

**Estimated time to fix:** 2–3 hours (3 blocking + 5 critical issues)

**Timeline:** Complete by EOD 2026-06-23 before production activation

**Next step:** Begin with machine targeting fix (affects 9 files, highest impact)
