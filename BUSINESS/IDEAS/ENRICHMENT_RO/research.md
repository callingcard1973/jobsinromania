# Research: ENRICHMENT RO (IDEA-043)
Date: 2026-04-16

## Description
Imbogatire 8.9M companii RO: CUI -> ANAF -> website -> scrape email. Enrich Romanian company database from 19K to 100K+ emails by chaining CUI lookup, ANAF fiscal data, website discovery, and email scraping.

## Market Size & Demand
- Romania has 3.65M+ registered companies (ClientSolutions.ro)
- B2B data market globally: USD 3.5B+ (2026), growing 15% CAGR
- Romanian-specific data providers charge EUR 0.01-0.50 per enriched record
- Demand: marketing agencies, recruiters, sales teams, EU project consultants

## Competitors Found

| Competitor | Records | Emails | Price | Notes |
|------------|---------|--------|-------|-------|
| ClientSolutions.ro | 3.65M companies | 1M+ | Quote-based | RO market leader, ANAF/ONRC data |
| GlobalDatabase.com | 1.68M records | 204K validated | Quote-based | Monthly validation, 39K phones |
| ListaFirme.eu | All RO companies | Unknown | Freemium + paid | ANAF, ONRC, BPI, insolvency |
| RRF.ro | Verification only | N/A | Free | Company checker, no bulk export |
| CUFinder | Global | Global | SaaS pricing | 15 enrichment services, not RO-specific |
| Termene.ro | All RO companies | Limited | Freemium | Insolvency, debts, legal data |

## Our Advantage
- **8.9M raw records** already in PostgreSQL -- competitors have 1.6-3.6M
- **Pipeline built**: CUI->ANAF->website->email scraping already operational on raspibig
- **Free ANAF API**: Government API is free and unlimited
- **LLM enrichment**: Qwen on raspibig can classify companies, extract patterns
- **Cost: EUR 0** operational (own infrastructure)
- **440K emails already found** (per database counts)

## Market Validated?
YES -- ClientSolutions.ro and GlobalDatabase.com are profitable businesses selling this data. ListaFirme.eu operating 10+ years. Demand for enriched Romanian B2B data is proven. Our advantage: scale (8.9M vs 3.6M) and cost (EUR 0 vs their infrastructure).

## Price Point
- Selling enriched data: EUR 0.02-0.10 per record
- Bulk packages: EUR 500-2,000 for 50K-200K enriched records
- API access: EUR 29-99/mo for 1,000-10,000 lookups
- Internal value: saves EUR 5,000-20,000/year vs buying from ClientSolutions

## Risk
- MEDIUM -- GDPR compliance critical (B2B email generally OK, personal data not)
- ClientSolutions has established reputation and sales channels
- Scraped emails may have lower deliverability than verified databases
- ANAF API could add rate limits or authentication
- Legal: bulk website scraping for emails is gray area under Romanian law

## Recommendation
USE INTERNALLY FIRST. Enrichment pipeline already works and feeds campaigns (440K emails). Selling as product requires GDPR legal review and sales channel. Priority: finish enriching to 100K+ validated emails for own campaigns. Consider selling via Gumroad or API only after 500K+ validated emails with >90% deliverability.

## Sources
- [ClientSolutions.ro - Romanian Companies Database](https://www.clientsolutions.ro/en/services/database/)
- [GlobalDatabase - Romania Companies](https://www.globaldatabase.com/romania-companies-database)
- [ListaFirme.eu - Romanian Company Search](https://listafirme.eu/)
- [CUFinder - Enrichment Engine](https://community.cufinder.io/enrichment-engine/post/enrichment-engine-hh6Muo6siZkf18L)
- [RRF.ro - Company Verification](https://www.rrf.ro/en/company-checker)
