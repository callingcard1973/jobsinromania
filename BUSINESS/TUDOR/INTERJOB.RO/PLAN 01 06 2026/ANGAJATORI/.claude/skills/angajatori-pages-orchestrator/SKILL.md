---
name: angajatori-pages-orchestrator
description: Use when refreshing or publishing the InterJob.ro employer pages (/angajatori/ parent + 8 sector pages) — triggers include "refresh angajatori counts", "update employer pages", "republish angajatori", "recompute candidate counts", "angajatori CTR/leads report", or working in the ANGAJATORI folder. Runs DB count refresh -> page regen -> WP REST publish -> verify -> analytics.
---

# ANGAJATORI Pages Orchestrator

Drives the employer-acquisition hub on `interjob.ro/angajatori/`: 1 parent (3152) + 8 sector pages (3154–3161), supply-side pitch with real `fw_candidates` counts.

## When to use
- "Refresh/recompute angajatori candidate counts"
- "Republish the employer pages" / "update /angajatori/"
- "Add/remove a sector page"
- "How are the employer pages converting?" (CTR/leads)
- Any work inside `"D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\ANGAJATORI"`

## Agents
- **angajatori-orchestrator** — runs the full cycle, gates each stage.
- **angajatori-sector-refresh** — recompute counts from `fw_candidates`, edit SECTORS + grid.
- **angajatori-page-publisher** — pscp + WP REST publish (raspibig plink) + 9-URL verify + menu.
- **angajatori-analytics** — PostHog leads/CTR per sector, flag underperformers.
- Reuse conceptually: **infrastructure-health** (raspibig/PG up before publish).

## Steps
1. Confirm scope (refresh-only, publish, or full cycle + analytics).
2. Run angajatori-sector-refresh if counts > 7 days old or forced.
3. If counts changed, run angajatori-page-publisher (parent then sectors), verify all 9 = http 200.
4. Run angajatori-analytics for the leads/CTR report.
5. Report one status line; stop (Tudor decides next).

## Hard rules
- WP publish via raspibig plink/pscp ONLY — never SSH to A2; static A2 file ops use cPanel API.
- Romanian copy, zero emoji/pictographic glyphs.
- Never invent counts — DB is source of truth.
- Idempotent UPDATE by slug; quote all spaced paths.
