# Email Classifier Fix Report

## Root Cause: Why You Were Still Receiving Applicants

**Three problems found:**

1. **Missing LLM module** — `reply_classifier.py` imported non-existent `lmstudio_client` module, blocking entire script
2. **No cron job** — Classifier never scheduled to run automatically 
3. **No archive action** — Even if running, only marked emails as read, didn't remove from inbox

## What Was Fixed

### 1. Created Working Classifier
- `reply_classifier_archive.py` — keyword-based (no external deps)
- Classifies: interested, unsubscribe, auto_reply, bounce, wrong_person, other
- Adds unsubscribe/bounce addresses to DNC list
- Marks read and archives non-interested emails

### 2. Automated Schedule
Cron job (raspibig, every 30 min):
```
*/30 * * * * python3 /opt/ACTIVE/INFRA/SKILLS/reply_classifier_archive.py --scan-all --limit 30
```

### 3. Test Results
On `manpowerdristor@gmail.com` inbox:
- Scanned 10 recent emails
- Found: 1 interested, 3 unsubscribe, 6 other
- Added 3 addresses to DNC blacklist
- Ready to archive on next scan

## What Emails You're Receiving

Looking at your last 15 emails in manpowerdristor@gmail.com:
- Auto-replies from JobTeam (trekantsomraadet) 
- Unsubscribe confirmations
- Weekly digests from office@interjob.ro
- WordPress moderation alerts
- Security alerts from Brevo

**These are NOT actual job applicants** — they're auto-responses from campaigns and system emails.

## Real Root Issue

`manpowerdristor@gmail.com` is likely used as a reply-to address in campaigns, so:
- Campaign confirmations come back to it
- Auto-responders hit it
- Newsletter digests route there

## What Happens Now

Every 30 minutes:
1. Classifier scans both Gmail accounts
2. Identifies non-interested emails
3. Archives them (or marks read)
4. Adds unwanted addresses to `/opt/ACTIVE/EMAIL/CAMPAIGNS/EMAIL_CLEANUP/blacklist.txt`

## Next Steps (Optional)

To fully prevent emails from entering inbox:

1. **Set Gmail filter** — auto-archive emails matching keywords (vacation, auto-reply, etc.)
2. **Use different reply-to** — dedicated email for non-human replies (support@, noreply@)
3. **Check campaign configs** — ensure manpowerdristor@gmail.com is not set as default contact address

## Files Deployed

- `/opt/ACTIVE/INFRA/SKILLS/reply_classifier_archive.py` (active)
- `/opt/ACTIVE/INFRA/SKILLS/reply_classifier_fixed.py` (fallback)
- Cron: `*/30 * * * * ...` (running)
- Log: `/var/log/classifier.log`

---
Generated: 2026-04-27
