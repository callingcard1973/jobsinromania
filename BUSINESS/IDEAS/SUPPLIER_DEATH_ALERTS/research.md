# Research: SUPPLIER DEATH ALERTS (IDEA-119)
Date: 2026-04-16

## Description
Alert suppliers/creditors when their clients enter insolvency. Monitor BPI daily, cross-reference with client portfolios. EUR 49/month per subscriber.

## Market Size
- ~10,000 insolvency procedures opened annually in Romania
- ~200,000 SMEs with supplier relationships needing monitoring
- Global supply chain risk management: $4.3B (2025), growing 10%/year
- Romania: ~5,000 companies actively use monitoring (RisCo claims 300K monitored companies)

## Competitors
| Competitor | Type | Price | Notes |
|-----------|------|-------|-------|
| RisCo.ro | Full platform | ~EUR 50-200/mo | BPI + financial ratings + litigation |
| Termene.ro | Full platform | ~EUR 30-100/mo | 12 criteria, 300K companies monitored |
| MonitorBPI.ro | BPI-specific | Unknown | Insolvency bulletin only |
| MonitorizareFirme.ro | Portal | ~EUR 20-50/mo | BPI + financial changes |
| MonitorizareJuridica.ro | Legal alerts | Unknown | BPI + litigation |
| Coface InfoQuick | Enterprise | EUR 297/yr+ | Credit insurance + BPI |
| Creditsafe | Enterprise | $20K+/yr | Global, not Romania-focused |
| AlertaCUI.ro | API-first | Per-query | ANAF+ONRC+BPI via API |

## Our Advantage
- 208M companies in PostgreSQL + 770K Romanian companies
- BPI data is public (ONRC daily) - can scrape and cross-reference
- Undercut RisCo/Termene at EUR 49/mo for focused "death alert"
- Existing campaign infrastructure for notifications

## Validated?
YES. RisCo, Termene, Coface all profitable. BPI data free/public. 300K+ companies monitored across platforms. Need differentiator: simpler, cheaper, focused.

## Price
EUR 49/mo (500 companies). EUR 99/mo (unlimited). EUR 199/mo with risk scoring.

## Risk
- MEDIUM: Crowded market with established players
- BPI scraping may face ONRC restrictions
- Differentiation challenge vs RisCo/Termene

## Recommendation
GO with caution. Build as lightweight layer on existing DB. Differentiate with supplier-specific angle + lower price. Could be feature of larger platform.

## Sources
- https://www.risco.ro/en/produse/monitorizare
- https://monitorbpi.ro/
- https://solutii.termene.ro/monitorizare-firma
- https://monitorizarefirme.ro/
- https://www.creditsafe.com/us/en/credit-risk/credit-reports/company-monitoring.html
- https://www.infoquick.ro/home/bpi-buletinul-procedurilor-de-insolventa
