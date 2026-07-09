# Research: TELEGRAM LICITATII BOT (IDEA-044)
Date: 2026-04-16

## Description
Bot Telegram platit: 5.1M licitatii + TED monitor. Gratuit 3/zi, premium EUR 19/luna nelimitat + filtre. Paid Telegram bot delivering procurement/tender alerts from SEAP (Romania) and TED (EU) with freemium model.

## Market Size & Demand
- EU public procurement: EUR 2 trillion/year (~14% of EU GDP)
- TED above-threshold contracts: EUR 670B+/year
- Europe procurement software market: USD 3.18B in 2026
- TenderAlpha indexes 80M+ contract awards across 60+ countries
- Romania SEAP: ~100K+ active tenders/year, 50K+ registered suppliers

## Competitors Found

| Competitor | Type | Coverage | Price | Notes |
|------------|------|----------|-------|-------|
| Mercell | Web platform | Pan-European | Enterprise (custom quote) | Full procurement suite |
| TenderAlpha | Data/API | 60+ countries, 80M awards | Enterprise (FactSet partner) | Financial data focus |
| OpenTender.eu | Free portal | 35 EU jurisdictions | Free | Gov Transparency Institute |
| Licitatie.ro | Web platform | Romania SEAP | Free + premium | Romanian market leader |
| e-licitatie.ro | Government | Romania (SEAP) | Free | Official platform |
| BidDetail | Web platform | Global | Subscription | Aggregator |
| TendersInfo | Web platform | Global | Subscription | 100+ countries |
| BotSubscription | Bot platform | N/A | Free to EUR 85/mo, then 1% | Telegram payment infra |

## Our Advantage
- **5.1M tenders already in database** (SEAP + TED scraped in PostgreSQL)
- **TED monitor already running** (cron 7:30 AM daily)
- **Telegram infrastructure ready**: 6 channels operational
- **Freemium model**: 3 free/day hooks users, EUR 19/mo converts serious bidders
- **Niche**: No one does Telegram-native tender alerts for SEAP + TED combined
- **Low cost**: BotSubscription charges only 1% after EUR 85/mo revenue

## Market Validated?
YES -- Mercell, Licitatie.ro, TendersInfo are profitable. Demand for tender alerts proven. Telegram delivery is the innovation -- no major competitor uses it. Target: 50K+ Romanian SEAP suppliers.

## Price Point
- Free tier: 3 alerts/day (keyword match)
- Premium: EUR 19/mo unlimited + custom filters + saved searches
- Enterprise: EUR 49/mo API access + export
- Target: 200-500 paying users = EUR 3,800-9,500/mo recurring
- Payment: Telegram Stars or Stripe via BotSubscription

## Risk
- MEDIUM -- Telegram bot monetization is emerging; conversion rates unknown
- e-licitatie.ro (free government platform) covers basic needs
- Licitatie.ro is established web competitor
- Telegram B2B adoption in Romania: growing but not dominant
- Must maintain scrapers for SEAP + TED continuously

## Recommendation
BUILD MVP. Data (5.1M tenders) and infrastructure (TED monitor, Telegram bots) already exist. Build simple bot: keyword subscribe, 3 free/day, EUR 19/mo premium via BotSubscription. Test with 100 Romanian construction/food companies from existing contacts. If 10+ convert in month 1, scale. Time to MVP: 3-5 days.

## Sources
- [Mercell - Tender Discovery](https://www.mercell.com/en/67077931/tender-offer.aspx)
- [TenderAlpha - Open Government Tenders](https://www.tenderalpha.com/products/open-tenders/)
- [OpenTender.eu](https://opentender.eu/)
- [BotSubscription - Telegram Subscription Bot](https://botsubscription.com/)
- [Euronews - EU Procurement EUR 2 Trillion](https://www.euronews.com/business/2024/05/06/europes-public-procurement-market-an-untapped-potential-of-2-trillion)
- [MarketDataForecast - Europe Procurement Software](https://www.marketdataforecast.com/market-reports/europe-procurement-software-market)
- [Jorpex - Public Procurement Statistics 2026](https://jorpex.com/guides/public-procurement-statistics-2026/)
