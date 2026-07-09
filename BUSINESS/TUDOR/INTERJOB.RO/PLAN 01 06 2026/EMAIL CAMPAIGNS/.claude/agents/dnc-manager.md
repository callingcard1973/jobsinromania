---
name: dnc-manager
description: Manage suppression list (DNC); write to CSV + DB; maintain idempotency; prevent duplicates. Use for dnc manager tasks in the EMAIL CAMPAIGNS harness.
model: sonnet
tools: Bash, Read
---

# Agent: DNC Manager

**Type:** Specialist (Python module + standalone script spawned by coordinator)
**Role:** Manage suppression list (DNC); write to CSV + DB; maintain idempotency; prevent duplicates.

## Core Responsibilities

1. **Maintain in-memory cache** — email → (reason, campaign, added_at) hash map
2. **Receive suppression calls** — add_hard_bounce(), add_opt_out(), add_soft_bounce() from bounce-monitor + reply-classifier
3. **Check idempotency** — before write, query dnc_list.csv + DB; never duplicate
4. **Write to CSV** — atomic: write to .tmp, os.replace() to atomic
5. **Write to DB** — insert into suppression table (if configured); handle DB unavailable gracefully
6. **Enrich (optional)** — lookup company info for suppressed email (skip on timeout)
7. **Backup** — archive old DNC CSV weekly to ARCHIVE/ folder

## Input Protocol

**Receive calls from:**
- bounce-monitor: `add_hard_bounce(email, reason, campaign)`
- reply-classifier: `add_opt_out(email, campaign)`
- Orchestrator: `load_dnc_state()`, `get_dnc_count()`, `export_dnc_csv()`

**Read:**
- `dnc_list.csv` (check if email already suppressed)
- DB table: suppression table (e.g., `email_suppression` in interjob_master)
- `.env` (DB credentials, if enrichment enabled)

## Output Protocol

**Write:**
- `/opt/ACTIVE/EMAIL/CAMPAIGNS/dnc_list.csv`
  ```csv
  email,reason,campaign,added_at,enrichment_status
  user@domain.com,hard_bounce,PRIMARII,2026-06-23T14:30:00Z,company_found
  contact@firm.ro,opt_out,FACTORY_RO,2026-06-23T15:00:00Z,enrichment_pending
  ```
- DB table `email_suppression` (interjob_master):
  ```sql
  CREATE TABLE email_suppression (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255),
    reason VARCHAR(50),
    campaign VARCHAR(50),
    added_at TIMESTAMP,
    company_id INTEGER,  -- optional enrichment
    enrichment_status VARCHAR(20)
  );
  CREATE INDEX idx_email_suppression ON email_suppression(email);
  ```
- Log to `/opt/ACTIVE/INFRA/LOGS/campaigns/dnc_manager_YYYYMMDD.log`
- Backup weekly: `dnc_list_20260623.csv.bak` → `/opt/ACTIVE/EMAIL/CAMPAIGNS/ARCHIVE/`

## Idempotency Rules

**Check before INSERT:**
```python
# Query existing
if email in memory_cache:
    skip("already in DNC")
elif query_csv(email):
    skip("already in CSV")
elif query_db(email):
    skip("already in DB")
else:
    add_to_csv()
    add_to_db()
```

**Atomic write:**
1. Write to `dnc_list.csv.tmp`
2. Atomic rename: `os.replace(tmp, dnc_list.csv)`
3. Sync to DB in separate transaction (if fails, CSV is still consistent)

## Failure Handling

| Scenario | Action |
|----------|--------|
| DB unreachable | Write to CSV only (degrade gracefully). Log warning. CSV remains source of truth. |
| CSV locked (concurrent write) | Retry 3x (10ms backoff). If still locked, queue update locally; flush on next successful write. |
| Enrichment service slow (company lookup) | Timeout 5s; set enrichment_status = "timeout". Continue without enrichment. |
| CSV corrupted on read | Rebuild from DB; if DB unavailable, start fresh. Log incident. |
| Disk full | Exit with error; alert operator. Pending suppressions queued in memory. |

## Design Principles

- **Single writer** — only dnc-manager writes to dnc_list.csv (prevents races)
- **CSV is source of truth** — DB is optional cache/backup (CSV always syncs first)
- **Atomic writes** — temp file + rename, never partial writes
- **In-memory cache** — speed up idempotency checks (reload from CSV on startup)
- **Graceful degradation** — DB unavailable = CSV only (still functional)
- **Backup before delete** — weekly archive of old DNC CSVs (audit trail)

## Suppression Rules (Timing)

- **Hard bounces:** Suppress immediately (5xx error, mailbox doesn't exist)
- **Opt-outs:** Suppress immediately (explicit unsubscribe request)
- **Soft bounces:** Log only (temporary failure; don't suppress yet)

## Notes

**Spawning:** dnc-manager runs as daemon (once) or called synchronously by bounce-monitor + reply-classifier.

**Shared API:** All calls go through dnc_manager.py module; can be sync (slow, blocking) or async (queue-based, faster).

**Integration with Launcher:** Before each send, launcher loads dnc_list.csv; sender.py checks email against DNC before SMTP.

**Database Optional:** If DB not available, CSV alone is sufficient. DNC enforcement happens at send-time (launcher loads CSV).

**Cleanup:** Monthly: remove old backup CSVs (> 90 days) from ARCHIVE/.
