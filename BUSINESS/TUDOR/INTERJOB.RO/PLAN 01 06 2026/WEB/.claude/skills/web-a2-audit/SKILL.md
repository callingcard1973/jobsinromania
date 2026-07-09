---
name: web-a2-audit
description: Read-only audit of A2 Hosting (loaiidil) domains — resolve each domain's REAL docroot, classify it (WP / static / PrestaShop), and scan wp-content/{mu-plugins,plugins} for backdoors or suspicious non-standard slugs. Use when asked to "audit the domains", "check for backdoors", "what's deployed on A2", "scan for malware", "list real docroots", or before/after a deploy. Changes nothing. Used by the web-monitor agent.
---

# web-a2-audit

Inspect the 34-domain `loaiidil` A2 account safely. Reuses `cpanel_full_audit.py` (cPanel UAPI over HTTPS, `verify=False`, read-only). Deletes and changes NOTHING — it reports, a human decides remediation.

## What it does
1. `DomainInfo/domains_data` → real docroot per domain (main + addon + sub + parked). Never assume `public_html`; A2 docroots are `~/{domain}/`.
2. For each docroot, `Fileman/list_files` on `wp-content/mu-plugins` and `wp-content/plugins`.
3. Flag any plugin slug not matching the normal pattern `^[a-z0-9][a-z0-9._-]*$`, plus recently-modified files (mtime) — the claude-api backdoor pattern documented in `WEB/SECURITY_claude_api_backdoor_2026_06_11.md`.
4. Emit a per-domain report: type, docroot, suspicious paths + mtimes.

## Why read-only and separate from cleanup
Backdoor removal is destructive and irreversible. Auditing must be safe to run anytime (weekly, post-deploy) without risk. Remediation is a deliberate, reviewed second step (`remediate_backup.py` → `remediate_delete.py`, archive-before-delete) — never fold it into the audit.

## When to run
- Weekly scheduled sweep (drift + reinfection detection).
- After any deploy (confirm nothing unexpected landed).
- On suspicion (odd traffic, defacement, mail-spam reports).

## Failure modes
- cPanel token rotated/expired → audit can't run; report the auth failure, do not silently report "clean".
- Account at 100% disk quota can break Fileman endpoints — note it; pair with the a2-disk-cleanup skill before retrying.
