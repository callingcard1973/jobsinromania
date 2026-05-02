# Skill Registry

## Project
- Name: FOOD
- Root: `D:/MEMORY/IDEAS/FOOD`
- Purpose: commercial planning and execution workspace for Romanian food supply, aggregation, buyer outreach, and raspibig synchronization.

## Project Conventions

| Source | Type | Relevance | Notes |
|--------|------|-----------|-------|
| `claude.md` | Project note | Medium | Brainstorm-style food ideas kept in the workspace root. |
| `FOOD_MARKET_STRATEGY_SUMMARY.md` | Strategy doc | High | Main strategy summary tying together supply, channels, and commercialization. |
| `FOOD_MASTER_PLAYBOOK.md` | Operating doc | High | Best current operating reference for workspace roles and execution order. |
| `FIRST_OUTREACH_PLAN.md` | Execution doc | High | First-wave buyer and seller outreach plan. |
| `SUPERMARKETS_CLAUDE_CODE_OVERLAP.md` | Architecture note | High | Defines code-role boundaries between supermarket workspaces. |

## Relevant User Skills

| Skill | Trigger Fit | Use In FOOD Workspace |
|-------|-------------|-----------------------|
| `catalog-generator` | Medium | Generate catalog-style HTML outputs from structured data if buyer/seller listings need publication. |
| `html-to-pdf` | Medium | Convert finished FOOD strategy or outreach docs to PDF. |
| `html-to-pdf-local` | Medium | Local Windows PDF conversion for large catalogs or strategy packets. |
| `sdd-init` | High | Initialize Spec-Driven Development structure in the FOOD workspace. |
| `sdd-propose` | High | Create change proposals for FOOD execution or workspace organization changes. |
| `sdd-spec` | High | Write delta specs for outreach, buyer workflow, or synchronization processes. |
| `sdd-design` | Medium | Write technical design when a FOOD change involves automation or architecture choices. |
| `sdd-tasks` | High | Break FOOD changes into execution checklists. |
| `sdd-apply` | High | Implement approved FOOD changes. |
| `sdd-verify` | High | Verify that FOOD changes match proposal, specs, and tasks. |
| `sdd-archive` | Medium | Archive completed FOOD changes into OpenSpec history. |

## Current Stack Notes
- Primary assets are markdown strategy and execution files.
- Local automation in the FOOD root is PowerShell and batch based.
- Imported supporting toolkits under sibling folders use Python.
- raspibig at `/opt/ACTIVE/FOOD` is the operational source of truth.

## Recommended Load Order
1. Read `FOOD_MASTER_PLAYBOOK.md` for current operating model.
2. Read `FOOD_MARKET_STRATEGY_SUMMARY.md` for strategic context.
3. Read `FIRST_OUTREACH_PLAN.md` for immediate execution sequence.
4. Read `SUPERMARKETS_CLAUDE_CODE_OVERLAP.md` before changing supermarket-related code or workflows.
5. Use SDD skills for multi-step changes that should persist in `openspec/`.