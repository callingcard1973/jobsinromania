# Trasabilitate Produs Alimentar

Food traceability SaaS for Romanian producers selling to hypermarkets, EU export, and B2B.

## Status: IDEA — Awaiting Decision (A vs B)

**Created**: 2026-03-07 | **Last active**: 2026-03-08

Two parallel tracks exist — must choose one before proceeding:
- **Track A** (research): Packaged products (cheese, honey). 26 warm leads, EUR 3.5K/mo potential. Zero code.
- **Track B** (code): Loose produce (vegetables). 60% Flask+React built, ARM-ready. Zero customers.

**Recommendation**: B first (speed), then A (revenue). See `00_READ_FIRST.md`.

## Who Needs This

NOT local market sellers. Only producers in B2B channels where compliance matters:

| Segment | Count | Why they pay | Price |
|---------|-------|--------------|-------|
| Hypermarket suppliers | ~102 | Kaufland QA demands batch trace | EUR 100-300/mo |
| EU Exporters | ~68 | EU 178/2002 mandatory traceability | EUR 200-500/mo |
| B2B Distributors | ~54 | Insurance + sourcing proof | EUR 150-400/mo |
| Restaurant/Hotel suppliers | ~34 | HACCP origin proof | EUR 80-200/mo |

**Total addressable**: 269 of 680 RNPM producers. Revenue ceiling: EUR 40K/mo.

## Competitive Position

- **Romania**: Zero competitors identified (blank market)
- **Global**: USD 23.3B market growing 7.45% CAGR
- **Nearest**: FoodDocs (EUR 159/mo, no RO presence), FoodReady (US-centric)
- **Moat**: First-mover + cooperative bundling (Gospodarii de Altadata) + hypermarket pre-integration
- **Window**: ~12 months before incumbents localize

## Architecture

**DB**: PostgreSQL — 4 tables: `batches`, `ingredients`, `movements`, `inspections`
**Backend**: Flask dashboard at `trasabilitate.agroevolution.com/batch/{batch_id}`
**CLI**: 3 commands — batch create, track movement, compliance report
**QR**: Each batch gets scannable QR → full trace page
**PDF**: Export compliance dossier for buyers/importers
**Deploy**: Docker on raspibig (ARM-optimized)

## Revenue Model

| Tier | EUR/mo | Use case |
|------|--------|----------|
| Starter | 99 | 1 producer, <50 batches |
| Pro | 299 | 5 producers, <500 batches |
| Enterprise | 999+ | Unlimited (distributor) |

**Baseline MRR**: EUR 1,900 (12 producers at 50% adoption)
**Year 1 ARR**: EUR 26K (conservative) | **Margin**: 95%

## Key Files

| File | What |
|------|------|
| `00_READ_FIRST.md` | Decision guide — read before anything |
| `BUSINESS_CASE.md` | Financial model, risks, projections |
| `COMPETITIVE_ANALYSIS.md` | 50+ competitors analyzed |
| `TARGET_CLIENTS.csv` | 26 validated prospects |
| `OUTREACH_EMAILS.md` | 3 segmented email templates |
| `SUMMARY_EXECUTIVE.md` | Executive overview |
| `MVP_7DAY_SPRINT.md` | 7-day implementation plan (Track B) |
| `PRODUS TRASABIL/` | Working code — Flask, CLI, Docker |
| `STATUS_REPORT.md` | Comparison of Track A vs B |

## Go/No-Go Criteria

1. Call Kaufland procurement: "Do you require batch trace from small suppliers?"
2. Contact Miklo/Tanko: "Test platform for 3 free batches?"
3. If both yes → Launch MVP. If Kaufland no → pivot to export-first.

## Related

- `D:\MEMORY\IDEAS\PRODUS MONTAN\` — 680 producers database (source of leads)
- `D:\MEMORY\IDEAS\COOPERATIVA BUSINESS\` — Gospodarii de Altadata cooperative
- `D:\MEMORY\IDEAS\FOOD\` — food industry research
