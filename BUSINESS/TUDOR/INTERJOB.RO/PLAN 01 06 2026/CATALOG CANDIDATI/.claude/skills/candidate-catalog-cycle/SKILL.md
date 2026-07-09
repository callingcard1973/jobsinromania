---
name: candidate-catalog-cycle
description: Use when refreshing, rebuilding, leak-auditing, or deploying the FactoryJobs candidate catalog. Triggers — "regenerate the candidate catalog", "rebuild factoryjobs catalog", "refresh and deploy candidates", "publish candidates to factoryjobs.eu", or any work in the CATALOG CANDIDATI folder. Coordinates data refresh → dual HTML build → zero-leak audit → cPanel deploy.
---

# Candidate Catalog Cycle

Trigger skill for the FactoryJobs candidate-catalog harness. Hands off to the
`candidate-catalog-orchestrator` agent, which sequences the specialists.

## When to use
- "Regenerate / rebuild the candidate catalog"
- "Refresh candidates and deploy"
- "Publish candidate catalog to factoryjobs.eu"
- Editing anything under `D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\CATALOG CANDIDATI`

## Pipeline (4 stages, gated)
1. **Refresh** (`candidate-data-refresher`) — pull fresh candidates from raspibig FARMWORKERS, dedup on email, write `DATA\candidates_master_final.csv` + `master.json`. STOP if row count drops.
2. **Build** (`candidate-catalog-builder`) — `python "CODE\build_single_html.py" --all` → client + internal HTML (~2 MB each).
3. **Audit** (`candidate-leak-auditor`) — verify CLIENT file has ZERO candidate mailto/tel/wa.me links. FAIL is blocking.
4. **Deploy** (`candidate-catalog-deployer`) — push client catalog to `factoryjobs.eu/candidates/` via cPanel API only. Verify 200.

## Hard rules
- A2 deploys = cPanel API ONLY. Never SSH/FTP.
- raspibig data pulls = documented plink/SSH.
- Internal catalog (with contacts) NEVER goes public.
- No stage proceeds if the previous one failed; failed leak audit halts everything.
- Brand: navy `#0f2942` + orange `#f5a000`, no emojis. Quote all paths (spaces).

## Quick commands
```powershell
cd "D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\CATALOG CANDIDATI"
python "CODE\build_single_html.py" --all     # build both variants
```
