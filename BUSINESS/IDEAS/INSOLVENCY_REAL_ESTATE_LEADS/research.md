# Research: INSOLVENCY REAL ESTATE LEADS (IDEA-132)
Date: 2026-04-16

## Description
Extract property listings from insolvent companies via BPI. Sell leads to RE investors. EUR 5-20/lead. 500/month = EUR 2,500-10,000.

## Market Size
- ~10,000 insolvency procedures/year in Romania
- ~30% involve RE assets = ~3,000 properties/year entering forced sale
- Coldwell Banker estimated EUR 500M in bankrupt RE projects (historical)
- RE investment market Romania: EUR 1.2B/year
- Target: ~2,000 active RE investors/flippers/fund managers in Romania

## Competitors
| Competitor | Type | Price | Notes |
|-----------|------|-------|-------|
| BPI/ONRC direct | Government | Free | Raw bulletins, hard to parse |
| MonitorBPI.ro | Alerts | Unknown | General insolvency, not RE-specific |
| Termene.ro | Platform | ~EUR 30-100/mo | Company monitoring, assets visible |
| RisCo.ro | Platform | ~EUR 50-200/mo | Financial + insolvency, not RE-focused |
| Licitatii-executari.ro | Auction portal | Free | Court-ordered sales, partial overlap |
| Imobiliare.ro | RE portal | Free/ads | Some auction listings, not systematic |
| RE agents (manual) | Manual | Commission | Some specialize in distressed |

## Our Advantage
- Already scraping BPI and monitoring insolvencies
- CIFN.eu portal exists (EU funds/insolvency alerts)
- Cross-reference insolvency with Trade Registry (property ownership)
- LLM extraction of property descriptions from BPI announcements
- No competitor offers curated "insolvency RE lead" product

## Validated?
PARTIALLY. Data source (BPI) proven and public. Investor interest real. No existing product = gap or insufficient demand. Test with 50 leads to 10 investors.

## Price
EUR 5/lead (basic). EUR 20/lead (enriched with value + liquidator). Subscription: EUR 99/mo (20 leads). EUR 299/mo unlimited.

## Risk
- MEDIUM: Not all insolvencies have RE. Property details sparse in BPI. GDPR considerations. Low conversion on encumbered properties.

## Recommendation
GO as automated side-project. LLM extracts property mentions from BPI, filters RE-relevant, enriches. Low build cost. Test with 10 investors. Integrate with CIFN.eu.

## Sources
- https://www.onrc.ro/index.php/en/content-structure/content-structure-13
- https://e-justice.europa.eu/topics/registers-business-insolvency-land/bankruptcy-and-insolvency-registers/ro_en
- https://www.romania-insider.com/coldwell-banker-expects-eur-500-mln-of-bankrupt-projects-in-romania-next-year
- https://monitorbpi.ro/
