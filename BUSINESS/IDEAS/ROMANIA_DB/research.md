# Research: ROMANIA DB (IDEA-007)
Date: 2026-04-16

## Description
8.9M companies in PostgreSQL but only 19K unique emails. Need enrichment to unlock Romanian email campaigns. Currently 144K non-null email fields but only 19K distinct values.

## Market Size & Demand
- Romania has 3.65M registered entities, ~940K active SRL/SA companies
- Company data enrichment is a proven B2B market in Romania
- RisCo, ListaFirme, ClientSolutions all profitable selling this data
- Email enrichment specifically is high-demand: every sales team needs verified emails

## Competitors Found

| Competitor | What they sell | Pricing | Scale |
|---|---|---|---|
| openapi.ro | API: CUI lookup, financials, CAEN | Free 100 req/mo, paid plans undisclosed | Major player since ~2015 |
| listafirme.ro | Web search + API, financial history, trademarks | Free tier + subscription (undisclosed) | Running since 2004, top traffic |
| risco.ro | API: financials, contacts, debts, ratings | 200 RON/1000 queries (~0.04 EUR/query), min 100 RON/mo | Established, CRM integrations |
| clientsolutions.ro | Bulk CSV databases by NACE code | Custom pricing (call for quote), ~940K companies | Bulk data seller |
| firme.info | Free company lookup | Ad-supported free | High traffic, no API |
| romanian-companies.eu | ListaFirme sister site (English) | Same as listafirme | International audience |
| totalfirme.ro | Company directory | Free/ad-supported | Smaller player |
| Coresignal | Tech companies data, LinkedIn-sourced | Enterprise pricing ($$$) | Global, not RO-specific |

## Our Advantage
- Already have 8.9M records in PostgreSQL (larger than any competitor's stated count)
- Own scraping infrastructure on raspibig (Playwright, Node-RED)
- Can enrich emails via pattern matching (79.9M website-fara-email rows waiting)
- Zero marginal cost for enrichment (own LLM, own scrapers)
- Not selling data -- using it for own campaigns (no legal/licensing friction)

## Market Validated?
YES. Multiple profitable competitors exist (RisCo, ListaFirme, ClientSolutions). The data enrichment market in Romania is mature. However, our use case is internal (campaign fuel), not resale.

## Price Point
- If resold: 0.02-0.20 EUR per enriched record (based on RisCo pricing)
- Internal value: each enriched email = potential campaign target worth 5-50 EUR in recruitment fees
- Enriching 100K emails could unlock 500K+ EUR in campaign potential

## Risk
- LOW for internal use. Email pattern matching has ~30-40% accuracy without verification
- MEDIUM if reselling: GDPR compliance required, competitors are established
- Bounced emails damage sender reputation if not verified

## Recommendation
**LAUNCH** -- This is not a product to sell, it's infrastructure that powers all RO campaigns. Prioritize enriching the 79.9M rows with website but no email. Use pattern-based email generation + MX verification pipeline already built.

## Sources
- [openapi.ro](https://openapi.ro/en)
- [listafirme.ro](https://www.listafirme.ro/lng/en/romanian-companies-database.htm)
- [risco.ro API pricing](https://www.risco.ro/en/api-firme)
- [clientsolutions.ro](https://www.clientsolutions.ro/en/services/database/)
- [listafirme.ro competitors (Similarweb)](https://www.similarweb.com/website/listafirme.ro/competitors/)
