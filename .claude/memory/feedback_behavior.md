---
name: Feedback on Behavior & Approach
description: Rules for how to work with this user - directness, no over-explanation, comprehensive setup
type: feedback
---

**Rule 1: Be Direct & Comprehensive**
- **Why**: User uses emphatic language ("fucking setup") to indicate they want complete, thorough work — not hints or partial solutions
- **How to apply**: When asked to inspect/propose/install, do the FULL audit. Show what's broken, what's working, rank priorities by impact. No hedging.

**Rule 2: Text-Only Summaries When Requested**
- **Why**: User explicitly said "CRITICAL: Respond with TEXT ONLY. Do NOT call any tools." to avoid context waste
- **How to apply**: When user asks for summary/analysis without explicit tool authorization, deliver text only. Once approved, execute everything at once.

**Rule 3: Execute in Sequence When Phases Depend on Each Other**
- **Why**: Setup has dependencies (SSH → deploy, DB → queries, memory → dispatch)
- **How to apply**: Run Phase 1 complete before Phase 2. Don't skip steps. Verify each phase before moving next.

**Rule 4: No Over-Permissioning**
- **Why**: User has clear safety rules in CLAUDE.md (no SSH to A2, cPanel API only, confirm before DELETE, etc.)
- **How to apply**: Always honor safety hooks. Ask before destructive operations. Don't guess on credentials or deploy paths.

**Rule 5: Dispatch Tasks to Specialized Subagents**
- **Why**: User built 5 expert subagents (brevo-sender, pg-enricher, cpanel-deployer, madr-scraper, cso-reviewer) for this reason
- **How to apply**: After setup complete, use smart dispatch: email tasks → brevo-sender, DB tasks → pg-enricher, etc. Route by keyword match.

**Rule 6: Treat Z.AI as Optional**
- **Why**: Investigation showed Z.AI API is broken (404 errors), goose config was lost in W11 reinstall — it's a nice-to-have, not critical
- **How to apply**: Restore config to be ready, but don't spend hours debugging Z.AI. Native Claude models work fine. Use Z.AI only if user specifically asks.
