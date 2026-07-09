# CLAUDE.md — Email Classifier

**v1.1 | 2026-06-15 | manpowerdristor@gmail.com candidate filter — FIXED**

---

## Goal

Keep candidate/application emails out of `manpowerdristor@gmail.com` inbox permanently.

**Status: ✅ WORKING.** 0 applications in inbox as of 2026-06-24 17:17 UTC. Hourly **systemd timer** active (was cron — evicted by campaign deploys, see Schedule section).

---

## Architecture (on raspibig)

```
/opt/ACTIVE/EMAIL/PROCESSORS/
  collect/email_collector.py     # IMAP pull all 34 accounts → raw_emails.jsonl
  organize/auto_organize.py      # classify + move via IMAP  ← PATCHED 2026-06-15
  rule_labeler.py                # regex classifier → labels.db
  data/models/email_classifier.pkl  # sklearn TF-IDF+LR, 94.5% accuracy, Apr 2026
  data/training_data/labels.db   # SQLite: email → intent (13K+ labeled)
```

**Classification flow:**
1. Look up email in `labels.db` (fast, from 6am collection run)
2. **[NEW - inline fallback]** If not in DB → run pkl model directly (≥0.65 confidence)
3. Move to correct Gmail folder

**Intent → Gmail folder mapping:**
| Intent | Folder |
|--------|--------|
| application | APPLICATIONS_RECEIVED |
| newsletter | NEWSLETTERS |
| bounce | BOUNCES |
| auto_reply | AUTOREPLY |
| spam | SPAM |
| unsubscribe | UNSUBSCRIBES |

---

## Schedule — systemd timers (NOT cron) — 2026-06-24

**Moved off cron.** Campaign deploy scripts repeatedly rewrite tudor's crontab (`crontab -` REPLACE) and silently drop unrelated lines — the classifier crons were evicted and the inbox piled up undetected for 6 days (2026-06-18 → 06-24). systemd timers survive crontab rewrites.

```bash
# Status
systemctl list-timers email-organize.timer email-pipeline.timer

# email-organize.timer   → hourly  → organize manpowerdristor inbox (inline pkl)
# email-pipeline.timer   → 06:00   → collect (34 accts) → label → organize
# Both: Persistent=true (catch-up after downtime). Units in /etc/systemd/system/

# Run a pass now
sudo systemctl start email-organize.service

# Logs unchanged: /opt/ACTIVE/INFRA/LOGS/email_organize.log
```

**Do NOT re-add these to crontab** — duplicate runs + the same eviction problem returns.

---

## What was fixed (2026-06-15)

**Problem:** `auto_organize.py` only moved emails already in `labels.db`. New emails arriving after the 6am collection run sat in inbox until next day.

**Fix applied to `/opt/ACTIVE/EMAIL/PROCESSORS/organize/auto_organize.py`:**
- Added `classify_inline()` function that loads the pkl model and classifies in-process
- After labels.db lookup fails → runs inline pkl classification (confidence ≥ 0.65)
- Backup: `auto_organize.py.bak_20260615_164432`

---

## Credentials

```
Account:  manpowerdristor@gmail.com
Env var:  GMAIL_MANPOWERDRISTOR_APP_PASSWORD  (in /opt/ACTIVE/EMAIL/.env)
Raw:      xibc xpuz qxfm caei
```

---

## Run manually

```bash
# Dry run — preview what would move
cd /opt/ACTIVE/EMAIL/PROCESSORS
python3 organize/auto_organize.py --account manpowerdristor@gmail.com --dry-run

# Live run — move now
python3 organize/auto_organize.py --account manpowerdristor@gmail.com

# Check log
tail -20 /opt/ACTIVE/INFRA/LOGS/email_organize.log
```

---

## Verify it's working

```bash
# Should show applications: 0 in dry-run
python3 organize/auto_organize.py --account manpowerdristor@gmail.com --dry-run

# See last 10 hourly runs
grep "Done:" /opt/ACTIVE/INFRA/LOGS/email_organize.log | tail -10
```

---

## Services (inactive — cron is sufficient)

```
email-classifier.service   inactive  (API on :5080, not needed)
email-collector.service    inactive  (replaced by 6am cron)
```

Do NOT restart these unless debugging.

---

## What NOT to do

- Do NOT rebuild the classifier — 94.5% accuracy is good enough
- Do NOT run the full email_collector.py on every hourly cron (scans 34 accounts, too slow)
- Do NOT change pkl model path: `data/models/email_classifier.pkl`
- Do NOT lower confidence threshold below 0.65 (false positives)

---

## Harness

**Added 2026-06-24.** Automation harness for IMAP inbox classification (sklearn TF-IDF+LR 94.5%, raspibig hourly cron).

**Trigger skill:** `email-classifier-orchestrator` (auto-applies in this folder; triggers: "run the email classifier", "move candidates out of the inbox", "why are applications in the inbox", "check classifier model health", "run the bounce digest").

**Agents (`.claude/agents/`):**
| Agent | Role |
|-------|------|
| email-classifier-orchestrator | Supervises the full cycle; delegates to specialists |
| email-classifier-imap-collector | Multi-account IMAP pull (34 accounts) → raw_emails.jsonl |
| email-classifier-labeler | rule_labeler.py (regex→labels.db) + inline pkl fallback + IMAP moves |
| email-classifier-model-health | pkl load check, outcome (inbox apps=0), confidence/accuracy drift, bounce digest |

**Reused (referenced, not redefined):** `bounce-monitor`, `dnc-manager` — drive bounce/DNC via `enhanced_bounce_processor.py`.

**Daily / trigger cycle:**
| Time (UTC) | Component | Agent | Output |
|-----------|-----------|-------|--------|
| 06:00 | Collect → label → organize | imap-collector → labeler | raw_emails.jsonl, labels.db, mail moved |
| Hourly | Organize manpowerdristor inbox | labeler | new mail moved (inline pkl, conf ≥ 0.65) |
| After organize | Outcome verify | model-health | inbox applications == 0, drift flag |
| Daily | Bounce digest + DNC | model-health + bounce-monitor + dnc-manager | digest → fruitnature4@gmail.com, DNC updated |

**Rules:** raspibig only via plink SSH; never rebuild model / change pkl path / lower 0.65 threshold; never run 34-account collect hourly; quote paths with spaces.

---

## Harness (2nd, co-located): Email Hygiene + Form Routing

**Added 2026-06-26.** Distinct from the classifier above; files physically live in this folder. (Pointer previously only in parent `PLAN 01 06 2026/CLAUDE.md` backlog #5 — added here 2026-06-28 to fix discoverability drift.)

**Trigger skill:** `email-hygiene-orchestrator` (triggers: "clean the inboxes", "purge CV emails", "free mailbox quota", "process form submissions", "route site leads", "run email hygiene", "drain the form inbox").

**Agents (`.claude/agents/`):** `inbox-purger` (gently purge CV-attachment emails across A2/Gmail/Yahoo, save attachments first, A2-rate-friendly chunks), `form-router` (classify web3forms submissions worker vs employer → fw_candidates / form_employer_leads).

**Wraps:** `cv_purge.py` + `form_router.py`. Default dry-run; live only on explicit instruction.

**변경 이력:**
| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-06-28 | Email Hygiene 하네스 포인터 추가 | CLAUDE.md | inbox-purger/form-router가 이 폴더에 있으나 로컬 문서에 미기재(drift) |
