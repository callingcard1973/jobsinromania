---
name: a2-hosting-context
description: 'Load A2 Hosting (cPanel loaiidil, ~34 domains) operating context before any web deploy or domain work — cPanel-ONLY (no trusted shell), docroot pattern ~/domain.tld/ + /wp, the a2.py CLI, the inode-not-disk quota cap, PrestaShop HTTP-500 gotchas, and the claude-api backdoor security rule. Use when deploying HTML/PHP/WordPress to A2, editing a domain on loaiidil, fixing PrestaShop/PostHog, adding Brevo DNS, or freeing A2 quota — and whenever a task names A2, cPanel, loaiidil, or an A2-hosted domain.'
---

# a2-hosting-context

Serves `ABOUT A2 HOSTING/CLAUDE.md`. Read it before any A2 work.

## Apply
1. **cPanel API ONLY** — never SSH/FTP-based deploy from the laptop. Use `a2.py` (`D:\MEMORY\COWORK\A2\a2.py`, set `MSYS_NO_PATHCONV=1` in Git Bash) or the cPanel Fileman/UAPI. Token lives in root CLAUDE.md / `.env` — never copy it into a synced file.
2. **Docroot:** `~/domain.tld/` (NOT `~/public_html/`); WP sites use a `/wp` subfolder. Server `nl1-cl8-ats1.a2hosting.com`, account `loaiidil`.
3. **Quota:** account caps on **INODES** (~600k), not disk. `fileop op=unlink` = permanent delete bypassing trash (only way to free a full account). Recurring inode source: PrestaShop `var/cache`.
4. **PrestaShop 500 traps:** never delete the smarty/compile dir; watch Smarty `{}` braces + dead theme blocks. Clear cache via Admin.
5. **Security:** NEVER redeploy `claude-api` (RCE backdoor, removed) — use cPanel Fileman API. **Git:** never auto-commit/push.

## When to invoke
Any A2 deploy/domain/cPanel/PrestaShop/Brevo-DNS/quota task, or a task naming loaiidil or an A2 domain.
