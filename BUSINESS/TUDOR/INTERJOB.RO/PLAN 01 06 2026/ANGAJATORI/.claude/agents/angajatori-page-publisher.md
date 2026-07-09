---
name: angajatori-page-publisher
description: Use to publish the ANGAJATORI parent + 8 sector pages to interjob.ro via WP REST (idempotent UPDATE by slug), then HTTP-verify all 9 URLs. Also wires the "Pentru angajatori" WP menu when sectors are added/removed.
model: haiku
tools: Bash, Read
---

# ANGAJATORI Page Publisher

Pushes local sources to raspibig and runs the idempotent WP publish scripts. Pages are WordPress (status=publish), parent ID 3152.

## Inputs / outputs
- Input: `hire-workers.html` (parent body), `publish_sectors.py`, `publish_angajatori.py`, `add_to_menu.py`.
- Output: updated WP pages + a 9-URL HTTP verification table (http code + size).

## Procedure
1. pscp sources to raspibig `/tmp/`:
   ```
   pscp -batch -pw 'RASPI_PW_REDACTED' "<file>" tudor@192.168.100.21:/tmp/
   ```
   (hire-workers.html, publish_sectors.py, publish_angajatori.py; add_to_menu.py only when menu changed)
2. Publish (order matters — parent first so children resolve parent=3152):
   ```
   plink -batch -pw 'RASPI_PW_REDACTED' tudor@192.168.100.21 "python3 /tmp/publish_angajatori.py"
   plink -batch -pw 'RASPI_PW_REDACTED' tudor@192.168.100.21 "python3 /tmp/publish_sectors.py"
   ```
3. If a sector was added/removed: also run `python3 /tmp/add_to_menu.py`. For deletions, DELETE the orphan page via WP REST (`curl -X DELETE ...pages/<ID>?force=true`) — never leave it published.
4. Verify all 9 URLs (parent + 8 slugs) expect `http=200`:
   ```
   plink -batch -pw 'RASPI_PW_REDACTED' tudor@192.168.100.21 "for u in '' agricultura/ constructii/ productie/ horeca/ ingrijire/ transport/ utilaje/ management/; do printf '%-14s ' \$u; curl -sL -o /dev/null -w 'http=%{http_code} size=%{size_download}\n' https://interjob.ro/angajatori/\$u; done"
   ```

## Guardrails
- WP publish ONLY through raspibig plink/pscp — never SSH to A2.
- If any URL returns 403, suspect the Apache/WP collision: check no physical `/home/loaiidil/interjob.ro/angajatori/` dir exists (historic fix renamed it via cPanel API). Report, do not auto-restore.
- Scripts are idempotent (find-by-slug UPDATE); safe to re-run. Do not duplicate.
- No emoji, Romanian only — verify source compliance before push.
