---
name: job-catalog-deploy
description: Publish a built InterJob job catalog (client/anonymized variant) to the domain's A2 web folder at domain.eu/catalog/ with a stable latest URL + dated archive, and optionally email it to warm leads (ASCII-only). Use when asked to "deploy the catalog", "publish the job catalog", "put the catalog online", or "email the catalog to leads".
---

# job-catalog-deploy

Take the client-variant catalog from the builder and make it publicly reachable, optionally emailing warm leads. Reuses `deploy_to_a2.py` / the global `a2-content-publish` skill for upload.

## Procedure
1. Read `_workspace/01_catalog-builder_manifest.json`; select the CLIENT (anonymized) PDF/HTML only.
2. Upload to `~/{domain}/catalog/` via cPanel (docroot is `~/{domain}/`, never `public_html`).
3. Write `catalog_latest.{pdf,html}` (stable URL) + a dated copy `catalog_YYYYMMDD.pdf` (archive).
4. `curl -sI` the latest URL → confirm 200.
5. (Optional, explicit only) email warm leads — ASCII subject+body, NFKD-fold names/occupations at send.

## Hard rules
- **Never publish the internal/with-contacts variant.** Employer contacts are the product; leaking them publicly destroys the lead-gen model.
- Catalog file keeps diacritics; only email text is ASCII-folded.
- Email defaults to dry-run; live send only when the user explicitly says so.

## Failure modes
- 100% disk quota / cPanel auth → blocker; pair with `a2-disk-cleanup`. Do not report a 404'd upload as success — always verify with curl.
