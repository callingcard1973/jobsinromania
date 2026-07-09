---
name: anofm-campaign-send
description: Execute the ANOFM cold-email campaign on raspi via the gentle MULTI-SENDER orchestrator (anofm_orchestrator.py) — 6 occupation-routed Brevo domains (factoryjobs=sudor/mecanic, electricjobs=electrician, buildjobs=zidar/tamplar, horecaworkers2026=bucatar, warehouseworkers=sofer; careworkers=yahoo-only), per-domain warmup ramp 30→150/day, 3-6min delay, disjoint partition (zero double-send), IPv4-forced for Brevo IP-allowlist, ASCII-only, flock, cron 09:00. Single source of truth = anofm DB (dnc_master + send_log); idempotent. Feedback loop auto (funnel_autosend). Used when sending/testing the ANOFM campaign, adding a sender domain, recovering interrupted sends, or checking send counts. (Legacy single-sender campaign_anofm_angajatori.py is SUPERSEDED.)
---

# Skill: anofm-campaign-send

**Domain:** Email campaign execution, rate limiting, bounce management  
**Target:** raspi (192.168.100.20), anofm/anofm_scrapes DB, Brevo API

## ARHITECTURĂ ACTUALĂ — MULTI-SENDER ORCHESTRATOR (2026-06-25)

Campania = `anofm_orchestrator.py` (NU `campaign_anofm_angajatori.py`, superseded). Toate pe raspi `/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/`.
- **Config:** `anofm_orchestrator.json` (segmente, fără secrete) + **chei `anofm_brevo_keys.json` (chmod 600)**.
- **6 domenii occupation-perfect:** factoryjobs(sudor/mecanic), electricjobs(electrician), buildjobs(zidar/tamplar), horecaworkers2026(bucatar), warehouseworkers(sofer); careworkers = doar yahoo (10/zi).
- **Gentle:** 1 thread/segment, ramp 30→60→100→150/zi, delay random 3-6 min, stagger 0-60s, **partiție disjunctă** (zero double-send), cap per segment.
- **IPv4-forțat** (`socket.getaddrinfo` patch) — Brevo IP-allowlist ține IPv4 raspi 86.126.144.222; IPv6 rotativ era blocat.
- **Suprimare unică:** `anofm.dnc_master` (DNC fresh 2h via `refresh_dnc_master.py`) + `anofm.send_log` (tot istoricul). Audiență din `anofm_scrapes` DB (deficit-only, gmail in / yahoo separat).
- **ASCII-only** (NFKD fold + punct map), List-Unsubscribe per domeniu, flock, cron `0 9 * * 1-5`.
- **Feedback auto:** `funnel_autosend.py` (interested → catalog via Brevo, gated send_log; timer email-catalog-funnel 30min) → coș → `process_requests.py`.
- **Vizibilitate/siguranță:** `anofm_digest.py` (cron 07:00 Telegram), `anofm_guard.py` (cron 6h, auto-pauză segment dacă bounce>8% peste ≥50 trimiteri).
- **Adăugare domeniu nou:** cheie în `anofm_brevo_keys.json` + segment în config (key_name, occupations, ramp) + scoate ocupația din segmentul generic (evită overlap).

**Input:** dry-run flag  ·  **Output:** sent/skipped per segment, send_log, digest

Secțiunile de mai jos (campaign_anofm_angajatori.py, cap 290) sunt LEGACY — păstrate pt referință istorică.

## ⚠️ UNSUBSCRIBE / List-Unsubscribe (Gmail/Yahoo compliance — DO NOT REMOVE)

Every ANOFM send MUST carry a `List-Unsubscribe` header (Gmail+Yahoo bulk-sender
rules 2024 — without it, gmail/yahoo deliverability tanks). Wiring:

- `campaign_anofm_angajatori.py` sets `UNSUB_HEADERS = {"List-Unsubscribe":
  "<mailto:unsubscribe@interjob.ro?subject=unsubscribe>"}` and passes it +
  `reply_to=office@interjob.ro` to `sender.send_brevo(..., headers=UNSUB_HEADERS)`.
- `sender.send_brevo` accepts `headers=` → Brevo payload `headers` (added 2026-06-25).
- **A2 forwarder** `unsubscribe@interjob.ro → office@interjob.ro` (cPanel loaiidil,
  Email/add_forwarder). office@interjob.ro is scanned by `universal_reply_handler.py`
  (raspibig, 2h); subject "unsubscribe" matches OPTOUT → writes `dnc_list.csv` →
  `refresh_dnc_master.py` pulls → `dnc_master` → campaign suppresses. Loop closed.
- Template also keeps the visible "raspundeti cu STOP" fallback.
- If you ever change the unsubscribe address, re-create the A2 forwarder and keep the
  mailbox in universal_reply_handler's scan list, else opt-outs are silently lost.

---

## When to Use

- **Live sends:** "Send today's batch of emails (up to 150)"
- **Dry-run test:** "Show me which 5 emails would be sent, without actually sending"
- **Recovery:** "Resume sends after interruption (safely skips already-sent)"
- **Bounce check:** "Collect bounces from Brevo and update DNC"
- **Daily cadence:** "Run the campaign as scheduled"

---

## How It Works

### Step 1: Pre-flight Checks
```bash
ssh tudor@192.168.100.20

# DB reachable
psql anofm_db -c "SELECT COUNT(*) FROM ij_jobs;" 

# Credentials loaded
test -r /opt/ACTIVE/ANOFM/.env && source /opt/ACTIVE/ANOFM/.env

# SINGLE SOURCE OF TRUTH (raspi anofm DB): dnc_master + send_log
psql -d anofm -c "SELECT count(*) FROM dnc_master;"   # DNC (bounces + opt-out replies, refreshed 2h)
psql -d anofm -c "SELECT count(*) FROM send_log;"     # all ANOFM sent history (ce/unde/cand)

# Daily cap NOT exceeded
psql -d anofm -tc "SELECT count(*) FROM send_log WHERE campaign='ANOFM_ANGAJATORI' AND sent_at::date=CURRENT_DATE;"
# If ≥ 290, do NOT run (Brevo free daily limit)
```

### Step 2: Load Suppression Lists (from the unified DB — NOT files)
The campaign script `campaign_anofm_angajatori.py` already loads these from the DB.
DNC = `anofm.dnc_master` (kept fresh every 2h by `refresh_dnc_master.py`, pulling
raspibig's live `dnc_bounces.txt`/`dnc_list.csv`/`dnc_bounces_annotated.csv`).
Sent = `anofm.send_log` (full ANOFM history across campaigns).
```python
import psycopg2
conn = psycopg2.connect(dbname='anofm', user='tudor', host='localhost', password='tudor')
cur = conn.cursor()
cur.execute("SELECT lower(email) FROM dnc_master"); dnc_set = {r[0] for r in cur.fetchall()}
cur.execute("SELECT lower(email) FROM send_log");   sent = {r[0] for r in cur.fetchall()}
# every real send also INSERTs into send_log (single source); sent.csv kept as mirror
```

### Step 3: Load Campaign Audience (Pre-Built CSV)
**CSV location:** `/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/anofm_angajatori_dedup.csv`

**NOTE:** Company emails come from the pre-built audience CSV, NOT from ij_jobs table. The CSV is maintained by `anofm_angajatori_rebuild.py` which dedupes companies and filters DNC.

```bash
CSV="/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/anofm_angajatori_dedup.csv"
test -r "$CSV" || { echo "ERROR: CSV not found"; exit 1; }

# CSV format: email,company,category,positions_available
# Already sorted by positions DESC (highest opportunity first)
```

### Step 4: Send Loop (With Rate Limiting)
```python
sent_count = 0
failed_count = 0

for company in query_results:
    # Check daily cap
    if sent_count >= 150:
        break
    
    # Check suppression lists
    if company['company_email'].lower() in dnc_set:
        continue  # Skip
    if company['company_email'].lower() in sent_today:
        continue  # Skip (already sent)
    
    # Render email body
    body = template.format(
        company_name=company['company'],
        positions=company['positions_available'],
        city=company['city'],
        title=company['job_title']
    )
    
    subject = f"Urgent: {company['positions_available']} positions in {company['city']}"
    
    try:
        # Send via Brevo
        result = send_brevo(
            api_key=BREVO_KEY,
            to=company['company_email'],
            subject=subject,
            body=body,
            sender="elena.manpower.dristor@gmail.com",
            delay=8  # seconds between sends
        )
        
        # Log to sent.csv (append)
        with open(sent_csv, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['email', 'company', 'timestamp', 'status'])
            writer.writerow({
                'email': company['company_email'],
                'company': company['company'],
                'timestamp': datetime.now().isoformat(),
                'status': 'SENT'
            })
        
        sent_count += 1
        
    except Exception as e:
        # Log error, continue
        log(f"FAILED: {company['company_email']} — {str(e)}")
        failed_count += 1
        continue
```

### Step 5: Bounce Collection (Async)
```bash
# Brevo bounces (last 24h)
curl -X GET "https://api.brevo.com/v3/smtp/bounces?startDate=$(date -u +%Y-%m-%d)" \
  -H "api-key: $BREVO_BUILDJOBS_API_KEY" | jq '.result[].email' >> dnc_bounces.txt

# Deduplicate
sort -u dnc_bounces.txt -o dnc_bounces.txt
```

### Step 6: Generate Report
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
  "runtime_seconds": 1200,
  "bounce_rate": 2.1,
  "recommendation": "Schedule next run in 24 hours",
  "notes": "All sends successful. 3 new bounces added to DNC."
}
```

---

## Dry-run Mode

```bash
# Read DB, load suppression lists, show what WOULD be sent
# Do NOT send emails
# Do NOT update sent.csv or DNC

python3 /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/campaign_anofm_angajatori.py \
  --dry-run \
  --limit 5  # Show first 5 candidates
```

Output (dry-run):
```
DRY-RUN MODE

Would send to:
1. vips@company1.ro (50 positions, Constanța)
2. hr@company2.ro (35 positions, Bucharest)
3. info@company3.ro (25 positions, Iasi)
[... 2 more ...]

Total to send: 5 (in live mode: 150)
Sent list size: 142
DNC list size: 50
```

---

## Error Scenarios

| Scenario | Handling |
|----------|----------|
| DB unreachable | FAIL. Do NOT send. Check PostgreSQL. |
| DNC list not found | FAIL. Do NOT send (risk re-mailing bounces). |
| Brevo API 429 (rate limit) | BACKOFF. Wait 60 sec, retry. |
| Brevo API 401 (invalid key) | FAIL. Check credentials in .env. |
| Email parse error (malformed address) | LOG & SKIP. Continue loop. |
| Daily cap exceeded at start | PAUSE. Do NOT send. Report. |
| Bounce rate > 20% | ALERT. Something wrong with audience. |

---

## Command Examples

```bash
# Live send (up to 150)
ssh tudor@192.168.100.20 "cd /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI && python3 campaign_anofm_angajatori.py"

# Dry-run (no emails sent)
ssh tudor@192.168.100.20 "cd /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI && python3 campaign_anofm_angajatori.py --dry-run --limit 5"

# Limited send (50 emails)
ssh tudor@192.168.100.20 "cd /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI && python3 campaign_anofm_angajatori.py --limit 50 --delay 8"

# Check sent count
ssh tudor@192.168.100.20 "wc -l /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/sent.csv"

# Monitor in real-time
ssh tudor@192.168.100.20 "tail -f /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/sent.csv"
```

---

## Rate Limiting & Daily Cap

**Daily cap:** 150 emails/day (Brevo quota safety)
- Checked at start of run
- If already sent 150 today: skip (wait until UTC midnight)
- Reset: automatic (sent.csv is daily snapshot) or manual archive

**Delay between sends:** 8 seconds
- Brevo recommendation: 8–10 sec per email
- Prevents account flagging as bot
- Can be adjusted if Brevo allows faster rate

---

## DNC List Management

**Sources:**
- Brevo bounces (hard bounces, unsubscribes): `/smtp/bounces` API
- Gmail bounces: IMAP BOUNCES folder parsing (optional)
- Manual additions: `echo "email@domain.com" >> dnc_bounces.txt`

**Dedup:** Sort -u to remove duplicates

**Size:** Currently ~50 entries. Monitor growth (if > 500, may indicate list decay).

---

## Performance Notes

- 150 emails with 8 sec delay = ~20 min runtime
- Brevo API call overhead: <1 sec per email
- If rate-limited (429), exponential backoff: 1s → 2s → 4s → 8s
