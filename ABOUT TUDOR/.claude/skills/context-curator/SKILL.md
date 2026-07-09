---
name: context-curator
description: 'Maintain the 5 canonical ABOUT folders (TUDOR, RASPIBIG, RASPI, A2 HOSTING, BUSINESSES) as the accurate single source of truth. Use when a new durable preference/feedback/decision-rule is learned, when an ABOUT file drifts from reality, after infra changes (host migration, new service, domain change), or to audit ABOUT vs the memory index. Triggers — "update ABOUT", "curate context", "sync ABOUT with memory", "audit the context files", or "fold this into ABOUT". Invokes the context-curator agent; reconstructs only from sourced material, never fabricates, never commits.'
---

# context-curator (skill)

Entry point for the `context-curator` agent. Keeps `ABOUT */CLAUDE.md` accurate and sourced — they drive every session.

## What it does
1. Fold a newly-learned durable preference/feedback/decision into the right ABOUT file + ensure a matching memory file (type `feedback`/`user`/`project`) exists; link them.
2. After an infra change (host migration, new/removed service, domain change), update the affected ABOUT file (RASPIBIG/RASPI/A2).
3. Audit ABOUT files against the memory index; flag stale/contradictory/missing context and resolve sourced gaps.

## Hard rules
- **Sourced only** — every line traces to memory or root CLAUDE.md; mark `unknown`, never invent.
- **No secrets / PII / legal amounts** in ABOUT files (GitHub-synced). Creds → reference memory/.env.
- **Never commit/push** (root CLAUDE.md GIT RULES) — leave changes in the working tree.
- Edit in place, keep the terse numbered style.

## Invoke when
"update/curate/sync/audit ABOUT", a new lasting Tudor preference appears, or infra/business facts changed.
