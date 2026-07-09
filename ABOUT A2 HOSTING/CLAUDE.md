# ABOUT A2 HOSTING — operating reference

**Reconstructed 2026-06-25 from sourced memory + root CLAUDE.md** (the canonical folder was missing; rebuilt from sourced material only — no fabrication). Single source of truth for *how to operate the A2 shared hosting*. Read before touching any A2 domain. Do NOT duplicate elsewhere.

---

## Role

A2 shared hosting hub: **~34 domains** (job boards, WP news/biz sites, PrestaShop shops) on one cPanel account. **cPanel ONLY — no shell trust.** All file/DNS/quota operations go through the cPanel API (UAPI + legacy API2), never SSH/FTP. Source: root CLAUDE.md infra table + key conventions.

## Account / server

- **cPanel user:** `loaiidil`
- **Server:** `nl1-cl8-ats1.a2hosting.com` (cPanel/WHM port `:2083`)
- **API token:** stored in root CLAUDE.md (verified live) and in `D:\MEMORY\COWORK\A2\a2.py` `.env` — **never copy the literal here** (GitHub-synced file). Earlier MK0W… token is dead; a newer write-capable token exists. Source: root CLAUDE.md, `a2_disk_quota_wedged`.

## Docroot convention

- **`~/domain.tld/`** — NOT `~/public_html/`. The doc-root is named after the domain. Confirmed: `~/factoryjobs.eu/`, `/home/loaiidil/agroevolution.com/`, `/home/loaiidil/expatsinromania.org/`. Source: root CLAUDE.md, `phase3_job_catalog_handoff`, `expatsinromania_audit`.
- **WordPress sites:** WP often lives in a **`/wp` subfolder** with static HTML in the docroot root (e.g. semnalulbuzau: HTML in root, WP at `/home/loaiidil/semnalulbuzau.xyz/wp/`). Source: `semnalulbuzau_project`.

## a2.py CLI (laptop control)

- Location: **`D:\MEMORY\COWORK\A2\a2.py`** (+ `a2.ps1`, `README`, `.env` holding the token).
- Drives cPanel `loaiidil` from the laptop: `ls / cat / upload / download / mkdir / mv / rm [--permanent] / domains / docroot / quota / raw`.
- `fileop` + `mkdir` use **legacy API2** (not UAPI).
- **Git Bash:** set `MSYS_NO_PATHCONV=1` (else paths get mangled).
- Source: `a2_cli_inode_cleanup`.

## Quota: INODES, not disk (HARD)

- `megabyte_limit = 0` → **disk is effectively unlimited; the only real cap is INODES (~600,000).**
- When wedged (`inodes_used ≥ inode_limit`, `under_quota_overall = 0`) the web process **cannot create any file/dir** — even moving to `~/.trash` fails (trash needs a lock file).
- **`fileop op=unlink` (API2 Fileman) = permanent delete bypassing trash** — works even when quota is full, recursive on files AND dirs. This is the ONLY way to free a fully-wedged account via API. (`op=rmdir`/`op=delete`/`emptytrash` don't exist.)
- Biggest inode hog = **mail Maildirs (~37 domains)** — do NOT touch (real business email). Safe to unlink: old backups (`site_backups_*`, `softaculous_backups/`, home tarballs), `lscache/`, PrestaShop `var/cache/*/smarty/cache/` — **never the compile dir** (see below).
- Existing cleanup cron on raspibig: `0 4 */3 * *` → `/opt/ACTIVE/INFRA/a2_cleanup.py --apply` (smarty cache + lscache + old backups + tmp sessions; does NOT cover Symfony `var/cache/prod/admin`, the recurring ~7k-inode source).
- Upload quirk: file must NOT pre-exist (rename original to `.bak` first; `overwrite=1` is ignored).
- Source: `a2_disk_quota_wedged`, `a2_cli_inode_cleanup`.

## PrestaShop gotchas (cause HTTP 500)

Applies to **hyperbndf.com, agroevolution.com**, any PrestaShop on A2. Skill: `prestashop-posthog-a2`.

- **NEVER delete/rename `var/cache/*/smarty/compile/`** — the web process will not recreate it → **instant 500 every time** (perms/ownership, not just quota). Restore by renaming the dir back.
- Inode quota full → cache clear can't recompile templates → 500. Keep inodes free first.
- Editing a `.tpl`: wrap any raw JS/braces in **`{literal}…{/literal}`** (Smarty parses `{}`).
- Override the **REAL parent block** (e.g. `javascript_head`), not dead/absent blocks (`head_extra`, `head_fonts` don't exist in the classic parent theme).
- Prod has `compile_check` off → to push a template change, **clear cache via PrestaShop Admin → Advanced Parameters → Performance → Clear cache** (runs as web process). Do NOT brute-force-delete the compile dir via API.
- Source: `a2_disk_quota_wedged`, `prestashop-posthog-a2` skill.

## DNS / Brevo (email auth)

- Skill **`brevo-dns-a2`** adds Brevo auth records (brevo-code TXT, DKIM1/DKIM2 CNAME, DMARC TXT) to any `loaiidil` domain via cPanel API2 **ZoneEdit** (`edit_zone_record`) — no SSH/FTP. Confirmed working (e.g. `_dmarc.seicarescu.com` edited via API2 ZoneEdit). Source: `brevo-dns-a2` skill, `seicarescu_dmarc_onesafe_scam`.
- **API limitation (UAPI `DNS/*`):** read (`parse_zone`), `mass_edit_zone remove`, and `edit` work; **`add` does NOT** (`add_zone_record` / `addzonerecord` not found; `ZoneEdit/add_zone_record` module not installed). Net: edit/remove via API, but **adding a brand-new record = manual via cPanel UI Zone Editor**, OR via API2 ZoneEdit per the skill.
- Always use the current SOA serial when calling `mass_edit_zone`; serial increments after each change (re-fetch).
- One `_dmarc` record per domain (RFC 7489) — Brevo errors on duplicates; delete the old one first.
- Source: `cpanel_dns_dmarc`.

## SECURITY — claude-api backdoor (HARD)

- A prior session deployed a `claude-api` WordPress plugin that is a **CRITICAL RCE backdoor** (`?claude_api=run_php` → `eval()`, arbitrary file r/w/delete, hardcoded key). It self-re-armed from leftover deploy scripts across ~18 sites.
- **NEVER (re)deploy `claude-api`**; never run `wp_claude_api.py` / `oipa_deploy.py` / `deploy_all.py`. Deploy toolkit was quarantined out of `/opt/ACTIVE/SKILLS`.
- For SSH-less WordPress/file ops on A2 use the **cPanel Fileman API** (`execute/Fileman/*` + API2 `fileop`) — proven.
- Open flag: a 2nd exposed cPanel token sits in `deploy_all.py` (not rotated per standing rule — user's call).
- Full report: `WEB/SECURITY_claude_api_backdoor_2026_06_11.md`. Source: `claude_api_backdoor_incident`.

## What NOT to do

1. **No SSH/FTP deploy from the laptop** (incl. BDA / job-site deploys) — cPanel API ONLY.
2. **Never delete the PrestaShop `smarty/compile` dir** (instant 500).
3. **Never unlink mail Maildirs** to free inodes (real business email).
4. **Never redeploy `claude-api`** or its deploy scripts.
5. **Never put the cPanel token literal in this file** (GitHub-synced).

## Cross-references

- Deploy/security patterns + per-domain audits: `WEB/`, `D:\MEMORY\COWORK\A2\`.
- Memory topics: `a2_cli_inode_cleanup`, `a2_disk_quota_wedged_hyperbndf_posthog`, `claude_api_backdoor_incident`, `cpanel_dns_dmarc`, `a2_hosting_audit_2026_05_28`, `prestashop-posthog-a2`, `brevo-dns-a2`.

---

## Gaps / unknowns (not in sourced material)

- **Exact current domain count** — root CLAUDE.md says "34 domains"; the 2026-05-28 audit counted 14 active. Treat 34 as the account total, ~14 as live-audited. Reconcile via `python a2.py domains`.
- **Live SSL status** — 2026-05-28 audit flagged 12/14 certs expiring; current state unverified (re-check before relying on it).
- **Full per-domain list** — see `ABOUT BUSINESSES` / `a2_hosting_audit_2026_05_28` / `a2.py domains`; not reproduced here.
