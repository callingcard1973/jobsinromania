---
name: angajatori-sector-refresh
description: Use to recompute the per-sector candidate counts for the ANGAJATORI employer pages from fw_candidates on raspibig, and update SECTORS counts in publish_sectors.py + the parent grid in hire-workers.html. Run when counts are stale (>7 days) or before any publish.
model: sonnet
tools: Bash, Read, Edit
---

# ANGAJATORI Sector Refresh

Keeps the "X muncitori gata pentru angajare" numbers truthful. Maps DB roles to the 8 sector slugs and rewrites the hardcoded `count` fields.

## Role → sector mapping (per CLAUDE.md data section)
- farm-worker → agricultura
- construction → constructii
- factory + packaging → productie
- hospitality → horeca
- care → ingrijire
- logistics → transport
- machinery → utilaje
- management → management

## Inputs / outputs
- Input: live counts from `interjob_master.fw_candidates`.
- Output: edited `publish_sectors.py` (SECTORS[].count) + `hire-workers.html` grid counts; a `role → count` summary.

## Procedure
1. Query raspibig:
   ```
   plink -batch -pw 'bucare' tudor@192.168.100.21 "psql -U tudor interjob_master -A -F',' -c \"SELECT role, count(*) FROM fw_candidates GROUP BY role ORDER BY count DESC;\""
   ```
2. Aggregate per the mapping above (sum factory+packaging into productie). Format Romanian thousands (e.g. `1.446`).
3. For each changed sector, Edit `count` in `"...\ANGAJATORI\publish_sectors.py"` SECTORS and the matching card in `"...\ANGAJATORI\hire-workers.html"`.
4. Report old→new per sector and TOTAL classified vs total candidates.

## Guardrails
- Read both files before editing; keep exact Romanian formatting and quoting.
- Do not change labels, bullets, salary bands, or countries — counts only.
- If a role disappears (count 0), flag it; do not silently zero a live sector.
- `~/.pgpass` entry is for user `tudor` — always `-U tudor`.
