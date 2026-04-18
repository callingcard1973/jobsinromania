# ULTRAPLAN — Execution Status (2026-04-10 15:00)
# READ THIS FIRST. This is the single source of truth. Don't re-explore.

## YOUR MISSION: Fix email sorting once and for all

The email pipeline has 3 overlapping systems. Consolidate into ONE that:
1. Scans all 55 IMAP accounts (every 15min via cron)
2. Classifies: ORDER, APPLICANT, BOUNCE, PARTNER, INQUIRY, SPAM, SKIP
3. Routes to: orders.csv, applicants.csv, contacts.csv, bounces.log
4. If one email is broken (encoding, parse error) → SKIP IT and continue
5. Uses sklearn first, escalates low-confidence to Qwen (Ollama localhost:11434, model qwen2.5:1.5b)
6. Max 250 lines per script

## Current Systems (OVERLAPPING — consolidate)

### 1. email_pipeline.py (cron every 2h)
- Location: /opt/ACTIVE/EMAIL/ORDERS/email_pipeline.py (249 lines)
- What: Scans ALL IMAP folders (INBOX + spam + custom) across 14 A2 + 13 Gmail + 2 Yahoo + 2 Zoho accounts
- Classifies via sklearn + optional LLM
- Outputs: orders.csv, applicants.csv, contacts.csv, bounces.log, handovers.csv
- Config: email_accounts.py (ACCOUNTS list, SKIP patterns, APPLICANT patterns, BOUNCE patterns)
- State: pipeline_state.json (processed message IDs)
- TODAY: 1,778 applicants + 140 bounces classified. 0 contacts/orders.

### 2. email_poller.py (cron every 15min)
- Location: /opt/AUTOMATE/email_poller.py (236 lines)
- What: Polls same 55 accounts, queues emails to PostgreSQL task_queue
- State: email_poller_state.json (seen_ids)
- Loads accounts from: governor creds JSON + a2_smtp_credentials.json

### 3. queue_worker.py + email_proposer.py
- Location: /opt/AUTOMATE/queue_worker.py + email_proposer.py
- What: Picks tasks from task_queue, runs sklearn→Qwen cascade (6-tier)
- Just fixed: was using Bonsai (773MB, timing out), now uses Qwen via Ollama
- 213 emails requeued and processing

### Problem: They duplicate work, use different state files, different account lists, different classification logic.

## FIXES ALREADY DONE TODAY (don't redo)

- Telegram order forwarding: FIXED (Markdown→HTML in forward_orders_approval.py)
- 8 IMAP accounts: FIXED (wrong passwords in governor creds + a2_smtp_credentials.json)
- CPU alert spam: FIXED (governor.py threshold 16→32)
- Unified .env: CREATED at /opt/ACTIVE/EMAIL/.env.unified
- Bonsai killed, Qwen via Ollama active (localhost:11434, model qwen2.5:1.5b)
- unknown-8bit codec registered in both pipeline and poller
- Per-email try/except added to pipeline (skips broken emails, continues)
- Both scripts trimmed to <=250 lines

## COMPLETED ULTRAPLAN DEMANDS

### D6: Scale Campaigns — DONE
- Norway: fixed dbname→interjob_master, table→norway_campaign (153K unsent, 16 sectors enabled)
- Denmark: same fix (7.5K unsent, 9 sectors enabled)
- 11 TED construction countries: all sectors enabled (51K contacts)
- 9 Romania corporate sectors: enabled
- Orchestrator restarted, cycling every 5min, ~3,600/day realistic throughput

### D2: Agencies Campaign — STAGED
- CSV: /opt/ACTIVE/EMAIL/CAMPAIGNS/DATA/recruitment_agencies_campaign.csv (18,133 agencies)
- Config: /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/recruitment_agencies.json
- Template: /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/templates/agencies/template1.txt
- BLOCKER: Tudor must approve template

### D5: TED Data Packages — EXPORTED
- 172 country CSVs: /opt/ACTIVE/SELL/DATA/ted_winners_by_country/ (370,690 unique emails)
- BLOCKER: Tudor must create Gumroad account

### D1: 15 Business Leads — UNBLOCKED
- All visible in Telegram @raspi_n8n_alerts_bot
- BLOCKER: Tudor must tap APROBA

## KEY FILES

- Accounts config: /opt/ACTIVE/EMAIL/ORDERS/email_accounts.py
- Pipeline: /opt/ACTIVE/EMAIL/ORDERS/email_pipeline.py
- Poller: /opt/AUTOMATE/email_poller.py
- Worker: /opt/AUTOMATE/queue_worker.py
- Proposer (classifier): /opt/AUTOMATE/email_proposer.py
- Pipeline state: /opt/ACTIVE/EMAIL/ORDERS/pipeline_state.json
- Poller state: /opt/AUTOMATE/email_poller_state.json
- Unified credentials: /opt/ACTIVE/EMAIL/.env.unified
- A2 creds: /opt/ACTIVE/EMAIL/CAMPAIGNS/a2_smtp_credentials.json
- Governor creds: /opt/ACTIVE/INFRA/GOVERNOR/tasks/email_credentials.json

## RULES

- Max 250 lines per script. No exceptions.
- If an email is broken (encoding, parse, timeout) → skip it, log it, move on. Never block.
- One sender per campaign. Brevo for corporate, Gmail for personal.
- Never send email without Tudor's approval. Draft, show, wait.
- Don't write code unless asked. Research and report first.
- Save to disk after every step. Don't accumulate in memory.
- SSH: always 192.168.100.21, single quotes around commands from Windows.

## DATABASE REFERENCE

- interjob_master.companies: 208M rows, 440K with email
- interjob_master.master_romania_companies: 8.9M, 145K with email
- interjob_master.ted_winners: 1.57M, 370K unique emails
- interjob_master.agencies: 148K, 18K unique valid emails
- interjob_master.no_companies_full: 1.15M, 324K with email
- european_funds.proiecte: 15,969, 15,932 with email
- european_funds.beneficiari_privati: 27,501, 9,227 with email
- opendata.faliment: 222,660 insolvency records
- Ollama: localhost:11434, model qwen2.5:1.5b
- PostgreSQL: localhost, user tudor, password tudor
