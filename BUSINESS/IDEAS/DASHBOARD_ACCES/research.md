# Research: DASHBOARD ACCES (IDEA-047)
Date: 2026-04-16

## Description
Sell subscription access to live dashboard combining insolvency data (770K companies), TED procurement alerts, and SEAP public procurement. EUR 49-199/month instead of one-shot CSV sales.

## Market Size & Demand
- Global BI market: $33B+ (2025), growing 10%+ CAGR
- Procurement intelligence platforms (Suplari, Beroe): enterprise pricing $10K-100K/yr
- TED alert services: EUR 5/day (~EUR 150/month) for basic alerts (tenders.eu)
- Romania-specific: RisCo, Termene.ro, ListaFirme.eu all offer paid monitoring
- RisCo API: minimum 100 RON/month (~EUR 20); alert subscriptions are paid
- SME certification (Excellent SME Romania): 297 EUR/year

## Competitors Found
| Competitor | Focus | Pricing | Market |
|-----------|-------|---------|--------|
| RisCo.ro | RO insolvency + company alerts | ~100 RON/mo+ | Romania |
| Termene.ro | RO court deadlines + company data | Freemium + paid | Romania |
| ListaFirme.eu | RO company directory + insolvency | Free + premium | Romania |
| Coface | Credit insurance + monitoring | Enterprise (EUR 1K+/yr) | Global |
| CreditReform | Credit reports + debt collection | Per-report + subscription | EU |
| Tenders.eu (TENDERTRACK) | EU TED alerts | ~EUR 150/month | EU |
| TenderAlerts.eu | EU procurement search | Free beta, Pro coming | EU |
| Suplari | Procurement intelligence | Enterprise ($10K+/yr) | Global |

## Our Advantage
- Already have 770K insolvency records + 222K bankruptcies + ANAF live feed
- TED scraper already running (370K+ exports)
- SEAP monitoring already built
- Combined view (insolvency + procurement + ANAF) is UNIQUE - no competitor offers all three in one dashboard
- Low price point (EUR 49-199) vs enterprise competitors (EUR 1K+)
- Already have Node-RED dashboard infrastructure on raspibig

## Market Validated?
YES. RisCo, Termene.ro, and Coface all have paying customers for subsets of this data. TED alert services charge EUR 150/month for procurement-only alerts. Combining all three data sources at SME-friendly pricing fills a clear gap.

## Price Point
- EUR 49/month: Insolvency alerts only (email daily digest)
- EUR 99/month: Insolvency + TED procurement alerts + basic dashboard
- EUR 199/month: Full dashboard (insolvency + TED + SEAP + ANAF) + API access + CSV export
- Annual discount: 2 months free

## Risk
- MEDIUM. Data quality and freshness are critical - stale data kills trust fast
- Legal: GDPR compliance needed for company monitoring data
- Support burden: B2B subscribers expect reliability and responsiveness
- Competition from RisCo/Termene who have established brand trust in Romania

## Recommendation
GO. Strong differentiation by combining 3 data sources no one else bundles at SME pricing. Start with EUR 49/month insolvency-only tier on cifn.eu (already has the domain and some content). Add procurement tier once 20+ paying subscribers validate demand.

## Sources
- [RisCo Insolvency Alerts](https://www.risco.ro/en/alerte-buletinul-insolventei)
- [Termene.ro Company Data](https://termene.ro/firme)
- [TENDERTRACK EU Alerts](https://www.tenders.eu/)
- [TenderAlerts.eu](https://tenderalerts.eu/)
- [Coface Romania](https://www.coface.ro/en/about-us/coface-in-romania)
- [CreditReform Romania](https://www.creditreform.com/en/contact/creditreform-romania)
