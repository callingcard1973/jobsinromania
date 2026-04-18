# Research: MADR LAND INVESTOR DATA (IDEA-070)
Date: 2026-04-16

## Description
9,658 agricultural land listings across 36 Romanian counties + monthly CMA (Comparative Market Analysis). Subscription service EUR 99-299/month targeting farmland investment funds and real estate investors.

## Market Size
- Romania has 8.5M hectares of agricultural land, average price 43,280 lei/ha (2024)
- Foreign investors control up to 10% of Romanian agricultural land
- Eurostat publishes EU-wide agricultural land price data (free but delayed, no granularity)
- Global agricultural data market growing, but Romania-specific farmland analytics is a gap

## Competitors
| Competitor | What | Price | Weakness |
|-----------|------|-------|----------|
| INSSE (National Statistics) | Annual average land prices by region | Free (PDF) | Delayed 12+ months, no listing-level data |
| Eurostat | EU-wide land price/rent statistics | Free | No Romania granularity, no individual listings |
| investmentsinromania.eu | Farm listings portal | Free listings | No analytics, no CMA, small inventory |
| Viviun | Romania farm/land listings aggregator | Free browse | No pricing analytics, no subscription tier |
| DealStream | Farm listings marketplace | Free browse | US-focused, minimal Romania data |
| Savills/Knight Frank | Farmland advisory reports | EUR 500-5,000/report | Focus on Western EU, minimal Romania |
| Datarade agricultural providers | Various ag datasets | $500-5,000+ | No Romania-specific land transaction data |

## Our Advantage
- 9,658 real MADR listings (government source, nobody else aggregates this)
- 36 counties = full national coverage
- Monthly CMA updates = time-series pricing intelligence
- Already built: scraper + database + agroevolution.com/harta.php map
- Zero competition for Romania-specific farmland subscription analytics
- 5 hours to productize (data already exists)

## Validated?
Partially. Investment funds (Mozaik Investments, Holde Agri, NCH Capital) actively buy Romanian farmland and need pricing data. No direct customer validation yet. INSSE data is free but unusable for deal-level analysis.

## Price
- Basic (county reports): EUR 99/month
- Pro (all counties + CMA + alerts): EUR 199/month
- Enterprise (API + custom reports): EUR 299/month

## Risk
- LOW: Data already exists, minimal development needed
- MADR may restrict scraping or change format
- Small addressable market in Romania (maybe 50-200 potential subscribers)
- Revenue ceiling: EUR 2,000-8,000/month realistically

## Recommendation
**GO** - Low effort (5h), unique data asset, no competition. Start with a landing page on agroevolution.com and email 50 known farmland investment funds. Even 20 subscribers at EUR 199 = EUR 3,980/month.

## Sources
- [INSSE Agricultural Land Prices 2024](https://insse.ro/cms/sites/default/files/com_presa/com_pdf/pta2024e.pdf)
- [Eurostat Land Prices and Rents](https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Agricultural_land_prices_and_rents_-_statistics)
- [Datarade Agricultural Data Providers](https://datarade.ai/data-categories/agricultural-data/providers)
- [Romania Agricultural Products - Trade.gov](https://www.trade.gov/country-commercial-guides/romania-agricultural-products)
