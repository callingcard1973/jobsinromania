# Research: ANAF ENRICHMENT SERVICE (IDEA-066)
Date: 2026-04-16

## Description
Data enrichment service: client sends list of CUI (Romanian tax IDs) -> gets back ANAF data + email + phone + financial statements. EUR 0.05-0.20/record bulk.

## Market Size & Demand
- Romania has ~1.1M active companies (ONRC)
- Sales teams, debt collectors, due diligence firms, banks all need enriched company data
- B2B data enrichment is a $3B+ global market
- Romanian-specific enrichment is underserved by global players (ZoomInfo, Apollo don't cover RO well)

## Competitors Found

| Competitor | Price | Data Sources | Coverage | Notes |
|-----------|-------|-------------|----------|-------|
| OpenAPI.ro | 99-499 RON/mo (5K-100K req) | ANAF, ONRC, BNR | RO companies | ~EUR 0.001-0.004/request |
| Alerta CUI | Per-request (unknown) | ANAF, ONRC, Min Finance | RO companies + alerts | Monitoring focus |
| ListaFirme.eu | Free + premium | ANAF, ONRC, BPI | RO companies | Web-only, no bulk API |
| Romanian-Companies.eu | API available | Trade Register | RO companies | Basic company info |
| DataCore (GitHub) | Open source | ANAF APIs | RO financial data | Self-hosted option |
| GlobalDatabase | Custom (enterprise) | Multiple | EU-wide | EUR 0.05-0.50/record |
| Prospeo | ~$0.01/lead | Web scraping | Global | Email finding, not ANAF |
| People Data Labs | $0.05-0.10/credit | Multiple | Global | No Romanian specialty |
| Apollo | $49-149/mo | Multiple | Global | Weak on Romanian data |

## Our Advantage
- Already have 208M companies in PostgreSQL (including Romanian ANAF data)
- 440K emails already enriched in master database
- Enrichment scripts already running (ANAF, web scraping, pattern matching)
- Can add phone/email/financial data that OpenAPI.ro doesn't provide
- OpenAPI.ro charges EUR 0.001-0.004/request for basic ANAF data; we can charge EUR 0.05-0.20 for ENRICHED data (ANAF + email + phone + financials = 5x more value)

## Market Validated?
YES. OpenAPI.ro has paying customers at 99-499 RON/mo. Alerta CUI has a subscription base. GlobalDatabase charges enterprise prices. The market pays for Romanian company data enrichment. Gap: nobody offers ANAF + email + phone + financials in one API call.

## Price Point
- EUR 0.05-0.20/record is realistic for enriched data (ANAF + email + phone)
- OpenAPI.ro charges EUR 0.001/req for basic ANAF -- we offer 50x more data
- Tiered: Starter EUR 49/mo (1K lookups), Pro EUR 149/mo (5K), Business EUR 399/mo (25K)
- Bulk one-time: EUR 0.10/record for 10K+ records

## Risk
- MEDIUM. OpenAPI.ro is established and cheap for basic data.
- Email/phone enrichment accuracy varies -- web-scraped data may be stale.
- GDPR compliance needed for personal data (phones, emails).
- API infrastructure needed (hosting, docs, auth, billing).
- Support burden for data quality complaints.

## Recommendation
**LAUNCH** -- Strong position with 208M companies already in DB. Start simple: web form where client uploads CSV of CUIs, gets enriched CSV back within 24h. No API needed initially. Price at EUR 0.10/record minimum order 500 records (EUR 50 minimum). Test with 10 clients, then build API if demand confirmed.

## Sources
- [OpenAPI.ro](https://openapi.ro/en)
- [Alerta CUI API](https://www.alertacui.ro/verificare-monitorizare-firme/en/api/)
- [ListaFirme.eu](https://listafirme.eu/)
- [DataCore GitHub](https://github.com/eranova-digital/datacore)
- [GlobalDatabase Enrichment](https://www.globaldatabase.com/data-enrichment)
- [Prospeo Company Data APIs](https://prospeo.io/s/company-data-api)
