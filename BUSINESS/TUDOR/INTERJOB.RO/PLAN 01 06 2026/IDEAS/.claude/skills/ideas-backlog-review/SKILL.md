---
name: ideas-backlog-review
description: Use when the user says "review the ideas backlog", "what should I build next", "score IDEAS.md", "top ROI ideas for InterJob", "any quick wins", or wants the SEO/automation improvement list re-prioritized. Triggers a ROI triage of IDEAS.md — reference only, no execution.
---

# IDEAS Backlog Review

Re-prioritize the InterJob SEO + automation improvement backlog by business ROI. Reference doc only — surfaces what to build next, builds nothing.

## When to use
- "review the ideas backlog" / "re-prioritize IDEAS"
- "what should I build next on InterJob"
- "top ROI ideas" / "quick wins" / "zero-cost SEO ideas"
- "score IDEAS.md"

## Steps
1. Invoke the `ideas-triage` agent.
2. Agent reads `D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\IDEAS\IDEAS.md` + strategic directive in `D:\MEMORY\CLAUDE.md`.
3. Each item scored on the 7-question decision framework; ROI = (traffic + revenue + data value) / effort.
4. Returns: ranked table (rank | item | category | ROI | effort | why now) + top-5 shortlist + separate "no new code / instant win" list.
5. Stop. Present data; Tudor decides what to action (do not auto-propose next steps).
6. Optional, only if asked: Edit the "Idei prioritare" sections of IDEAS.md / CLAUDE.md with the new ranking, dated 2026-06-24.

## Notes
- Output language: Romanian. Quantify everything (searches/month, €/month, hours).
- Favor zero-cost high-traffic SEO (JobPosting schema, county pages) and crons for scripts that already exist on raspibig.
- No deploys, no scraping, no raspibig changes. A2/WP only ever via cPanel API.
