# ANOFM Pipeline Verification — 2026-06-22

**Session:** ~05:20 UTC | **Scope:** Verify handoff claims (06-18 + 06-21) before action
**Method:** SSH both machines (key auth works for raspibig 192.168.100.21 + raspi 192.168.100.20)

---

## ✅ Healthy — live now (raspibig production)

| Component | Status | Evidence |
|-----------|--------|----------|
| `campaign-orchestrator.service` | active, 0 restarts | up since Sun 06-21 09:19 EEST, MainPID 3421 |
| ANOFM_ANGAJATORI sends | sending today | `sent.csv` 388 lines, last 3 dated **2026-06-22** (DRAKUPLAST, DCA, RECON SA) |
| `anofm-daily-report.timer` | ran today | last activation Mon 06-22 04:00 EEST |
| BDA_ARHITECTI campaign | exit 0 | healthy loop in orchestrator log |

---

## ⚠️ Issues found (NOT in prior handoffs)

### Issue A — `PRODUCATORI_VIAPROFI_SEGMENTED` crash loop (NEW)
- **Symptom:** orchestrator log shows `Done (exit 126)` → `Restart in 300s`, repeating all morning (08:09, 08:14, ...).
- **exit 126** = permission/exec error (script not executable or interpreter missing).
- **Impact:** log spam every 5 min; no emails sent for this campaign.
- **Not mentioned** in HANDOFF_2026_06_18 — added to stack after that session.

### Issue B — raspi ANOFM NOT actually autonomous (06-21 handoff overstated)
The 06-21 handoff claims "95% ready, timers disabled, ready to activate". Reality:
- `anofm-scraper.timer` = **active** but **did not fire today** (last run 06-21 09:17, manual). No 06-22 CSV in `/opt/ACTIVE/ANOFM_DATA/csv/`.
- `anofm-ingest.timer` = **inactive**.
- `anofm-audience-rebuild.timer` = **inactive**.
- `anofm_db` frozen at **16,429** rows (06-21 sync) — not growing.
- `sent.csv` stopped at **2026-06-20** (246 lines) — raspi hasn't sent since.
- **Conclusion:** pipeline is **stalled**, not "paused-and-ready". Day-1 activation checklist never completed.

### Issue C — `ij_jobs` frozen 3 days (raspibig) — benign
- Latest ingest row `created_at` = **2026-06-19 16:30:20**.
- Cause = Mon-Fri schedule + weekend (not a bug).
- Next ingest timer fires ~09:00 EEST today. 13,137 active rows currently.
- **Action:** re-check after 09:00 to confirm ingest resumes.

---

## ⏸ Leftovers from HANDOFF_2026_06_18 (Pending section)

1. **Dup service file** `/etc/systemd/system/interjob-campaigns.service` — inactive + disabled, **still on disk**. Safe to `rm` + `daemon-reload`.
2. **`romania_send_log.company_name` column missing** — blocks NECALIFICATI logging.
3. **NECALIFICATI disabled** — needs valid `BREVO_CAREWORKERS_API_KEY` (HTTP 401 on old key).

---

## Recommended next sequence (agreed, not started)

1. ✅ Verify (this report)
2. **Kill `PRODUCATORI_VIAPROFI_SEGMENTED` loop** — fix exit 126, ~3 min. Highest value: stops ongoing log spam.
3. **Activate + truly fix raspi ANOFM** — debug why scraper timer didn't fire + enable ingest timer + fix ingest schema mismatch (06-21 Known Issue #1). The actual 06-21 objective.
4. **Clear 3 raspibig leftovers** (dup file rm, `company_name` ALTER, source new careworkers key).

*Skipped:* ANOFM delay 240s→120s (hold until bounce data available).

---

## Repro / quick-check commands

```bash
# raspibig
ssh tudor@192.168.100.21
systemctl is-active campaign-orchestrator.service   # active
systemctl is-enabled interjob-campaigns.service     # disabled (file still exists)
tail -20 /opt/ACTIVE/INFRA/LOGS/campaigns/orchestrator_$(date +%Y%m%d).log
PGPASSWORD=tudor psql -h 127.0.0.1 -U tudor -d interjob_master -t -c \
  "SELECT MAX(created_at) FROM ij_jobs WHERE source='anofm';"
tail -3 /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/sent.csv

# raspi
ssh tudor@192.168.100.20
systemctl is-active anofm-scraper.timer anofm-ingest.timer anofm-audience-rebuild.timer
sudo -u postgres psql anofm_db -t -c "SELECT COUNT(*) FROM ij_jobs WHERE source='anofm';"
ls -lat /opt/ACTIVE/ANOFM_DATA/csv/ | head -5
wc -l /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA/sent.csv
```

---

**Status:** Verification complete. Findings saved. No changes applied — awaiting decision on items 2/3/4.
**Next session pickup:** start at "Recommended next sequence" item 2.
