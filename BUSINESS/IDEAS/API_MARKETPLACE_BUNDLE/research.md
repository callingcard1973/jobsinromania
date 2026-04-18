# Research: API MARKETPLACE BUNDLE (IDEA-133)
Date: 2026-04-16

## Description
5 APIs on RapidAPI: ANAF lookup, email validator, company search, CV parser, insolvency check. EUR 0.01-0.50/call. 100K calls/month target.

## Market Size
- RapidAPI: 4M+ developers, 40K+ APIs listed
- Company data API market growing (KYC/compliance driver)
- openapi.ro: 99-499 RON/mo plans, proving Romania demand
- Global API economy: $5.1B (2023), projected $14.6B by 2028

## Competitors
| Competitor | Type | Price/call | Notes |
|-----------|------|-----------|-------|
| openapi.ro | RO company API | EUR 0.005-0.10 | 99-499 RON/mo, free 100/mo |
| OpenAPI.com (console) | EU company data | EUR 0.001-1.10 | Italy focus, expanding EU |
| ListaFirme.eu API | RO company search | Credit-based | Annual plans |
| AlertaCUI.ro API | ANAF+ONRC+BPI | Per-query | Historical data included |
| Eranova/DataCore | Open source ANAF | Free (self-host) | GitHub REST API |
| HitHorizons | EU company data | Enterprise | 80M+ European businesses |
| RapidAPI company APIs | Various | $0.001-0.05 | Generic company info |

## Our Advantage
- 208M companies in PostgreSQL (pan-European, not just Romania)
- ANAF integration, BPI monitoring, email validation already built
- CV parser exists. Zero marginal cost per query.
- Can offer Romania depth no global API has

## Validated?
YES. openapi.ro and ListaFirme.eu prove demand. Question is volume: can we get 100K calls/month?

## Price
ANAF lookup EUR 0.01. Company search EUR 0.02. Email validator EUR 0.005. CV parser EUR 0.10. Insolvency EUR 0.05. Bundle EUR 49/mo (10K calls), EUR 199/mo (100K).

## Risk
- MEDIUM: Competition from free ANAF API and open-source. RapidAPI takes 20%. Need uptime infrastructure. ANAF data is public = hard to charge premium.

## Recommendation
GO. Start with 2 APIs (ANAF + company search) on RapidAPI. Near-zero launch cost. If 1K calls/month in 60 days, add remaining 3. Pan-European angle as differentiator.

## Sources
- https://openapi.ro/en
- https://console.openapi.com/apis/company/pricing
- https://www.alertacui.ro/verificare-monitorizare-firme/en/api/
- https://listafirme.eu/specificatii/api-info-v2.asp
- https://github.com/eranova-digital/datacore
- https://rapidapi.com/collection/company-information-apis
