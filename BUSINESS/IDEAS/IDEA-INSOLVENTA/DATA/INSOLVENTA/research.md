# Research: INSOLVENTA (IDEA-003)
Date: 2026-04-16

## Description
Insolvency alert service targeting 17K accountants (CECCAR) + 1,850 auditors (CAFR) in Romania. EUR 19/month subscription for automated BPI (Buletinul Procedurilor de Insolventa) monitoring and alerts.

## Market Size & Demand
- CECCAR has ~33,278 members (expert + licensed accountants, 2023 data)
- CAFR has ~4,570 financial auditors
- Total addressable: ~37,800 professionals who need insolvency monitoring daily
- 7,553 new insolvency proceedings opened in Romania in 2025, trend rising in 2026
- Global insolvency software market: USD 1.5B (2023) growing to USD 2.4B by 2028 (CAGR 10.4%)
- If 5% of target converts at EUR 19/mo = ~1,890 subscribers = EUR 35,910/month

## Competitors Found

| Name | Type | Focus | Pricing |
|------|------|-------|---------|
| RisCo.ro | SaaS platform | Daily insolvency alerts, credit reports, BPI monitoring | ~5,000 RON/mo (~EUR 1,000) for full insolvency alerts |
| Termene.ro | SaaS platform | Company monitoring (12 criteria), insolvency deadlines | Custom pricing, 300K+ companies monitored |
| AlertaCUI.ro | SaaS platform | CUI-based monitoring: insolvency, fiscal, ONRC changes | Tiered by company count (50-1000), pricing hidden |
| ListaFirme.eu | Freemium portal | Free monitoring with paid access packages, insolvency lists | Free basic + paid packages |
| Wolters Kluwer Sintact | Enterprise SaaS | Legal + financial analysis, insolvency/pre-insolvency module | Enterprise pricing (expensive) |
| MonitorizareJuridica.ro | Email alerts | BPI monitoring, insolvency + litigation alerts | Unknown |
| MonitorizareFirme.ro | Portal | Company changes, insolvency status | Unknown |
| MonitorBPI.ro | Niche tool | Focused specifically on BPI (insolvency bulletin) | Unknown |

## Our Advantage
- **Price disruption**: Competitors charge EUR 100-1,000+/month. We offer EUR 19/month — 5-50x cheaper
- **Target audience**: Direct access to 17K+ accountants and 1,850 auditors via email campaigns (already have infrastructure)
- **Data already available**: BPI is public data published by ONRC, can be scraped/parsed automatically
- **Tech stack ready**: Email infrastructure (6,300/day capacity), PostgreSQL, LLM for enrichment
- **Low build effort**: 8 hours estimated — parse BPI daily, match against subscriber watchlists, send email alerts

## Market Validated? YES
- Multiple established competitors (RisCo, Termene, AlertaCUI) prove paying demand exists
- 300K+ companies already monitored on Termene.ro alone
- Rising insolvency trend (3.8% increase in 2025) increases urgency for monitoring
- Accountants/auditors have legal obligation to monitor client solvency status
- BPI is mandatory reading for insolvency practitioners

## Price Point
- EUR 19/month is aggressive undercut vs competitors (RisCo at ~EUR 1,000/mo for similar)
- Risk: may be TOO cheap, could price at EUR 29-49/mo and still massively undercut
- Freemium model possible: 5 companies free, unlimited at EUR 19/mo

## Risk
- **Low barrier to entry** — BPI data is public, competitors could match price
- **RisCo/Termene are established** with brand recognition among accountants
- **Customer support burden** — accountants expect responsiveness
- **GDPR compliance** needed for subscriber data
- **Churn risk** — accountants may cancel after checking a few clients

## Recommendation: LAUNCH
Strong market validation, massive price advantage, low build effort (8h), existing email infrastructure to reach target audience. Start with MVP (daily BPI email digest) and iterate.

## Sources
- [RisCo Insolvency Alerts](https://www.risco.ro/en/alerte-zilnice-insolventa)
- [RisCo Products & Pricing](https://www.risco.ro/en/produse)
- [AlertaCUI Monitoring](https://www.alertacui.ro/monitorizare-firme/tarife/)
- [Termene.ro Monitoring](https://solutii.termene.ro/monitorizare-firma)
- [Wolters Kluwer Sintact](https://info.wolterskluwer.ro/insolventa-si-preinsolventa/)
- [ListaFirme Monitoring](https://listafirme.eu/monitorizare.asp)
- [MonitorizareJuridica.ro](https://monitorizarejuridica.ro/)
- [CECCAR Members - Accountancy Europe](https://accountancyeurope.eu/fact-figure/romania/)
- [CAFR Romania](https://www.cafr.ro/en/)
- [Coface Insolvency Report 2025](https://www.romania-insider.com/coface-insolvencies-march-2026)
- [Insolvency Software Market](https://www.marketsandmarkets.com/Market-Reports/insolvency-software-market-217636399.html)
- [EU Insolvency Registers](https://e-justice.europa.eu/topics/registers-business-insolvency-land/bankruptcy-and-insolvency-registers/ro_en)
