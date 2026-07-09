# RASPI INSPECT — Romania Hub Health Harness

**v1.0 | 2026-06-26**

## Harness: raspi (192.168.100.20) Romania Inspection

**Goal:** Repeatable read-only audit of the Romania ops hub. raspi runs **all Romania work + all ANOFM email sending** — never raspibig (.21) or laptop. (Hard rule; see [[anofm-host-map]].)

**Trigger:** `raspi-romania-inspect` skill / `raspi-inspector` agent — "inspect raspi", "check Romania pipeline", "audit raspi crons", "is ANOFM sending healthy".

**Runner:** `inspect_raspi.py` (laptop → plink → .20). Read-only; exit 1 on findings.

| Component | File |
|-----------|------|
| Inspector script | `inspect_raspi.py` |
| Skill | `.claude/skills/raspi-romania-inspect/SKILL.md` |
| Agent | `.claude/agents/raspi-inspector.md` |

## Checks
1. Crontab — duplicates (double-run) + malformed `HH:MM` schedules (never run).
2. ANOFM pipeline — ij_jobs / send_log / dnc + last sends.
3. Failed systemd units + /tmp pressure.
4. ANOFM malformed-email rejections (today's HTTP_400 `not valid in to`) + parked count.

## Change history
| Date | Change | Reason |
|------|--------|--------|
| 2026-06-26 | Harness created; crontab deduped (24 dup lines removed) | Audit found duplicate EU-scraper block + 15 malformed schedules + chkrootkit flap |
| 2026-07-02 | Pre-send email validator added: raspi orchestrator `pick_email` skips malformed + parks; raspibig shared `sender.py` now calls `is_valid_email()` before Brevo/Gmail send | Audit found HTTP_400 `email is not valid in to` from 45 distinct malformed source addresses; sender never format-checked recipients |
| 2026-07-02 | Inspector hardened: added ANOFM_REJECTS_TODAY + ANOFM_PARKED_LAST probes (check #4) | Harness must auto-catch what the manual audit found |
| 2026-07-02 | Lead recovery: `repair_email()` added to `pick_email` — repair-then-validate before parking. Recovers 26/45 distinct malformed (free-provider TLD completion + whitespace-around-@); drops 19 unsafe (fragmented local part, corp no-TLD). Deployed + compile-verified on raspi | Validator was parking repairable real leads; durable in-`pick_email` (survives daily `build_scrape_db.py` rebuild) |

## Open items
- ~~15 EU-wholesale scrapers on malformed `HH:MM` schedules~~ **RESOLVED 2026-07-02**: raspi crontab clean (16 active lines, 0 malformed/dup).
- chkrootkit.service flaps to failed on /tmp churn — benign (manual scan clean).
- ~~Lead recovery (gated)~~ **RESOLVED 2026-07-02**: `repair_email()` in `pick_email` recovers 26/45 malformed safely (0 bad repairs verified via dry-run). The 19 dropped are junk (`0@0`), corp domains with unguessable TLD (`office@agrinvest`), or fragmented local parts (`bkt _forest@`) — intentionally not guessed.
