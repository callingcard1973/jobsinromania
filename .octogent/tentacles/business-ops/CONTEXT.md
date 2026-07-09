# business-ops

Revenue initiatives with their own code: publishing, procurement, agri, B2B verticals.

## Scope

- `BUSINESS/TUDOR SEICARESCU LIFE STRATEGY/PRINTING/CODE/` — Tudor Printing House FastAPI (Lulu + Stripe)
- `CODE/INFRA/AUTOMATE/skills/enrich_seap_winners.py` + SEAP bid intelligence system (5 tools)
- `CODE/INFRA/AUTOMATE/skills/ebrd_psd_scraper.py` + EBRD procurement pipeline
- `BUSINESS/BOGDAN GAVRA/` — Spații Verzi + Parcuri campaigns + catalogs
- `BUSINESS/IDEAS/` — MASTER.csv (source of truth for all ideas)

## Key Decisions

- **Printing House uses embedded Stripe payment** — payment form renders on-page, user never redirected to Stripe checkout. Enforced rule from prior session. `payment_routes.py` handles Stripe intent; `routes.py` handles Lulu API calls.
- **Lulu API: upload PDF → create print job** — flow: `POST /files/` (upload) → `POST /print-jobs/` (order). Bearer token auth. Credentials in `.env`, never hardcoded.
- **SEAP/EBRD = outreach lead sources** — procurement winner data feeds into `leads` table then campaign pipeline. Not standalone — always connects back to campaigns tentacle.
- **BUSINESS/IDEAS/MASTER.csv is source of truth** — all ideas tracked with ID (IDEA-NNN). Never delete rows. Add new ideas at end.
- **Bogdan Gavra = separate B2B client** — CAEN 8130 (landscaping), AVP Park data, targets 3K primării. agroevolution.com/spatii-verzi is live. Catalogs generated via catalog skill pipeline.

## Conventions

- All printing house files under 250 lines. Currently split: `app.py` (FastAPI init), `routes.py` (Lulu), `payment_routes.py` (Stripe), `lulu_client.py` (API wrapper).
- Never redirect to Stripe — always embedded payment intent flow.
- Never auto-publish WordPress articles — draft only, publish on explicit approval.
- SEAP/EBRD enrichment: always LLM-classify sector before inserting to campaigns pipeline.
- Business ideas → note in MASTER.csv before implementing.

## Key Files

```
PRINTING/CODE/
├── app.py              — FastAPI app, CORS, mounts /uploads static dir
├── routes.py           — Lulu API: upload PDF, create print job, order status
├── lulu_client.py      — Lulu Bearer token + API wrapper
├── payment_routes.py   — Stripe payment intent (embedded, never redirect)
└── stripe_handler.py   — Stripe webhook handling

BUSINESS/IDEAS/
└── MASTER.csv          — all ideas, IDEA-NNN IDs, source of truth
```

## Revenue Streams Tracked Here

| Initiative | Status | Code location |
|-----------|--------|---------------|
| Tudor Printing House | MVP complete | `PRINTING/CODE/` |
| SEAP bid intelligence | Live, 5 tools | `AUTOMATE/skills/enrich_seap_winners.py` |
| EBRD procurement | Live, 4,176 projects | `AUTOMATE/skills/ebrd_psd_scraper.py` |
| Bogdan Gavra spatii verzi | Active | `BUSINESS/BOGDAN GAVRA/` |
| Lulu/KDP publishing | Setup done | `PRINTING/` |
