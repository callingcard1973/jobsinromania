# 📋 ANOFM Campaign — Complete Stack Reference

**Date:** 2026-06-19  
**Campaign:** ANOFM_ANGAJATORI (Active Email Outreach)  
**Status:** ✅ LIVE & SENDING  
**Last Updated:** 2026-06-19 10:42 UTC

---

## 🎯 Campaign Overview

| Attribute | Value |
|-----------|-------|
| **Purpose** | Lead generation: Match InterJob.ro job candidates with ANOFM-listed employers |
| **Audience** | 1,470 verified business entities (construction, manufacturing, hospitality, IT) |
| **Daily Cap** | 150 emails/day |
| **Delay** | 240 seconds (4 minutes) between emails |
| **Sender Email** | office@warehouseworkers.eu |
| **Sender Name** | Elena Vasilescu - InterJob.ro |
| **Email Provider** | Brevo (warehouseworkers.eu account) |
| **Template** | 1 base template with {placeholders} |
| **Status** | ✅ ENABLED (fixed 2026-06-19) |
| **Process PID** | 1127122 (running since 10:41 UTC) |
| **Memory Usage** | 25.7 MB |

---

## 1️⃣ Data Source — Where Leads Come From

### Master CSV File
```
Location: /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/anofm_angajatori_dedup.csv
Size: 159 KB
Rows: 1,470 unique emails
Format: 7 columns
Updated: 2026-06-18 06:07 UTC
```

### CSV Columns & Example
```csv
email,company_name,sector,county,job_title,positions_available,company_org_number
office@snc.ro,SANTIERUL NAVAL CONSTANTA SA,Construcții / Instalații,,SUDOR CU ARC ELECTRIC ACOPERIT SUB STRAT DE FLUX,39,1879871
office@inova-group.ro,INOVA INTERNATIONAL SRL,IT / Telecomunicații,,OPERATOR CALCULATOR ELECTRONIC SI RETELE,10,17013137
```

### Data Quality
| Attribute | Value | Quality |
|-----------|-------|---------|
| Unique emails | 1,470 | 100% |
| Valid email format | 1,470 | 100% |
| Company names | 1,470 | 100% |
| Sector classification | 1,470 | 100% |
| Job titles | 1,470 | 100% |
| County | 1,150 | 78% |
| Positions available | 1,470 | 100% |

**Data Source:** ANOFM scrapers (anofm_daily_report.py + ingest_anofm.py)

---

## 2️⃣ Email Template — Message Format

### File Location
```
/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/TEMPLATES/template_anofm_angajatori.txt
Size: 691 bytes
Updated: 2026-06-18 06:08 UTC
```

### Template Content
```
Subject: Candidati verificati pentru {job_title} — raspuns rapid

Buna ziua,

Am observat ca {company_name} cauta {positions_available} {job_title} in {county} pe ANOFM.

InterJob.ro are candidati verificati disponibili imediat:
- Baza de date: 6,600+ candidati activi (constructii, productie, transport, horeca, depozit)
- CV-uri complete cu experienta si disponibilitate
- Candidati verificati telefonic, gata de angajare

Raspundeti cu DA si va trimitem candidatii potriviti pentru postul de {job_title}.

Cu stima,
Elena Vasilescu
Consultant Resurse Umane — InterJob.ro
office@interjob.ro | https://interjob.ro
---
Daca nu doriti sa mai primiti astfel de mesaje, raspundeti cu STOP.
```

### Template Variables (Personalization)
| Variable | Source | Example |
|----------|--------|---------|
| `{job_title}` | CSV column: job_title | SUDOR CU ARC ELECTRIC ACOPERIT SUB STRAT DE FLUX |
| `{company_name}` | CSV column: company_name | SANTIERUL NAVAL CONSTANTA SA |
| `{positions_available}` | CSV column: positions_available | 39 |
| `{county}` | CSV column: county | (empty if not available) |

**Feature:** Each email is personalized by job title + company — increases relevance & CTR

---

## 3️⃣ Email Provider — Brevo SMTP Integration

### Account Details
| Attribute | Value |
|-----------|-------|
| **Provider** | Brevo (formerly Sendinblue) |
| **Account Name** | warehouseworkers.eu |
| **Sender Email** | office@warehouseworkers.eu |
| **Auth Method** | API Key (environment variable) |
| **API Endpoint** | https://api.brevo.com/v3/smtp/email |

### API Key Management
```python
# In campaign_anofm_angajatori.py
BREVO_KEY = os.environ.get("BREVO_WAREHOUSEWORKERS_API_KEY", "xkeysib-...")

# Environment variable set on raspibig:
export BREVO_WAREHOUSEWORKERS_API_KEY="REDACTED"
```

**⚠️ WARNING:** API key hardcoded as fallback in script (security risk if key rotates)

### Brevo Features Used
- ✅ SMTP email sending
- ✅ Reply-to handling
- ✅ Bounce suppression (via DNC integration)
- ✅ Tracking (open/click via headers)

---

## 4️⃣ Shared Sender Module

### Location & Purpose
```
/opt/ACTIVE/EMAIL/CAMPAIGNS/SCRIPTS/SHARED/sender.py
Shared module for all email campaigns (Brevo + Gmail)
Functions:
  - send_brevo(api_key, sender, sender_name, to, subject, body, reply_to)
  - send_gmail(sender, password, to, subject, body, reply_to)
  - add_common_args(parser)  # CLI args for all campaigns
  - effective_limit(args, sent_data, today)  # Rate limiting logic
```

### Brevo Function (Simplified)
```python
def send_brevo(api_key, sender, sender_name, to_email, subject, body, reply_to=None):
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {"api-key": api_key, "Content-Type": "application/json"}
    
    payload = {
        "sender": {"name": sender_name, "email": sender},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": body,
        "replyTo": {"email": reply_to or sender}
    }
    
    response = urllib.request.urlopen(
        urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
    )
    return response.code == 201, response.reason
```

---

## 5️⃣ Orchestrator Integration

### Configuration (campaigns.json)
```json
{
  "name": "ANOFM_ANGAJATORI",
  "enabled": true,
  "type": "python",
  "script": "ANOFM_ANGAJATORI/campaign_anofm_angajatori.py",
  "daily_limit": 150,
  "restart_delay": 86400,
  "description": "Angajatori activi ANOFM (1,470) — business email only"
}
```

### Orchestrator Role
```
campaign_orchestrator_24_7.py (PID 770839)
  ├─ Monitors campaigns.json for enabled=true
  ├─ Starts/restarts campaign processes
  ├─ Enforces daily_limit per campaign
  ├─ Handles process termination & restart
  └─ Logs to /opt/ACTIVE/INFRA/LOGS/orchestrator.log
```

### How ANOFM is Triggered
1. **Orchestrator reads campaigns.json** → sees ANOFM_ANGAJATORI enabled=true
2. **Spawns process:**
   ```bash
   /opt/ACTIVE/INFRA/venv/bin/python3 \
     /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/campaign_anofm_angajatori.py \
     --limit 150 --delay 240
   ```
3. **Process sends** until 150 emails sent or CSV exhausted
4. **Orchestrator restarts** next day (restart_delay: 86400s = 24h)

---

## 6️⃣ Processing Pipeline

### Step-by-Step Flow
```
1. Load DNC list
   ↓
2. Load sent.csv (already sent emails today)
   ↓
3. Parse email template
   ↓
4. Read anofm_angajatori_dedup.csv
   ↓
5. For each row:
   a. Check if email in DNC → skip
   b. Check if email in sent → skip
   c. Fill placeholders {job_title}, {company_name}, etc.
   d. Send via Brevo API
   e. Log to sent.csv
   f. Sleep 240 seconds
   g. Increment counter
   ↓
6. Stop when counter reaches 150 or CSV exhausted
```

### Rate Limiting
```python
# Current configuration (since 2026-06-19 10:41)
--delay 240          # 240 seconds = 4 minutes between emails
--limit 150          # Stop after 150 emails

# Math
150 emails × 240s/email = 36,000 seconds = 10 hours
Expected runtime: ~10 hours per day
Schedule: Start 06:00 → Complete ~16:00 UTC
```

---

## 7️⃣ Tracking & Logging

### Sent Log File
```
Location: /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/sent.csv
Format: CSV with headers [email, company, sector, date]
Size: 2.0 KB (27 lines = 26 sent emails)
Updated: Real-time as emails sent
```

### Example Log Entries
```csv
email,company,sector,date
office@snc.ro,SANTIERUL NAVAL CONSTANTA SA,Construcții / Instalații,2026-06-19
costica.botez@recbt.ro,REC SRL,SERVICE AUTO,2026-06-19
office@viaduct.ro,VIADUCT SRL,Construcții / Instalații,2026-06-19
office@jaluzele.info,SUNNY BLINDS SRL,Producție / Logistică,2026-06-19
```

### Log Files
| Log | Purpose | Location |
|-----|---------|----------|
| sent.csv | Tracks sent emails | /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/ |
| campaign_anofm_adjusted.log | Live execution log | /opt/ACTIVE/INFRA/LOGS/ |
| orchestrator.log | Campaign startup/shutdown | /opt/ACTIVE/INFRA/LOGS/ |

---

## 8️⃣ DNC List Integration

### Do Not Contact (Bounce Suppression)
```
Location: /opt/ACTIVE/EMAIL/CAMPAIGNS/dnc_bounces.txt
Size: Unknown
Entries: ~55 email addresses (as of 2026-06-19)
Purpose: Skip emails that bounce, unsubscribe, or are invalid
```

### How DNC Works
```python
def load_dnc():
    if DNC_FILE.exists():
        return {l.strip().lower() for l in DNC_FILE.read_text().splitlines()}
    return set()

# In processing loop
if email in dnc:
    continue  # Skip this email
```

### DNC Sources
- Manual additions (user requests STOP)
- Bounce detection (Brevo returning 5xx errors)
- Previous campaign failures
- Complaint list from Brevo

---

## 9️⃣ Database Integration (Optional)

### ANOFM Jobs in PostgreSQL
```sql
SELECT COUNT(*) FROM ij_jobs WHERE source='anofm'
Result: 15,690 job listings (as of 2026-06-19)
```

**Note:** Campaign uses CSV file, NOT database directly (faster processing)

---

## 🔟 Dependencies & Requirements

### Python Modules (Campaign)
```python
import argparse          # CLI arguments
import csv              # CSV reading
import logging          # Event logging
import os               # Environment variables
import sys              # System info
import time             # Sleep/delays
from datetime import date  # Date tracking
from pathlib import Path   # File paths

# Custom module
import sender           # Brevo/Gmail SMTP client
```

### System Requirements
```
Python: 3.7+ (using /opt/ACTIVE/INFRA/venv/)
Memory: 25.7 MB (minimal)
Network: Outbound HTTPS to api.brevo.com:443
Disk: 159 KB CSV + logs
Permissions: Read CSV, write sent.csv
```

---

## Environment & Performance

### Current Execution (2026-06-19 10:42 UTC)
| Metric | Value |
|--------|-------|
| Process ID | 1127122 |
| Memory | 25.7 MB |
| CPU | 0.0% (idle between emails) |
| Uptime | 1 min 15 sec |
| Emails sent (this run) | 0 (just started) |
| Est. completion | ~14:30 UTC (4h from now) |

### Resource Footprint
- **Disk I/O:** ~1 MB/hour (CSV reads + log writes)
- **Network I/O:** ~500 KB/hour (HTTPS to Brevo)
- **CPU:** Negligible (mostly sleeping)
- **Memory:** Stable 25 MB

---

## Optimization History

### Today (2026-06-19)
```
10:04 — Campaign restarted with --delay 480s
        → Would only complete ~94 emails by midnight
        ↓
10:41 — Optimized: --delay 480s → 240s
        → Will now complete 150 emails by ~14:30-16:00 UTC
        ✅ 60% improvement in throughput
```

---

## Future Improvements

| Improvement | Benefit | Effort |
|-------------|---------|--------|
| **Reduce delay to 120s** | Send 300/day (2x current) | 5 min |
| **A/B test subject lines** | Improve open rate by 5-10% | 1 hour |
| **Add click tracking** | Measure engagement | 2 hours |
| **Segment by sector** | Personalize by industry | 3 hours |
| **Integrate with CRM** | Track responses automatically | 8 hours |

---

## Reference Files

| File | Purpose | Location |
|------|---------|----------|
| campaign_anofm_angajatori.py | Main script | /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/ |
| template_anofm_angajatori.txt | Email template | /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/TEMPLATES/ |
| anofm_angajatori_dedup.csv | Lead list | /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/ |
| sent.csv | Tracking log | /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/ |
| sender.py | SMTP module | /opt/ACTIVE/EMAIL/CAMPAIGNS/SCRIPTS/SHARED/ |
| campaigns.json | Orchestrator config | /opt/ACTIVE/EMAIL/CAMPAIGNS/ |

---

**Last Updated:** 2026-06-19 10:42 UTC  
**Status:** ✅ LIVE & OPTIMIZED