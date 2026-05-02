# Proposal: Launch Food Outreach Pipeline

## Intent

The FOOD workspace already contains the essential strategy, buyer lists, seller lists, and supermarket intelligence, but it is still document-heavy rather than execution-ready. This change turns the current material into a controlled first outreach pipeline so the project can move from planning into buyer and seller contact execution.

## Scope

### In Scope
- Define the first operational outreach pack for buyers and sellers.
- Formalize the role split between `PRODUSMONTAN`, `ZAI_SUPERMARKETS`, `SUPERMARKETS_CLAUDE`, and cooperative documents.
- Produce SDD artifacts for the first-wave outreach workflow so future execution can be tracked cleanly.

### Out of Scope
- Sending live outreach emails or campaigns.
- Rebuilding or merging the supermarket codebases.
- Changing remote data pipelines inside imported workspaces.

## Approach

Use the existing FOOD strategy documents as the source material, then define a first-wave operating workflow centered on wholesale-first buyer outreach, a fixed initial seller pack, and a clear boundary between supply, aggregation, intelligence, and campaign execution. Persist the change in `openspec/` so specs, design, tasks, and verification can follow without losing continuity.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `FOOD_MASTER_PLAYBOOK.md` | Modified | Serves as the operating baseline for execution decisions. |
| `FIRST_OUTREACH_PLAN.md` | Modified | Defines the buyer and seller wave structure that this change will operationalize. |
| `SUPERMARKETS_CLAUDE_CODE_OVERLAP.md` | Modified | Provides architecture boundaries between supermarket workspaces. |
| `openspec/config.yaml` | New | Establishes SDD rules for the FOOD workspace. |
| `openspec/changes/launch-food-outreach-pipeline/` | New | Stores the proposal and future artifacts for this change. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Outreach plan stays theoretical and never becomes executable assets | Medium | Follow with specs and tasks that force concrete deliverables such as buyer deck, outreach email, and seller sheet. |
| Confusion between `ZAI_SUPERMARKETS` and `SUPERMARKETS_CLAUDE` roles | Medium | Keep the role split explicit in specs and tasks; do not merge scripts. |
| Buyer outreach starts before seller readiness is validated | High | Require seller readiness checks as a prerequisite in the next spec and task phases. |

## Rollback Plan

If the workflow or artifact structure proves unhelpful, stop at the proposal stage and archive or remove the change folder without touching the operational FOOD documents. No production code or datasets are modified by this proposal alone.

## Dependencies

- Existing FOOD strategy documents in the workspace root.
- Raspibig workspace at `/opt/ACTIVE/FOOD` remaining the source of truth.
- Access to seller readiness details from `PRODUSMONTAN` materials.

## Success Criteria

- [ ] A spec defines the first outreach workflow using Given/When/Then scenarios.
- [ ] A task list breaks the workflow into concrete buyer, seller, and asset-preparation steps.
- [ ] The final workflow clearly states which workspace owns each data, supply, and outreach responsibility.