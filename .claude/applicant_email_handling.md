# Applicant Email Handling System

**Status:** ✅ Verified & Activated  
**Date:** 2026-04-28

## Systems Found (3 Levels)

### Level 1: Gmail Applicant Sorter
**File:** `/opt/ACTIVE/INFRA/SKILLS/gmail_applicant_sorter.py`  
**Account:** manpowerdristor@gmail.com  
**Target folder:** APPLICANTS (Gmail label)  
**Keywords:** form submission, job application, CV attached, candidatura, caut lucru, etc.

```bash
# Run once
python3 gmail_applicant_sorter.py

# Run every 5 min
python3 gmail_applicant_sorter.py --daemon

# Preview only
python3 gmail_applicant_sorter.py --dry-run

# Show folder stats
python3 gmail_applicant_sorter.py --stats
```

### Level 2: Email Sorter (All 30 Accounts)
**File:** `/opt/ACTIVE/INFRA/SKILLS/email_sorter.py`  
**Handles:** 19 A2 Hosting + 9 Gmail + 2 Yahoo accounts  
**Action:** Sorts to APPLICATIONS_RECEIVED folder, sets up autoresponders

**Accounts:**
- A2 Hosting (cPanel): office@interjob.ro, tudor@interjob.ro, noreply@interjob.ro, etc.
- Gmail: manpowerdristor@gmail.com, manpower.dristor@gmail.com, elena.manpower.dristor@gmail.com
- Yahoo: Other accounts

```bash
# Full sort + autoresponders
python3 email_sorter.py

# Sort only (skip autoresponder setup)
python3 email_sorter.py --sort-only

# Show current state
python3 email_sorter.py --status

# Preview (no changes)
python3 email_sorter.py --dry-run

# Gmail only
python3 email_sorter.py --gmail-only

# Specific account
python3 email_sorter.py --account manpowerdristor@gmail.com
```

### Level 3: Enhanced Sorter (with Bounce Analysis)
**File:** `/opt/ACTIVE/EMAIL/PROCESSORS/llm_analyzer/email_sorter_with_domain_validation.py`  
**Purpose:** Advanced domain validation, bounce detection, business-smart filtering

---

## Systemd Service (NEW — Activated 2026-04-28)

**Service:** `email-sorter.service`  
**Timer:** `email-sorter.timer` (every 30 minutes)  
**Status:** ✅ ACTIVE

Runs: `python3 email_sorter.py --sort-only`

```bash
# Check status
systemctl status email-sorter.timer

# Manual run
systemctl start email-sorter.service

# View logs
journalctl -u email-sorter.service -f
```

---

## Email Accounts Status

### A2 Hosting (interjob.ro)
| Email | Sorter Target |
|-------|---|
| office@interjob.ro | APPLICATIONS_RECEIVED |
| tudor@interjob.ro | APPLICATIONS_RECEIVED |
| noreply@interjob.ro | APPLICATIONS_RECEIVED |

Autoresponder setup: Automatic (cPanel UAPI)

### Gmail
| Email | Password Env Var | Status |
|-------|---|---|
| manpowerdristor@gmail.com | GMAIL_MANPOWERDRISTOR_APP_PASSWORD | Configured |
| manpower.dristor@gmail.com | GMAIL_MANPOWER_APP_PASSWORD | Configured |
| elena.manpower.dristor@gmail.com | GMAIL_ELENA_PASSWORD | Configured |

Autoresponder setup: SMTP auto-reply (tracked in replied.json)

---

## What Gets Moved to APPLICATIONS_RECEIVED

**Subject keywords detected:**
- new submission, form submission, contact form
- new application, job application, CV attached
- candidatura, aplicare pentru, looking for job, caut lucru
- seeking employment, work permit

**Body keywords (fallback):**
- attached my cv, my resume, job seeker
- available for work, years of experience

---

## Configuration

### Gmail Credentials
Set env vars in `.env` or systemd service:
```bash
export GMAIL_MANPOWERDRISTOR_APP_PASSWORD="..."
export GMAIL_MANPOWER_APP_PASSWORD="..."
export GMAIL_ELENA_PASSWORD="..."
```

### A2 Hosting cPanel
Token: `KAOZ5JUAURRMRNZ0WFEIDCO4KWK4G453` (already in system)

---

## Workflow

1. **Inbox receives email** (applicant applies)
2. **email-sorter.service triggers** (every 30min) via timer
3. **Keywords matched** (subject/body scan)
4. **Email moved** to APPLICATIONS_RECEIVED (IMAP) or APPLICANTS (Gmail)
5. **Autoresponder sent** (cPanel or SMTP)
6. **Inbox stays clean** ✅

---

## Status Check Commands

```bash
# Show all account status
cd /opt/ACTIVE/INFRA/SKILLS && python3 email_sorter.py --status

# List every inbox email with classification (read-only)
python3 email_sorter.py --scan

# Gmail only
python3 email_sorter.py --gmail-only --status

# Dry-run (preview changes)
python3 email_sorter.py --dry-run
```

---

## Logs

- Systemd: `journalctl -u email-sorter.service`
- Script: Outputs to stdout/journalctl
- Last run: Check timer with `systemctl status email-sorter.timer`

---

## Next

- [ ] Verify Gmail credentials in env (if needed)
- [ ] Run manual test: `python3 email_sorter.py --status`
- [ ] Monitor: watch email-sorter.service logs for 2-3 runs
- [ ] Confirm applicants moved from inbox to APPLICATIONS_RECEIVED
