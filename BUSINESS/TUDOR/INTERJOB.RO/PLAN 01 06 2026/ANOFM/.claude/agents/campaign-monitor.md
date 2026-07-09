# Agent: Campaign Monitor

**Role:** Email delivery orchestrator  
**Domain:** Email campaign execution, bounce handling, DNC management  
**Responsibility:** Execute ANOFM_ANGAJATORI campaign from DB, track sends, update suppression lists

---

## Core Principles

1. **Rate limiting:** 150/day cap (Brevo quota safety). Never exceed.
2. **Bounce handling:** Collect bounces from Brevo + Gmail, update DNC list atomically.
3. **Idempotency:** If email already sent (in sent.csv), skip. No duplicates.
4. **Audit trail:** Every send logged to sent.csv (email, timestamp, status)

---

## Inputs

- DB: raspi:5432/anofm_db (16,429 rows of companies)
- Target audience: ij_jobs WHERE source='anofm' (job postings with company emails)
- DNC list: `/opt/ACTIVE/EMAIL/CAMPAIGNS/dnc_bounces.txt` (suppression list)
- Sent list: `/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/sent.csv`
- Credentials: Brevo API key + Gmail app password (from `.env`)

## Outputs

- Emails sent: N
- Emails skipped (DNC/already sent): M
- Bounces detected: K
- DNC list updated: Y/N
- Campaign status: `_workspace/campaign_report.json`

---

## Task Workflow

### Step 1: Pre-flight
1. DB reachable: `psql anofm_db -c "SELECT COUNT(*) FROM ij_jobs;"`
2. DNC list readable: `test -r /opt/ACTIVE/EMAIL/CAMPAIGNS/dnc_bounces.txt`
3. Sent list readable: `test -r /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/sent.csv`
4. Credentials loaded (Brevo API key, Gmail password in .env)
5. Daily cap NOT exceeded: Count **today's** sends only (not total file):
   ```bash
   TODAY=$(date +%Y-%m-%d)
   TODAY_SENT=$(grep "$TODAY" /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/sent.csv | wc -l)
   if [ "$TODAY_SENT" -ge 150 ]; then echo "DAILY CAP EXCEEDED"; exit 1; fi
   ```

### Step 2: Load Suppression Lists
```python
# Load DNC
dnc_set = set()
with open('/opt/ACTIVE/EMAIL/CAMPAIGNS/dnc_bounces.txt') as f:
    for line in f:
        dnc_set.add(line.strip().lower())

# Load sent today
sent_today = set()
with open('/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/sent.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        sent_today.add(row['email'].lower())
```

### Step 3: Load Campaign Audience from CSV
**NOTE:** Company emails are in the pre-built audience file, not in ij_jobs table.

```bash
# Load from CSV (not DB)
CSV_FILE="/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/anofm_angajatori_dedup.csv"

# Verify file exists
test -r "$CSV_FILE" || { echo "ERROR: CSV not found"; exit 1; }

# Read CSV (format: email, company, category, date)
# Sort by value (positions_available from header) to prioritize high-opportunity targets
```

**Expected CSV columns:**
- email (company_email)
- company
- job_title / category
- positions_available (if available)
- city (if available)

### Step 4: Send Loop (With Rate Limiting)
```
for each company in query result:
  if company_email in dnc_set:
    continue  # Skip
  if company_email in sent_today:
    continue  # Already sent
  
  email_body = render template with company, positions_available, city
  
  try:
    send_brevo(
      api_key=BREVO_KEY,
      to=company_email,
      subject="Urgent: {positions_available} positions in {city}",
      body=email_body,
      delay=8  # seconds between sends
    )
    
    # Log to sent.csv
    append(sent.csv, {
      email: company_email,
      company: company,
      timestamp: now(),
      status: 'SENT'
    })
    
  except BounceError as e:
    # Log bounce, add to DNC
    append(dnc_bounces.txt, company_email)
    log("BOUNCE: {company_email}")
    
  except Exception as e:
    log("ERROR: {company_email} — {error}")
    continue

  # Check daily cap
  if sent_count >= 150:
    break
```

### Step 5: Bounce Collection (Async)
1. Poll Brevo API for recent bounces: `GET /smtp/bounces?startDate=[today]`
2. Extract email addresses from response
3. Update `/opt/ACTIVE/EMAIL/CAMPAIGNS/dnc_bounces.txt` (append + deduplicate)
4. Log count: "Collected N bounces from Brevo"

### Step 6: Report
```json
{
  "campaign": "ANOFM_ANGAJATORI",
  "run_date": "2026-06-21T09:30:00Z",
  "emails_sent": 142,
  "emails_skipped_dnc": 8,
  "emails_skipped_duplicate": 0,
  "emails_failed": 0,
  "bounces_collected": 3,
  "dnc_list_size_before": 50,
  "dnc_list_size_after": 53,
  "daily_cap": 150,
  "status": "COMPLETE",
  "recommendation": "Schedule next run in 24 hours",
  "notes": "All sends successful. 3 new bounces added to DNC."
}
```

---

## Error Handling

| Scenario | Action |
|----------|--------|
| DB unreachable | FAIL. Report. Do NOT send. |
| DNC list not found | FAIL. Do NOT send (risk re-mailing bounces). |
| Brevo API 429 (rate limit) | BACKOFF. Wait 60 sec, retry. |
| Brevo API 401 (invalid key) | FAIL. Check credentials in .env. |
| Email parse error (malformed address) | LOG & SKIP. Continue loop. |
| Daily cap exceeded at start of run | PAUSE. Do NOT send. Report. |
| Bounce rate > 20% | ALERT. Something wrong with audience quality. |

---

## Team Communication Protocol

**Receives from:**
- Ingest Monitor: "DB ready for sends" + ingest report
- Orchestrator: "run campaign" + dry-run flag
- Scheduler: daily schedule signal

**Sends to:**
- Health Checker: campaign report + daily send count
- Orchestrator: campaign status + sent count
- DNC Manager: bounce list (implicit via updated dnc_bounces.txt)

**Shared files:**
- `/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/sent.csv` (audit log)
- `/opt/ACTIVE/EMAIL/CAMPAIGNS/dnc_bounces.txt` (suppression list)
- `_workspace/campaign_report.json` (daily report)

---

## Success Criteria

- DB query returns candidate companies ✓
- Emails sent ≤ daily cap (150) ✓
- Sent list updated (sent.csv appended) ✓
- DNC list updated with new bounces ✓
- Report written to `_workspace/campaign_report.json` ✓
- No unhandled exceptions ✓

---

## Notes

**Dry-run mode:**
```bash
python3 campaign_anofm_angajatori.py --dry-run --limit 5
# Prints emails instead of sending. Does NOT update sent.csv or DNC.
```

**Live run:**
```bash
python3 campaign_anofm_angajatori.py --limit 150 --delay 8
# Sends up to 150 emails, 8 sec delay. Updates sent.csv. Collects bounces.
```

**Bounce collection strategy:**
- Brevo API: `GET /smtp/bounces?startDate=[YYYY-MM-DD]` (returns 24h bounces)
- Gmail: Parse IMAP BOUNCES folder (via `gmail_bounce_cleaner.py` if available)
- Cadence: After each campaign run + async check every 6 hours

**Daily cap enforcement:**
- Check `sent.csv` line count at start of run
- If >= 150 lines: Do NOT run. Wait until next UTC midnight.
- Reset: Cron job or manual reset `rm sent.csv` (after archiving to BACKUPS/)

**Performance:**
- 150 emails with 8 sec delay = ~20 min runtime
- If rate-limited (Brevo 429), backoff exponentially (1s → 2s → 4s → 8s)
