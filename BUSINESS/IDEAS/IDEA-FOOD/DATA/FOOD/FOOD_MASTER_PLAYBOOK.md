# Food Master Playbook

## Purpose
- This is the main operating playbook for the FOOD workspace.
- It consolidates strategy, workspaces, shortlists, and execution order into one document.

## Source Of Truth
- Main machine: raspibig.
- Main workspace: `/opt/ACTIVE/FOOD`.
- Windows mirror: `D:/MEMORY/IDEAS/FOOD`.

## Workspace Roles

### PRODUSMONTAN
- Role: supply pipeline.
- Use for: producer discovery, product catalog, seller outreach, and marketplace preparation.

### COOPERATIVA BUSINESS
- Role: legal and operational wrapper.
- Use for: aggregation, contracting, central invoicing, and producer onboarding.

### ZAI_SUPERMARKETS
- Role: commercial database packaging layer.
- Use for: simple list exports, sellable buyer segments, and fast lead-generation products.

### SUPERMARKETS_CLAUDE
- Role: strategic intelligence and enrichment layer.
- Use for: SEAP, cross-match, alerts, enrichment, segmentation, insolvency filtering, and wider route-to-market analysis.

### ROMCONSERV
- Role: focused outreach runner for packaged-food companies.
- Use for: direct campaign execution in a narrower niche.

### SEAP FOOD WINNERS
- Role: public procurement buyer-signal dataset.
- Use for: procurement targeting and tender-driven food outreach.

## Core Commercial Model
1. Build supply from `PRODUSMONTAN` sellers.
2. Aggregate commercially through the cooperative.
3. Use `ZAI_SUPERMARKETS` and `SUPERMARKETS_CLAUDE` to identify buyers, segments, and channels.
4. Start with shelf-stable products.
5. Expand into cold-chain dairy and cheese after logistics and compliance are validated.

## First Products
1. Honey.
2. Preserves and jams.
3. Juices and vinegar.
4. Dried fruit and similar shelf-stable products.
5. Cheese and dairy as a second phase.

## First Buyers
1. Metro Romania.
2. Selgros Romania.
3. Kaufland Romania.
4. Carrefour Romania.
5. Mega Image.
6. Profi.
7. Lidl and Schwarz supplier channels.
8. Auchan and Carrefour group supplier channels.
9. Diaspora shops.
10. Restaurants, hotels, online grocery, and cooperative networks.

## First Sellers
1. Peter Miklo.
2. Peter Tanko / Cooperativa Trotusi.
3. Stupina Igna.
4. Mister Juice.
5. Martinovici Svetlana.

## Required Commercial Pack
1. Cooperative presentation.
2. Seller sheet.
3. SKU and pricing sheet.
4. Delivery coverage note.
5. Compliance checklist.
6. Outreach email and buyer deck.

## Execution Order
1. Confirm first sellers and SKU readiness.
2. Finalize the first buyer outreach pack.
3. Send wholesale-first outreach.
4. Follow with retail-chain local sourcing outreach.
5. Use smaller channels to close early pilot orders.
6. Feed responses back into product selection and pricing.

## Working Rules
1. Keep raspibig as the main source of truth.
2. Do not merge supermarket workspaces blindly.
3. Use `ZAI_SUPERMARKETS` for packaging and simple exports.
4. Use `SUPERMARKETS_CLAUDE` for deeper intelligence and SEAP-related work.
5. Keep `PRODUSMONTAN` and `ROMCONSERV` focused on execution.

## Key Supporting Files
- `FOOD_MARKET_STRATEGY_SUMMARY.md`
- `BUYER_SHORTLIST.md`
- `SELLER_SHORTLIST.md`
- `FIRST_OUTREACH_PLAN.md`
- `SUPERMARKETS_CLAUDE_CODE_OVERLAP.md`
- `INVENTORY.md` on raspibig

## Current Best Play
- The best immediate commercial path is:
  `seller supply -> cooperative aggregation -> wholesale-first buyer outreach -> early orders -> retail expansion -> recurring data and outreach services`.