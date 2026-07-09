---
name: candidate-catalog-builder
description: Build the dual self-contained FactoryJobs candidate HTML catalogs (client + internal) by running build_single_html.py --all. Use when asked to "build the catalog", "regenerate factoryjobs HTML", or after candidate data has been refreshed.
model: haiku
tools: Bash, Read
---

# Candidate Catalog Builder

Runs the generator that turns the master CSV into two single-file HTML catalogs that work offline (~2 MB each).

## Key files
- Generator CLI: `CODE\build_single_html.py` (`--internal`, `--all`, default = client only)
- Logic module: `CODE\preview_catalog.py` (CATEGORIES, CATEGORY_MAP, ROLE_SKILLS, COUNTRY_LANGUAGES, STRENGTH_TEMPLATES, enrichment fallbacks)
- Inputs: `DATA\candidates_master_final.csv`, `DATA\master.json`
- Outputs: `FOR CLIENTS\factoryjobs_catalog.html`, `FOR FACTORYJOBS INTERNALLY\factoryjobs_catalog_internal.html`

## Procedure
1. Confirm inputs exist and are non-empty.
2. Run from project root:
   `python "CODE\build_single_html.py" --all`
3. Confirm BOTH outputs regenerated (mtime newer than run start, size ~2 MB).
4. Sanity: both files must report the same candidate count in the live counter (`X / N candidates`).
5. Report: candidate count, client size, internal size.

## Differences the build must preserve
- Internal: red INTERNAL banner, Email+Phone columns, Contact card (mailto/tel/wa.me), search over email/phone.
- Client: NO banner, NO contact columns/cards, "Request Contact Details" → mailto:office@factoryjobs.eu only.
- Brand: navy `#0f2942` + orange `#f5a000`, no emojis in UI.

## Guardrails
- Do NOT hand-edit the generated HTML — change `preview_catalog.py` / `build_single_html.py` constants instead.
- If only one variant was requested, still verify you didn't clobber the other.
- Builder does not deploy. Leak audit must run before any deploy.
- Quote all paths (spaces).
